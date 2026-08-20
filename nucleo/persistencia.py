"""Persistencia (paso 10): unica pieza que conoce SQLite -- el resto del
nucleo no debe importar sqlite3 ni saber que esta tabla existe.

Dos patrones de escritura distintos, segun la naturaleza del dato:

- Incrementales (nunca se sobrescriben de golpe): `entidades` (una fila
  por entidad que alguna vez existio -- viva=1 al nacer, viva=0 al morir,
  nunca se borra) y `cronica_eventos` (append-only, solo NOTABLE/
  HISTORICO -- RUIDO no se persiste). Se escriben en el momento en que
  ocurre el hecho, no en un volcado periodico.
- Snapshot (se sobrescriben por completo en cada guardado):
  `componentes_estado`, `celdas_estado`, `configuracion_ejecucion`. No
  importa el historico, solo el valor actual.

tipo_terreno de las celdas NO se persiste -- se regenera con la misma
semilla al cargar (generar_zona_bioma es determinista). Intencion
tampoco -- SistemaDecision la recalcula sola en el primer tick tras
cargar, a partir de las necesidades (que si estan guardadas).

Nota sobre el generador aleatorio: aunque el paso 10 del orden de
construccion solo pide guardar "semilla y tick_actual", eso no basta
para reanudar de verdad -- si al cargar se resembrara el rng de partida
desde la semilla, el flujo de numeros aleatorios se reiniciaria desde
cero en vez de continuar donde se quedo, y una partida cargada divergiria
de como habria seguido la misma ejecucion sin interrupcion. Por eso
tambien se persiste el estado completo del rng de partida
(random.getstate(), serializado con pickle). El rng usado SOLO para
generar el mapa es independiente y siempre se resiembra desde la
semilla (fresco), porque generar_zona_bioma es una funcion pura que no
necesita continuidad -- volver a llamarla da siempre el mismo mapa.
"""
import json
import os
import pickle
import sqlite3

from componentes.capacidad_mental import CapacidadMental
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Especie, Identidad
from componentes.intencion import Intencion
from componentes.memoria_espacial import MemoriaEspacial
from componentes.necesidades import Necesidades
from componentes.planta import Planta
from componentes.pool_fisico import PoolFisico
from componentes.gestacion import Gestacion
from componentes.pool_mental import PoolMental
from componentes.posicion import Posicion
from componentes.reproduccion import Reproduccion, Sexo
from componentes.temperamento import Temperamento
from nucleo.entidad import GestorEntidades
from nucleo.eventos import Severidad

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS entidades (
    id INTEGER PRIMARY KEY,
    especie TEXT NOT NULL,
    nombre TEXT,
    viva INTEGER NOT NULL,
    tick_nacimiento INTEGER NOT NULL DEFAULT 0,
    id_madre INTEGER,
    id_padre INTEGER
);

CREATE TABLE IF NOT EXISTS componentes_estado (
    entidad_id INTEGER PRIMARY KEY,
    x INTEGER NOT NULL,
    y INTEGER NOT NULL,
    saciedad REAL NOT NULL,
    energia REAL NOT NULL,
    seguridad REAL NOT NULL,
    hidratacion REAL NOT NULL,
    aliviado REAL NOT NULL,
    peso REAL NOT NULL,
    fuerza REAL NOT NULL,
    agilidad REAL NOT NULL,
    vitalidad_maxima REAL NOT NULL,
    resistencia_maxima REAL NOT NULL,
    curacion REAL NOT NULL,
    recuperacion REAL NOT NULL,
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
    altura REAL NOT NULL,
    longevidad REAL NOT NULL,
    velocidad REAL NOT NULL,
    resistencia_enfermedad REAL NOT NULL,
    agudeza_sensorial REAL NOT NULL,
    vitalidad_actual REAL NOT NULL,
    resistencia_actual REAL NOT NULL,
    estabilidad_mental_actual REAL NOT NULL,
    sexo TEXT NOT NULL DEFAULT 'hembra',
    duracion_gestacion_dias REAL NOT NULL DEFAULT 0,
    tick_inicio_gestacion INTEGER,
    gestacion_padre_id INTEGER,
    gestacion_padre_snapshot TEXT,
    recuerdos TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS cronica_eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tick INTEGER NOT NULL,
    tipo TEXT NOT NULL,
    severidad TEXT NOT NULL,
    entidad_id INTEGER,
    datos TEXT
);

CREATE TABLE IF NOT EXISTS configuracion_ejecucion (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    semilla INTEGER NOT NULL,
    tick_actual INTEGER NOT NULL,
    version_esquema TEXT NOT NULL,
    rng_estado BLOB
);

CREATE TABLE IF NOT EXISTS celdas_estado (
    x INTEGER NOT NULL,
    y INTEGER NOT NULL,
    recursos TEXT NOT NULL,
    fertilidad REAL NOT NULL DEFAULT 0.0,
    en_llamas INTEGER NOT NULL DEFAULT 0,
    tiene_recurso INTEGER NOT NULL DEFAULT 0,
    tipo_recurso TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (x, y)
);

CREATE TABLE IF NOT EXISTS plantas_estado (
    entidad_id INTEGER PRIMARY KEY,
    x INTEGER NOT NULL,
    y INTEGER NOT NULL,
    especie TEXT NOT NULL,
    etapa REAL NOT NULL
);
"""

# 0.2: Bloque B del plan de migracion a criatura.docx -- componentes_estado
# separa DimensionesFisicas (peso, fuerza, agilidad) de Temperamento
# (valentia, sociabilidad, agresividad), sustituyendo a la vieja columna
# unica de Categoria (que incluia ademas 'resistencia', retirada -- ver
# sistema_depredacion.py para su reemplazo por fuerza+agilidad).
# 0.3: Bloque C1 -- se anaden las dimensiones fijas vitalidad_maxima,
# resistencia_maxima, curacion, recuperacion (DimensionesFisicas) y el
# componente dinamico PoolFisico (vitalidad_actual, resistencia_actual).
# Sin mecanica de consumo todavia (Bloque C2, pendiente): estos valores
# se persisten para que el sustrato quede completo, aunque hoy no hay
# nada que los haga variar mas alla de la regeneracion pasiva.
# 0.4: Bloque D1 -- se anade hidratacion a Necesidades (segunda necesidad
# fisica nueva tras saciedad, resuelta bebiendo en terreno Ribera).
# 0.5: Bloque D2 -- se anade aliviado a Necesidades (tercera necesidad
# fisica nueva, resuelta in situ sin buscar ningun recurso). oxigenacion
# y confort_termico (Bloque D3) NO se persisten -- declaradas sin
# mecanica, nada las muta, cargar siempre reconstruye el mismo valor
# por defecto.
# 0.6: Bloque E -- se anaden a Temperamento dominancia, empatia, lealtad,
# fe y curiosidad. A diferencia de D3, estas SI se persisten: se sortean
# por individuo al nacer y deben sobrevivir a guardar/cargar aunque
# ningun sistema las lea todavia.
# 0.7: Bloque F1 -- componente CapacidadMental nuevo (inteligencia,
# memoria, voluntad, resiliencia, estabilidad_mental_maxima, consciencia)
# y componente dinamico PoolMental (estabilidad_mental_actual). Mismo
# criterio que Temperamento: se sortean/mutan por individuo, se
# persisten aunque casi ningun sistema los lea todavia.
# 0.8: Abono (celdas_estado gana fertilidad) -- a diferencia de
# tipo_terreno/tiene_agua (Bloque agua), fertilidad SI se persiste: es
# estado mutado por la partida real (Accion.ALIVIARSE + decaimiento por
# dia), no derivable de la semilla del mundo.
# 0.9: Bloque G -- componentes_estado gana las 5 dimensiones fisicas fijas
# restantes de criatura.docx 3.3 (altura, longevidad, velocidad,
# resistencia_enfermedad, agudeza_sensorial). Mismo criterio que Bloque E/
# F1: se sortean por individuo al nacer y deben sobrevivir a guardar/
# cargar aunque ningun sistema las lea todavia (ver dimensiones_fisicas.py
# para el detalle de cuales tienen dato real de referencia y cuales son
# provisionales por analogia).
# 0.10: Ciclo vital, paso 1 (fundamento de edad, ver
# componentes/identidad.py) -- entidades gana tick_nacimiento. Vive en
# `entidades` (no en componentes_estado) porque es dato de nacimiento
# inmutable, mismo criterio que especie/nombre -- no una edad que se
# recalcule o resetee, se persiste una unica vez al crear la entidad y
# nunca se vuelve a escribir.
# 0.11: Ciclo vital, 6.3 paso 1 (componentes/reproduccion.py) --
# componentes_estado gana sexo y duracion_gestacion_dias. A diferencia de
# tick_nacimiento, SI viven en componentes_estado (no en `entidades`):
# aunque son fijos de por vida como el resto del plano fisico/
# temperamento/capacidad mental, siguen ese mismo patron de persistencia
# por consistencia con como se guarda el resto de rango-racial-y-sorteo,
# no por ninguna necesidad de mutabilidad futura.
# 0.12: Ciclo vital, 6.3 paso 2 (componentes/gestacion.py) --
# componentes_estado gana tick_inicio_gestacion, NULLABLE (a diferencia de
# todo lo demas de esta tabla): Gestacion es el primer componente
# verdaderamente opcional del motor, solo existe en hembras gestando ahora
# mismo. NULL significa "no gestando", no un valor por defecto sin
# sentido -- omitirlo del todo habria perdido embarazos reales al
# guardar/cargar, que es justo el tipo de estado mutado por la partida que
# esta tabla existe para no perder.
# 0.15: Fase terreno 4 (flora como entidad con crecimiento -- ver
# componentes/planta.py, sistemas/sistema_flora.py). Dos cambios:
# (a) tabla nueva `plantas_estado`, patron SNAPSHOT (como celdas_estado,
#     no como entidades/componentes_estado): una Planta no tiene
#     identidad individual que importe conservar historicamente (a
#     diferencia de un gnomo o un lobo con nombre y linaje) -- si se
#     destruye y otra brota en su lugar manana, no es un hecho narrable
#     distinto. Por eso NO se registra en la tabla `entidades` (pensada
#     para especie/nombre/tick_nacimiento/parentesco de una criatura, no
#     encaja) -- entidad_id sigue viniendo del mismo contador global de
#     GestorEntidades (los ids de planta y de criatura conviven en el
#     mismo espacio de numeros, nunca colisionan), pero su ciclo de vida
#     entero vive en esta tabla aparte. cargar_partida() tiene que
#     considerar el MAXIMO id de AMBAS tablas (entidades y
#     plantas_estado) para no arriesgarse a reciclar un id de planta al
#     crear una entidad nueva tras cargar.
# (b) celdas_estado gana tiene_recurso (INTEGER 0/1): dejo de ser
#     derivable de la semilla del mundo en el momento en que
#     sistema_flora.py empezo a poder mutarlo en juego (propagacion lo
#     activa, un incendio lo desactiva -- ver nucleo/celda.py,
#     redefinicion del campo) -- mismo criterio que fertilidad/en_llamas.
# 0.14: Fase terreno 1 (estaciones, clima, desastres -- ver nucleo/clima.py,
# sistemas/sistema_clima.py, sistemas/sistema_desastres.py). celdas_estado
# gana en_llamas (INTEGER 0/1, mismo patron booleano-como-entero que el
# resto del esquema): es estado mutado por la partida real (un incendio en
# curso), no derivable de la semilla, mismo criterio que fertilidad. NO se
# anade columna para clima_actual/estacion_previa (ZonaBioma) -- decision
# deliberada, documentada en nucleo/zona_bioma.py: se resiembran en el
# primer corte de dia tras cargar, mismo estatus de imprecision aceptada
# que ya tiene Intencion.
# 0.13: Ciclo vital, 6.3 paso 3 (nacimiento -- herencia y parentesco).
# Dos cambios de esquema distintos para dos datos distintos:
# (a) `entidades` gana id_madre/id_padre (NULLABLE): parentesco, dato de
#     nacimiento inmutable como tick_nacimiento -- vive junto a el, no en
#     componentes_estado, por el mismo criterio documentado en
#     componentes/identidad.py. NULL = "generacion cero" (poblacion
#     inicial o entidad de antes de este bloque), no "desconocido".
# (b) `componentes_estado` gana gestacion_padre_id (INTEGER) y
#     gestacion_padre_snapshot (TEXT, JSON): la instantanea del padre que
#     componentes/gestacion.py fija en la concepcion (dimensiones,
#     temperamento, capacidad_mental, duracion_gestacion_padre). Se
#     serializa como UN campo JSON en vez de explotar en ~30 columnas
#     planas nuevas (una por atributo heredable x3 componentes) -- el
#     resto de la tabla sigue el patron de columnas planas porque esos
#     valores se leen y escriben individualmente por muchos sistemas; esta
#     instantanea, en cambio, solo se escribe una vez (al concebir) y solo
#     se lee una vez completa (al nacer, siempre los 3 componentes juntos),
#     asi que no hay ninguna ventaja en tener columnas sueltas y si un
#     coste real de legibilidad del esquema. Ambas columnas NULLABLE,
#     mismo criterio que tick_inicio_gestacion: NULL junto con
#     tick_inicio_gestacion NULL significa "no gestando ahora mismo".
# 0.16: Correccion biomas/especies (posterior a fase terreno 4, discutida
# y confirmada con Diego -- ver nucleo/celda.py, componentes/planta.py,
# nucleo/flora.py). Tres cambios de esquema:
# (a) `plantas_estado.tipo_terreno` renombrada a `especie` (TEXT, mismo
#     tipo): una Planta ya no lleva su bioma, lleva la clave de su especie
#     en el catalogo config/constantes.yaml (flora.especies) -- ya no hay
#     conversion a/desde TipoTerreno al guardar/cargar, especie es un
#     string plano de punta a punta.
# (b) `celdas_estado.recursos` cambia de REAL a TEXT: pasa a guardar un
#     objeto JSON {nombre_recurso: cantidad} en vez de un unico float --
#     una especie puede producir mas de un recurso de categoria alimento a
#     la vez (hierba_silvestre: raices Y hierba), asi que la celda necesita
#     poder llevar varias cantidades simultaneas. Mismo patron JSON-en-TEXT
#     que gestacion_padre_snapshot (0.13).
# (c) `celdas_estado` gana `tipo_recurso` (TEXT, mismo campo y mismo
#     motivo que en Celda -- ver nucleo/celda.py): que ESPECIE ocupa la
#     celda ahora mismo, dato DINAMICO (propagacion lo activa, un incendio
#     lo desactiva), no derivable de la semilla -- un bioma puede alojar
#     mas de una especie, asi que el bioma solo ya no basta para saber cual
#     hay en una celda concreta.
# 0.17: Memoria espacial (nucleo/memoria.py, discutida y confirmada con
# Diego -- ver componentes/memoria_espacial.py). `componentes_estado`
# gana `recuerdos` (TEXT, JSON) -- mismo patron JSON-en-TEXT que
# `recursos`/`gestacion_padre_snapshot`: un diccionario {tipo_recuerdo:
# [[x, y], ...]}, no columnas planas, porque el numero de claves no esta
# cerrado (hoy solo 'comida'/'agua', pensado para crecer sin migrar el
# esquema otra vez -- ver docstring de MemoriaEspacial). SI se persiste,
# a diferencia de datos deterministas de celda -- es experiencia
# acumulada de una vida entera, perderla al recargar seria una
# inconsistencia real, no una imprecision aceptable como Intencion.
_VERSION_ESQUEMA = "0.17-fase0"


def _conectar(ruta_db: str) -> sqlite3.Connection:
    directorio = os.path.dirname(ruta_db)
    if directorio:
        os.makedirs(directorio, exist_ok=True)
    conn = sqlite3.connect(ruta_db)
    conn.executescript(_ESQUEMA)
    return conn


def registrar_entidad_nueva(
    ruta_db: str, id_entidad: int, especie: str, nombre, tick_nacimiento: int = 0,
    id_madre: int | None = None, id_padre: int | None = None,
) -> None:
    with _conectar(ruta_db) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO entidades (id, especie, nombre, viva, tick_nacimiento, id_madre, id_padre) "
            "VALUES (?, ?, ?, 1, ?, ?, ?)",
            (id_entidad, especie, nombre, tick_nacimiento, id_madre, id_padre),
        )


def marcar_entidad_muerta(ruta_db: str, id_entidad: int) -> None:
    with _conectar(ruta_db) as conn:
        conn.execute("UPDATE entidades SET viva = 0 WHERE id = ?", (id_entidad,))


def registrar_eventos(ruta_db: str, eventos: list) -> None:
    narrables = [e for e in eventos if e.severidad != Severidad.RUIDO]
    if not narrables:
        return
    with _conectar(ruta_db) as conn:
        conn.executemany(
            "INSERT INTO cronica_eventos (tick, tipo, severidad, entidad_id, datos) VALUES (?, ?, ?, ?, ?)",
            [
                (e.tick, e.tipo, e.severidad.value, e.entidad_id, json.dumps(e.datos, ensure_ascii=False))
                for e in narrables
            ],
        )


def guardar_estado(ruta_db: str, semilla: int, tick_actual: int, gestor, zona, rng_juego) -> None:
    with _conectar(ruta_db) as conn:
        conn.execute("DELETE FROM componentes_estado")
        conn.execute("DELETE FROM celdas_estado")
        conn.execute("DELETE FROM plantas_estado")
        conn.execute("DELETE FROM configuracion_ejecucion")

        filas_componentes = []
        for id_entidad in gestor.entidades_con(
            Posicion, Necesidades, DimensionesFisicas, Temperamento, PoolFisico,
            CapacidadMental, PoolMental, Reproduccion, MemoriaEspacial,
        ):
            pos = gestor.obtener_componente(id_entidad, Posicion)
            nec = gestor.obtener_componente(id_entidad, Necesidades)
            dim = gestor.obtener_componente(id_entidad, DimensionesFisicas)
            tem = gestor.obtener_componente(id_entidad, Temperamento)
            pool = gestor.obtener_componente(id_entidad, PoolFisico)
            cap = gestor.obtener_componente(id_entidad, CapacidadMental)
            pool_m = gestor.obtener_componente(id_entidad, PoolMental)
            rep = gestor.obtener_componente(id_entidad, Reproduccion)
            mem = gestor.obtener_componente(id_entidad, MemoriaEspacial)
            gest = gestor.obtener_componente(id_entidad, Gestacion)
            if gest is not None:
                snapshot_padre = json.dumps({
                    "dimensiones": vars(gest.dimensiones_padre),
                    "temperamento": vars(gest.temperamento_padre),
                    "capacidad_mental": vars(gest.capacidad_mental_padre),
                    "duracion_gestacion_padre": gest.duracion_gestacion_padre,
                }, ensure_ascii=False)
            else:
                snapshot_padre = None
            filas_componentes.append((
                id_entidad, pos.x, pos.y,
                nec.saciedad, nec.energia, nec.seguridad, nec.hidratacion, nec.aliviado,
                dim.peso, dim.fuerza, dim.agilidad,
                dim.vitalidad_maxima, dim.resistencia_maxima, dim.curacion, dim.recuperacion,
                tem.valentia, tem.sociabilidad, tem.agresividad,
                tem.dominancia, tem.empatia, tem.lealtad, tem.fe, tem.curiosidad,
                cap.inteligencia, cap.memoria, cap.voluntad, cap.resiliencia,
                cap.estabilidad_mental_maxima, cap.consciencia,
                dim.altura, dim.longevidad, dim.velocidad,
                dim.resistencia_enfermedad, dim.agudeza_sensorial,
                pool.vitalidad, pool.resistencia, pool_m.estabilidad,
                rep.sexo.value, rep.duracion_gestacion_dias,
                gest.tick_inicio if gest is not None else None,
                gest.id_padre if gest is not None else None,
                snapshot_padre,
                json.dumps(mem.recuerdos, ensure_ascii=False),
            ))
        conn.executemany(
            """INSERT INTO componentes_estado
               (entidad_id, x, y, saciedad, energia, seguridad, hidratacion, aliviado, peso, fuerza,
                agilidad, vitalidad_maxima, resistencia_maxima, curacion, recuperacion,
                valentia, sociabilidad, agresividad, dominancia, empatia, lealtad, fe, curiosidad,
                inteligencia, memoria, voluntad, resiliencia, estabilidad_mental_maxima, consciencia,
                altura, longevidad, velocidad, resistencia_enfermedad, agudeza_sensorial,
                vitalidad_actual, resistencia_actual, estabilidad_mental_actual,
                sexo, duracion_gestacion_dias, tick_inicio_gestacion,
                gestacion_padre_id, gestacion_padre_snapshot, recuerdos)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            filas_componentes,
        )

        filas_celdas = [
            (
                x, y, json.dumps(celda.recursos), celda.fertilidad,
                int(celda.en_llamas), int(celda.tiene_recurso), celda.tipo_recurso,
            )
            for x, y, celda in zona.celdas()
        ]
        conn.executemany(
            """INSERT INTO celdas_estado (x, y, recursos, fertilidad, en_llamas, tiene_recurso, tipo_recurso)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            filas_celdas,
        )

        filas_plantas = []
        for id_planta in gestor.entidades_con(Posicion, Planta):
            pos = gestor.obtener_componente(id_planta, Posicion)
            planta = gestor.obtener_componente(id_planta, Planta)
            filas_plantas.append((id_planta, pos.x, pos.y, planta.especie, planta.etapa))
        conn.executemany(
            "INSERT INTO plantas_estado (entidad_id, x, y, especie, etapa) VALUES (?, ?, ?, ?, ?)",
            filas_plantas,
        )

        conn.execute(
            """INSERT INTO configuracion_ejecucion (id, semilla, tick_actual, version_esquema, rng_estado)
               VALUES (1, ?, ?, ?, ?)""",
            (semilla, tick_actual, _VERSION_ESQUEMA, pickle.dumps(rng_juego.getstate())),
        )


def hay_partida_guardada(ruta_db: str) -> bool:
    if not os.path.exists(ruta_db):
        return False
    with _conectar(ruta_db) as conn:
        fila = conn.execute("SELECT 1 FROM configuracion_ejecucion LIMIT 1").fetchone()
        return fila is not None


def _reconstruir_gestacion(tick_inicio_gestacion, gestacion_padre_id, gestacion_padre_snapshot) -> list:
    """tick_inicio_gestacion es NULL exactamente cuando la entidad no
    esta gestando (ver 0.12 en el historico de _VERSION_ESQUEMA) --
    gestacion_padre_id/snapshot viajan siempre junto con el, nunca por
    separado, asi que basta comprobar el primero. Devuelve una lista de
    0 o 1 elementos para poder sumarla con + a la lista de componentes
    fijos, mismo patron que ya usaba esta funcion antes de extraerse."""
    if tick_inicio_gestacion is None:
        return []
    snapshot = json.loads(gestacion_padre_snapshot)
    return [Gestacion(
        tick_inicio=tick_inicio_gestacion,
        id_padre=gestacion_padre_id,
        dimensiones_padre=DimensionesFisicas(**snapshot["dimensiones"]),
        temperamento_padre=Temperamento(**snapshot["temperamento"]),
        capacidad_mental_padre=CapacidadMental(**snapshot["capacidad_mental"]),
        duracion_gestacion_padre=snapshot["duracion_gestacion_padre"],
    )]


def _reconstruir_recuerdos(recuerdos_json) -> dict:
    """JSON no distingue tuplas de listas -- [x, y] vuelve como lista tras
    json.loads(), pero nucleo/memoria.py y sistema_movimiento.py comparan
    y deduplican posiciones como tuplas (misma convencion que el resto
    del motor, Posicion.x/y aparte). Sin esta reconstruccion, `posicion
    in lista` en recordar() nunca encontraria una coincidencia tras
    cargar una partida -- [3, 4] != (3, 4) en Python -- y cada visita a un
    sitio ya conocido duplicaria el recuerdo en vez de refrescarlo.
    '{}' si la columna esta vacia (fila de antes de este bloque, o
    entidad recien creada sin nada grabado todavia)."""
    if not recuerdos_json:
        return {}
    bruto = json.loads(recuerdos_json)
    return {tipo: [tuple(p) for p in posiciones] for tipo, posiciones in bruto.items()}


def cargar_partida(ruta_db: str):
    """Devuelve (semilla, tick_actual, gestor_reconstruido, rng_estado) o
    None si no hay partida guardada. rng_estado es el blob pickled listo
    para rng_juego.setstate(pickle.loads(...)) -- None si la partida es
    de antes de que existiera esta columna. No genera el mapa: eso lo
    hace quien llame, con generar_zona_bioma() y la semilla devuelta
    aqui, igual que en una partida nueva."""
    if not hay_partida_guardada(ruta_db):
        return None

    with _conectar(ruta_db) as conn:
        fila_config = conn.execute(
            "SELECT semilla, tick_actual, rng_estado FROM configuracion_ejecucion WHERE id = 1"
        ).fetchone()
        if fila_config is None:
            return None
        semilla, tick_actual, rng_estado_blob = fila_config

        filas = conn.execute(
            """SELECT e.id, e.especie, e.nombre, e.tick_nacimiento, e.id_madre, e.id_padre,
                      c.x, c.y, c.saciedad, c.energia, c.seguridad,
                      c.hidratacion, c.aliviado, c.peso, c.fuerza, c.agilidad, c.vitalidad_maxima,
                      c.resistencia_maxima, c.curacion, c.recuperacion, c.valentia,
                      c.sociabilidad, c.agresividad, c.dominancia, c.empatia, c.lealtad, c.fe,
                      c.curiosidad, c.inteligencia, c.memoria, c.voluntad, c.resiliencia,
                      c.estabilidad_mental_maxima, c.consciencia, c.altura, c.longevidad,
                      c.velocidad, c.resistencia_enfermedad, c.agudeza_sensorial,
                      c.vitalidad_actual, c.resistencia_actual, c.estabilidad_mental_actual,
                      c.sexo, c.duracion_gestacion_dias, c.tick_inicio_gestacion,
                      c.gestacion_padre_id, c.gestacion_padre_snapshot, c.recuerdos
               FROM entidades e JOIN componentes_estado c ON c.entidad_id = e.id
               WHERE e.viva = 1"""
        ).fetchall()

        fila_max = conn.execute("SELECT MAX(id) FROM entidades").fetchone()
        max_id_criaturas = fila_max[0] if fila_max and fila_max[0] is not None else -1
        # Plantas no viven en `entidades` (ver 0.15 en el historico de
        # _VERSION_ESQUEMA) -- su propio maximo hay que consultarlo aparte
        # y quedarse con el mayor de los dos, o un id de planta reciente
        # podria reciclarse al crear la siguiente entidad tras cargar.
        fila_max_plantas = conn.execute("SELECT MAX(entidad_id) FROM plantas_estado").fetchone()
        max_id_plantas = fila_max_plantas[0] if fila_max_plantas and fila_max_plantas[0] is not None else -1
        max_id = max(max_id_criaturas, max_id_plantas)

        filas_plantas = conn.execute("SELECT entidad_id, x, y, especie, etapa FROM plantas_estado").fetchall()

    gestor = GestorEntidades()
    for (id_e, especie, nombre, tick_nacimiento, id_madre, id_padre,
         x, y, saciedad, energia, seguridad, hidratacion, aliviado,
         peso, fuerza, agilidad, vitalidad_maxima, resistencia_maxima,
         curacion, recuperacion, valentia, sociabilidad, agresividad,
         dominancia, empatia, lealtad, fe, curiosidad,
         inteligencia, memoria, voluntad, resiliencia, estabilidad_mental_maxima, consciencia,
         altura, longevidad, velocidad, resistencia_enfermedad, agudeza_sensorial,
         vitalidad_actual, resistencia_actual, estabilidad_mental_actual,
         sexo, duracion_gestacion_dias, tick_inicio_gestacion,
         gestacion_padre_id, gestacion_padre_snapshot, recuerdos_json) in filas:
        gestor.anadir_entidad_existente(id_e, [
            Posicion(x=x, y=y),
            Necesidades(
                saciedad=saciedad, energia=energia, seguridad=seguridad,
                hidratacion=hidratacion, aliviado=aliviado,
            ),
            Identidad(
                especie=Especie(especie), nombre=nombre, tick_nacimiento=tick_nacimiento,
                id_madre=id_madre, id_padre=id_padre,
            ),
            DimensionesFisicas(
                peso=peso, fuerza=fuerza, agilidad=agilidad,
                vitalidad_maxima=vitalidad_maxima, resistencia_maxima=resistencia_maxima,
                curacion=curacion, recuperacion=recuperacion,
                altura=altura, longevidad=longevidad, velocidad=velocidad,
                resistencia_enfermedad=resistencia_enfermedad,
                agudeza_sensorial=agudeza_sensorial,
            ),
            Temperamento(
                valentia=valentia, sociabilidad=sociabilidad, agresividad=agresividad,
                dominancia=dominancia, empatia=empatia, lealtad=lealtad, fe=fe,
                curiosidad=curiosidad,
            ),
            CapacidadMental(
                inteligencia=inteligencia, memoria=memoria, voluntad=voluntad,
                resiliencia=resiliencia, estabilidad_mental_maxima=estabilidad_mental_maxima,
                consciencia=consciencia,
            ),
            PoolFisico(vitalidad=vitalidad_actual, resistencia=resistencia_actual),
            PoolMental(estabilidad=estabilidad_mental_actual),
            Intencion(),  # valor por defecto -- SistemaDecision la recalcula en el siguiente tick
            Reproduccion(sexo=Sexo(sexo), duracion_gestacion_dias=duracion_gestacion_dias),
            MemoriaEspacial(recuerdos=_reconstruir_recuerdos(recuerdos_json)),
        ] + _reconstruir_gestacion(tick_inicio_gestacion, gestacion_padre_id, gestacion_padre_snapshot))

    for id_planta, x, y, especie, etapa in filas_plantas:
        gestor.anadir_entidad_existente(id_planta, [
            Posicion(x=x, y=y),
            Planta(especie=especie, etapa=etapa),
        ])

    if max_id >= 0:
        gestor.registrar_id_existente(max_id)

    return semilla, tick_actual, gestor, rng_estado_blob


def contar_eventos_por_tipo(ruta_db: str, tipo: str) -> int:
    """Cuenta el total historico de eventos de un tipo dado, consultando
    la cronica persistida -- no un contador en memoria, para que el
    resultado sea correcto aunque la partida se haya cargado y guardado
    en varias sesiones distintas."""
    if not os.path.exists(ruta_db):
        return 0
    with _conectar(ruta_db) as conn:
        fila = conn.execute(
            "SELECT COUNT(*) FROM cronica_eventos WHERE tipo = ?", (tipo,)
        ).fetchone()
        return fila[0] if fila else 0


def contar_muertes_por_causa(ruta_db: str) -> dict:
    """Desglose de la crónica de eventos Muerte por su campo 'causa' (por
    ejemplo 'inanicion', 'depredacion' -- paso 12.3). Lee el JSON de
    datos guardado con cada evento; una fila sin 'causa' legible se
    cuenta como 'desconocida' en vez de romper el conteo."""
    if not os.path.exists(ruta_db):
        return {}
    with _conectar(ruta_db) as conn:
        filas = conn.execute(
            "SELECT datos FROM cronica_eventos WHERE tipo = 'Muerte'"
        ).fetchall()
    desglose: dict = {}
    for (datos_json,) in filas:
        causa = "desconocida"
        if datos_json:
            try:
                causa = json.loads(datos_json).get("causa", "desconocida")
            except json.JSONDecodeError:
                pass
        desglose[causa] = desglose.get(causa, 0) + 1
    return desglose


def contar_entidades_totales(ruta_db: str, especie: str | None = None) -> int:
    """Total de entidades que existieron alguna vez (vivas o muertas).
    Sin reproduccion (fase 0), esto equivale siempre a la poblacion
    inicial real de esa especie, independientemente de en cuantas
    sesiones se haya jugado. especie=None cuenta todas las especies
    juntas (uso: informativo general, no el criterio de fase 1, que es
    especifico de gnomo)."""
    if not os.path.exists(ruta_db):
        return 0
    with _conectar(ruta_db) as conn:
        if especie is None:
            fila = conn.execute("SELECT COUNT(*) FROM entidades").fetchone()
        else:
            fila = conn.execute(
                "SELECT COUNT(*) FROM entidades WHERE especie = ?", (especie,)
            ).fetchone()
        return fila[0] if fila else 0


def aplicar_recursos_guardados(ruta_db: str, zona) -> None:
    """No-op si no hay celdas_estado guardadas (partida nueva). Nombre
    historico ("recursos") -- desde el Bloque de abono tambien aplica
    fertilidad, mismo motivo: es estado mutado por la partida real, no
    derivable de la semilla (a diferencia de tipo_terreno/tiene_agua).

    recursos viaja como JSON (correccion biomas/especies, 0.16) -- se
    deserializa aqui a dict, mismo patron que gestacion_padre_snapshot.
    tipo_recurso viaja como columna nueva, mismo criterio dinamico que
    tiene_recurso."""
    with _conectar(ruta_db) as conn:
        filas = conn.execute(
            "SELECT x, y, recursos, fertilidad, en_llamas, tiene_recurso, tipo_recurso FROM celdas_estado"
        ).fetchall()
    for x, y, recursos_json, fertilidad, en_llamas, tiene_recurso, tipo_recurso in filas:
        if 0 <= x < zona.ancho and 0 <= y < zona.alto:
            celda = zona.celda(x, y)
            celda.recursos = json.loads(recursos_json) if recursos_json else {}
            celda.fertilidad = fertilidad
            celda.en_llamas = bool(en_llamas)
            celda.tiene_recurso = bool(tiene_recurso)
            celda.tipo_recurso = tipo_recurso or ""
