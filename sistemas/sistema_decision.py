"""SistemaDecision (paso 7): Utility AI minima. Calcula, cada tick, cual
de las tres acciones candidatas (comer, dormir, deambular) tiene mayor
utilidad para cada entidad, y la guarda en su componente Intencion.

No ejecuta nada fisico todavia -- comer y deambular necesitan movimiento
y consumo de recursos, que llegan en el paso 8. Este sistema solo decide.

Utilidad v1 (deliberadamente simple, sin personalidad ni histeresis --
ver informe de implementacion para el razonamiento de por que se dejan
fuera de esta primera version):
  utilidad(comer)      = hambre
  utilidad(dormir)      = energia
  utilidad(deambular)  = utilidad_deambular_base (constante, config)

Empate se resuelve con prioridad fija (comer > dormir > deambular), no
con el rng, para no gastar tiradas del generador sembrado en algo que
no lo necesita.
"""
from componentes.intencion import Accion, Intencion
from componentes.necesidades import Necesidades


def actualizar(gestor, config: dict) -> None:
    base_deambular = config["decision"]["utilidad_deambular_base"]

    for id_entidad in gestor.entidades_con(Necesidades, Intencion):
        necesidades = gestor.obtener_componente(id_entidad, Necesidades)
        intencion = gestor.obtener_componente(id_entidad, Intencion)

        candidatas = (
            (necesidades.hambre, Accion.COMER),
            (necesidades.energia, Accion.DORMIR),
            (base_deambular, Accion.DEAMBULAR),
        )
        # max() con esta lista respeta el orden de prioridad en empates
        # porque conserva el primer maximo encontrado.
        _, elegida = max(candidatas, key=lambda par: par[0])
        intencion.accion = elegida
