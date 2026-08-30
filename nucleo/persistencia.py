"""
nucleo/persistencia.py

Capa de serialización y persistencia SQLite del estado de simulación.
Gestiona el guardado y carga incremental de crónica y snapshots atómicos de:
  - Entidades biológicas (criaturas vivas)
  - Entidades vegetales (flora)
  - Entidades inertes (necromasa / detritos orgánicos)
  - Celdas y estado del generador pseudoaleatorio (RNG)
"""

from __future__ import annotations

import dataclasses
import json
import pickle
import random
import sqlite3
import sys
from pathlib import Path
from typing import Any

from componentes.capacidad_mental import CapacidadMental
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.gestacion import Gestacion
from componentes.identidad import Especie, Identidad
from componentes.intencion import Accion, Intencion
from componentes.memoria_espacial import MemoriaEspacial
from componentes.necesidades import Necesidades
from componentes.necromasa import Necromasa
from componentes.planta import Planta
from componentes.pool_fisico import PoolFisico
from componentes.pool_mental import PoolMental
from componentes.posicion import Posicion
from componentes.reproduccion import Reproduccion, Sexo
from componentes.temperamento import Temperamento
from nucleo.celda import Celda
from nucleo.entidad import GestorEntidades
from nucleo.eventos import BusEventos, Evento, Severidad
from nucleo.mundo import Mundo
from nucleo.reloj import Reloj

def _serializar_snapshot_padre(gest: Gestacion | None) -> dict[str, Any]:
    """
    Convierte la instantánea del padre guardada en Gestacion (dimensiones_
    padre, temperamento_padre, capacidad_mental_padre, duracion_gestacion_
    padre, tamano_camada) en un dict serializable a JSON.

    CORRECCIÓN (2026-08-23): esta función y su inversa (_reconstruir_
    gestacion, más abajo) reemplazan un guardado/carga que leía/escribía
    gest.padre_id y gest.padre_snapshot -- campos que Gestacion nunca tuvo
    en su forma actual (ver componentes/gestacion.py: es id_padre, y en
    vez de un único snapshot genérico tiene cuatro campos tipados más
    tamano_camada). Nunca se detectó en producción porque main.py no
    invoca guardar_snapshot/cargar_snapshot -- se encontró auditando el
    código, no por una excepción real. tick_inicio e id_padre SÍ tienen
    sus propias columnas (no van aquí); todo lo demás de la instantánea
    del padre se empaqueta en un único blob JSON, igual que antes,
    evitando así añadir columnas nuevas.
    """
    if gest is None:
        return {}
    return {
        "dimensiones_padre": dataclasses.asdict(gest.dimensiones_padre),
        "temperamento_padre": dataclasses.asdict(gest.temperamento_padre),
        "capacidad_mental_padre": dataclasses.asdict(gest.capacidad_mental_padre),
        "duracion_gestacion_padre": gest.duracion_gestacion_padre,
        "tamano_camada": gest.tamano_camada,
    }


def _reconstruir_gestacion(tick_inicio: int, id_padre: int, snapshot: dict[str, Any]) -> Gestacion:
    """Inversa de _serializar_snapshot_padre -- ver su docstring."""
    return Gestacion(
        tick_inicio=tick_inicio,
        id_padre=id_padre,
        dimensiones_padre=DimensionesFisicas(**snapshot["dimensiones_padre"]),
        temperamento_padre=Temperamento(**snapshot["temperamento_padre"]),
        capacidad_mental_padre=CapacidadMental(**snapshot["capacidad_mental_padre"]),
        duracion_gestacion_padre=snapshot["duracion_gestacion_padre"],
        tamano_camada=snapshot["tamano_camada"],
    )


VERSION_ESQUEMA = "0.23-fase0"

_TABLAS_APP = (
    "entidades",
    "componentes_estado",
    "plantas_estado",
    "necromasa_estado",
    "celdas_estado",
    "cronica_eventos",
    "configuracion_ejecucion",
)


class Persistencia:
    """Gestiona la base de datos SQLite para snapshots y crónica histórica.

    Versionado de esquema (2026-08-23, feedback ya registrado en memoria del
    proyecto: "cambio de esquema exige DROP TABLE, no DELETE FROM"):
    `CREATE TABLE IF NOT EXISTS` nunca migra columnas -- si el código cambia
    la forma de una tabla (como pasó hoy con componentes_estado y
    configuracion_ejecucion, verificado con PRAGMA table_info contra un
    datos/bosque.db real que llevaba varios días de desfase), una base de
    datos ya existente se queda con el esquema VIEJO para siempre, y
    cualquier INSERT/SELECT contra las columnas nuevas falla en tiempo de
    ejecución. Antes de crear las tablas, se compara VERSION_ESQUEMA contra
    lo que ya hay guardado; si no coincide (o la tabla de control ni
    siquiera existe todavía, o existe con columnas de una versión anterior
    a este propio versionado), se hace DROP explícito de las siete tablas
    de la aplicación antes de recrearlas. No hay migración de datos entre
    versiones de esquema -- en esta fase del proyecto (todavía sin
    campañas reales que conservar) perder una partida guardada al cambiar
    el modelo de datos es aceptable; lo que NO es aceptable es que la app
    siga funcionando en apariencia mientras escribe o lee contra columnas
    equivocadas.
    """

    def __init__(self, ruta_db: Path) -> None:
        self.ruta_db = ruta_db
        self.ruta_db.parent.mkdir(parents=True, exist_ok=True)
        self._inicializar_tablas()

    def _conectar(self) -> sqlite3.Connection:
        return sqlite3.connect(self.ruta_db)

    def _version_desactualizada(self, cur: sqlite3.Cursor) -> bool:
        """True si hay que purgar el esquema antes de (re)crear las tablas:
        la tabla de control no existe, existe pero con columnas de una
        versión anterior a este versionado (OperationalError), o su valor
        guardado no coincide con VERSION_ESQUEMA."""
        try:
            cur.execute("SELECT valor FROM configuracion_ejecucion WHERE clave = 'version_esquema'")
            fila = cur.fetchone()
            return fila is None or fila[0] != VERSION_ESQUEMA
        except sqlite3.OperationalError:
            return True

    def _purgar_esquema_anterior(self, cur: sqlite3.Cursor) -> None:
        for tabla in _TABLAS_APP:
            cur.execute(f"DROP TABLE IF EXISTS {tabla}")

    def _inicializar_tablas(self) -> None:
        """Crea el esquema relacional si no existe, purgando primero
        cualquier versión anterior incompatible (ver docstring de la clase)."""
        with self._conectar() as con:
            cur = con.cursor()

            if self._version_desactualizada(cur):
                self._purgar_esquema_anterior(cur)
                con.commit()

            # 1. Registro permanente de entidades históricas
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS entidades (
                    id INTEGER PRIMARY KEY,
                    especie TEXT NOT NULL,
                    nombre TEXT,
                    viva BOOLEAN NOT NULL,
                    tick_nacimiento INTEGER NOT NULL,
                    id_madre INTEGER,
                    id_padre INTEGER
                )
                """
            )

            # 2. Snapshot de criaturas vivas
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS componentes_estado (
                    entidad_id INTEGER PRIMARY KEY,
                    x INTEGER NOT NULL,
                    y INTEGER NOT NULL,
                    saciedad REAL NOT NULL,
                    energia REAL NOT NULL,
                    seguridad REAL NOT NULL,
                    hidratacion REAL NOT NULL,
                    aliviado REAL NOT NULL,
                    oxigenacion REAL NOT NULL,
                    confort_termico REAL NOT NULL,
                    impulso_reproductivo REAL NOT NULL,
                    peso REAL NOT NULL,
                    altura REAL NOT NULL,
                    longevidad REAL NOT NULL,
                    fuerza REAL NOT NULL,
                    agilidad REAL NOT NULL,
                    velocidad REAL NOT NULL,
                    resistencia_enfermedad REAL NOT NULL,
                    agudeza_sensorial REAL NOT NULL,
                    vitalidad_maxima REAL NOT NULL,
                    resistencia_maxima REAL NOT NULL,
                    curacion REAL NOT NULL,
                    recuperacion REAL NOT NULL,
                    vitalidad REAL NOT NULL,
                    resistencia REAL NOT NULL,
                    valentia REAL NOT NULL,
                    sociabilidad REAL NOT NULL,
                    agresividad REAL NOT NULL,
                    dominancia REAL NOT NULL,
                    empatia REAL NOT NULL,
                    lealtad REAL NOT NULL,
                    fe REAL NOT NULL,
                    curiosidad REAL NOT NULL,
                    inteligencia REAL NOT NULL,
                    memoria REAL NOT NULL,
                    voluntad REAL NOT NULL,
                    resiliencia REAL NOT NULL,
                    estabilidad_mental_maxima REAL NOT NULL,
                    consciencia REAL NOT NULL,
                    estabilidad REAL NOT NULL,
                    sexo TEXT NOT NULL,
                    duracion_gestacion_dias REAL NOT NULL,
                    tick_inicio_gestacion INTEGER,
                    gestacion_padre_id INTEGER,
                    gestacion_padre_snapshot TEXT,
                    recuerdos TEXT
                )
                """
            )

            # 3. Snapshot de flora
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS plantas_estado (
                    entidad_id INTEGER PRIMARY KEY,
                    x INTEGER NOT NULL,
                    y INTEGER NOT NULL,
                    especie TEXT NOT NULL,
                    etapa REAL NOT NULL
                )
                """
            )

            # 4. Snapshot de necromasa. masas (2026-08-30, CÍRCULO 2 de
            # materiales físicos): antes columna masa_organica REAL única;
            # ahora JSON de {material: kg} -- mismo patrón que
            # celdas_estado.recursos mas abajo (dict serializado, no una
            # columna por material). VERSION_ESQUEMA subida para que un
            # esquema anterior se purgue y recree en vez de fallar leyendo
            # una columna que ya no existe.
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS necromasa_estado (
                    entidad_id INTEGER PRIMARY KEY,
                    x INTEGER NOT NULL,
                    y INTEGER NOT NULL,
                    masas TEXT NOT NULL,
                    agua_tisular REAL NOT NULL,
                    tasa_putrefaccion REAL NOT NULL,
                    origen_especie TEXT NOT NULL
                )
                """
            )

            # 5. Snapshot dinámico de celdas
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS celdas_estado (
                    x INTEGER NOT NULL,
                    y INTEGER NOT NULL,
                    fertilidad REAL NOT NULL,
                    profundidad_charco REAL NOT NULL,
                    en_llamas BOOLEAN NOT NULL,
                    recursos TEXT NOT NULL,
                    tiene_recurso BOOLEAN NOT NULL,
                    tipo_recurso TEXT NOT NULL,
                    PRIMARY KEY (x, y)
                )
                """
            )

            # 6. Crónica de eventos (incremental)
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS cronica_eventos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tick INTEGER NOT NULL,
                    tipo TEXT NOT NULL,
                    severidad TEXT NOT NULL,
                    entidad_id INTEGER,
                    datos TEXT
                )
                """
            )

            # 7. Configuración y generador RNG
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS configuracion_ejecucion (
                    clave TEXT PRIMARY KEY,
                    valor BLOB
                )
                """
            )
            # Registrar la versión ya aquí (no solo al primer guardar_snapshot):
            # una base de datos recién creada que nunca llega a guardar una
            # partida no debería purgarse en cada arranque solo porque la
            # tabla de control está vacía.
            cur.execute(
                "REPLACE INTO configuracion_ejecucion VALUES ('version_esquema', ?)",
                (VERSION_ESQUEMA,),
            )
            con.commit()

    def registrar_entidad_nueva(self, entidad_id: int, datos: dict[str, Any]) -> None:
        """Registra una entidad recién nacida en la tabla histórica."""
        with self._conectar() as con:
            cur = con.cursor()
            cur.execute(
                """
                INSERT OR REPLACE INTO entidades (id, especie, nombre, viva, tick_nacimiento, id_madre, id_padre)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entidad_id,
                    datos.get("especie", ""),
                    datos.get("nombre"),
                    True,
                    datos.get("tick_nacimiento", 0),
                    datos.get("id_madre"),
                    datos.get("id_padre"),
                ),
            )
            con.commit()

    def persistir_eventos(self, eventos: list[Evento]) -> None:
        """Persiste eventos notables e históricos."""
        filas = [
            (
                ev.tick,
                ev.tipo,
                ev.severidad.value,
                ev.entidad_id,
                json.dumps(ev.datos) if ev.datos else None,
            )
            for ev in eventos
            if ev.severidad in (Severidad.NOTABLE, Severidad.HISTORICO)
        ]
        if not filas:
            return
        with self._conectar() as con:
            cur = con.cursor()
            cur.executemany(
                """
                INSERT INTO cronica_eventos (tick, tipo, severidad, entidad_id, datos)
                VALUES (?, ?, ?, ?, ?)
                """,
                filas,
            )
            con.commit()

    def guardar_snapshot(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        reloj: Reloj,
        rng_juego: random.Random,
        semilla: int,
    ) -> None:
        """Serializa el estado completo en una transacción atómica.

        semilla (2026-08-23): la semilla de generación de mundo NUNCA se
        persistía -- cargar_snapshot solo restaura el estado DINÁMICO de
        celda (fertilidad, charcos, fuego, recursos); el TERRENO en sí
        (tipo de bioma, elevación) lo regenera Mundo() a partir de la
        semilla de config en cada arranque. Si esa semilla cambia entre
        guardar y cargar, el terreno regenerado no coincide con el que
        produjo el estado dinámico guardado, y hasta ahora eso pasaba en
        silencio. Guardarla aquí permite que cargar_snapshot lo detecte y
        avise -- ver su propio docstring."""
        zona = mundo.territorio.zonas[0]

        with self._conectar() as con:
            cur = con.cursor()

            # A. Criaturas
            cur.execute("DELETE FROM componentes_estado")
            filas_criaturas = []
            for eid in sorted(gestor.entidades_con(Identidad, Posicion, Necesidades, DimensionesFisicas)):
                pos = gestor.obtener_componente(eid, Posicion)
                nec = gestor.obtener_componente(eid, Necesidades)
                dims = gestor.obtener_componente(eid, DimensionesFisicas)
                pf = gestor.obtener_componente(eid, PoolFisico)
                temp = gestor.obtener_componente(eid, Temperamento)
                cm = gestor.obtener_componente(eid, CapacidadMental)
                pm = gestor.obtener_componente(eid, PoolMental)
                rep = gestor.obtener_componente(eid, Reproduccion)
                gest = gestor.obtener_componente(eid, Gestacion)
                mem = gestor.obtener_componente(eid, MemoriaEspacial)

                if pos and nec and dims and pf and temp and cm and pm and rep:
                    filas_criaturas.append(
                        (
                            eid,
                            pos.x,
                            pos.y,
                            nec.saciedad,
                            nec.energia,
                            nec.seguridad,
                            nec.hidratacion,
                            nec.aliviado,
                            nec.oxigenacion,
                            nec.confort_termico,
                            nec.impulso_reproductivo,
                            dims.peso,
                            dims.altura,
                            dims.longevidad,
                            dims.fuerza,
                            dims.agilidad,
                            dims.velocidad,
                            dims.resistencia_enfermedad,
                            dims.agudeza_sensorial,
                            dims.vitalidad_maxima,
                            dims.resistencia_maxima,
                            dims.curacion,
                            dims.recuperacion,
                            pf.vitalidad,
                            pf.resistencia,
                            temp.valentia,
                            temp.sociabilidad,
                            temp.agresividad,
                            temp.dominancia,
                            temp.empatia,
                            temp.lealtad,
                            temp.fe,
                            temp.curiosidad,
                            cm.inteligencia,
                            cm.memoria,
                            cm.voluntad,
                            cm.resiliencia,
                            cm.estabilidad_mental_maxima,
                            cm.consciencia,
                            pm.estabilidad,
                            rep.sexo.value,
                            rep.duracion_gestacion_dias,
                            gest.tick_inicio if gest else None,
                            gest.id_padre if gest else None,
                            json.dumps(_serializar_snapshot_padre(gest)) if gest else None,
                            json.dumps(mem.recuerdos) if mem else None,
                        )
                    )
            cur.executemany(
                """
                INSERT INTO componentes_estado VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?
                )
                """,
                filas_criaturas,
            )

            # B. Flora
            cur.execute("DELETE FROM plantas_estado")
            filas_flora = []
            for pid in sorted(gestor.entidades_con(Planta, Posicion)):
                planta = gestor.obtener_componente(pid, Planta)
                pos_p = gestor.obtener_componente(pid, Posicion)
                if planta and pos_p:
                    filas_flora.append((pid, pos_p.x, pos_p.y, planta.especie, planta.etapa))
            cur.executemany("INSERT INTO plantas_estado VALUES (?, ?, ?, ?, ?)", filas_flora)

            # C. Necromasa
            cur.execute("DELETE FROM necromasa_estado")
            filas_necromasa = []
            for nid in sorted(gestor.entidades_con(Necromasa, Posicion)):
                nec_comp = gestor.obtener_componente(nid, Necromasa)
                pos_n = gestor.obtener_componente(nid, Posicion)
                if nec_comp and pos_n:
                    filas_necromasa.append(
                        (
                            nid,
                            pos_n.x,
                            pos_n.y,
                            json.dumps(nec_comp.masas),
                            nec_comp.agua_tisular,
                            nec_comp.tasa_putrefaccion,
                            nec_comp.origen_especie,
                        )
                    )
            cur.executemany("INSERT INTO necromasa_estado VALUES (?, ?, ?, ?, ?, ?, ?)", filas_necromasa)

            # D. Celdas dinámicas
            cur.execute("DELETE FROM celdas_estado")
            filas_celdas = []
            for y in range(zona.alto):
                for x in range(zona.ancho):
                    celda = zona.obtener_celda(x, y)
                    filas_celdas.append(
                        (
                            x,
                            y,
                            celda.fertilidad,
                            celda.profundidad_charco,
                            celda.en_llamas,
                            json.dumps(celda.recursos),
                            celda.tiene_recurso,
                            celda.tipo_recurso,
                        )
                    )
            cur.executemany("INSERT INTO celdas_estado VALUES (?, ?, ?, ?, ?, ?, ?, ?)", filas_celdas)

            # E. Metadatos de ejecución y RNG
            cur.execute("REPLACE INTO configuracion_ejecucion VALUES ('tick_actual', ?)", (reloj.tick_actual,))
            cur.execute("REPLACE INTO configuracion_ejecucion VALUES ('version_esquema', ?)", (VERSION_ESQUEMA,))
            cur.execute("REPLACE INTO configuracion_ejecucion VALUES ('semilla', ?)", (semilla,))
            cur.execute(
                "REPLACE INTO configuracion_ejecucion VALUES ('rng_juego_state', ?)",
                (pickle.dumps(rng_juego.getstate()),),
            )

            con.commit()

    def cargar_snapshot(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        reloj: Reloj,
        rng_juego: random.Random,
        semilla: int,
    ) -> bool:
        """Restaura el estado completo desde la base de datos.

        semilla (2026-08-23, ver docstring de guardar_snapshot): se
        compara contra la guardada en la propia partida. El terreno
        (bioma, elevación, ríos) NO se persiste -- lo regenera Mundo() a
        partir de la semilla de config en cada arranque, antes de que se
        llame a esta función. Si la semilla actual no coincide con la que
        generó el terreno sobre el que se guardó el estado dinámico de
        celda, el mundo resultante mezcla un terreno nuevo con recursos/
        fertilidad/charcos de otro terreno -- inconsistente, aunque no
        impide cargar. Se avisa por stderr en vez de fallar en silencio o
        bloquear la carga: no hay overhead de UI de por medio (nucleo/ no
        importa nada de presentacion/) y un guardado antiguo sigue siendo
        mejor que ninguno, incluso si el terreno ya no encaja."""
        zona = mundo.territorio.zonas[0]

        with self._conectar() as con:
            cur = con.cursor()

            cur.execute("SELECT valor FROM configuracion_ejecucion WHERE clave = 'tick_actual'")
            fila_tick = cur.fetchone()
            if not fila_tick:
                return False

            cur.execute("SELECT valor FROM configuracion_ejecucion WHERE clave = 'semilla'")
            fila_semilla = cur.fetchone()
            if fila_semilla is not None and int(fila_semilla[0]) != int(semilla):
                print(
                    f"[persistencia] AVISO: la partida guardada se generó con "
                    f"semilla={fila_semilla[0]}, pero la configuración actual usa "
                    f"semilla={semilla}. El terreno se ha regenerado con la semilla "
                    f"actual y NO coincide con el que produjo el estado dinámico de "
                    f"celda (fertilidad, charcos, fuego, recursos) que se va a "
                    f"cargar. La carga continúa, pero el mundo resultante puede ser "
                    f"inconsistente.",
                    file=sys.stderr,
                )
            # CORRECCIÓN (2026-08-23): Reloj.tick_actual es un atributo de
            # instancia plano fijado en __init__ (nucleo/reloj.py), NO una
            # property respaldada por _tick_actual -- escribir en
            # reloj._tick_actual creaba un atributo nuevo sin efecto real,
            # dejando el reloj congelado en tick 0 tras cada carga aunque
            # cargar_snapshot devolviera True. Bug preexistente, no
            # introducido en la reescritura de hoy; detectado al probar el
            # roundtrip guardar/cargar por primera vez (nunca se había
            # ejecutado antes porque main.py no llamaba a cargar_snapshot).
            reloj.tick_actual = int(fila_tick[0])

            cur.execute("SELECT valor FROM configuracion_ejecucion WHERE clave = 'rng_juego_state'")
            fila_rng = cur.fetchone()
            if fila_rng:
                rng_juego.setstate(pickle.loads(fila_rng[0]))

            # Limpiar gestor en memoria
            for eid in list(gestor.entidades_con(Posicion)):
                gestor.eliminar_entidad(eid)

            # 1. Cargar celdas
            cur.execute(
                "SELECT x, y, fertilidad, profundidad_charco, en_llamas, recursos, "
                "tiene_recurso, tipo_recurso FROM celdas_estado"
            )
            for x, y, fert, prof_ch, fuego, rec_json, tiene_rec, tipo_rec in cur.fetchall():
                celda = zona.obtener_celda(x, y)
                celda.fertilidad = float(fert)
                celda.profundidad_charco = float(prof_ch)
                celda.en_llamas = bool(fuego)
                celda.recursos = json.loads(rec_json)
                # CORRECCIÓN (2026-08-23): tiene_recurso/tipo_recurso tienen
                # su propio docstring en nucleo/celda.py afirmando "SI se
                # persiste" -- hasta ahora no había columnas para ellos y se
                # perdían en cada carga, quedando siempre en su valor por
                # defecto (False/""), inconsistente con celda.recursos ya
                # restaurado. Sin consumidor real todavía (ningún sistema
                # los lee), así que esto no cambiaba el comportamiento
                # observable hoy -- pero es la promesa documentada la que
                # ahora se cumple.
                celda.tiene_recurso = bool(tiene_rec)
                celda.tipo_recurso = str(tipo_rec)

            # 2. Cargar entidades biológicas
            cur.execute(
                """
                SELECT c.*, e.especie, e.nombre, e.tick_nacimiento, e.id_madre, e.id_padre
                FROM componentes_estado c
                JOIN entidades e ON c.entidad_id = e.id
                """
            )
            for fila in cur.fetchall():
                eid = fila[0]
                gestor.anadir_componente(eid, Posicion(x=fila[1], y=fila[2]))
                gestor.anadir_componente(
                    eid,
                    Necesidades(
                        saciedad=fila[3],
                        energia=fila[4],
                        seguridad=fila[5],
                        hidratacion=fila[6],
                        aliviado=fila[7],
                        oxigenacion=fila[8],
                        confort_termico=fila[9],
                        impulso_reproductivo=fila[10],
                    ),
                )
                dims = DimensionesFisicas(
                    peso=fila[11],
                    altura=fila[12],
                    longevidad=fila[13],
                    fuerza=fila[14],
                    agilidad=fila[15],
                    velocidad=fila[16],
                    resistencia_enfermedad=fila[17],
                    agudeza_sensorial=fila[18],
                    vitalidad_maxima=fila[19],
                    resistencia_maxima=fila[20],
                    curacion=fila[21],
                    recuperacion=fila[22],
                )
                gestor.anadir_componente(eid, dims)
                gestor.anadir_componente(eid, PoolFisico(vitalidad=fila[23], resistencia=fila[24]))
                gestor.anadir_componente(
                    eid,
                    Temperamento(
                        valentia=fila[25],
                        sociabilidad=fila[26],
                        agresividad=fila[27],
                        dominancia=fila[28],
                        empatia=fila[29],
                        lealtad=fila[30],
                        fe=fila[31],
                        curiosidad=fila[32],
                    ),
                )
                cm = CapacidadMental(
                    inteligencia=fila[33],
                    memoria=fila[34],
                    voluntad=fila[35],
                    resiliencia=fila[36],
                    estabilidad_mental_maxima=fila[37],
                    consciencia=fila[38],
                )
                gestor.anadir_componente(eid, cm)
                gestor.anadir_componente(eid, PoolMental(estabilidad=fila[39]))
                gestor.anadir_componente(
                    eid,
                    Reproduccion(
                        sexo=Sexo(fila[40]),
                        duracion_gestacion_dias=fila[41],
                    ),
                )

                if fila[42] is not None:
                    snapshot_padre = json.loads(fila[44]) if fila[44] else {}
                    gestor.anadir_componente(
                        eid,
                        _reconstruir_gestacion(tick_inicio=fila[42], id_padre=fila[43], snapshot=snapshot_padre),
                    )

                recuerdos_dict = json.loads(fila[45]) if fila[45] else {}
                gestor.anadir_componente(eid, MemoriaEspacial(recuerdos=recuerdos_dict))
                gestor.anadir_componente(eid, Intencion(accion=Accion.DEAMBULAR))
                gestor.anadir_componente(
                    eid,
                    Identidad(
                        especie=Especie(fila[46]),
                        nombre=fila[47],
                        tick_nacimiento=fila[48],
                        id_madre=fila[49],
                        id_padre=fila[50],
                    ),
                )

            # 3. Cargar Flora
            cur.execute("SELECT entidad_id, x, y, especie, etapa FROM plantas_estado")
            for pid, px, py, esp, etapa in cur.fetchall():
                gestor.anadir_componente(pid, Posicion(x=px, y=py))
                gestor.anadir_componente(pid, Planta(especie=esp, etapa=float(etapa)))

            # 4. Cargar Necromasa
            cur.execute("SELECT entidad_id, x, y, masas, agua_tisular, tasa_putrefaccion, origen_especie FROM necromasa_estado")
            for nid, nx, ny, masas_json, agua, tasa, orig in cur.fetchall():
                gestor.anadir_componente(nid, Posicion(x=nx, y=ny))
                gestor.anadir_componente(
                    nid,
                    Necromasa(
                        masas=json.loads(masas_json),
                        agua_tisular=float(agua),
                        tasa_putrefaccion=float(tasa),
                        origen_especie=str(orig),
                    ),
                )

            # Ajustar siguiente id autoincremental
            cur.execute("SELECT MAX(id) FROM entidades")
            max_id_ent = cur.fetchone()[0] or 0
            cur.execute("SELECT MAX(entidad_id) FROM plantas_estado")
            max_id_plant = cur.fetchone()[0] or 0
            cur.execute("SELECT MAX(entidad_id) FROM necromasa_estado")
            max_id_nec = cur.fetchone()[0] or 0

            gestor._siguiente_id = max(max_id_ent, max_id_plant, max_id_nec) + 1
            return True