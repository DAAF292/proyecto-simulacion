"""SistemaCapacidadFisica: gestion completa de los pools de capacidad
fisica -- vitalidad y resistencia (la herida de vitalidad al ser
capturado vive en sistema_depredacion.py, no aqui, porque depende del
propio evento de captura).

Mecanica de resistencia: mientras la intencion del tick sea CAZAR o
HUIR -- los dos verbos de "esfuerzo fisico sostenido" -- resistencia
baja a tasa_perdida_resistencia_por_esfuerzo (config, provisional). En
cualquier otra intencion, se repone con recuperacion (dimension
individual). Nota de orden: este sistema corre antes que SistemaDecision
en el bucle de main.py, asi que consume la Intencion decidida en el
tick ANTERIOR -- mismo tipo de desfase de un tick que ya tiene
documentado sistema_necesidades.py para el dormir.

Al llegar resistencia a 0.0 ("agotamiento"), este sistema no hace nada
directamente -- el efecto se aplica en sistema_decision.py, que pone a
0 la utilidad de CAZAR/HUIR mientras resistencia este agotada, forzando
a elegir otra accion en su lugar. Consecuencia emergente de la
competencia de utilidad, no una accion nueva escrita a mano.

vitalidad se repone con DimensionesFisicas.curacion, mas lenta cuanto
mas baja este Necesidades.energia -- unica interaccion cruzada entre
pools fisicos. Formula provisional, no calibrada contra el motor en
marcha: la tasa de curacion se multiplica directamente por el valor de
energia (energia=1.0 -> curacion a ritmo pleno, energia=0.0 -> curacion
detenida del todo).

Ambos pools se acotan en [0.0, 1.0], misma convencion que Necesidades.

La perdida de resistencia por esfuerzo no es la tasa bruta de config
directamente -- se divide por DimensionesFisicas.resistencia_maxima
antes de restarse: un individuo con mas aguante relativo se cansa mas
despacio con el mismo esfuerzo bruto. La regeneracion (recuperacion) NO
se toca -- ya es su propio campo individual para eso, dividir tambien
ahi duplicaria el mismo concepto dos veces.
"""
from typing import Any

from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.intencion import Accion, Intencion
from componentes.necesidades import Necesidades
from componentes.pool_fisico import PoolFisico

_ACCIONES_DE_ESFUERZO = (Accion.CAZAR, Accion.HUIR)


class SistemaCapacidadFisica:
    """Envoltorio de clase: __init__(config) + ejecutar(gestor), mismo
    patrón que el resto de sistemas de main.py:instanciar_sistemas() y
    ejecutar_tick()."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.tasa_perdida_resistencia: float = float(
            config["capacidad_fisica"]["tasa_perdida_resistencia_por_esfuerzo"]
        )

    def ejecutar(self, gestor) -> None:
        for id_entidad in gestor.entidades_con(PoolFisico, DimensionesFisicas, Necesidades, Intencion):
            pool = gestor.obtener_componente(id_entidad, PoolFisico)
            dimensiones = gestor.obtener_componente(id_entidad, DimensionesFisicas)
            necesidades = gestor.obtener_componente(id_entidad, Necesidades)
            intencion = gestor.obtener_componente(id_entidad, Intencion)

            factor_energia = necesidades.energia
            pool.vitalidad = min(1.0, pool.vitalidad + dimensiones.curacion * factor_energia)

            if intencion.accion in _ACCIONES_DE_ESFUERZO:
                perdida_fraccional = self.tasa_perdida_resistencia / dimensiones.resistencia_maxima
                pool.resistencia = max(0.0, pool.resistencia - perdida_fraccional)
            else:
                pool.resistencia = min(1.0, pool.resistencia + dimensiones.recuperacion)
