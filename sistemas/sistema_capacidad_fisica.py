"""SistemaCapacidadFisica (Bloque C del plan de adaptacion a
criatura.docx, seccion 3.2 y seccion 6): gestion completa de los pools
de capacidad fisica -- vitalidad y resistencia. Bloque C1 cubria solo la
reposicion; Bloque C2 anade aqui el consumo de resistencia por esfuerzo
sostenido (la herida de vitalidad al ser capturado vive en
sistema_depredacion.py, no aqui, porque depende del propio evento de
captura).

Mecanica de resistencia (Bloque C2, propuesta discutida y confirmada con
Diego antes de escribir esto -- criatura.docx la dejaba como pendiente
explicito, sin mecanica de aplicacion definida): mientras la intencion
del tick sea CAZAR o HUIR -- los dos verbos de "esfuerzo fisico
sostenido" que nombra criatura.docx 3.2 -- resistencia baja a
tasa_perdida_resistencia_por_esfuerzo (config, provisional). En cualquier
otra intencion, se repone con recuperacion (dimension individual), igual
que en el Bloque C1. Nota de orden: este sistema corre antes que
SistemaDecision en el bucle de main.py, asi que consume la Intencion
decidida en el tick ANTERIOR -- mismo tipo de desfase de un tick que ya
tiene documentado sistema_necesidades.py para el dormir, no es nuevo.

Al llegar resistencia a 0.0 ("agotamiento"), este sistema no hace nada
directamente -- el efecto se aplica en sistema_decision.py, que pone a
0 la utilidad de CAZAR/HUIR mientras resistencia este agotada, forzando
a elegir otra accion en su lugar. Un lobo agotado no puede seguir
persiguiendo indefinidamente; un gnomo agotado no puede seguir huyendo
indefinidamente -- consecuencia emergente de la competencia de utilidad,
no una accion nueva escrita a mano.

vitalidad se repone con DimensionesFisicas.curacion, mas lenta cuanto
mas baja este Necesidades.energia -- unica interaccion cruzada
confirmada entre pools fisicos (criatura.docx, seccion 6: "un cuerpo mal
descansado cicatriza peor"). Formula provisional, no calibrada contra el
motor en marcha: la tasa de curacion se multiplica directamente por el
valor de energia (energia=1.0 -> curacion a ritmo pleno, energia=0.0 ->
curacion detenida del todo).

Ambos pools se acotan en [0.0, 1.0], misma convencion que Necesidades.

Escalares de techo (correccion posterior, discutida y confirmada con
Diego -- resistencia_maxima llevaba desde el Bloque C1 sin ningun
consumidor real, mismo hueco que vitalidad_maxima en
sistema_depredacion.py): la perdida de resistencia por esfuerzo ya no es
la tasa bruta de config directamente -- se divide por
DimensionesFisicas.resistencia_maxima antes de restarse. Mismo criterio
que vitalidad: un individuo con mas aguante relativo se cansa mas
despacio con el mismo esfuerzo bruto. La regeneracion (recuperacion) NO
se toca -- ya es su propio campo individual para eso, dividir tambien
ahi duplicaria el mismo concepto dos veces.
"""
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.intencion import Accion, Intencion
from componentes.necesidades import Necesidades
from componentes.pool_fisico import PoolFisico

_ACCIONES_DE_ESFUERZO = (Accion.CAZAR, Accion.HUIR)


def actualizar(gestor, config: dict) -> None:
    tasa_perdida_resistencia = config["capacidad_fisica"]["tasa_perdida_resistencia_por_esfuerzo"]

    for id_entidad in gestor.entidades_con(PoolFisico, DimensionesFisicas, Necesidades, Intencion):
        pool = gestor.obtener_componente(id_entidad, PoolFisico)
        dimensiones = gestor.obtener_componente(id_entidad, DimensionesFisicas)
        necesidades = gestor.obtener_componente(id_entidad, Necesidades)
        intencion = gestor.obtener_componente(id_entidad, Intencion)

        factor_energia = necesidades.energia
        pool.vitalidad = min(1.0, pool.vitalidad + dimensiones.curacion * factor_energia)

        if intencion.accion in _ACCIONES_DE_ESFUERZO:
            perdida_fraccional = tasa_perdida_resistencia / dimensiones.resistencia_maxima
            pool.resistencia = max(0.0, pool.resistencia - perdida_fraccional)
        else:
            pool.resistencia = min(1.0, pool.resistencia + dimensiones.recuperacion)
