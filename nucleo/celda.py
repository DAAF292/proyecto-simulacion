"""Celda: unidad minima del grid. Dato puro (bioma + campos fisicos +
recursos + presencia de agua).

tipo_terreno es ahora de verdad un BIOMA (fase de correccion de biomas,
posterior a fase terreno 3 -- discutido y confirmado con Diego): hasta
este cambio, Claro y Espesura eran valores de TipoTerreno al mismo nivel
que Montana/Estepa/Tundra, como si las cinco fueran alternativas
climaticas equivalentes -- error de modelo real, no cosmetico. Un bioma
es una zona climatica (Pradera, Bosque, Desierto, Montana, Tundra); Claro
y Espesura nunca fueron eso, eran una textura LOCAL de densidad de
vegetacion dentro de un bosque real. Esa distincion ahora vive en que
ESPECIE de planta ocupa cada celda (ver componentes/planta.py) -- Bosque
puede tener hierba silvestre (sus zonas mas abiertas) o manzano (sus
zonas mas densas), dos especies dentro del mismo bioma, en vez de dos
biomas distintos.

El tipo de recurso que produce una celda ya NO se deriva de tipo_terreno
(antes: Claro -> raices, Espesura -> bayas, informe de implementacion
seccion 3.5 -- ese acoplamiento directo terreno-recurso es precisamente
lo que se corrige aqui). Se deriva de que ESPECIE de planta ocupa la
celda (Celda.tipo_recurso, ver mas abajo) -- un bioma puede alojar varias
especies posibles (config/constantes.yaml, seccion 'flora'), cada una con
su propio recurso.

tiene_agua (correccion de diseno anterior, surgida de una pregunta directa
de Diego -- ver nucleo/zona_bioma.py para la generacion): hasta ese
cambio, el agua potable era un TipoTerreno mas (RIBERA), exclusivo con
Claro y Espesura -- eso forzaba que donde hubiera agua no pudiera haber
vegetacion, y viceversa, cuando son hechos fisicos independientes. Sigue
siendo una capa ortogonal: cualquier celda, de cualquier bioma, puede
tener agua o no.

tipo_agua (correccion de diseno posterior, discutida y confirmada con
Diego -- ver nucleo/agua.py para la generacion): antes de este cambio,
`tiene_agua` era el unico dato -- toda agua era identica, un unico rio
generado como un paseo aleatorio ciego al terreno, sin relacion con
elevacion y sin distincion entre rio/lago/poza. Ahora el agua se deriva
del campo de elevacion (descenso de pendiente desde picos, cuencas donde
el descenso termina) y puede haber varios cuerpos a la vez, de tres tipos
distintos -- necesarios ya no solo para la generacion en si, sino porque
Diego anticipa fauna futura que dependa del tipo concreto (anfibios en
pozas, fauna acuatica en rios/lagos). tiene_agua se mantiene como
booleano derivado (tipo_agua != "") por el mismo criterio que
tiene_recurso/tipo_recurso: la mayoria de consumidores actuales
(Accion.BEBER, filtro de habitat del lobo) solo necesitan saber SI hay
agua, no de que tipo.
"""
from dataclasses import dataclass, field
from enum import Enum


class TipoTerreno(Enum):
    """Bioma de la celda -- zona climatica, determinada por elevacion+
    lluvia+temperatura (nucleo/bioma.py). Ya NO incluye Claro/Espesura
    como valores propios (ver docstring del modulo) -- los cinco valores
    de aqui son biomas de verdad, mutuamente excluyentes por definicion
    climatica, no por densidad de vegetacion local."""
    PRADERA = "pradera"    # lluvia y temperatura moderadas -- pastizal abierto
    BOSQUE = "bosque"      # lluvia abundante -- aloja hierba silvestre Y manzano
    DESIERTO = "desierto"  # lluvia escasa -- arido
    MONTANA = "montana"    # elevacion alta -- vegetacion escasa (liquen)
    TUNDRA = "tundra"      # temperatura muy baja -- vegetacion escasa (musgo)


@dataclass
class Celda:
    tipo_terreno: TipoTerreno
    elevacion: float = 0.0
    """Fase terreno 2: magnitud continua en [0, 1], generada por
    nucleo/campo_continuo.py (value noise). Determina el bioma junto con
    lluvia y temperatura (nucleo/bioma.py). NO se persiste: determinista
    a partir de la semilla del mundo, se regenera igual en cada carga."""
    lluvia: float = 0.0
    """Fase terreno 3: campo continuo en [0, 1], mismo generador que
    elevacion. Doble uso: (a) junto con elevacion/temperatura, decide el
    bioma de la celda al generar el mundo (nucleo/bioma.py); (b) despues
    de eso, sigue viva como dato de la celda -- sistema_flora.py la lee
    cada dia para modular cuanto produce la planta presente segun su
    preferencia de lluvia (config/constantes.yaml, seccion flora,
    'preferencia_lluvia' por especie). NO se persiste, mismo criterio que
    elevacion."""
    temperatura: float = 0.0
    """Fase terreno 3: igual que lluvia, campo continuo en [0, 1] --
    decide bioma al generar el mundo y modula produccion de flora despues
    (preferencia_temperatura por especie). NO se persiste."""
    recursos: dict = field(default_factory=dict)
    """{nombre_recurso: cantidad_disponible} -- YA NO un unico float
    (correccion de diseno, discutida y confirmada con Diego): una misma
    especie puede producir mas de un recurso de categoria alimento (por
    ejemplo hierba silvestre da raices Y hierba/pasto -- pensado para un
    futuro herbivoro de pastoreo que coma hierba en vez de raices, ver
    config/constantes.yaml seccion flora), asi que una celda necesita
    poder llevar varias cantidades a la vez, no una sola. Vacio {} si
    tiene_recurso=False. Sin restriccion dietetica todavia -- cualquier
    entidad con Accion.COMER consume de cualquier recurso presente, sin
    mirar cual prefiere su especie (sistema_recursos.py); eso es deuda
    tecnica declarada a proposito, se conecta cuando exista una especie
    para la que de verdad importe la diferencia."""
    tiene_recurso: bool = False
    """Si esta celda tiene una planta produciendo recurso ahora mismo.
    Las celdas con tiene_recurso=False se quedan siempre con recursos={}:
    caminables, pero sin comida. DINAMICO (sistema_flora.py,
    sistema_desastres.py): se pone a True cuando una entidad Planta
    madura coloniza la celda, a False cuando esa planta se destruye (un
    incendio). SI se persiste (celdas_estado) -- estado mutado por la
    partida real."""
    tiene_agua: bool = False
    """Si esta celda tiene agua potable -- capa geografica independiente
    de la vegetacion (ver docstring del modulo). No produce recurso
    alimenticio propio directamente, pero SI modula la produccion de
    flora (bono de humedad de subsuelo, ver nucleo/flora.py:
    factor_humedad_subsuelo) y habilita
    Accion.BEBER. Derivado de tipo_agua (tipo_agua != ""), mismo patron
    que tiene_recurso/tipo_recurso. NO se persiste: determinista a partir
    del campo de elevacion y la semilla del mundo (nucleo/agua.py), igual
    que elevacion/lluvia/temperatura/tipo_terreno -- nunca se muta en
    juego, no hay erosion ni sequias todavia."""
    fertilidad: float = 0.0
    """Abono: Accion.ALIVIARSE sobre esta celda la sube; decae con el
    tiempo (cadencia de dia). Bono multiplicativo sobre la produccion de
    la planta presente (sistema_flora.py) -- SOLO en celdas que ya tienen
    tiene_recurso=True, no activa recurso donde no lo habia. SI se
    persiste -- estado mutado por la partida real."""
    en_llamas: bool = False
    """Desastres naturales: unico tipo implementado es incendio, unico
    bioma inflamable es Bosque (mas combustible que el resto). Destruye
    la vegetacion en pie (recursos a 0, la Planta presente se elimina y
    tiene_recurso/tipo_recurso vuelven a False/'') e inflige dano a la
    vitalidad de cualquier entidad que siga de pie en la celda cada tick
    que dure. SI se persiste -- estado mutado por la partida real."""
    tipo_recurso: str = ""
    """Que ESPECIE de planta ocupa esta celda ahora mismo (clave del
    catalogo config/constantes.yaml, seccion flora.especies -- por
    ejemplo 'manzano', 'cactus', 'hierba_silvestre'), o "" si no hay
    ninguna (tiene_recurso=False). Reemplaza el viejo acoplamiento
    "recurso = f(tipo_terreno)" -- ahora un bioma puede alojar varias
    especies distintas (Bosque aloja hierba silvestre Y manzano), asi que
    la celda necesita decir CUAL de ellas tiene, no basta con su bioma.
    DINAMICO, igual que tiene_recurso (propagacion lo activa, incendio lo
    desactiva) -- SI se persiste, mismo motivo."""
    tipo_agua: str = ""
    """Que TIPO de cuerpo de agua ocupa esta celda ahora mismo -- 'rio',
    'lago', 'poza', o "" si no hay agua (nucleo/agua.py para la
    generacion completa). 'rio' es el camino de descenso de pendiente
    desde un pico de elevacion; 'lago' es la cuenca donde ese descenso
    termina en un minimo local; 'poza' es una cuenca pequena y aislada,
    sin rio que la alimente. Sin ningun consumidor mecanico real todavia
    (declarado con intencion, mismo criterio que los recursos de
    categoria material en flora.py): la distincion existe para cuando
    haya fauna acuatica que dependa de cual es (anfibios en poza, peces
    en rio/lago). NO se persiste, mismo motivo que tiene_agua -- estatico
    de por vida una vez generado el mundo."""
    profundidad_agua: float = 0.0
    """Profundidad del agua PERMANENTE de esta celda, en METROS -- unica
    magnitud de Celda con unidad real en vez de escala normalizada [0,1],
    a proposito: comparable con DimensionesFisicas.altura (tambien en
    metros), consumida por ahogamiento (sistema_necesidades.py) y por el
    bloqueo de agua profunda en el movimiento (sistema_movimiento.py:
    _mover_si_posible). 0.0 si tipo_agua == "" (sin agua). Se deriva de la
    MISMA geometria de cuenca (nucleo/agua.py:_profundidades_cuenca) para
    los tres tipos -- lago/poza/rio -- mas profunda cerca del centro de su
    cuenca (o de la orilla, para rio, ver _generar_riberas_rio), casi nula
    en el borde: un gradiente que emerge del relieve real en vez de
    asignarse a mano (CORRECCION DE DISENO 2026-08-21, ver docstring de
    nucleo/agua.py para el detalle completo -- version anterior de esta
    nota, que hablaba de "pieza 4 sin construir" y de rio con valor FIJO,
    quedo obsoleta con esa correccion). NO se persiste: determinista a
    partir del campo de elevacion y la semilla del mundo, igual que
    tipo_agua/tiene_agua -- nunca se muta en juego, no hay erosion ni
    sequias todavia.

    Distinto de profundidad_charco (mas abajo): esta es agua PERMANENTE
    y geografica; profundidad_charco es agua EFIMERA y climatica. Donde
    haga falta tratar "cualquier agua bebible ahora mismo" sin importar
    el origen, usar nucleo/agua.py:hay_agua_potable/profundidad_efectiva
    en vez de comparar este campo solo."""
    tipo_sustrato: str = ""
    """CÍRCULO 1 de materiales físicos (2026-08-30, ver config/materiales.yaml
    y conversación de diseño con Diego): clave del catálogo de materiales
    (piedra/arcilla/arena/tierra hoy), derivada del bioma en generación
    (materiales.sustrato_por_bioma) -- determinista, NO se persiste, mismo
    criterio que elevacion/lluvia/temperatura. Reemplaza el "decreto
    climático" anterior de _actualizar_charcos (sistema_recursos.py): la
    velocidad de infiltración y la capacidad de retención de agua de esta
    celda salen de las propiedades físicas de ESTE material, no de una
    tasa uniforme igual para cualquier terreno."""
    humedad_subsuelo: float = 0.0
    """CÍRCULO 1 de materiales físicos (2026-08-30): reserva de agua de
    subsuelo -- la "memoria hídrica profunda" que Diego señaló como
    ausente. Se llena con la fracción de lluvia que el material logra
    infiltrar (sistema_recursos.py:_actualizar_charcos), topada por
    materiales.<tipo_sustrato>.capacidad_retencion, y drena mucho más
    despacio que un charco (charcos.tasa_drenaje_humedad_subsuelo_por_tick).
    Para una celda con agua permanente (tiene_agua=True) se fija en
    generación al tope de capacidad_retencion de su sustrato -- está
    literalmente empapada por definición, sin necesidad de simularlo tick
    a tick (nucleo/zona_bioma.py). SÍ se persiste -- estado mutado por la
    partida real, mismo motivo que fertilidad/profundidad_charco. Único
    consumidor mecánico hoy: nucleo/flora.py:factor_humedad_subsuelo (bono
    de producción vegetal, sustituye al antiguo factor_ribera -- una celda
    con agua permanente da el mismo bono de siempre, pero como consecuencia
    de la ley general de humedad, no como caso especial hardcodeado)."""
    deposito_mineral: str = ""
    """Vetas de mineral (2026-08-30, ver nucleo/materiales.py y la
    conversación de diseño con Diego). Ortogonal a tipo_sustrato -- una
    celda de sustrato 'piedra' puede además tener una veta de 'hierro' o
    'cobre' dentro; el mineral no sustituye a la roca, existe dentro de
    ella (mismo criterio que tiene_agua es ortogonal al bioma). "" si no
    hay veta -- la inmensa mayoría de celdas de piedra. La UBICACIÓN de
    las vetas sigue siendo determinista de la semilla (colocación fija en
    generación), pero desde el Círculo 2 de profundidad (2026-08-30, ver
    masa_mineral_restante) este campo SÍ se persiste -- deja de ser
    puramente derivable porque la extracción real lo vacía a "" cuando la
    veta se agota, un hecho de la partida, no de la semilla.

    ALCANCE ORIGINAL, ya superado (Diego, 2026-08-30, tras señalar "cual
    es la profundidad del suelo? ahora es una celda, pero hacia donde va
    eso?"): este campo nació como la MISMA abstracción plana que ya usan
    flora y agua -- un recurso presente en la celda, sin geometría de
    profundidad real, con la decisión de un eje de profundidad de verdad
    aparcada aparte. El Círculo 1 (mecanismo multi-zona, ver CLAUDE.md)
    resolvió esa decisión: sí hay eje de profundidad (Posicion.zona_idx,
    Territorio.zonas[1]). El Círculo 2 (nucleo/cueva.py) es el primer
    consumidor mecánico real -- ver masa_mineral_restante y
    sistemas/sistema_recursos.py:_resolver_recolectar."""
    masa_mineral_restante: float = 0.0
    """CÍRCULO 2 de profundidad (2026-08-30, confirmado con Diego: las
    vetas se agotan de verdad al extraerlas, no son infinitas como
    tipo_sustrato). Kg de mineral que quedan en esta veta -- asignada en
    generación (nucleo/zona_bioma.py, generacion_vetas.
    masa_inicial_por_celda_veta_kg, PROVISIONAL) y decrementada por
    Accion.RECOLECTAR cuando deposito_mineral no está vacío
    (sistema_recursos.py:_resolver_recolectar). Al llegar a 0.0,
    deposito_mineral vuelve a "" (la celda queda como piedra corriente,
    sin caso especial que ningún consumidor tenga que comprobar aparte:
    todo el motor ya trata deposito_mineral == "" como "sin veta"). 0.0
    si deposito_mineral == "" -- mismo criterio de invariante que
    recursos/tiene_recurso (Celda.recursos vacío si tiene_recurso=False).
    SÍ se persiste, mismo motivo que deposito_mineral (ver su docstring)."""
    profundidad_charco: float = 0.0
    """Charco efimero (pieza 3 de la revision del sistema de agua pedida
    por Diego, 2026-08-21 -- "quizas la tormenta y lluvia podrian generar
    charcos en las celdas y estos despues se agotarian o se evaporan"),
    en METROS, mismo criterio de unidad que profundidad_agua. A
    diferencia de esta, es agua EFIMERA y climatica, no geografica: sube
    mientras zona.clima_actual es lluvioso/tormenta, baja por evaporacion
    pasiva cuando no llueve, y se agota especificamente por consumo
    (Accion.BEBER) cuando es la unica agua presente en la celda -- ver
    sistemas/sistema_recursos.py (_generar_charcos, _evaporar_charcos,
    _beber). Deliberadamente NUNCA tan profundo como para ahogar a nadie
    ni bloquear un paso (config.charcos.techo_profundidad_charco muy por
    debajo de cualquier altura racial actual) -- un charco, por
    definicion fisica, no es un cuerpo de agua hondo; no es una regla
    pensada contra ninguna especie en concreto (mismo criterio neutro que
    ya se aplico al redisenar profundidad_agua). SI se persiste -- estado
    mutado por la partida real, mismo motivo que fertilidad/tiene_recurso/
    en_llamas, NO el mismo motivo que profundidad_agua/tiene_agua (esos
    son deterministas de la semilla; esto no)."""
