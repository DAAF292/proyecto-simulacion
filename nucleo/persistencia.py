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

from componentes.agarre import Agarre
from componentes.capacidad_mental import CapacidadMental
from componentes.construccion import Construccion
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.fogata import Fogata
from componentes.gestacion import Gestacion
from componentes.identidad import Especie, Identidad
from componentes.intencion import Accion, Intencion
from componentes.inventario import Inventario
from componentes.memoria_espacial import MemoriaEspacial
from componentes.necesidades import Necesidades
from componentes.necromasa import Necromasa
from componentes.planta import Planta
from componentes.pool_fisico import PoolFisico
from componentes.pool_mental import PoolMental
from componentes.posicion import Posicion
from componentes.reproduccion import Reproduccion, Sexo
from componentes.relaciones import Relaciones, Vinculo
from componentes.semillas import Semillas
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
    padre, tamano_camada) en un dict serializable a JSON. tick_inicio e
    id_padre SÍ tienen sus propias columnas (no van aquí); todo lo demás
    de la instantánea del padre se empaqueta en un único blob JSON.
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


VERSION_ESQUEMA = "0.33-fase0"

_TABLAS_APP = (
    "entidades",
    "componentes_estado",
    "plantas_estado",
    "necromasa_estado",
    "construccion_estado",
    "fogata_estado",
    "celdas_estado",
    "cronica_eventos",
    "configuracion_ejecucion",
)


class Persistencia:
    """Gestiona la base de datos SQLite para snapshots y crónica histórica.

    Versionado de esquema: `CREATE TABLE IF NOT EXISTS` nunca migra
    columnas -- si el código cambia la forma de una tabla, una base de
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
                    recuerdos TEXT,
                    inventario TEXT,
                    zona_idx INTEGER NOT NULL DEFAULT 0,
                    agarre TEXT,
                    -- semillas (2026-09-02, ver componentes/semillas.py):
                    -- Semillas.especie_transportada, mismo criterio que
                    -- agarre -- perderla al recargar sería una regresión
                    -- silenciosa en un mecanismo con efecto real conectado.
                    semillas TEXT,
                    -- relaciones (2026-09-04, ver componentes/relaciones.py):
                    -- Relaciones.vinculos, mismo criterio que agarre/semillas
                    -- -- perder los vinculos al recargar seria una regresion
                    -- silenciosa en un mecanismo con efecto real conectado.
                    relaciones TEXT
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
                    etapa REAL NOT NULL,
                    zona_idx INTEGER NOT NULL DEFAULT 0
                )
                """
            )

            # 4. Snapshot de necromasa. masas: JSON de {material: kg} --
            # mismo patrón que celdas_estado.recursos mas abajo (dict
            # serializado, no una columna por material).
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS necromasa_estado (
                    entidad_id INTEGER PRIMARY KEY,
                    x INTEGER NOT NULL,
                    y INTEGER NOT NULL,
                    masas TEXT NOT NULL,
                    agua_tisular REAL NOT NULL,
                    tasa_putrefaccion REAL NOT NULL,
                    origen_especie TEXT NOT NULL,
                    zona_idx INTEGER NOT NULL DEFAULT 0
                )
                """
            )

            # 4b. Snapshot de construcciones (refugio/almacén -- ver
            # componentes/construccion.py). Mismo molde que necromasa_estado:
            # entidad física sin fila en `entidades` (no tiene Identidad).
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS construccion_estado (
                    entidad_id INTEGER PRIMARY KEY,
                    x INTEGER NOT NULL,
                    y INTEGER NOT NULL,
                    tipo TEXT NOT NULL,
                    materiales TEXT NOT NULL,
                    propietario_id INTEGER,
                    progreso REAL NOT NULL,
                    completado_alguna_vez BOOLEAN NOT NULL,
                    zona_idx INTEGER NOT NULL DEFAULT 0
                )
                """
            )

            # 4c. Snapshot de fogatas (ver componentes/fogata.py). Mismo
            # molde que construccion_estado: entidad física sin fila en
            # `entidades` (no tiene Identidad).
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS fogata_estado (
                    entidad_id INTEGER PRIMARY KEY,
                    x INTEGER NOT NULL,
                    y INTEGER NOT NULL,
                    combustible_restante REAL NOT NULL,
                    zona_idx INTEGER NOT NULL DEFAULT 0
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
                    zona_idx INTEGER NOT NULL DEFAULT 0,
                    deposito_mineral TEXT NOT NULL DEFAULT '',
                    masa_mineral_restante REAL NOT NULL DEFAULT 0.0,
                    PRIMARY KEY (x, y, zona_idx)
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

    def marcar_entidad_muerta(self, entidad_id: int) -> None:
        """Actualiza el registro histórico de una entidad para reflejar
        que ha muerto. Se llama desde main.py al procesar cualquier
        Evento con tipo == "Muerte", el mismo patrón que ya usa
        registrar_entidad_nueva para "Nacimiento"."""
        with self._conectar() as con:
            cur = con.cursor()
            cur.execute(
                "UPDATE entidades SET viva = 0 WHERE id = ?",
                (entidad_id,),
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
        rng_reproduccion: random.Random,
    ) -> None:
        """Serializa el estado completo en una transacción atómica.

        semilla: la semilla de generación de mundo se guarda aquí, no
        solo el estado DINÁMICO de celda (fertilidad, charcos, fuego,
        recursos) -- el TERRENO en sí (tipo de bioma, elevación) lo
        regenera Mundo() a partir de la semilla de config en cada
        arranque, así que guardar la semilla usada permite a
        cargar_snapshot detectar y avisar si no coincide con la actual
        (ver su propio docstring)."""
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
                inv = gestor.obtener_componente(eid, Inventario)
                agarre = gestor.obtener_componente(eid, Agarre)
                semillas = gestor.obtener_componente(eid, Semillas)
                relaciones = gestor.obtener_componente(eid, Relaciones)

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
                            json.dumps(
                                {"contenidos": inv.contenidos, "objetos": inv.objetos}
                            ) if inv else None,
                            pos.zona_idx,
                            json.dumps(agarre.objetos) if agarre else None,
                            semillas.especie_transportada if semillas else None,
                            json.dumps(
                                {
                                    str(oid): {
                                        "afinidad": v.afinidad,
                                        "ultima_actualizacion_tick": v.ultima_actualizacion_tick,
                                    }
                                    for oid, v in (relaciones.vinculos.items() if relaciones else {}.items())
                                }
                            ) if relaciones else None,
                        )
                    )
            cur.executemany(
                """
                INSERT INTO componentes_estado VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
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
                    filas_flora.append(
                        (pid, pos_p.x, pos_p.y, planta.especie, planta.etapa, pos_p.zona_idx)
                    )
            cur.executemany("INSERT INTO plantas_estado VALUES (?, ?, ?, ?, ?, ?)", filas_flora)

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
                            pos_n.zona_idx,
                        )
                    )
            cur.executemany("INSERT INTO necromasa_estado VALUES (?, ?, ?, ?, ?, ?, ?, ?)", filas_necromasa)

            # C2. Construcciones
            cur.execute("DELETE FROM construccion_estado")
            filas_construccion = []
            for cid in sorted(gestor.entidades_con(Construccion, Posicion)):
                con_comp = gestor.obtener_componente(cid, Construccion)
                pos_c = gestor.obtener_componente(cid, Posicion)
                if con_comp and pos_c:
                    filas_construccion.append(
                        (
                            cid,
                            pos_c.x,
                            pos_c.y,
                            con_comp.tipo,
                            json.dumps(con_comp.materiales),
                            con_comp.propietario_id,
                            con_comp.progreso,
                            con_comp.completado_alguna_vez,
                            pos_c.zona_idx,
                        )
                    )
            cur.executemany(
                "INSERT INTO construccion_estado VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", filas_construccion
            )

            # C3. Fogatas (ver componentes/fogata.py)
            cur.execute("DELETE FROM fogata_estado")
            filas_fogata = []
            for fid in sorted(gestor.entidades_con(Fogata, Posicion)):
                fogata_comp = gestor.obtener_componente(fid, Fogata)
                pos_f = gestor.obtener_componente(fid, Posicion)
                if fogata_comp and pos_f:
                    filas_fogata.append(
                        (fid, pos_f.x, pos_f.y, fogata_comp.combustible_restante, pos_f.zona_idx)
                    )
            cur.executemany("INSERT INTO fogata_estado VALUES (?, ?, ?, ?, ?)", filas_fogata)

            # D. Celdas dinámicas -- TODAS las zonas del territorio, no
            # solo zonas[0].
            cur.execute("DELETE FROM celdas_estado")
            filas_celdas = []
            for zona_idx, zona in enumerate(mundo.territorio.zonas):
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
                                zona_idx,
                                celda.deposito_mineral,
                                celda.masa_mineral_restante,
                            )
                        )
            cur.executemany(
                "INSERT INTO celdas_estado VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", filas_celdas
            )

            # E. Metadatos de ejecución y RNG
            cur.execute("REPLACE INTO configuracion_ejecucion VALUES ('tick_actual', ?)", (reloj.tick_actual,))
            cur.execute("REPLACE INTO configuracion_ejecucion VALUES ('version_esquema', ?)", (VERSION_ESQUEMA,))
            cur.execute("REPLACE INTO configuracion_ejecucion VALUES ('semilla', ?)", (semilla,))
            cur.execute(
                "REPLACE INTO configuracion_ejecucion VALUES ('rng_juego_state', ?)",
                (pickle.dumps(rng_juego.getstate()),),
            )
            cur.execute(
                "REPLACE INTO configuracion_ejecucion VALUES ('rng_reproduccion_state', ?)",
                (pickle.dumps(rng_reproduccion.getstate()),),
            )

            con.commit()

    def cargar_snapshot(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        reloj: Reloj,
        rng_juego: random.Random,
        semilla: int,
        rng_reproduccion: random.Random,
    ) -> bool:
        """Restaura el estado completo desde la base de datos.

        semilla (ver docstring de guardar_snapshot): se compara contra la
        guardada en la propia partida. El terreno (bioma, elevación,
        ríos) NO se persiste -- lo regenera Mundo() a partir de la
        semilla de config en cada arranque, antes de que se llame a esta
        función. Si la semilla actual no coincide con la que generó el
        terreno sobre el que se guardó el estado dinámico de celda, el
        mundo resultante mezcla un terreno nuevo con recursos/fertilidad/
        charcos de otro terreno -- inconsistente, aunque no impide
        cargar. Se avisa por stderr en vez de fallar en silencio o
        bloquear la carga: no hay overhead de UI de por medio (nucleo/ no
        importa nada de presentacion/) y un guardado antiguo sigue siendo
        mejor que ninguno, incluso si el terreno ya no encaja."""
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
            # Reloj.tick_actual es un atributo de instancia plano fijado
            # en __init__ (nucleo/reloj.py), NO una property respaldada
            # por _tick_actual -- escribir en reloj._tick_actual crearía
            # un atributo nuevo sin efecto real, dejando el reloj
            # congelado en tick 0 tras cada carga.
            reloj.tick_actual = int(fila_tick[0])

            cur.execute("SELECT valor FROM configuracion_ejecucion WHERE clave = 'rng_juego_state'")
            fila_rng = cur.fetchone()
            if fila_rng:
                rng_juego.setstate(pickle.loads(fila_rng[0]))

            cur.execute("SELECT valor FROM configuracion_ejecucion WHERE clave = 'rng_reproduccion_state'")
            fila_rng_reproduccion = cur.fetchone()
            if fila_rng_reproduccion:
                rng_reproduccion.setstate(pickle.loads(fila_rng_reproduccion[0]))

            # Limpiar gestor en memoria
            for eid in list(gestor.entidades_con(Posicion)):
                gestor.eliminar_entidad(eid)

            # 1. Cargar celdas -- TODAS las zonas. Una fila cuyo zona_idx
            # ya no existe en el territorio recien generado (semilla
            # distinta, o menos zonas que cuando se guardo) se descarta
            # sin reventar -- mismo criterio defensivo que el aviso de
            # semilla de mas arriba.
            cur.execute(
                "SELECT x, y, fertilidad, profundidad_charco, en_llamas, recursos, "
                "tiene_recurso, tipo_recurso, zona_idx, deposito_mineral, "
                "masa_mineral_restante FROM celdas_estado"
            )
            for (
                x, y, fert, prof_ch, fuego, rec_json, tiene_rec, tipo_rec, zona_idx,
                dep_mineral, masa_mineral,
            ) in cur.fetchall():
                if zona_idx >= len(mundo.territorio.zonas):
                    continue
                celda = mundo.territorio.zonas[zona_idx].obtener_celda(x, y)
                celda.fertilidad = float(fert)
                celda.profundidad_charco = float(prof_ch)
                celda.en_llamas = bool(fuego)
                celda.recursos = json.loads(rec_json)
                # deposito_mineral/masa_mineral_restante son estado
                # mutable de la partida (una veta agotada por
                # Accion.RECOLECTAR), no puramente derivable de la
                # semilla -- se restauran igual que fertilidad/
                # profundidad_charco.
                celda.deposito_mineral = str(dep_mineral)
                celda.masa_mineral_restante = float(masa_mineral)
                celda.tiene_recurso = bool(tiene_rec)
                celda.tipo_recurso = str(tipo_rec)

            # 2. Cargar entidades biológicas. zona_idx es la columna
            # fila[47]; agarre se añadió DESPUÉS de zona_idx, como
            # fila[48] -- desplaza en +1 los índices e.especie..e.id_padre
            # de más abajo (fila[49]..fila[53]); semillas se añadió
            # después de agarre, como fila[49], y desplaza en +1 esos
            # índices una vez más (fila[50]..fila[54]); relaciones se
            # añadió después de semillas, como fila[50], y desplaza en
            # +1 esos índices otra vez más (fila[51]..fila[55]). La columna
            # inventario (fila[46]) guarda un JSON único con
            # {"contenidos": ..., "objetos": ...} desde armas primitivas v2
            # (2026-09-03) -- ver carga de Inventario más abajo. Ninguno
            # de los índices anteriores (0..46, incluida la instantánea
            # de gestación) cambia.
            cur.execute(
                """
                SELECT c.*, e.especie, e.nombre, e.tick_nacimiento, e.id_madre, e.id_padre
                FROM componentes_estado c
                JOIN entidades e ON c.entidad_id = e.id
                """
            )
            for fila in cur.fetchall():
                eid = fila[0]
                gestor.anadir_componente(eid, Posicion(x=fila[1], y=fila[2], zona_idx=fila[47]))
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
                inventario_dict = json.loads(fila[46]) if fila[46] else {}
                inventario_objetos = inventario_dict.get("objetos", []) if isinstance(inventario_dict, dict) else []
                contenidos = inventario_dict.get("contenidos", {}) if isinstance(inventario_dict, dict) else inventario_dict
                gestor.anadir_componente(
                    eid,
                    Inventario(contenidos=contenidos, objetos=list(inventario_objetos)),
                )
                agarre_lista = json.loads(fila[48]) if fila[48] else []
                gestor.anadir_componente(eid, Agarre(objetos=agarre_lista))
                semillas_valor = fila[49] if fila[49] else ""
                gestor.anadir_componente(eid, Semillas(especie_transportada=str(semillas_valor)))
                relaciones_json = fila[50] if fila[50] else "{}"
                relaciones_dict = json.loads(relaciones_json)
                gestor.anadir_componente(
                    eid,
                    Relaciones(
                        vinculos={
                            int(oid): Vinculo(
                                afinidad=float(datos["afinidad"]),
                                ultima_actualizacion_tick=int(datos["ultima_actualizacion_tick"]),
                            )
                            for oid, datos in (relaciones_dict or {}).items()
                        }
                    ),
                )
                gestor.anadir_componente(eid, Intencion(accion=Accion.DEAMBULAR))
                gestor.anadir_componente(
                    eid,
                    Identidad(
                        especie=Especie(fila[51]),
                        nombre=fila[52],
                        tick_nacimiento=fila[53],
                        id_madre=fila[54],
                        id_padre=fila[55],
                    ),
                )

            # 3. Cargar Flora
            cur.execute("SELECT entidad_id, x, y, especie, etapa, zona_idx FROM plantas_estado")
            for pid, px, py, esp, etapa, zidx in cur.fetchall():
                gestor.anadir_componente(pid, Posicion(x=px, y=py, zona_idx=zidx))
                gestor.anadir_componente(pid, Planta(especie=esp, etapa=float(etapa)))

            # 4. Cargar Necromasa
            cur.execute(
                "SELECT entidad_id, x, y, masas, agua_tisular, tasa_putrefaccion, origen_especie, "
                "zona_idx FROM necromasa_estado"
            )
            for nid, nx, ny, masas_json, agua, tasa, orig, zidx in cur.fetchall():
                gestor.anadir_componente(nid, Posicion(x=nx, y=ny, zona_idx=zidx))
                gestor.anadir_componente(
                    nid,
                    Necromasa(
                        masas=json.loads(masas_json),
                        agua_tisular=float(agua),
                        tasa_putrefaccion=float(tasa),
                        origen_especie=str(orig),
                    ),
                )

            # 4b. Cargar Construcciones
            cur.execute(
                "SELECT entidad_id, x, y, tipo, materiales, propietario_id, progreso, "
                "completado_alguna_vez, zona_idx FROM construccion_estado"
            )
            for coid, cx, cy, tipo, mats_json, propietario_id, progreso, completado, zidx in cur.fetchall():
                gestor.anadir_componente(coid, Posicion(x=cx, y=cy, zona_idx=zidx))
                gestor.anadir_componente(
                    coid,
                    Construccion(
                        tipo=str(tipo),
                        materiales=json.loads(mats_json),
                        propietario_id=propietario_id,
                        progreso=float(progreso),
                        completado_alguna_vez=bool(completado),
                    ),
                )

            # 4c. Cargar Fogatas
            cur.execute(
                "SELECT entidad_id, x, y, combustible_restante, zona_idx FROM fogata_estado"
            )
            for foid, fx, fy, combustible, fzidx in cur.fetchall():
                gestor.anadir_componente(foid, Posicion(x=fx, y=fy, zona_idx=fzidx))
                gestor.anadir_componente(foid, Fogata(combustible_restante=float(combustible)))

            # Ajustar siguiente id autoincremental
            cur.execute("SELECT MAX(id) FROM entidades")
            max_id_ent = cur.fetchone()[0] or 0
            cur.execute("SELECT MAX(entidad_id) FROM plantas_estado")
            max_id_plant = cur.fetchone()[0] or 0
            cur.execute("SELECT MAX(entidad_id) FROM necromasa_estado")
            max_id_nec = cur.fetchone()[0] or 0
            cur.execute("SELECT MAX(entidad_id) FROM construccion_estado")
            max_id_con = cur.fetchone()[0] or 0
            cur.execute("SELECT MAX(entidad_id) FROM fogata_estado")
            max_id_fog = cur.fetchone()[0] or 0

            gestor._siguiente_id = (
                max(max_id_ent, max_id_plant, max_id_nec, max_id_con, max_id_fog) + 1
            )
            return True
