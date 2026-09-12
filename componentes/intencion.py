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
    # COCINAR (2026-09-08, ver docs/superpowers/specs/
    # 2026-09-08-como-cocinar-design.md): misma compuerta de consciencia
    # que CONSTRUIR/RECOLECTAR. Utilidad BASE FIJA (no derivada de una
    # necesidad, a diferencia de ENCENDER_FUEGO) -- cocinar es preparar
    # comida para más tarde, no una urgencia. Gateada a 0.0 si no hay una
    # Fogata activa en la celda o no queda nada crudo en
    # Inventario.provisiones. Sin desplazamiento -- se resuelve donde ya
    # se esté.
    COCINAR = "cocinar"
    # FABRICAR (2026-09-11, renombrada desde FABRICAR_ARMA -- ver
    # historial de conversacion de diseno, docs/superpowers/specs/ si se
    # llega a escribir spec): verbo GENERICO, mismo criterio que ya
    # aplica CONSTRUIR (Construccion.tipo abierto, resuelto en runtime)
    # -- "arma" es hoy la UNICA categoria real implementada
    # (Intencion.fabricar_categoria), no parte del nombre de la Accion.
    # Exclusiva de quien supera decision.umbral_consciencia_agencia
    # (gnomo hoy) -- fabricar es agencia consciente, no instinto. La
    # categoria "arma" esta gateada por necesidad real (Necesidades.
    # seguridad, mismo patron causal que ENCENDER_FUEGO con el frio): un
    # individuo que nunca ha sentido inseguridad real nunca desarrolla
    # interes en tallar un palo. Se resuelve donde se esta, sin
    # desplazamiento propio (como RECOLECTAR/ALIVIARSE) -- consume
    # materiales crudos apto_arma de Inventario.objetos y produce un arma
    # de nivel >= 2 (ver config/armas.yaml:recetas) en Inventario.objetos.
    # Una segunda categoria futura (herramienta) se anadiria como un
    # candidato mas al resolutor interno de sistema_decision.py (mismo
    # molde que objetivo_construccion_actual:tipos_paralelos), sin crear
    # una Accion nueva.
    FABRICAR = "fabricar"
    # SOCIALIZAR (2026-09-06, ocio consciente -- ver
    # docs/superpowers/specs/2026-09-06-ocio-consciente-socializar-design.md):
    # accion nueva e INDEPENDIENTE del sesgo gregario de DEAMBULAR (que se
    # queda exactamente igual). Compite por el tiempo de ocio cuando ninguna
    # necesidad fisica esta bajo decision.umbral_atencion_pareja; utilidad
    # modulada por Temperamento.sociabilidad/curiosidad (primer consumidor
    # real de curiosidad). Exclusiva de conscientes
    # (consciencia >= decision.umbral_consciencia_agencia). Busca a
    # CUALQUIER consciente cercano (no solo misma especie, a diferencia del
    # sesgo gregario) y al contacto a distancia 0 escribe afinidad POSITIVA
    # MUTUA en Relaciones -- ver sistema_movimiento.py:_calcular_socializar.
    SOCIALIZAR = "socializar"
    # Crisis mental: anulan la Utility AI normal mientras
    # PoolMental.estabilidad esté en crisis -- ver sistema_decision.py
    # para el disparador y sistema_movimiento.py para la resolución de
    # cada una. Tipología emergente de valentía/agresividad del
    # individuo, no escrita de antemano por caso concreto.
    HUIDA_ERRATICA = "huida_erratica"     # valentia baja: huye de cualquiera cercano, sin amenaza real
    CRISIS_VIOLENTA = "crisis_violenta"   # agresividad alta: se acerca a cualquiera cercano; a contacto real resuelve con el mismo resolutor que refugio ocupado/roce social (drena seguridad, escribe rencor)
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
    # Transitorio por tick (2026-09-11, circulo 2 "fabricacion de
    # herramientas" -- ver nucleo/herramientas.py): mismo mecanismo que
    # recolectar_motivo_arma, arriba, pero para el eslabon heredado de
    # la categoria "herramienta" de FABRICAR (RECOLECTAR elevado porque
    # falta material crudo para una herramienta, no un arma). NO se
    # persiste -- se recalcula cada tick.
    recolectar_motivo_herramienta: bool = False
    # Transitorio por tick (2026-09-12, "prioridad consciente" -- ver
    # sistema_recursos.py:_resolver_recolectar Vía 1): mismo mecanismo
    # que recolectar_motivo_arma/herramienta, retrofitado al eslabón
    # heredado de piedra_suelta para fuego (existía desde antes que este
    # patrón, 2026-08-31, sin usarlo nunca) -- Vía 1 solo agarra
    # piedra_suelta cuando fuego fue de verdad el motivo que ganó el
    # RECOLECTAR de este tick, no siempre que haya hueco en Agarre. NO
    # se persiste -- se recalcula cada tick.
    recolectar_motivo_fuego: bool = False
    # Transitorio por tick (2026-09-11, rename FABRICAR_ARMA -> FABRICAR):
    # que categoria gano el resolutor interno de FABRICAR este tick --
    # "arma" (unica categoria real hoy) o "" si Accion.FABRICAR no fue
    # la elegida. sistema_recursos.py:_resolver_fabricar ramifica por
    # este valor para saber que receta/catalogo aplicar. NO se persiste,
    # se recalcula cada tick como la propia accion.
    fabricar_categoria: str = ""
