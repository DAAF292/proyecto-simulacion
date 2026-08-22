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

import json
import pickle
import random
import sqlite3
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

VERSION_ESQUEMA = "0.20-fase0"


class Persistencia:
    """Gestiona la base de datos SQLite para snapshots y crónica histórica."""

    def __init__(self, ruta_db: Path) -> None:
        self.ruta_db = ruta_db
        self.ruta_db.parent.mkdir(parents=True, exist_ok=True)
        self._inicializar_tablas()

    def _conectar(self) -> sqlite3.Connection:
        return sqlite3.connect(self.ruta_db)

    def _inicializar_tablas(self) -> None:
        """Crea el esquema relacional si no existe."""
        with self._conectar() as con:
            cur = con.cursor()

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

            # 4. Snapshot de necromasa
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS necromasa_estado (
                    entidad_id INTEGER PRIMARY KEY,
                    x INTEGER NOT NULL,
                    y INTEGER NOT NULL,
                    masa_organica REAL NOT NULL,
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
    ) -> None:
        """Serializa el estado completo en una transacción atómica."""
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
                            gest.padre_id if gest else None,
                            json.dumps(gest.padre_snapshot) if gest and gest.padre_snapshot else None,
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
                            nec_comp.masa_organica,
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
                        )
                    )
            cur.executemany("INSERT INTO celdas_estado VALUES (?, ?, ?, ?, ?, ?)", filas_celdas)

            # E. Metadatos de ejecución y RNG
            cur.execute("REPLACE INTO configuracion_ejecucion VALUES ('tick_actual', ?)", (reloj.tick_actual,))
            cur.execute("REPLACE INTO configuracion_ejecucion VALUES ('version_esquema', ?)", (VERSION_ESQUEMA,))
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
    ) -> bool:
        """Restaura el estado completo desde la base de datos."""
        zona = mundo.territorio.zonas[0]

        with self._conectar() as con:
            cur = con.cursor()

            cur.execute("SELECT valor FROM configuracion_ejecucion WHERE clave = 'tick_actual'")
            fila_tick = cur.fetchone()
            if not fila_tick:
                return False
            reloj._tick_actual = int(fila_tick[0])

            cur.execute("SELECT valor FROM configuracion_ejecucion WHERE clave = 'rng_juego_state'")
            fila_rng = cur.fetchone()
            if fila_rng:
                rng_juego.setstate(pickle.loads(fila_rng[0]))

            # Limpiar gestor en memoria
            for eid in list(gestor.entidades_con(Posicion)):
                gestor.eliminar_entidad(eid)

            # 1. Cargar celdas
            cur.execute("SELECT x, y, fertilidad, profundidad_charco, en_llamas, recursos FROM celdas_estado")
            for x, y, fert, prof_ch, fuego, rec_json in cur.fetchall():
                celda = zona.obtener_celda(x, y)
                celda.fertilidad = float(fert)
                celda.profundidad_charco = float(prof_ch)
                celda.en_llamas = bool(fuego)
                celda.recursos = json.loads(rec_json)

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
                    padre_snap = json.loads(fila[44]) if fila[44] else {}
                    gestor.anadir_componente(
                        eid,
                        Gestacion(
                            tick_inicio=fila[42],
                            padre_id=fila[43],
                            padre_snapshot=padre_snap,
                        ),
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
            cur.execute("SELECT entidad_id, x, y, masa_organica, agua_tisular, tasa_putrefaccion, origen_especie FROM necromasa_estado")
            for nid, nx, ny, masa, agua, tasa, orig in cur.fetchall():
                gestor.anadir_componente(nid, Posicion(x=nx, y=ny))
                gestor.anadir_componente(
                    nid,
                    Necromasa(
                        masa_organica=float(masa),
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