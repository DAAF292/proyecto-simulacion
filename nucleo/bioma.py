"""Clasificación de bioma por elevación+lluvia+temperatura -- elevación
domina sobre el resto, lluvia/drenaje y temperatura deciden dentro del
rango medio. Función pura, mismo patrón que nucleo/ciclo_vital.py y
nucleo/clima.py.

Prioridad de reglas (árbol de decisión simple, no una fórmula ponderada
continua -- más fácil de razonar y de depurar visualmente):

1. Temperatura muy baja -> Tundra. Con relieve orográfico real la
   temperatura de las cumbres CAE por el gradiente térmico, así que una
   cumbre fría es una cumbre nevada (tundra de altura) -- por eso esta
   regla va antes que la de Montaña, no después.
2. Elevación alta (pero no congelada) -> Montaña.
3. Lluvia escasa -> Desierto (árido).
4. Lluvia abundante -> Bosque (denso).
5. Resto (elevación/temperatura/lluvia todas moderadas) -> Pradera.

Umbrales calibrados por inspección de proporciones en varias semillas
(config/clima.yaml, sección 'bioma') para que Pradera+Bosque sigan
siendo mayoría del mapa (~75/25) y Montaña/Desierto/Tundra queden como
terreno minoritario en los extremos -- decisión deliberada para no
deshacer la calibración de supervivencia ya validada, no para producir
un mapa físicamente "correcto".

Esta función SOLO decide el bioma -- una zona climática. Qué especies
de flora concretas viven dentro de cada bioma (y si un mismo bioma
aloja más de una) es una decisión completamente distinta, que vive en
config/flora.yaml y se resuelve en nucleo/zona_bioma.py -- esta función
no sabe nada de plantas, solo de clima.

Historial de diseño y decisiones: docs/historial_nucleo.md.
"""
from nucleo.celda import TipoTerreno


def clasificar_bioma(elevacion: float, lluvia: float, temperatura: float, config_bioma: dict) -> TipoTerreno:
    if temperatura < config_bioma["umbral_temperatura_tundra"]:
        return TipoTerreno.TUNDRA
    if elevacion > config_bioma["umbral_elevacion_montana"]:
        return TipoTerreno.MONTANA
    if lluvia < config_bioma["umbral_lluvia_desierto"]:
        return TipoTerreno.DESIERTO
    if lluvia > config_bioma["umbral_lluvia_bosque"]:
        return TipoTerreno.BOSQUE
    return TipoTerreno.PRADERA
