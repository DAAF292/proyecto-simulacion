"""Mundo: el conjunto completo, representado como grafo de territorios
(informe tecnico, seccion 2.1). En fase 0 contiene un unico Territorio.
"""


class Mundo:
    def __init__(self, semilla: int, territorios: list):
        self.semilla = semilla
        self.territorios = territorios
