"""Clasificacion de bioma por elevacion+lluvia+temperatura (fase terreno
3, informe tecnico -- referencia Dwarf Fortress: elevacion domina sobre
el resto, lluvia/drenaje y temperatura deciden dentro del rango medio).
Funcion pura, mismo patron que nucleo/ciclo_vital.py y nucleo/clima.py.

Prioridad de reglas (arbol de decision simple, no una formula ponderada
continua -- mas facil de razonar y de depurar visualmente, mismo criterio
de simplicidad que llevo a nucleo/campo_continuo.py a elegir value noise
en vez de Perlin):

1. Elevacion alta -> Montana, incondicional (una cumbre es una cumbre sin
   importar la lluvia o temperatura local -- regla dominante, igual que
   en Dwarf Fortress).
2. Temperatura muy baja -> Tundra.
3. Lluvia escasa -> Desierto (arido).
4. Lluvia abundante -> Bosque (denso).
5. Resto (elevacion/temperatura/lluvia todas moderadas) -> Pradera.

Umbrales calibrados por inspeccion de proporciones en varias semillas
(ver config/constantes.yaml, seccion 'bioma') para que Pradera+Bosque
sigan siendo mayoria del mapa (proporcion similar a la version binaria
de antes de esta fase, ~75/25) y Montana/Desierto/Tundra queden como
terreno minoritario en los extremos -- una decision deliberada, no viene
de ningun dato de referencia real: el objetivo era no deshacer sin querer
la calibracion de supervivencia ya validada, no producir un mapa
fisicamente "correcto".

Correccion posterior (discutida y confirmada con Diego, ver
nucleo/celda.py): esta funcion SOLO decide el bioma -- una zona
climatica. Que especies de flora concretas viven dentro de cada bioma (y
si un mismo bioma aloja mas de una, como Bosque con hierba silvestre y
manzano) es una decision completamente distinta, que vive en
config/constantes.yaml (seccion flora) y se resuelve en
nucleo/zona_bioma.py -- esta funcion no sabe nada de plantas, solo de
clima.
"""
from nucleo.celda import TipoTerreno


def clasificar_bioma(elevacion: float, lluvia: float, temperatura: float, config_bioma: dict) -> TipoTerreno:
    if elevacion > config_bioma["umbral_elevacion_montana"]:
        return TipoTerreno.MONTANA
    if temperatura < config_bioma["umbral_temperatura_tundra"]:
        return TipoTerreno.TUNDRA
    if lluvia < config_bioma["umbral_lluvia_desierto"]:
        return TipoTerreno.DESIERTO
    if lluvia > config_bioma["umbral_lluvia_bosque"]:
        return TipoTerreno.BOSQUE
    return TipoTerreno.PRADERA
