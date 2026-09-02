"""Celda: unidad minima del grid. Dato puro (bioma + campos fisicos +
recursos + presencia de agua).

tipo_terreno es un BIOMA -- zona climatica (Pradera, Bosque, Desierto,
Montana, Tundra). Un bioma puede alojar varias especies de planta a la
vez (Bosque aloja hierba silvestre Y manzano) -- esa variación local
vive en qué ESPECIE de planta ocupa cada celda (ver componentes/planta.py
y Celda.tipo_recurso), no en el propio tipo_terreno.

El tipo de recurso que produce una celda se deriva de qué ESPECIE de
planta ocupa la celda (Celda.tipo_recurso, ver más abajo), no de
tipo_terreno directamente -- un bioma puede alojar varias especies
posibles (config/flora.yaml), cada una con su propio recurso.

tiene_agua es una capa geográfica ortogonal al bioma: cualquier celda,
de cualquier bioma, puede tener agua o no. tipo_agua distingue 'rio',
'lago' o 'poza' (ver nucleo/agua.py para la generación); el agua se
deriva del campo de elevación (descenso de pendiente desde picos,
cuencas donde el descenso termina) y puede haber varios cuerpos a la
vez. tiene_agua se mantiene como booleano derivado (tipo_agua != "")
porque la mayoría de consumidores (Accion.BEBER, filtro de hábitat del
lobo) solo necesitan saber SI hay agua, no de qué tipo.

Historial de diseño y decisiones: docs/historial_celda.md.
"""
from dataclasses import dataclass, field
from enum import Enum


class TipoTerreno(Enum):
    """Bioma de la celda -- zona climática, determinada por elevación+
    lluvia+temperatura (nucleo/bioma.py). Los cinco valores son biomas
    de verdad, mutuamente excluyentes por definición climática."""
    PRADERA = "pradera"    # lluvia y temperatura moderadas -- pastizal abierto
    BOSQUE = "bosque"      # lluvia abundante -- aloja hierba silvestre Y manzano
    DESIERTO = "desierto"  # lluvia escasa -- arido
    MONTANA = "montana"    # elevacion alta -- vegetacion escasa (liquen)
    TUNDRA = "tundra"      # temperatura muy baja -- vegetacion escasa (musgo)


@dataclass
class Celda:
    tipo_terreno: TipoTerreno
    elevacion: float = 0.0
    """Magnitud continua en [0, 1], generada por nucleo/campo_continuo.py
    (value noise). Determina el bioma junto con lluvia y temperatura
    (nucleo/bioma.py). NO se persiste: determinista a partir de la
    semilla del mundo, se regenera igual en cada carga."""
    lluvia: float = 0.0
    """Campo continuo en [0, 1], mismo generador que elevacion. Doble
    uso: (a) junto con elevacion/temperatura, decide el bioma de la
    celda al generar el mundo (nucleo/bioma.py); (b) después, sigue viva
    como dato de la celda -- sistema_flora.py la lee cada día para
    modular cuánto produce la planta presente según su
    preferencia_lluvia (config/flora.yaml). NO se persiste, mismo
    criterio que elevacion."""
    temperatura: float = 0.0
    """Igual que lluvia, campo continuo en [0, 1] -- decide bioma al
    generar el mundo y modula producción de flora después
    (preferencia_temperatura por especie). NO se persiste."""
    recursos: dict = field(default_factory=dict)
    """{nombre_recurso: cantidad_disponible} -- no un único float: una
    misma especie puede producir más de un recurso de categoría
    alimento (p.ej. hierba silvestre da raíces Y hierba). Vacío {} si
    tiene_recurso=False. Sin restricción dietética todavía -- cualquier
    entidad con Accion.COMER consume de cualquier recurso presente, sin
    mirar cuál prefiere su especie (sistema_recursos.py); eso es deuda
    técnica declarada a propósito, se conecta cuando exista una especie
    para la que de verdad importe la diferencia."""
    tiene_recurso: bool = False
    """Si esta celda tiene una planta produciendo recurso ahora mismo.
    Las celdas con tiene_recurso=False se quedan siempre con recursos={}:
    caminables, pero sin comida. DINÁMICO (sistema_flora.py,
    sistema_desastres.py): se pone a True cuando una entidad Planta
    madura coloniza la celda, a False cuando esa planta se destruye (un
    incendio). SÍ se persiste (celdas_estado) -- estado mutado por la
    partida real."""
    tiene_agua: bool = False
    """Si esta celda tiene agua potable -- capa geográfica independiente
    de la vegetación (ver docstring del módulo). No produce recurso
    alimenticio propio directamente, pero SÍ modula la producción de
    flora (bono de humedad de subsuelo, ver nucleo/flora.py:
    factor_humedad_subsuelo) y habilita Accion.BEBER. Derivado de
    tipo_agua (tipo_agua != ""), mismo patrón que tiene_recurso/
    tipo_recurso. NO se persiste: determinista a partir del campo de
    elevación y la semilla del mundo (nucleo/agua.py) -- nunca se muta
    en juego, no hay erosión ni sequías todavía."""
    fertilidad: float = 0.0
    """Abono: Accion.ALIVIARSE sobre esta celda la sube; decae con el
    tiempo (cadencia de día). Bono multiplicativo sobre la producción de
    la planta presente (sistema_flora.py) -- SOLO en celdas que ya
    tienen tiene_recurso=True, no activa recurso donde no lo había. SÍ
    se persiste -- estado mutado por la partida real."""
    en_llamas: bool = False
    """Desastres naturales: único tipo implementado es incendio, único
    bioma inflamable es Bosque. Destruye la vegetación en pie (recursos
    a 0, la Planta presente se elimina y tiene_recurso/tipo_recurso
    vuelven a False/'') e inflige daño a la vitalidad de cualquier
    entidad que siga de pie en la celda cada tick que dure. SÍ se
    persiste -- estado mutado por la partida real."""
    tipo_recurso: str = ""
    """Qué ESPECIE de planta ocupa esta celda ahora mismo (clave del
    catálogo config/flora.yaml, sección flora.especies -- por ejemplo
    'manzano', 'cactus', 'hierba_silvestre'), o "" si no hay ninguna
    (tiene_recurso=False). Un bioma puede alojar varias especies
    distintas, así que la celda necesita decir CUÁL de ellas tiene, no
    basta con su bioma. DINÁMICO, igual que tiene_recurso (propagación
    lo activa, incendio lo desactiva) -- SÍ se persiste, mismo motivo."""
    tipo_agua: str = ""
    """Qué TIPO de cuerpo de agua ocupa esta celda ahora mismo -- 'rio',
    'lago', 'poza', o "" si no hay agua (nucleo/agua.py para la
    generación completa). 'rio' es el camino de descenso de pendiente
    desde un pico de elevación; 'lago' es la cuenca donde ese descenso
    termina en un mínimo local; 'poza' es una cuenca pequeña y aislada,
    sin río que la alimente. Sin ningún consumidor mecánico real
    todavía -- la distinción existe para cuando haya fauna acuática que
    dependa de cuál es (anfibios en poza, peces en río/lago). NO se
    persiste, mismo motivo que tiene_agua -- estático de por vida una
    vez generado el mundo."""
    profundidad_agua: float = 0.0
    """Profundidad del agua PERMANENTE de esta celda, en METROS -- única
    magnitud de Celda con unidad real en vez de escala normalizada
    [0,1], a propósito: comparable con DimensionesFisicas.altura
    (también en metros), consumida por ahogamiento
    (sistema_necesidades.py) y por el bloqueo de agua profunda en el
    movimiento (sistema_movimiento.py:_mover_si_posible). 0.0 si
    tipo_agua == "" (sin agua). Se deriva de la misma geometría de
    cuenca (nucleo/agua.py:_profundidades_cuenca) para los tres tipos --
    lago/poza/río -- más profunda cerca del centro de su cuenca (o de la
    orilla, para río), casi nula en el borde. NO se persiste:
    determinista a partir del campo de elevación y la semilla del
    mundo -- nunca se muta en juego, no hay erosión ni sequías todavía.

    Distinto de profundidad_charco (más abajo): esta es agua PERMANENTE
    y geográfica; profundidad_charco es agua EFÍMERA y climática. Donde
    haga falta tratar "cualquier agua bebible ahora mismo" sin importar
    el origen, usar nucleo/agua.py:hay_agua_potable/profundidad_efectiva
    en vez de comparar este campo solo."""
    tipo_sustrato: str = ""
    """Clave del catálogo de materiales (piedra/arcilla/arena/tierra),
    derivada del bioma en generación (materiales.sustrato_por_bioma) --
    determinista, NO se persiste, mismo criterio que
    elevacion/lluvia/temperatura. La velocidad de infiltración y la
    capacidad de retención de agua de esta celda salen de las
    propiedades físicas de ESTE material, no de una tasa uniforme igual
    para cualquier terreno."""
    humedad_subsuelo: float = 0.0
    """Reserva de agua de subsuelo. Se llena con la fracción de lluvia
    que el material logra infiltrar (sistema_recursos.py:
    _actualizar_charcos), topada por materiales.<tipo_sustrato>.
    capacidad_retencion, y drena mucho más despacio que un charco.
    Para una celda con agua permanente (tiene_agua=True) se fija en
    generación al tope de capacidad_retencion de su sustrato.
    SÍ se persiste -- estado mutado por la partida real. Único
    consumidor mecánico hoy: nucleo/flora.py:factor_humedad_subsuelo."""
    deposito_mineral: str = ""
    """Vetas de mineral (ver nucleo/materiales.py). Ortogonal a
    tipo_sustrato -- una celda de sustrato 'piedra' puede además tener
    una veta de 'hierro' o 'cobre' dentro; el mineral no sustituye a la
    roca, existe dentro de ella. "" si no hay veta -- la inmensa mayoría
    de celdas de piedra. La UBICACIÓN de las vetas es determinista de la
    semilla (colocación fija en generación), pero este campo SÍ se
    persiste -- la extracción real lo vacía a "" cuando la veta se
    agota, un hecho de la partida, no de la semilla."""
    masa_mineral_restante: float = 0.0
    """Kg de mineral que quedan en esta veta -- asignada en generación
    (nucleo/zona_bioma.py, generacion_vetas.masa_inicial_por_celda_veta_kg)
    y decrementada por Accion.RECOLECTAR cuando deposito_mineral no está
    vacío (sistema_recursos.py:_resolver_recolectar). Al llegar a 0.0,
    deposito_mineral vuelve a "" (la celda queda como piedra corriente,
    sin caso especial que ningún consumidor tenga que comprobar aparte).
    0.0 si deposito_mineral == "". SÍ se persiste, mismo motivo que
    deposito_mineral."""
    profundidad_charco: float = 0.0
    """Charco efímero, en METROS, mismo criterio de unidad que
    profundidad_agua. A diferencia de esta, es agua EFÍMERA y climática,
    no geográfica: sube mientras zona.clima_actual es lluvioso/tormenta,
    baja por evaporación pasiva cuando no llueve, y se agota
    específicamente por consumo (Accion.BEBER) cuando es la única agua
    presente en la celda -- ver sistemas/sistema_recursos.py
    (_generar_charcos, _evaporar_charcos, _beber). Deliberadamente NUNCA
    tan profundo como para ahogar a nadie ni bloquear un paso -- un
    charco, por definición física, no es un cuerpo de agua hondo; no es
    una regla pensada contra ninguna especie en concreto. SÍ se
    persiste -- estado mutado por la partida real, NO el mismo motivo
    que profundidad_agua/tiene_agua (esos son deterministas de la
    semilla; esto no)."""
