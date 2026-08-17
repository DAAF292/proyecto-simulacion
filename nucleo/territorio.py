"""Territorio: unidad geografica neutra, unidad de viaje y de asignacion
de nivel de detalle (informe tecnico, seccion 2.1). En fase 0 contiene una
unica ZonaBioma (el bosque); el contenedor existe igualmente completo
porque asi lo pide la arquitectura ya decidida, no porque haga falta hoy.
"""


class Territorio:
    def __init__(self, nombre: str, zonas_bioma: list):
        self.nombre = nombre
        self.zonas_bioma = zonas_bioma
