"""Componente Intencion: dato puro, sin logica.

Guarda la accion elegida por SistemaDecision en el tick mas reciente.
No tiene efecto fisico por si sola en el paso 7 -- eso llega en el
paso 8, cuando SistemaMovimiento/SistemaRecursos empiecen a leer este
componente para ejecutar de verdad lo que decide.
"""
from dataclasses import dataclass
from enum import Enum


class Accion(Enum):
    COMER = "comer"
    DORMIR = "dormir"
    DEAMBULAR = "deambular"
    CAZAR = "cazar"   # paso 12: exclusiva de depredadores (lobo)
    HUIR = "huir"     # paso 12.4: exclusiva de quien puede ser presa (gnomo)
    BEBER = "beber"   # universal, todas las especies la necesitan
    ALIVIARSE = "aliviarse"   # universal, sin recurso en el mapa
    # BUSCAR_PAREJA: universal para las cuatro especies, igual que
    # BEBER/ALIVIARSE -- se activa cuando Necesidades.impulso_reproductivo
    # baja lo bastante Y hay un conspecifico adulto de sexo opuesto
    # elegible dentro del radio de percepcion. Mueve a distancia 0 del
    # conspecifico elegido (a diferencia del sesgo gregario de DEAMBULAR,
    # que se detiene a distancia 1) -- ver sistema_movimiento.py.
    BUSCAR_PAREJA = "buscar_pareja"
    # CONSTRUIR: exclusiva de quien supera decision.umbral_consciencia_agencia
    # (gnomo hoy), mismo umbral que ya exime del sesgo de territorio y
    # gatea el uso real de Inventario -- construir es agencia consciente,
    # no instinto animal. Se resuelve en dos sistemas, mismo patrón que
    # COMER/BEBER: sistema_movimiento.py decide hacia dónde ir (crea la
    # construcción propia si no existe, navega hacia ella),
    # sistema_recursos.py transfiere materiales del Inventario una vez
    # allí.
    CONSTRUIR = "construir"
    # RECOLECTAR: convierte tipo_sustrato de la celda actual
    # (piedra/arcilla/tierra, siempre presente, no depletable) en
    # material de Inventario. Misma compuerta de consciencia que
    # CONSTRUIR. Sin desplazamiento propio (se resuelve donde ya se
    # está, como ALIVIARSE) -- el sustrato está bajo los pies de
    # cualquiera, no hay que buscarlo.
    RECOLECTAR = "recolectar"
    # ENCENDER_FUEGO: misma compuerta de consciencia que
    # CONSTRUIR/RECOLECTAR. Utilidad = 1.0 - Necesidades.confort_termico,
    # mismo patrón que el resto de necesidades físicas -- no una utilidad
    # base fija como CONSTRUIR/RECOLECTAR, porque esto SÍ responde a una
    # necesidad real (tener frío). Gateada a 0.0 si faltan piedras en
    # Agarre, no hay combustible en la celda actual, o ya hay una Fogata
    # ahí. Sin desplazamiento (como RECOLECTAR/ALIVIARSE) -- se resuelve
    # donde ya se esté.
    ENCENDER_FUEGO = "encender_fuego"
    # FABRICAR_ARMA: exclusiva de quien supera
    # decision.umbral_consciencia_agencia (gnomo hoy) -- fabricar un arma
    # es agencia consciente, no instinto. Gateada por necesidad real
    # (Necesidades.seguridad, mismo patron causal que ENCENDER_FUEGO con
    # el frio): un individuo que nunca ha sentido inseguridad real nunca
    # desarrolla interes en tallar un palo. Se resuelve donde se esta, sin
    # desplazamiento propio (como RECOLECTAR/ALIVIARSE) -- consume
    # materiales crudos apto_arma de Inventario.objetos y produce un arma
    # de nivel >= 2 (ver config/armas.yaml:recetas) en Inventario.objetos.
    FABRICAR_ARMA = "fabricar_arma"
    # Crisis mental: anulan la Utility AI normal mientras
    # PoolMental.estabilidad esté en crisis -- ver sistema_decision.py
    # para el disparador y sistema_movimiento.py para la resolución de
    # cada una. Tipología emergente de valentía/agresividad del
    # individuo, no escrita de antemano por caso concreto.
    HUIDA_ERRATICA = "huida_erratica"     # valentia baja: huye de cualquiera cercano, sin amenaza real
    CRISIS_VIOLENTA = "crisis_violenta"   # agresividad alta: se acerca a cualquiera cercano -- sin mecanica de dano todavia, deliberado
    CATATONIA = "catatonia"               # ni lo uno ni lo otro: se queda quieto, sin actuar


@dataclass
class Intencion:
    accion: Accion = Accion.DEAMBULAR
    # Transitorio por tick (armas primitivas v2, ver
    # sistema_decision.py): cuando el argmax de este tick elige RECOLECTAR
    # con el material de arma como MOTIVO REAL (el eslabon heredado elevo
    # la utilidad por 1.0 - seguridad), el reflejo cae aqui para que
    # sistema_recursos.py recolecte a Inventario.objetos; si RECOLECTAR
    # se eligio por construccion, se queda False y la resolucion no
    # recoge armas "porque se lo encuentra". NO se persiste -- se
    # recalcula cada tick, como la propia accion.
    recolectar_motivo_arma: bool = False
