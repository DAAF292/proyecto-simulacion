"""
sistemas/sistema_movimiento.py

Sistema de cinemática, fricción espacial y desplazamiento local (Fase 2).
Resuelve el movimiento ortogonal condicionado por intenciones (COMER, BEBER,
CAZAR, HUIR, BUSCAR_PAREJA, DEAMBULAR), aplicando restricciones de relieve,
profundidad de agua y drenaje de resistencia por sprint y desnivel positivo.
"""

from __future__ import annotations

import random
from typing import Any

from componentes.agarre import Agarre
from componentes.capacidad_mental import CapacidadMental
from componentes.construccion import Construccion
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Especie, Identidad
from componentes.intencion import Accion, Intencion
from componentes.inventario import Inventario
from componentes.memoria_espacial import MemoriaEspacial
from componentes.necesidades import Necesidades
from componentes.necromasa import Necromasa
from componentes.pool_fisico import PoolFisico
from componentes.pool_mental import PoolMental
from componentes.posicion import Posicion
from componentes.temperamento import Temperamento
# Gestacion vive en su propio módulo (componentes/gestacion.py, ver su
# docstring) para no mezclar el rasgo fijo de por vida (Reproduccion) con
# el estado de un embarazo concreto.
from componentes.gestacion import Gestacion
from componentes.reproduccion import Reproduccion
from componentes.relaciones import Relaciones
from nucleo.agua import hay_agua_potable, profundidad_agua_potable
from nucleo.amenaza import posicion_amenaza_mas_cercana
from nucleo.armas import bono_ofensivo_arma, mayor_nivel_arma, nivel_arma, objetos_arma
from nucleo.asentamiento import almacen_cercano, asentamiento_de
from nucleo.conflicto import ResultadoDisputa, resolver_disputa
from nucleo.disposicion import contar_conspecificos_cercanos
from nucleo.indice_espacial import construir_indice_espacial
from nucleo.intercambio import transferir_recurso
from nucleo.inventario import espacio_disponible_kg, espacio_disponible_provisiones_kg
from nucleo.manada import manada_de
from nucleo.parentesco import es_familia_directa
from nucleo.construccion import (
    construccion_completada_de_asentamiento,
    construccion_propia,
    espacio_disponible_para_construir,
    huella_m2_para,
    material_suficiente_para,
    objetivo_construccion_actual,
)
from nucleo.entidad import GestorEntidades, crear_construccion
from nucleo.memoria import (
    capacidad_memoria,
    objetivo_recordado,
    registrar_recuerdo,
)
from nucleo.relaciones import ajustar_afinidad, capacidad_vinculos
from nucleo.mundo import Mundo
from nucleo.percepcion import radio_efectivo_por_peso, radio_individual
from nucleo.sonido import emitir_sonido, sonido_mas_cercano
from nucleo.relieve import costo_resistencia_por_pendiente, pendiente_maxima_transitable


class SistemaMovimiento:
    """
    Ejecuta el desplazamiento físico de las entidades sobre el grid en la Fase 2.
    """

    def __init__(self, config: dict[str, Any], rng: random.Random) -> None:
        self.config = config
        self.rng = rng
        # IndiceEspacial del tick en curso (2026-09-08) -- None hasta la
        # primera llamada a ejecutar(); los metodos _calcular_* que lo
        # consultan lo pasan tal cual a las funciones de nucleo/*.py, que
        # con indice=None hacen su propio escaneo interno (comportamiento
        # identico a antes). Permite llamar a _calcular_* directamente en
        # tests aislados sin pasar por ejecutar() primero.
        self._indice_actual = None
        # Contadores de actividad para la verificacion contra el motor real
        # (BOSQUE_AUTO_TICKS) y los tests dirigidos: cuantas veces este
        # sistema resolvio un roce social y cuantas un CRISIS_VIOLENTA con
        # contacto real (2026-09-06, conflicto verbal). Solo observacion,
        # ningun camino de decision los lee.
        self._stats_roce_social_resueltos: int = 0
        self._stats_crisis_violenta_contacto: int = 0
        # Robo y compartir por confianza (2026-09-07, circulos 3/4 del
        # arco "robo/intercambio de recursos"). Solo observacion.
        self._stats_robos_intentados: int = 0
        self._stats_robos_exitosos: int = 0
        self._stats_robos_material_intentados: int = 0
        self._stats_robos_material_exitosos: int = 0
        self._stats_robos_arma_intentados: int = 0
        self._stats_robos_arma_exitosos: int = 0
        self._stats_compartir_confianza: int = 0
        # Memoria espacial compartida (2026-09-06, ver spec
        # docs/superpowers/specs/2026-09-06-memoria-espacial-compartida-design.md):
        # cuantos recuerdos de verdad se transfirieron entre conscientes y
        # el detalle (receptor, tipo, x, y) para poder confirmar contra la
        # BD (componentes_estado) que algun consciente termino con una
        # coordenada que el mismo nunca visito directamente. Solo
        # observacion, ningun camino de decision los lee.
        self._stats_memoria_compartida_transferencias: int = 0
        self._stats_memoria_transferida_detalle: set[tuple[int, str, int, int]] = set()
        # Ocio consciente / SOCIALIZAR (2026-09-06, ver spec
        # docs/superpowers/specs/2026-09-06-ocio-consciente-socializar-design.md):
        # cuantas resoluciones de contacto a distancia 0 aplico esta pieza, y
        # que pares DIRIGIDOS (autor -> otro) recibieron afinidad positiva por
        # ella -- para la verificacion obligatoria contra BOSQUE_AUTO_TICKS:
        # confirmar que Relaciones muestra ganancias positivas atribuibles a
        # SOCIALIZAR, distintas de amistad por convivencia / afinidad por
        # concepcion. Solo observacion, ningun camino de decision los lee.
        self._stats_socializar_contacto: int = 0
        self._stats_socializar_afinidad_pares: set[tuple[int, int]] = set()
        # Sonido fisico como pista de caza (2026-09-06, circulo 4b -- ver
        # spec docs/superpowers/specs/2026-09-06-sonido-fisico-caza-design.md):
        # cuantas veces el fallback de sonido dentro de _calcular_caza dirigio
        # el movimiento, y de esas cuantas apuntaban a una presa real (caza),
        # a una Necromasa comestible (carroña) o a nada (pista falsa) -- para
        # la verificacion obligatoria contra BOSQUE_AUTO_TICKS. Solo
        # observacion, ningun camino de decision los lee.
        self._stats_sonido_caza_fallback_usos: int = 0
        self._stats_sonido_caza_fallback_caza: int = 0
        self._stats_sonido_caza_fallback_carrona: int = 0
        self._stats_sonido_caza_fallback_nulo: int = 0
        # Cohesion de manada en el fallback de caza (2026-09-10, sustituye
        # al aullido de caza -- ver CLAUDE.md "Aullido de caza en manada,
        # revertido" y spec docs/superpowers/specs/
        # 2026-09-10-cohesion-manada-fallback-caza-design.md): cuantas
        # veces un cazador sin presa valida propia se dejo llevar hacia el
        # centro de su Manada en vez de caer directo a sonido/paso
        # aleatorio -- para la verificacion obligatoria contra
        # BOSQUE_AUTO_TICKS. Solo observacion, ningun camino de decision
        # lo lee.
        self._stats_manada_cohesion_fallback_caza: int = 0
        # Rumor social (2026-09-06, circulo 5a -- ver spec
        # docs/superpowers/specs/2026-09-06-rumor-social-design.md): cuantos
        # rumores se propagaron de verdad (cada direccion emisor->receptor que
        # disparo con la sociabilidad del emisor y encontro un tercero candidato)
        # y que pares (receptor, tercero) recibieron una opinion sobre un tercero
        # que el receptor NO tenia antes (evidencia de "opinion de segunda mano"
        # pura, nunca formada directamente) -- para la verificacion obligatoria
        # contra BOSQUE_AUTO_TICKS. Solo observacion, ningun camino de decision
        # los lee.
        self._stats_rumores_propagados: int = 0
        self._stats_rumor_terceros_nuevos: set[tuple[int, int]] = set()
        # Deduplicacion de conflicto por tick (fix 2026-09-07, encontrado por
        # revision de codigo independiente): _resolver_conflicto_entre tiene
        # TRES disparadores (refugio ocupado, roce social, CRISIS_VIOLENTA por
        # contacto) que no se coordinaban entre si -- el mismo par podia
        # resolverse dos veces en el mismo tick (p.ej. roce social lo resuelve
        # probabilisticamente y CRISIS_VIOLENTA lo resuelve de forma
        # determinista al contacto), doblando el drenaje de seguridad y el
        # rencor escrito para un solo suceso real. Se reinicia en cada
        # ejecutar() (un tick); _resolver_conflicto_entre consulta y actualiza
        # este set como primer paso, sin importar quien lo invoque.
        self._pares_conflicto_resueltos_este_tick: set[frozenset[int]] = set()
        self._cachear_configuracion()

    def _cachear_configuracion(self) -> None:
        """Extrae parámetros de percepción, relieve, fricción y costes."""
        cfg_per = self.config.get("percepcion", {})
        self.radio_min: int = int(cfg_per.get("radio_minimo_celdas", 0))
        self.radio_max: int = int(cfg_per.get("radio_maximo_celdas", 4))
        # Radio propio de BUSCAR_PAREJA (2026-09-06/07, PR #19 -- ver
        # config/comportamiento.yaml para el detalle completo) y de BEBER
        # (2026-09-07, mismo patron aplicado a la investigacion de
        # estabilidad de poblacion): mayores que el generico de
        # comida/amenaza, sin tocarlo.
        self.radio_min_pareja: int = int(cfg_per.get("radio_minimo_pareja_celdas", 3))
        self.radio_max_pareja: int = int(cfg_per.get("radio_maximo_pareja_celdas", 12))
        self.radio_min_agua: int = int(cfg_per.get("radio_minimo_agua_celdas", 2))
        self.radio_max_agua: int = int(cfg_per.get("radio_maximo_agua_celdas", 8))
        # Radio propio de CAZAR (2026-09-09, TERCER intento aislado -- ver
        # CLAUDE.md "Intento real de radio de caza + preferencia por
        # presa" y su segundo intento con formula de tasa, ambos
        # revertidos por perjudicar la frecuencia de caza real. Ninguno
        # de los dos probo el radio EN SOLITARIO, sin ninguna preferencia
        # por valor -- este circulo lo aisla: mismo patron ya usado por
        # BEBER/BUSCAR_PAREJA (radio propio, mayor que el generico), pero
        # la eleccion de presa sigue siendo "la mas cercana" sin cambios
        # -- solo se amplia lo que el lobo PERCIBE, no como elige entre lo
        # percibido. Mismo rango moderado ya usado en el primer intento
        # (Diego: "ajustar... pero tampoco pasarnos").
        self.radio_min_caza: int = int(cfg_per.get("radio_minimo_caza_celdas", 1))
        self.radio_max_caza: int = int(cfg_per.get("radio_maximo_caza_celdas", 7))

        cfg_rel = self.config.get("relieve", {})
        self.pend_min: float = float(cfg_rel.get("pendiente_minima_transitable", 0.05))
        self.pend_max: float = float(cfg_rel.get("pendiente_maxima_transitable", 0.22))
        # Retenido como dict, no como escalar suelto, para pasarlo tal
        # cual a nucleo.relieve.costo_resistencia_por_pendiente() en
        # _aplicar_movimiento -- evita reimplementar inline la formula de
        # una funcion ya centralizada (mismo riesgo de divergencia que el
        # proyecto se advierte a si mismo en nucleo/percepcion.py y
        # nucleo/disposicion.py).
        self.cfg_relieve: dict[str, Any] = cfg_rel

        cfg_mov = self.config.get("movimiento", {})
        self.coste_sprint: float = float(cfg_mov.get("coste_resistencia_sprint", 0.08))
        self.umbral_agotamiento: float = float(
            cfg_mov.get("umbral_resistencia_agotamiento", 0.05)
        )

        cfg_mem = self.config.get("memoria", {})
        self.factor_error_memoria: float = float(
            cfg_mem.get("factor_error_por_distancia", 0.3)
        )

        self.dist_deseada_conspecifico: int = int(
            self.config.get("social", {}).get("distancia_deseada_conspecifico", 1)
        )
        self.dist_deseada_territorio: int = int(
            self.config.get("social", {}).get("distancia_deseada_territorio", 1)
        )
        self.umbral_consciencia_agencia: float = float(
            self.config.get("decision", {}).get("umbral_consciencia_agencia", 0.3)
        )
        # Almacén de asentamiento -- ver nucleo/asentamiento.py y
        # nucleo/construccion.py:objetivo_construccion_actual.
        self.radio_cluster_asentamiento: int = int(
            self.config.get("asentamiento", {}).get("radio_cluster_celdas", 6)
        )
        # Conflicto por refugio ocupado -- ver nucleo/conflicto.py.
        self.config_conflicto: dict[str, Any] = self.config.get("conflicto", {})
        self.drenaje_seguridad_perdedor: float = float(
            self.config_conflicto.get("drenaje_seguridad_perdedor", 0.3)
        )
        self.drenaje_seguridad_enfrentamiento: float = float(
            self.config_conflicto.get("drenaje_seguridad_enfrentamiento", 0.2)
        )
        # Roce social (2026-09-06, conflicto verbal -- ver
        # docs/superpowers/specs/2026-09-06-conflicto-verbal-design.md):
        # probabilidad base de friccion entre dos conscientes que comparten
        # celda, mas los pesos de agresividad combinada y de estres
        # (1 - PoolMental.estabilidad del mas inestable de los dos) como
        # moduladores continuos -- mismo pool que dispara la crisis, aqui
        # sin umbral binario. PROVISIONAL, sin calibrar.
        self.probabilidad_base_roce_social: float = float(
            self.config_conflicto.get("probabilidad_base_roce_social", 0.01)
        )
        self.peso_agresividad_roce: float = float(
            self.config_conflicto.get("peso_agresividad_roce", 0.05)
        )
        self.peso_estres_roce: float = float(
            self.config_conflicto.get("peso_estres_roce", 0.05)
        )
        # Robo (2026-09-07, circulo 3 del arco "robo/intercambio de
        # recursos" -- ver docs/superpowers/specs/
        # 2026-09-07-robo-compartir-confianza-design.md). PROVISIONAL,
        # sin calibrar.
        self.umbral_saciedad_para_robar: float = float(
            self.config_conflicto.get("umbral_saciedad_para_robar", 0.3)
        )
        self.probabilidad_base_robo: float = float(
            self.config_conflicto.get("probabilidad_base_robo", 0.05)
        )
        # Robo de materiales/armas (2026-09-11, extension mas alla de
        # comida -- ver docstring de _intentar_robo_material/
        # _intentar_robo_arma). PROVISIONAL.
        self.probabilidad_base_robo_material: float = float(
            self.config_conflicto.get("probabilidad_base_robo_material", 0.05)
        )
        self.urgencia_robo_material: float = float(
            self.config_conflicto.get("urgencia_robo_material", 0.5)
        )
        self.probabilidad_base_robo_arma: float = float(
            self.config_conflicto.get("probabilidad_base_robo_arma", 0.05)
        )
        # Capacidad de carga compartida (contenidos+objetos) -- ver
        # nucleo/inventario.py:espacio_disponible_kg. Necesaria para topar
        # cuanto puede recibir un ladron de material/arma.
        self.fraccion_carga_maxima: float = float(
            self.config.get("inventario", {}).get("fraccion_carga_maxima", 0.25)
        )
        self.peso_objeto_kg: dict[str, Any] = self.config.get("peso_objeto_kg", {})
        # Capacidad de provisiones (2026-09-07, ver componentes/inventario.py:
        # Inventario.provisiones) -- necesaria aqui para topar cuanto puede
        # recibir un ladron o un receptor de reparto por confianza.
        self.fraccion_provisiones_maxima: float = float(
            self.config.get("inventario", {}).get("fraccion_provisiones_maxima", 0.05)
        )
        # Capacidad de construcción por celda -- ver
        # config/materiales.yaml sección construccion y
        # nucleo/construccion.py:espacio_disponible_para_construir.
        self.config_construccion: dict[str, Any] = self.config.get("construccion", {})
        # Armas primitivas v2 (2026-09-03, ver config/armas.yaml y
        # nucleo/armas.py): catalogo y recetas para calcular el componente
        # ofensivo del arma empunada en las disputas (nucleo/conflicto.py).
        self.config_armas: dict[str, Any] = self.config.get("armas", {})
        self.catalogo_materiales: dict[str, Any] = self.config.get("materiales", {})
        self.recetas_armas: list[dict[str, Any]] = self.config_armas.get("recetas", [])

        # Rencor por refugio ocupado (2026-09-04, ver componentes/relaciones.py
        # y nucleo/relaciones.py): magnitud NEGATIVA que ajusta cada disputa
        # sobre el Relaciones del consciente. PROVISIONAL.
        self.config_relaciones: dict[str, Any] = self.config.get("relaciones", {})
        self.delta_rencor_disputa: float = float(
            self.config_relaciones.get("delta_rencor_disputa", -0.2)
        )
        # Afinidad POSITIVA de SOCIALIZAR al contacto (2026-09-06, ocio
        # consciente -- ver config/relaciones.yaml). PROVISIONAL.
        self.delta_afinidad_socializar: float = float(
            self.config_relaciones.get("delta_afinidad_socializar", 0.02)
        )
        # Peso de credibilidad del rumor (2026-09-06, rumor social -- ver
        # config/relaciones.yaml y spec
        # docs/superpowers/specs/2026-09-06-rumor-social-design.md): fraccion
        # del camino que el receptor recorre hacia la opinion reportada del
        # emisor, no una sustitucion completa. PROVISIONAL, sin calibrar.
        self.peso_credibilidad_rumor: float = float(
            self.config_relaciones.get("peso_credibilidad_rumor", 0.15)
        )
        # Compartir por confianza (2026-09-07, circulo 4 del arco
        # "robo/intercambio de recursos" -- ver docs/superpowers/specs/
        # 2026-09-07-robo-compartir-confianza-design.md). PROVISIONAL,
        # sin calibrar.
        self.umbral_confianza_compartir: float = float(
            self.config_relaciones.get("umbral_confianza_compartir", 0.3)
        )
        self.probabilidad_base_compartir_confianza: float = float(
            self.config_relaciones.get("probabilidad_base_compartir_confianza", 0.05)
        )
        self.saciedad_maxima_para_recibir_compartido: float = float(
            self.config_relaciones.get("saciedad_maxima_para_recibir_compartido", 0.5)
        )

        # Coste de forrajeo vs. beneficio -- ver docstring de
        # _calcular_caza.
        cfg_dep = self.config.get("depredacion", {})
        self.fraccion_minima_peso_presa: float = float(
            cfg_dep.get("fraccion_minima_peso_presa", 0.001)
        )
        self.peso_referencia_deteccion_plena: float = float(
            cfg_dep.get("peso_referencia_deteccion_plena", 0.1)
        )
        # (2026-09-04) umbral y bono de agresividad PROPIOS de la amenaza
        # -- ver el comentario de config/combate.yaml. Mismos valores que
        # usa el drenaje de seguridad en sistema_necesidades.py y el deseo
        # de empunar arma en sistema_decision.py -- una sola nocion de
        # amenaza en todo el motor.
        self.umbral_disposicion_amenaza: float = float(
            cfg_dep.get("umbral_amenaza_percibida", 0.65)
        )
        self.peso_agresividad_amenaza: float = float(
            cfg_dep.get("peso_agresividad_amenaza", 0.3)
        )
        # (2026-09-05) valentia PROPIA del que percibe -- ver
        # nucleo/disposicion.py. Mismo valor en los tres consumidores.
        self.factor_valentia_amenaza: float = float(
            cfg_dep.get("factor_valentia_amenaza", 0.0)
        )
        # Techo de presa por manada (2026-09-05, ver
        # docs/superpowers/specs/2026-09-05-especie-caballo-design.md):
        # un cazador SOLITARIO sigue limitado a presas mas ligeras que el
        # mismo (comportamiento original, sin cambios). Un cazador con
        # aliados cazando activamente cerca (mismo dato y mismo radio que
        # ya usa el bono de exito de sistema_depredacion.py) puede
        # perseguir presas mas pesadas -- el GRUPO decide que vale la
        # pena perseguir, no el individuo solo. radio_apoyo_grupal
        # reutilizado tal cual (misma clave de config, un solo radio de
        # cooperacion en todo el motor).
        self.radio_apoyo_grupal: int = int(
            self.config.get("social", {}).get("radio_apoyo_grupal", 3)
        )
        self.factor_ampliacion_techo_manada: float = float(
            cfg_dep.get("factor_ampliacion_techo_manada", 1.0)
        )
        # Sonido fisico (2026-09-06, circulo 4a -- ver
        # docs/superpowers/specs/2026-09-06-sonido-fisico-amenaza-design.md):
        # techo de escaneo (no el alcance real) para la tercera fuente de
        # amenaza. PROVISIONAL, mismo valor cacheado en los tres
        # consumidores de nucleo/amenaza.py.
        self.radio_busqueda_maxima_sonido: int = int(
            self.config.get("sonido", {}).get("radio_busqueda_maxima_sonido", 0)
        )

    def ejecutar(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        reloj: Any | None = None,
        indice=None,
    ) -> None:
        """
        Ejecuta el paso de movimiento para todas las criaturas con Intencion y Posicion.

        reloj: opcional, para resolver el rencor del conflicto por refugio
        ocupado con el tick actual (ultima_actualizacion_tick de los
        vínculos, nucleo/relaciones.py). Sin reloj (tests aislados) se usa
        tick 0.

        indice (2026-09-08, nucleo/indice_espacial.py): IndiceEspacial ya
        construido, opcional -- si no se pasa, se construye uno interno
        (mismo criterio que _pares_conflicto_resueltos_este_tick: estado
        de este tick, guardado en self y leido por los metodos _calcular_*
        internos en vez de enhebrarlo como parametro explicito por cada
        uno de ellos). Refleja el cierre del tick anterior -- todo el
        calculo de intencion/movimiento de este tick ve la misma foto,
        con independencia del orden en que se procese cada entidad.
        """
        self._indice_actual = indice if indice is not None else construir_indice_espacial(gestor)
        tick_actual: int = reloj.tick_actual if reloj is not None else 0
        # Reiniciado cada tick -- ver docstring en __init__ sobre por que
        # _resolver_conflicto_entre necesita saber que pares ya se resolvieron
        # este mismo tick, sin importar por cual de sus tres disparadores.
        self._pares_conflicto_resueltos_este_tick = set()

        # Roce social, memoria compartida, rumor social, robo y compartir
        # por confianza (2026-09-06/07, ver docs/superpowers/specs/
        # 2026-09-06-memoria-espacial-compartida-design.md,
        # 2026-09-06-rumor-social-design.md y
        # 2026-09-07-robo-compartir-confianza-design.md): UNA VEZ por
        # tick, no por entidad, sobre las posiciones tal como quedaron al
        # cierre del tick anterior -- mismo criterio que el conflicto por
        # refugio ocupado (todos resuelven sobre la posicion vigente al
        # empezar el tick, no sobre una posicion a medio actualizar por el
        # propio bucle). No compiten por ninguna Accion: son chequeos
        # pasivos independientes de que este haciendo cada consciente ese
        # tick. La agrupacion por celda se construye UNA sola vez y se
        # comparte entre los cinco procesadores.
        por_celda = self._agrupar_conscientes_por_celda(gestor)
        self._procesar_roce_social(gestor, mundo, tick_actual, por_celda)
        self._procesar_memoria_compartida(gestor, por_celda)
        self._procesar_rumor(gestor, por_celda, tick_actual)
        self._procesar_robo(gestor, mundo, tick_actual, por_celda)
        self._procesar_compartir_confianza(gestor, por_celda)

        entidades = sorted(
            gestor.entidades_con(Intencion, Posicion, DimensionesFisicas, Identidad)
        )

        for eid in entidades:
            intencion = gestor.obtener_componente(eid, Intencion)
            pos = gestor.obtener_componente(eid, Posicion)
            dims = gestor.obtener_componente(eid, DimensionesFisicas)
            ident = gestor.obtener_componente(eid, Identidad)
            pf = gestor.obtener_componente(eid, PoolFisico)
            mem = gestor.obtener_componente(eid, MemoriaEspacial)
            cap_mental = gestor.obtener_componente(eid, CapacidadMental)
            temperamento = gestor.obtener_componente(eid, Temperamento)

            if intencion is None or pos is None or dims is None or ident is None:
                continue

            # Zona resuelta POR ENTIDAD, no una unica variable fija a
            # zonas[0] -- dos entidades en la misma llamada a ejecutar()
            # pueden estar en zonas distintas (ver
            # componentes/posicion.py:zona_idx).
            zona = mundo.territorio.zonas[pos.zona_idx]

            # Bloqueo temporal por extenuación muscular extrema
            if pf is not None and pf.resistencia <= self.umbral_agotamiento:
                continue

            radio = radio_individual(dims.agudeza_sensorial, self.radio_min, self.radio_max)
            accion = intencion.accion

            dx, dy = 0, 0

            if accion == Accion.DORMIR:
                dx, dy = self._calcular_dormir(
                    gestor, mundo, eid, ident.especie, pos.x, pos.y, radio, mem, cap_mental,
                    temperamento, pos.zona_idx, tick_actual,
                )
            elif accion == Accion.HUIR:
                dx, dy = self._calcular_huida(
                    gestor, zona, eid, pos.x, pos.y, dims.peso, radio, pos.zona_idx,
                    temperamento, tick_actual, dims.agudeza_sensorial,
                )
            elif accion == Accion.CAZAR:
                radio_caza = radio_individual(
                    dims.agudeza_sensorial, self.radio_min_caza, self.radio_max_caza
                )
                dx, dy = self._calcular_caza(
                    gestor, eid, ident.especie, pos.x, pos.y, dims.peso, radio_caza, pos.zona_idx,
                    zona=zona, tick_actual=tick_actual, agudeza_sensorial=dims.agudeza_sensorial,
                    mundo=mundo,
                )
            elif accion == Accion.COMER:
                dx, dy = self._calcular_forrajeo(
                    gestor, mundo, eid, zona, ident.especie, pos.x, pos.y, radio, mem, cap_mental, pos.zona_idx
                )
            elif accion == Accion.BEBER:
                radio_agua = radio_individual(
                    dims.agudeza_sensorial, self.radio_min_agua, self.radio_max_agua
                )
                dx, dy = self._calcular_hidratacion(
                    zona, pos.x, pos.y, dims.altura, radio_agua, mem, cap_mental
                )
            elif accion == Accion.BUSCAR_PAREJA:
                radio_pareja = radio_individual(
                    dims.agudeza_sensorial, self.radio_min_pareja, self.radio_max_pareja
                )
                dx, dy = self._calcular_pareja(
                    gestor, eid, ident.especie, pos.x, pos.y, radio_pareja, pos.zona_idx
                )
            elif accion == Accion.CONSTRUIR:
                dx, dy = self._calcular_construir(
                    gestor, mundo, eid, ident.especie, pos.x, pos.y, radio, mem, cap_mental,
                    temperamento, pos.zona_idx,
                )
            elif accion == Accion.DEAMBULAR:
                dx, dy = self._calcular_deambular(
                    gestor, mundo, eid, ident.especie, pos.x, pos.y, radio, mem, cap_mental,
                    temperamento, pos.zona_idx,
                )
            elif accion == Accion.SOCIALIZAR:
                dx, dy = self._calcular_socializar(
                    gestor, mundo, eid, pos.x, pos.y, radio, pos.zona_idx, tick_actual,
                )
            elif accion == Accion.HUIDA_ERRATICA:
                dx, dy = self._calcular_huida_erratica(
                    gestor, eid, pos.x, pos.y, radio, pos.zona_idx
                )
            elif accion == Accion.CRISIS_VIOLENTA:
                dx, dy = self._calcular_crisis_violenta(
                    gestor, mundo, eid, pos.x, pos.y, radio, pos.zona_idx,
                    temperamento, tick_actual,
                )
            # Accion.CATATONIA: sin rama a proposito, mismo criterio que
            # Accion.ALIVIARSE (arriba, tampoco tiene rama) -- dx=dy=0 por
            # defecto es literalmente la definicion de catatonia ("se
            # queda quieto, sin actuar", componentes/intencion.py), no un
            # descuido. Accion.RECOLECTAR y Accion.ENCENDER_FUEGO
            # tampoco tienen rama, mismo motivo: se resuelven donde ya se
            # está (sistemas/sistema_recursos.py), sin desplazamiento
            # propio.

            if dx != 0 or dy != 0:
                self._aplicar_movimiento(gestor, mundo, zona, eid, pos, dims, pf, dx, dy, accion)

    def _aplicar_movimiento(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        zona: Any,
        entidad_id: int,
        pos: Posicion,
        dims: DimensionesFisicas,
        pf: PoolFisico | None,
        dx: int,
        dy: int,
        accion: Accion,
    ) -> None:
        """Valida restricciones de terreno y aplica el gasto metabólico de resistencia."""
        nx, ny = pos.x + dx, pos.y + dy

        if not (0 <= nx < zona.ancho and 0 <= ny < zona.alto):
            return

        # TRANSICION DE ZONA -- mecanismo de "portal", no una decision de
        # la Utility AI: pisar la celda de acceso es en si mismo el
        # cruce, igual que una escalera de Dwarf Fortress -- ninguna
        # especie necesita "elegir" bajar, es un rasgo fisico del terreno
        # (leyes neutras, nunca teleologicas -- principio 5). Se
        # comprueba ANTES de las restricciones de agua/relieve de mas
        # abajo porque son restricciones DE LA CELDA DE ORIGEN de esta
        # misma zona, no tienen sentido aplicadas al destino en otra
        # zona. territorio.accesos_subterraneos es una LISTA (una entrada
        # por cueva, ver nucleo/territorio.py:AccesoSubterraneo) --
        # busqueda lineal O(N) sobre un puñado de cuevas por mundo, mismo
        # limite de escalabilidad ya aceptado en el resto del motor a
        # esta escala.
        territorio = mundo.territorio
        if pos.zona_idx == 0:
            for acceso in territorio.accesos_subterraneos:
                if (nx, ny) == acceso.superficie:
                    pos.zona_idx = acceso.zona_idx
                    pos.x, pos.y = acceso.entrada
                    return
        else:
            for acceso in territorio.accesos_subterraneos:
                if pos.zona_idx == acceso.zona_idx and (nx, ny) == acceso.entrada:
                    pos.zona_idx = 0
                    pos.x, pos.y = acceso.superficie
                    return

        celda_orig = zona.obtener_celda(pos.x, pos.y)
        celda_dest = zona.obtener_celda(nx, ny)

        # 1. Chequeo de profundidad de agua frente a la estatura corporal
        prof_agua = profundidad_agua_potable(celda_dest)
        if prof_agua > dims.altura and profundidad_agua_potable(celda_orig) <= dims.altura:
            return

        # 2. Chequeo de relieve y pendiente máxima transitable
        delta_elev = celda_dest.elevacion - celda_orig.elevacion
        pend_max = pendiente_maxima_transitable(dims.fuerza, self.pend_min, self.pend_max)

        if delta_elev > pend_max:
            return

        # 3. Drenaje de resistencia física (únicamente en desnivel positivo y sprint)
        if pf is not None:
            coste_total = 0.0
            if delta_elev > 0.0:
                # Llama a la funcion centralizada de nucleo/relieve.py en
                # vez de reimplementar la misma formula inline -- coste
                # BRUTO devuelto por la funcion, dividido por
                # resistencia_maxima aqui (mismo criterio que
                # sistema_capacidad_fisica.py, documentado en el propio
                # docstring de costo_resistencia_por_pendiente).
                coste_total += costo_resistencia_por_pendiente(
                    celda_orig.elevacion, celda_dest.elevacion, self.cfg_relieve
                ) / max(0.1, dims.resistencia_maxima)
            # HUIDA_ERRATICA/CRISIS_VIOLENTA usan el mismo coste de
            # esfuerzo sostenido que CAZAR/HUIR: son fisicamente el mismo
            # tipo de movimiento urgente (correr en panico o embestir con
            # agresividad), no caminar tranquilo.
            if accion in (Accion.CAZAR, Accion.HUIR, Accion.HUIDA_ERRATICA, Accion.CRISIS_VIOLENTA):
                coste_total += self.coste_sprint / max(0.1, dims.resistencia_maxima)

            pf.resistencia = max(0.0, pf.resistencia - coste_total)

        # 4. Actualización atómica de coordenadas espaciales
        pos.x = nx
        pos.y = ny

    def _calcular_huida(
        self,
        gestor: GestorEntidades,
        zona: Any,
        entidad_id: int,
        pos_x: int,
        pos_y: int,
        peso_propio: float,
        radio: int,
        zona_idx: int = 0,
        temperamento: Temperamento | None = None,
        tick_actual: int = 0,
        agudeza_sensorial: float = 0.0,
    ) -> tuple[int, int]:
        """Calcula el vector opuesto a la amenaza más cercana percibida.

        tick_actual/agudeza_sensorial (2026-09-06, circulo 4a -- sonido
        fisico): se reenvian a posicion_amenaza_mas_cercana para la
        tercera fuente de amenaza (sonido), junto con el radio de busqueda
        cacheado y la config."""
        amenaza_pos = posicion_amenaza_mas_cercana(
            gestor, zona, entidad_id, pos_x, pos_y, radio,
            peso_propio, self.umbral_disposicion_amenaza, zona_idx=zona_idx,
            peso_agresividad_candidato=self.peso_agresividad_amenaza,
            valentia_propia=temperamento.valentia if temperamento is not None else 0.0,
            factor_valentia_amenaza=self.factor_valentia_amenaza,
            tick_actual=tick_actual,
            agudeza_sensorial=agudeza_sensorial,
            radio_busqueda_sonido=self.radio_busqueda_maxima_sonido,
            config=self.config,
            indice=self._indice_actual,
        )
        if amenaza_pos is None:
            return self._paso_aleatorio()

        ax, ay = amenaza_pos
        if (ax, ay) == (pos_x, pos_y):
            # La amenaza ambiental esta en la propia celda (2026-09-11,
            # p.ej. de pie sobre fuego) -- "huir de uno mismo" no tiene
            # una direccion bien definida (dx=dy=0), un paso aleatorio
            # saca del sitio peligroso igual de bien.
            return self._paso_aleatorio()
        dx = 0 if ax == pos_x else (1 if pos_x > ax else -1)
        dy = 0 if ay == pos_y else (1 if pos_y > ay else -1)
        return dx, dy

    # HUIDA_ERRATICA, CRISIS_VIOLENTA y SOCIALIZAR reaccionan a CUALQUIER
    # entidad cercana (o a cualquier consciente cercano), no a una amenaza
    # calculada por disposicion -- de ahi que necesiten su propia busqueda
    # en vez de reutilizar posicion_amenaza_mas_cercana.
    def _buscar_entidad_cercana(
        self,
        gestor: GestorEntidades,
        entidad_id: int,
        pos_x: int,
        pos_y: int,
        radio: int,
        zona_idx: int = 0,
        solo_conscientes: bool = False,
    ) -> tuple[int | None, tuple[int, int] | None]:
        """Entidad con Posicion mas cercana dentro del radio, excluyendo a
        quien busca. Sin filtro de amenaza ni de disposicion por tamano --
        una crisis mental no razona sobre quien es peligroso o presa.

        solo_conscientes=True filtra a CapacidadMental.consciencia >=
        umbral_consciencia_agencia (cualquier especie, no solo la propia --
        a diferencia de _buscar_conspecifico_mas_cercano).

        Usa self._indice_actual si esta disponible (no filtra por
        CapacidadMental, el guard se aplica aparte); sin el, escanea toda
        la poblacion."""
        componentes = (Posicion, CapacidadMental) if solo_conscientes else (Posicion,)
        fuente = (
            self._indice_actual.en_radio(pos_x, pos_y, zona_idx, radio)
            if self._indice_actual is not None
            else gestor.entidades_con(*componentes)
        )
        mejor_id: int | None = None
        mejor: tuple[int, int] | None = None
        mejor_dist = radio + 1
        for otro_id in fuente:
            if otro_id == entidad_id:
                continue
            if solo_conscientes:
                cap_otro = gestor.obtener_componente(otro_id, CapacidadMental)
                if cap_otro is None or cap_otro.consciencia < self.umbral_consciencia_agencia:
                    continue
            pos_o = gestor.obtener_componente(otro_id, Posicion)
            if pos_o is None or pos_o.zona_idx != zona_idx:
                continue
            dist = abs(pos_o.x - pos_x) + abs(pos_o.y - pos_y)
            if dist <= radio and dist < mejor_dist:
                mejor_id = otro_id
                mejor = (pos_o.x, pos_o.y)
                mejor_dist = dist
        return mejor_id, mejor

    def _consciente_mas_cercano_con_id(
        self,
        gestor: GestorEntidades,
        entidad_id: int,
        pos_x: int,
        pos_y: int,
        radio: int,
        zona_idx: int = 0,
    ) -> tuple[int | None, tuple[int, int] | None]:
        return self._buscar_entidad_cercana(
            gestor, entidad_id, pos_x, pos_y, radio, zona_idx, solo_conscientes=True
        )

    def _calcular_huida_erratica(
        self,
        gestor: GestorEntidades,
        entidad_id: int,
        pos_x: int,
        pos_y: int,
        radio: int,
        zona_idx: int = 0,
    ) -> tuple[int, int]:
        """HUIDA_ERRATICA: huye de cualquiera cercano, sin evaluar si es
        una amenaza real (valentia baja ante la crisis, no ante un
        peligro concreto) -- mismo patron de direccion que
        _calcular_huida, sobre un objetivo encontrado por
        _buscar_entidad_cercana en vez de posicion_amenaza_mas_cercana."""
        _, objetivo = self._buscar_entidad_cercana(gestor, entidad_id, pos_x, pos_y, radio, zona_idx)
        if objetivo is None:
            return self._paso_aleatorio()
        ox, oy = objetivo
        dx = 0 if ox == pos_x else (1 if pos_x > ox else -1)
        dy = 0 if oy == pos_y else (1 if pos_y > oy else -1)
        return dx, dy

    def _calcular_crisis_violenta(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        entidad_id: int,
        pos_x: int,
        pos_y: int,
        radio: int,
        zona_idx: int = 0,
        temperamento: Temperamento | None = None,
        tick_actual: int = 0,
    ) -> tuple[int, int]:
        """CRISIS_VIOLENTA + contacto real (2026-09-06, conflicto verbal):
        se acerca a cualquiera cercano, como antes, PERO cuando el mas
        cercano ya esta a distancia 0 (misma celda: contacto real, no
        solo aproximacion) resuelve la disputa con el resolutor compartido
        _resolver_conflicto_entre en vez de seguir devolviendo movimiento
        hacia el -- el estado que antes era un gesto vacio (ver
        docstring anterior) ahora tiene consecuencia. A distancia > 0 el
        comportamiento es exactamente el de antes: acercarse sin resolver.
        No es una fuente nueva de riesgo: CRISIS_VIOLENTA ya ocurría a la
        misma frecuencia; esta pieza solo le da consecuencia. Devuelve
        (0, 0) tras resolver (no se mueve en el tick del contacto)."""
        objetivo_id, objetivo_pos = self._buscar_entidad_cercana(
            gestor, entidad_id, pos_x, pos_y, radio, zona_idx
        )
        if objetivo_id is None:
            return self._paso_aleatorio()
        if objetivo_pos == (pos_x, pos_y):  # contacto real, no solo cercania
            tempe_objetivo = gestor.obtener_componente(objetivo_id, Temperamento)
            if temperamento is not None and tempe_objetivo is not None:
                self._resolver_conflicto_entre(
                    gestor, mundo, entidad_id, objetivo_id,
                    temperamento, tempe_objetivo, tick_actual,
                    pos_x, pos_y, zona_idx,
                )
                self._stats_crisis_violenta_contacto += 1
            return (0, 0)
        return self._acercarse_a(pos_x, pos_y, *objetivo_pos)

    def _calcular_socializar(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        entidad_id: int,
        pos_x: int,
        pos_y: int,
        radio: int,
        zona_idx: int = 0,
        tick_actual: int = 0,
    ) -> tuple[int, int]:
        """SOCIALIZAR (2026-09-06, ocio consciente -- ver spec): acto
        consciente e independiente del sesgo gregario de DEAMBULAR.

        Busca al consciente mas cercano de CUALQUIER especie (sin la
        restriccion biologica de _buscar_conspecifico_mas_cercano -- hoy
        solo hay una especie consciente, pero el mecanismo no debe
        asumirlo). Si no hay ninguno, cae a paso aleatorio (ocio sin
        mas nadie cerca). Si el mas cercano ya esta a distancia 0
        (misma celda: contacto real), resuelve una ganancia de afinidad
        MUTUA (ambas direcciones, incondicional al contacto -- no depende
        de que la otra parte tambien este "eligiendo" SOCIALIZAR ese tick,
        mismo criterio que CRISIS_VIOLENTA) y devuelve (0, 0): no sigue
        moviendose tras "conseguir" socializar. A distancia > 0 se acerca
        sin resolver nada, igual que CRISIS_VIOLENTA.

        Salón común (2026-09-08, ver docs/superpowers/specs/
        2026-09-08-salon-comun-design.md): si el asentamiento propio ya
        tiene uno completado, es el destino preferente -- se camina hacia
        él EN VEZ DE perseguir al consciente más cercano al azar (ley
        simple, sin comparar distancias: un consciente que decide
        socializar va al punto de encuentro real del pueblo, no a quien
        le pille más cerca). Sin salón común disponible, comportamiento
        IDÉNTICO al de antes de esta pieza. La resolución de contacto
        real de arriba NO cambia -- sigue disparándose igual si ya se
        está junto a alguien, sea porque ambos caminaron al salón o por
        pura casualidad."""
        objetivo_id, objetivo_pos = self._consciente_mas_cercano_con_id(
            gestor, entidad_id, pos_x, pos_y, radio, zona_idx
        )
        if objetivo_id is not None and objetivo_pos == (pos_x, pos_y):  # contacto real, no solo cercania
            self._aplicar_afinidad(
                gestor, entidad_id, objetivo_id, self.delta_afinidad_socializar, tick_actual,
            )
            self._aplicar_afinidad(
                gestor, objetivo_id, entidad_id, self.delta_afinidad_socializar, tick_actual,
            )
            self._stats_socializar_contacto += 1
            self._stats_socializar_afinidad_pares.add((entidad_id, objetivo_id))
            self._stats_socializar_afinidad_pares.add((objetivo_id, entidad_id))
            return (0, 0)

        salon_pos = self._salon_comun_de(gestor, mundo, entidad_id)
        if salon_pos is not None:
            if salon_pos == (pos_x, pos_y):
                return (0, 0)  # ya en el salon -- esperar aqui a que lleguen otros
            return self._acercarse_a(pos_x, pos_y, *salon_pos)

        # Cocina comun como respaldo social (2026-09-08, ver
        # docs/superpowers/specs/2026-09-08-cocinas-comunes-design.md):
        # SOLO si no hay salon comun -- el salon sigue siendo el iman
        # social principal, la cocina solo lo sustituye cuando el
        # asentamiento aun no tiene uno.
        cid_cocina = self._cocina_de(gestor, mundo, entidad_id)
        if cid_cocina is not None:
            pos_cocina = gestor.obtener_componente(cid_cocina, Posicion)
            if pos_cocina is not None:
                cocina_pos = (pos_cocina.x, pos_cocina.y)
                if cocina_pos == (pos_x, pos_y):
                    return (0, 0)
                return self._acercarse_a(pos_x, pos_y, *cocina_pos)

        if objetivo_id is not None:
            return self._acercarse_a(pos_x, pos_y, *objetivo_pos)
        return self._paso_aleatorio()

    def _salon_comun_de(
        self, gestor: GestorEntidades, mundo: Mundo, entidad_id: int,
    ) -> tuple[int, int] | None:
        """Coordenadas del salón común COMPLETADO del asentamiento de
        `entidad_id`, o None si no pertenece a ninguno o su asentamiento
        no tiene uno terminado todavía (2026-09-08, ver
        docs/superpowers/specs/2026-09-08-salon-comun-design.md)."""
        asen = asentamiento_de(mundo, entidad_id)
        if asen is None:
            return None
        cid = almacen_cercano(
            gestor, asen.centro, self.radio_cluster_asentamiento,
            zona_idx=asen.zona_idx, tipo="salon_comun", indice=self._indice_actual,
        )
        if cid is None:
            return None
        construccion = gestor.obtener_componente(cid, Construccion)
        if construccion is None or not construccion.completado_alguna_vez:
            return None
        pos = gestor.obtener_componente(cid, Posicion)
        if pos is None:
            return None
        return (pos.x, pos.y)

    def _cocina_de(
        self, gestor: GestorEntidades, mundo: Mundo, entidad_id: int,
    ) -> int | None:
        """Id de la cocina común COMPLETADA del asentamiento de
        `entidad_id`, o None si no pertenece a ninguno o su asentamiento
        no tiene una terminada todavía (2026-09-08, cocinas comunes --
        ver docs/superpowers/specs/2026-09-08-cocinas-comunes-design.md).
        Devuelve el cid (no la posición como _salon_comun_de) porque los
        dos consumidores reales (imán social de respaldo, alacena de
        _calcular_forrajeo) necesitan cosas distintas del resultado."""
        return construccion_completada_de_asentamiento(
            gestor, mundo, entidad_id, self.radio_cluster_asentamiento, "cocina",
            indice=self._indice_actual,
        )

    def _agrupar_conscientes_por_celda(
        self, gestor: GestorEntidades,
    ) -> dict[tuple[int, int, int], list[int]]:
        """Agrupa entidades conscientes por (x, y, zona_idx) exacta.
        Extraido de _procesar_roce_social (2026-09-06) para reutilizarse
        tambien en _procesar_memoria_compartida -- filtra solo por
        Posicion/Temperamento/CapacidadMental + umbral_consciencia_agencia;
        NO exige PoolMental/Necesidades aqui (requisitos propios de roce
        social, comprobados por el llamador que los necesite)."""
        por_celda: dict[tuple[int, int, int], list[int]] = {}
        for eid in gestor.entidades_con(Posicion, Temperamento, CapacidadMental):
            cap_mental = gestor.obtener_componente(eid, CapacidadMental)
            if cap_mental is None or cap_mental.consciencia < self.umbral_consciencia_agencia:
                continue
            pos = gestor.obtener_componente(eid, Posicion)
            if pos is None:
                continue
            por_celda.setdefault((pos.x, pos.y, pos.zona_idx), []).append(eid)
        return por_celda

    def _pares_no_ordenados(
        self, por_celda: dict[tuple[int, int, int], list[int]],
    ):
        """Cada par (a_id, b_id) con i<j de cada grupo de por_celda, una
        sola vez por par -- para efectos simetricos (roce_social) o que
        el propio llamador resuelve en ambas direcciones (robo,
        compartir_confianza)."""
        for celda_key, ids in por_celda.items():
            if len(ids) < 2:
                continue
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    yield celda_key, ids[i], ids[j]

    def _pares_ordenados(
        self, por_celda: dict[tuple[int, int, int], list[int]],
    ):
        """Cada par (emisor_id, receptor_id) de cada grupo de por_celda,
        las DOS direcciones por separado -- para efectos asimetricos
        (memoria compartida, rumor) donde cada direccion es un camino de
        efecto independiente."""
        for ids in por_celda.values():
            if len(ids) < 2:
                continue
            for i in range(len(ids)):
                for j in range(len(ids)):
                    if i == j:
                        continue
                    yield ids[i], ids[j]

    def _procesar_roce_social(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        tick_actual: int,
        por_celda: dict[tuple[int, int, int], list[int]] | None = None,
    ) -> None:
        """Una vez por ejecutar(), no por entidad -- sortea friccion para
        cada par de conscientes que comparte celda+zona exacta.

        Disparador 2 del conflicto verbal (2026-09-06, ver
        docs/superpowers/specs/2026-09-06-conflicto-verbal-design.md):
        SOLO entre conscientes (gnomo hoy, umbral_consciencia_agencia);
        la probabilidad de roce se modula por proximidad real (compartir
        celda), agresividad combinada de ambos y gradiente de estres
        (1 - PoolMental.estabilidad del mas inestable de los dos -- el
        mismo pool que dispara la crisis, aqui como modulador continuo,
        no umbral binario). Cuando dispara, resuelve con el resolutor
        compartido _resolver_conflicto_entre. Un mismo par no se procesa
        dos veces en el mismo tick (bucles i<j sobre cada celda, y cada
        par aparece en una unica celda por construccion).

        Refactor 2026-09-06 (memoria espacial compartida): recibe
        por_celda ya construido por _agrupar_conscientes_por_celda -- el
        filtro base ya NO exige PoolMental/Necesidades (requisitos
        propios del roce social), asi que se comprueban por pareja con el
        mismo resultado observable que antes, cuando se filtraban en la
        agrupacion: ningun par que los necesite llega a sortearse. El
        parametro es opcional para compatibilidad con los tests dirigidos,
        que llaman al metodo sin por_celda (entonces se construye aqui).
        """
        if por_celda is None:
            por_celda = self._agrupar_conscientes_por_celda(gestor)

        for (celda_x, celda_y, celda_zona_idx), a_id, b_id in self._pares_no_ordenados(por_celda):
            temp_a = gestor.obtener_componente(a_id, Temperamento)
            temp_b = gestor.obtener_componente(b_id, Temperamento)
            pm_a = gestor.obtener_componente(a_id, PoolMental)
            pm_b = gestor.obtener_componente(b_id, PoolMental)
            nec_a = gestor.obtener_componente(a_id, Necesidades)
            nec_b = gestor.obtener_componente(b_id, Necesidades)
            if (
                temp_a is None or temp_b is None
                or pm_a is None or pm_b is None
                or nec_a is None or nec_b is None
            ):
                continue
            estres = max(1.0 - pm_a.estabilidad, 1.0 - pm_b.estabilidad)
            prob = (
                self.probabilidad_base_roce_social
                + self.peso_agresividad_roce * (temp_a.agresividad + temp_b.agresividad) / 2.0
                + self.peso_estres_roce * estres
            )
            if self.rng.random() < prob:
                self._resolver_conflicto_entre(
                    gestor, mundo, a_id, b_id, temp_a, temp_b, tick_actual,
                    celda_x, celda_y, celda_zona_idx,
                )
                self._stats_roce_social_resueltos += 1

    def _procesar_robo(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        tick_actual: int,
        por_celda: dict[tuple[int, int, int], list[int]] | None = None,
    ) -> None:
        """Robo (2026-09-07, círculo 3 del arco "robo/intercambio de
        recursos" -- ver docs/superpowers/specs/
        2026-09-07-robo-compartir-confianza-design.md). Mismo molde de
        recorrido que _procesar_roce_social (_pares_no_ordenados), pero
        asimétrico: para cada par prueba las DOS direcciones (a robando a
        b, luego b robando a a) -- sin necesidad de lógica de dedup
        propia, el propio _resolver_conflicto_entre ya descarta un
        segundo intento sobre el mismo par este tick devolviendo
        COMPARTE (ningún efecto).

        Tres tipos de robo, cada uno motivado por la MISMA señal de
        déficit que ya usa el motor para decidir si RECOLECTAR/CONSTRUIR/
        FABRICAR categoria "arma" (2026-09-11): comida (hambre), materiales de
        construcción (falta de masa apta para el objetivo actual) y
        objetos apto_arma (inseguridad real) -- nunca de Agarre, solo de
        Inventario (lo activamente empuñado no es robable)."""
        if por_celda is None:
            por_celda = self._agrupar_conscientes_por_celda(gestor)

        for (celda_x, celda_y, celda_zona_idx), a_id, b_id in self._pares_no_ordenados(por_celda):
            self._intentar_robo(
                gestor, mundo, a_id, b_id, tick_actual, celda_x, celda_y, celda_zona_idx
            )
            self._intentar_robo(
                gestor, mundo, b_id, a_id, tick_actual, celda_x, celda_y, celda_zona_idx
            )
            self._intentar_robo_material(
                gestor, mundo, a_id, b_id, tick_actual, celda_x, celda_y, celda_zona_idx
            )
            self._intentar_robo_material(
                gestor, mundo, b_id, a_id, tick_actual, celda_x, celda_y, celda_zona_idx
            )
            self._intentar_robo_arma(
                gestor, mundo, a_id, b_id, tick_actual, celda_x, celda_y, celda_zona_idx
            )
            self._intentar_robo_arma(
                gestor, mundo, b_id, a_id, tick_actual, celda_x, celda_y, celda_zona_idx
            )

    def _intentar_robo(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        ladron_id: int,
        victima_id: int,
        tick_actual: int,
        pos_x: int,
        pos_y: int,
        zona_idx: int,
    ) -> None:
        """Un consciente hambriento (saciedad < umbral_saciedad_para_robar)
        sin nada guardado propio, junto a otro con provisiones reales,
        puede intentar robarle -- probabilidad modulada por lo hambriento
        que está. Resuelve con el mismo resolutor que refugio ocupado/
        conflicto verbal (mismo_grupo/familia -> COMPARTE automático, no
        se roba a los suyos), pasando la urgencia REAL del ladrón (su
        propia hambre) en vez del déficit de seguridad genérico. Si se
        impone, se lleva TODO lo que la víctima tenga del primer recurso
        no vacío, topado por su propio espacio de provisiones."""
        nec_ladron = gestor.obtener_componente(ladron_id, Necesidades)
        inv_ladron = gestor.obtener_componente(ladron_id, Inventario)
        inv_victima = gestor.obtener_componente(victima_id, Inventario)
        if nec_ladron is None or inv_ladron is None or inv_victima is None:
            return
        if nec_ladron.saciedad >= self.umbral_saciedad_para_robar:
            return
        if inv_ladron.provisiones or not inv_victima.provisiones:
            return

        saciedad_ladron = nec_ladron.saciedad
        prob = self.probabilidad_base_robo * (1.0 - saciedad_ladron)
        if self.rng.random() >= prob:
            return

        temp_ladron = gestor.obtener_componente(ladron_id, Temperamento)
        temp_victima = gestor.obtener_componente(victima_id, Temperamento)
        if temp_ladron is None or temp_victima is None:
            return

        self._stats_robos_intentados += 1
        resultado = self._resolver_conflicto_entre(
            gestor, mundo, ladron_id, victima_id, temp_ladron, temp_victima, tick_actual,
            pos_x, pos_y, zona_idx,
            urgencia_a=1.0 - saciedad_ladron,
        )
        if resultado != ResultadoDisputa.CEDE_B:
            return

        dims_ladron = gestor.obtener_componente(ladron_id, DimensionesFisicas)
        if dims_ladron is None:
            return
        recurso = next(iter(inv_victima.provisiones), None)
        if recurso is None:
            return
        espacio = espacio_disponible_provisiones_kg(
            inv_ladron.provisiones, dims_ladron.peso, self.fraccion_provisiones_maxima
        )
        cantidad = transferir_recurso(
            inv_victima.provisiones, inv_ladron.provisiones, recurso,
            inv_victima.provisiones.get(recurso, 0.0), espacio,
        )
        if cantidad > 0.0:
            self._stats_robos_exitosos += 1

    def _intentar_robo_material(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        ladron_id: int,
        victima_id: int,
        tick_actual: int,
        pos_x: int,
        pos_y: int,
        zona_idx: int,
    ) -> None:
        """Robo de materiales de construcción (2026-09-11, extensión del
        círculo de robo más allá de comida, ver docstring de
        _procesar_robo). Mismo molde que _intentar_robo, pero motivado
        por la MISMA señal de déficit que ya activa RECOLECTAR/CONSTRUIR
        -- material insuficiente para el objetivo de construcción actual
        del ladrón -- en vez de inventar una "necesidad de robar"
        aparte. Déficit binario (no una magnitud continua como el
        hambre), así que la probabilidad y la urgencia pasada al
        resolutor son valores FIJOS (mismo criterio que
        utilidad_construir_base/utilidad_recolectar_base, también fijas)."""
        inv_ladron = gestor.obtener_componente(ladron_id, Inventario)
        inv_victima = gestor.obtener_componente(victima_id, Inventario)
        if inv_ladron is None or inv_victima is None or not inv_victima.contenidos:
            return
        objetivo = objetivo_construccion_actual(
            gestor, mundo, ladron_id, self.radio_cluster_asentamiento, indice=self._indice_actual
        )
        if objetivo is None:
            return
        tipo_objetivo, cid_objetivo, _ = objetivo
        suficiente = material_suficiente_para(
            gestor, cid_objetivo, tipo_objetivo, inv_ladron.contenidos,
            self.catalogo_materiales, self.config_construccion,
        )
        if suficiente:
            return

        if self.rng.random() >= self.probabilidad_base_robo_material:
            return

        temp_ladron = gestor.obtener_componente(ladron_id, Temperamento)
        temp_victima = gestor.obtener_componente(victima_id, Temperamento)
        if temp_ladron is None or temp_victima is None:
            return

        self._stats_robos_material_intentados += 1
        resultado = self._resolver_conflicto_entre(
            gestor, mundo, ladron_id, victima_id, temp_ladron, temp_victima, tick_actual,
            pos_x, pos_y, zona_idx,
            urgencia_a=self.urgencia_robo_material,
        )
        if resultado != ResultadoDisputa.CEDE_B:
            return

        dims_ladron = gestor.obtener_componente(ladron_id, DimensionesFisicas)
        if dims_ladron is None:
            return
        recurso = next(iter(inv_victima.contenidos), None)
        if recurso is None:
            return
        espacio = espacio_disponible_kg(
            inv_ladron.contenidos, dims_ladron.peso, self.fraccion_carga_maxima,
            inv_ladron.objetos, self.peso_objeto_kg,
        )
        cantidad = transferir_recurso(
            inv_victima.contenidos, inv_ladron.contenidos, recurso,
            inv_victima.contenidos.get(recurso, 0.0), espacio,
        )
        if cantidad > 0.0:
            self._stats_robos_material_exitosos += 1

    def _intentar_robo_arma(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        ladron_id: int,
        victima_id: int,
        tick_actual: int,
        pos_x: int,
        pos_y: int,
        zona_idx: int,
    ) -> None:
        """Robo de un objeto apto_arma (2026-09-11, extensión del círculo
        de robo más allá de comida). Motivado por la MISMA señal que ya
        activa la categoría "arma" de FABRICAR -- inseguridad real (1 - seguridad) -- solo
        si el ladrón todavía no porta ningún objeto apto_arma, ni
        empuñado (Agarre) ni guardado (Inventario.objetos): quien ya
        tiene con qué defenderse no tiene motivo real para robar otro.
        Roba SOLO de Inventario.objetos de la víctima -- nunca de su
        Agarre (lo activamente empuñado no es robable, ver docstring del
        módulo: quitarle un arma de la mano a alguien sería un desarme,
        un mecanismo distinto que no existe)."""
        nec_ladron = gestor.obtener_componente(ladron_id, Necesidades)
        inv_ladron = gestor.obtener_componente(ladron_id, Inventario)
        inv_victima = gestor.obtener_componente(victima_id, Inventario)
        if nec_ladron is None or inv_ladron is None or inv_victima is None:
            return
        agarre_ladron = gestor.obtener_componente(ladron_id, Agarre)
        objetos_propios = list(inv_ladron.objetos)
        if agarre_ladron is not None:
            objetos_propios.extend(agarre_ladron.objetos)
        if objetos_arma(objetos_propios, self.catalogo_materiales, self.recetas_armas):
            return  # ya porta algo apto_arma, sin motivo para robar

        objeto_robable = next(
            (
                o for o in inv_victima.objetos
                if nivel_arma(o, self.catalogo_materiales, self.recetas_armas) > 0
            ),
            None,
        )
        if objeto_robable is None:
            return

        urgencia = 1.0 - nec_ladron.seguridad
        if self.rng.random() >= self.probabilidad_base_robo_arma * urgencia:
            return

        temp_ladron = gestor.obtener_componente(ladron_id, Temperamento)
        temp_victima = gestor.obtener_componente(victima_id, Temperamento)
        if temp_ladron is None or temp_victima is None:
            return

        self._stats_robos_arma_intentados += 1
        resultado = self._resolver_conflicto_entre(
            gestor, mundo, ladron_id, victima_id, temp_ladron, temp_victima, tick_actual,
            pos_x, pos_y, zona_idx,
            urgencia_a=urgencia,
        )
        if resultado != ResultadoDisputa.CEDE_B:
            return

        dims_ladron = gestor.obtener_componente(ladron_id, DimensionesFisicas)
        if dims_ladron is None:
            return
        espacio = espacio_disponible_kg(
            inv_ladron.contenidos, dims_ladron.peso, self.fraccion_carga_maxima,
            inv_ladron.objetos, self.peso_objeto_kg,
        )
        if espacio < float(self.peso_objeto_kg.get(objeto_robable, 0.0)):
            return
        inv_victima.objetos.remove(objeto_robable)
        inv_ladron.objetos.append(objeto_robable)
        self._stats_robos_arma_exitosos += 1

    def _procesar_compartir_confianza(
        self,
        gestor: GestorEntidades,
        por_celda: dict[tuple[int, int, int], list[int]] | None = None,
    ) -> None:
        """Compartir por confianza (2026-09-07, círculo 4 del arco
        "robo/intercambio de recursos"): unidireccional y voluntario, sin
        pasar por el resolutor de conflicto -- no es una disputa. Mismo
        molde de recorrido que _procesar_robo (_pares_no_ordenados),
        probando las dos direcciones por par; ambas pueden dispararse el
        mismo tick (no es adversarial, no hace falta dedup)."""
        if por_celda is None:
            por_celda = self._agrupar_conscientes_por_celda(gestor)

        for _celda_key, a_id, b_id in self._pares_no_ordenados(por_celda):
            self._intentar_compartir_confianza(gestor, a_id, b_id)
            self._intentar_compartir_confianza(gestor, b_id, a_id)

    def _intentar_compartir_confianza(
        self, gestor: GestorEntidades, donante_id: int, receptor_id: int,
    ) -> None:
        """Un consciente con provisiones reales y afinidad (unidireccional,
        SIN exigir reciprocidad -- "confío en ti" no requiere que tú
        confíes en mí) por encima de umbral_confianza_compartir hacia
        otro que pasa hambre (saciedad < saciedad_maxima_para_recibir_
        compartido) puede darle algo de lo que tiene guardado, sin nada a
        cambio. No modifica Necesidades.seguridad, rencor, ni Relaciones
        -- es cooperación, no conflicto."""
        inv_donante = gestor.obtener_componente(donante_id, Inventario)
        inv_receptor = gestor.obtener_componente(receptor_id, Inventario)
        nec_receptor = gestor.obtener_componente(receptor_id, Necesidades)
        rel_donante = gestor.obtener_componente(donante_id, Relaciones)
        dims_receptor = gestor.obtener_componente(receptor_id, DimensionesFisicas)
        if (
            inv_donante is None or inv_receptor is None or nec_receptor is None
            or rel_donante is None or dims_receptor is None
        ):
            return
        if not inv_donante.provisiones:
            return
        if nec_receptor.saciedad >= self.saciedad_maxima_para_recibir_compartido:
            return
        vinculo = rel_donante.vinculos.get(receptor_id)
        if vinculo is None or vinculo.afinidad < self.umbral_confianza_compartir:
            return
        if self.rng.random() >= self.probabilidad_base_compartir_confianza:
            return

        recurso = next(iter(inv_donante.provisiones), None)
        if recurso is None:
            return
        espacio = espacio_disponible_provisiones_kg(
            inv_receptor.provisiones, dims_receptor.peso, self.fraccion_provisiones_maxima
        )
        cantidad = transferir_recurso(
            inv_donante.provisiones, inv_receptor.provisiones, recurso,
            inv_donante.provisiones.get(recurso, 0.0), espacio,
        )
        if cantidad > 0.0:
            self._stats_compartir_confianza += 1

    def _procesar_memoria_compartida(
        self,
        gestor: GestorEntidades,
        por_celda: dict[tuple[int, int, int], list[int]],
    ) -> None:
        """Disparador 2 del informe de comunicacion (2026-09-06, ver
        docs/superpowers/specs/2026-09-06-memoria-espacial-compartida-design.md):
        para cada par de conscientes que comparte celda, cada direccion se
        sortea por separado con la sociabilidad de quien comparte (misma
        linea que el sesgo gregario de _calcular_deambular). Si dispara, por
        cada categoria de MemoriaEspacial.recuerdos del emisor se comparte el
        sitio mas cercano que el emisor conoce (objetivo_recordado desde SU
        posicion/capacidad mental -- ya perturbado por su propia imprecision)
        hacia el receptor, via registrar_recuerdo()."""
        for emisor_id, receptor_id in self._pares_ordenados(por_celda):
            self._compartir_memoria(gestor, emisor_id, receptor_id)

    def _compartir_memoria(
        self, gestor: GestorEntidades, emisor_id: int, receptor_id: int
    ) -> None:
        """Una direccion de transferencia de memoria: sortea con la
        sociabilidad del emisor y, si dispara, comparte por cada categoria
        de recuerdos del emisor el sitio mas cercano que el conoce desde SU
        posicion (una unica llamada a objetivo_recordado por categoria -- ya
        combina 'mas cercano' + 'perturbar', llamarla por coordenada seria
        redundante), registrado en el receptor con su propia capacidad."""
        temp_emisor = gestor.obtener_componente(emisor_id, Temperamento)
        if temp_emisor is None or self.rng.random() >= temp_emisor.sociabilidad:
            return
        mem_emisor = gestor.obtener_componente(emisor_id, MemoriaEspacial)
        mem_receptor = gestor.obtener_componente(receptor_id, MemoriaEspacial)
        cap_emisor = gestor.obtener_componente(emisor_id, CapacidadMental)
        cap_receptor = gestor.obtener_componente(receptor_id, CapacidadMental)
        pos_emisor = gestor.obtener_componente(emisor_id, Posicion)
        if mem_emisor is None or mem_receptor is None or cap_emisor is None or cap_receptor is None or pos_emisor is None:
            return
        capacidad_receptor = capacidad_memoria(cap_receptor, self.config)
        for tipo in mem_emisor.recuerdos:
            objetivo = objetivo_recordado(
                mem_emisor, tipo, pos_emisor.x, pos_emisor.y, cap_emisor, self.rng, self.config,
            )
            if objetivo is not None:
                registrar_recuerdo(mem_receptor, tipo, objetivo[0], objetivo[1], capacidad_receptor)
                self._stats_memoria_compartida_transferencias += 1
                self._stats_memoria_transferida_detalle.add(
                    (receptor_id, tipo, objetivo[0], objetivo[1])
                )

    def _procesar_rumor(
        self, gestor: GestorEntidades, por_celda: dict[tuple[int, int, int], list[int]],
        tick_actual: int,
    ) -> None:
        """Tercera pasada sobre la agrupacion de conscientes por celda
        (2026-09-06, rumor social -- ver
        docs/superpowers/specs/2026-09-06-rumor-social-design.md): cada
        direccion (emisor->receptor) se sortea por separado con la
        sociabilidad del emisor, mismo patron que _procesar_memoria_compartida.
        Un mismo par se procesa DOS veces (una por direccion) porque cada
        direccion es un camino de efecto independiente: A puede contarle a B
        su opinion sobre C sin que B le cuente nada a A ese mismo tick."""
        for emisor_id, receptor_id in self._pares_ordenados(por_celda):
            self._compartir_rumor(gestor, emisor_id, receptor_id, tick_actual)

    def _compartir_rumor(
        self, gestor: GestorEntidades, emisor_id: int, receptor_id: int, tick_actual: int,
    ) -> None:
        """Una direccion de rumor: sortea con la sociabilidad del emisor y,
        si dispara, elige un TERCERO al azar de los vinculos del emisor
        (excluyendo al receptor: contarle a alguien su opinion sobre EL no es
        un rumor, es confrontacion directa, fuera de alcance). El receptor NO
        adopta la opinion del emisor de golpe: su afinidad hacia ese tercero
        se desplaza una FRACCION (peso_credibilidad_rumor) hacia la del
        emisor, via ajustar_afinidad (ninguna funcion nueva en
        nucleo/relaciones.py). Sin opinion previa, parte de neutral (0.0)."""
        temp_emisor = gestor.obtener_componente(emisor_id, Temperamento)
        if temp_emisor is None or self.rng.random() >= temp_emisor.sociabilidad:
            return
        rel_emisor = gestor.obtener_componente(emisor_id, Relaciones)
        rel_receptor = gestor.obtener_componente(receptor_id, Relaciones)
        cap_receptor = gestor.obtener_componente(receptor_id, CapacidadMental)
        if rel_emisor is None or rel_receptor is None or cap_receptor is None:
            return
        candidatos = [tid for tid in rel_emisor.vinculos if tid != receptor_id]
        if not candidatos:
            return
        tercero_id = self.rng.choice(candidatos)
        # Defensivo (spec): el emisor nunca deberia aparecer en su propio
        # vinculos, pero si ocurriera no es un rumor valido -- excluirlo.
        if emisor_id == tercero_id:
            return
        opinion_emisor = rel_emisor.vinculos[tercero_id].afinidad
        opinion_actual = (
            rel_receptor.vinculos[tercero_id].afinidad
            if tercero_id in rel_receptor.vinculos else 0.0
        )
        delta = self.peso_credibilidad_rumor * (opinion_emisor - opinion_actual)
        capacidad = capacidad_vinculos(cap_receptor, self.config)
        if tercero_id not in rel_receptor.vinculos:
            self._stats_rumor_terceros_nuevos.add((receptor_id, tercero_id))
        ajustar_afinidad(rel_receptor, tercero_id, delta, tick_actual, capacidad)
        self._stats_rumores_propagados += 1

    def _calcular_caza(
        self,
        gestor: GestorEntidades,
        cazador_id: int,
        especie: Especie,
        pos_x: int,
        pos_y: int,
        peso_cazador: float,
        radio: int,
        zona_idx: int = 0,
        zona: Any | None = None,
        tick_actual: int = 0,
        agudeza_sensorial: float = 0.0,
        mundo: Any | None = None,
    ) -> tuple[int, int]:
        """
        Avanza hacia la presa válida más cercana dentro del radio sensorial
        -- `radio` ya llega calculado con self.radio_min_caza/
        radio_max_caza (2026-09-09, propio de CAZAR, mismo patrón que
        BEBER/BUSCAR_PAREJA) desde `ejecutar()`, no el genérico de
        comida/amenaza. Elección de presa DELIBERADAMENTE sin cambios --
        la más cercana, sin ponderar valor: dos intentos previos de
        preferencia por valor (resta lineal, luego tasa) se revirtieron
        por empeorar la frecuencia de caza real (ver CLAUDE.md), así que
        este círculo aísla el radio en solitario para saber si esa
        palanca sola ayuda sin la penalización de perseguir presa lejana.

        Tres filtros de "presa válida", todos PROVISIONALES:

        1. Viabilidad energética (fraccion_minima_peso_presa=0.001): una
           presa por debajo de ese porcentaje del peso del cazador no
           compensa el coste de perseguirla -- se descarta ANTES de
           caminar hacia ella, no solo al resolver el ataque. Elegido
           para no tocar ninguna de las cuatro especies actuales (el lobo
           más ligero, 60kg, exige solo 0.06kg -- muy por debajo de la
           ardilla más ligera, 0.3kg): salvaguarda para fauna futura
           mucho más pequeña, no un ajuste que deba notarse hoy. Se
           aplica también en sistema_depredacion.py:_es_presa_valida,
           para el caso en que coincidan en la misma celda por casualidad
           sin haber caminado el cazador hacia ella.

        2. Detectabilidad por tamaño absoluto (nucleo.percepcion.
           radio_efectivo_por_peso, peso_referencia_deteccion_plena=0.1kg):
           el radio de percepción no solo depende de la agudeza sensorial
           de quien mira, también del tamaño de lo mirado -- un objetivo
           por debajo del peso de referencia reduce el radio efectivo
           SOLO para esa búsqueda de presa, calculado por candidato (cada
           uno tiene su propio radio efectivo según su propio peso).
           0.1kg está por debajo de la ardilla (0.3-0.6kg), así que hoy
           este filtro no cambia nada observable, solo prepara el
           terreno para fauna mucho más pequeña.

        3. Techo de presa por manada (2026-09-05, ver CLAUDE.md, "Por qué
           lobo se muere de hambre pese a cazar más que nadie" +
           docs/superpowers/specs/2026-09-05-especie-caballo-design.md):
           un cazador SOLITARIO (sin ningún conespecífico cazando
           activamente cerca) sigue limitado a presas más ligeras que él
           mismo -- comportamiento original, sin cambios. Con aliados
           cazando cerca (mismo dato -- `contar_conspecificos_cercanos`,
           `solo_cazando=True` -- y mismo radio -- `radio_apoyo_grupal`
           -- que ya usa el bono de éxito en `sistema_depredacion.py`),
           el techo sube proporcionalmente: el GRUPO decide qué vale la
           pena perseguir, no el individuo solo. Es una ley general
           (cualquier especie con conespecíficos cazando cerca se
           beneficia igual, no una regla especial de lobo), coherente con
           el resto de usos ya existentes de esta misma función.
        Cohesion de manada como fallback de caza (2026-09-10, SUSTITUYE al
        aullido de caza -- ver CLAUDE.md "Aullido de caza en manada,
        revertido" + spec docs/superpowers/specs/
        2026-09-10-cohesion-manada-fallback-caza-design.md): el primer
        intento (un cazador excluido por el techo de manada aullaba para
        "convocar" ayuda a mitad de acecho) no era fiel a como caza un
        lobo real -- un aullido en plena persecucion alertaria a la presa,
        rompiendo el sigilo; la coordinacion real de una manada es
        ESTRUCTURAL, no reactiva: el grupo ya viaja/descansa/busca junto
        ANTES de encontrar presa. _calcular_deambular ya tira hacia el
        centro de la Manada propia como sesgo gregario, pero queda
        deliberadamente desactivado mientras haya un objetivo activo
        (CAZAR incluido) -- correcto cuando SI hay una presa real que
        perseguir, pero deja sin ningun sesgo de cohesion el caso "no
        encontre nada que cazar", que es justo el que importa para que
        varios cazadores acaben cerca a la vez. Mismo mecanismo exacto
        que ya usa deambular (nucleo.manada.manada_de + tirar hacia
        manada.centro si esta a mas de dist_deseada_conspecifico),
        aplicado aqui SOLO en el fallback sin presa -- sin sonido nuevo,
        sin constante nueva.

        Fallback de sonido (2026-09-06, circulo 4b): si no queda ninguna
        presa valida, se intenta primero sonido_mas_cercano (consumido tal
        cual de nucleo/sonido.py) con radio_busqueda_maxima_sonido, tick_actual
        y agudeza_sensorial -- el cazador avanza hacia el sonido audible mas
        cercano con _acercarse_a (una senal real de que algo esta pasando
        cerca -- un encuentro de caza o conflicto ajeno ya emite sonido por
        su cuenta, sin relacion con esta pieza). Incertidumbre real: al
        llegar puede haber una presa todavia cerca, un cadaver de una caza
        ajena (carroneo automatico via _calcular_forrajeo) o nada. Si no
        hay sonido audible tampoco, cae a la cohesion de manada (arriba);
        si ninguna de las dos aplica, paso aleatorio -- comportamiento
        identico al de antes de esta pieza. `zona` distingue la llamada
        nueva desde ejecutar() (pasa la ZonaBioma) de las llamadas legacy
        sin zona: sin zona ambos fallbacks quedan desactivados, identico a
        antes de 2026-09-06. Si hay presa valida ni sonido ni manada se
        consultan -- presa real > cualquier fallback.
        """
        peso_minimo_viable = peso_cazador * self.fraccion_minima_peso_presa
        aliados_cazando = contar_conspecificos_cercanos(
            gestor, cazador_id, especie, pos_x, pos_y,
            self.radio_apoyo_grupal, solo_cazando=True, zona_idx=zona_idx,
            indice=self._indice_actual,
        )
        peso_maximo_presa = peso_cazador * (
            1.0 + aliados_cazando * self.factor_ampliacion_techo_manada
        )
        presas = []
        # radio_efectivo_por_peso siempre devuelve <= radio (reduce el
        # alcance para presas por debajo del peso de referencia, nunca lo
        # amplia) -- indice.en_radio(radio) es una sobre-aproximacion
        # segura del candidato final, filtrado exacto abajo sin cambios
        # (2026-09-08, nucleo/indice_espacial.py).
        candidatos = (
            self._indice_actual.en_radio(pos_x, pos_y, zona_idx, radio)
            if self._indice_actual is not None
            else gestor.entidades_con(Posicion, DimensionesFisicas)
        )
        for eid in candidatos:
            if eid == cazador_id:
                continue
            pos_p = gestor.obtener_componente(eid, Posicion)
            dims_p = gestor.obtener_componente(eid, DimensionesFisicas)
            if not (pos_p and dims_p) or pos_p.zona_idx != zona_idx:
                continue
            if dims_p.peso < peso_minimo_viable:
                continue
            dist = abs(pos_p.x - pos_x) + abs(pos_p.y - pos_y)
            if dist > radio:
                # cuando self._indice_actual es None (tests directos sin
                # indice) `candidatos` no viene pre-filtrado por radio.
                continue
            if dims_p.peso >= peso_maximo_presa:
                continue
            radio_efectivo = radio_efectivo_por_peso(
                radio, dims_p.peso, self.peso_referencia_deteccion_plena
            )
            if dist <= radio_efectivo:
                presas.append((dist, pos_p.x, pos_p.y))

        if not presas:
            # Fallback de sonido como pista de caza (2026-09-06, circulo
            # 4b -- ver spec docs/superpowers/specs/2026-09-06-sonido-fisico-caza-design.md):
            # sin presa valida en la percepcion normal, se intenta primero seguir
            # el sonido audible mas cercano en vez de caer directo al paso
            # aleatorio. Incertidumbre real aceptada: al llegar al punto puede
            # haber una presa todavia cerca (encuentro de caza genuino), un
            # cadaver de una caza ajena (carroneo automatico via
            # _calcular_forrajeo), o nada (pista falsa). `zona is not None`
            # distingue la llamada nueva desde ejecutar() de las llamadas legacy
            # (tests antiguos) que no disponen de zona: sin zona no hay sonido,
            # identico a antes.
            if zona is not None:
                objetivo_sonido = sonido_mas_cercano(
                    zona, pos_x, pos_y, self.radio_busqueda_maxima_sonido,
                    tick_actual, agudeza_sensorial, self.config,
                )
                if objetivo_sonido is not None:
                    self._stats_sonido_caza_fallback_usos += 1
                    destino = self._clasificar_destino_sonido(
                        gestor, cazador_id, *objetivo_sonido,
                        radio, zona_idx, peso_minimo_viable, peso_maximo_presa,
                    )
                    if destino == "caza":
                        self._stats_sonido_caza_fallback_caza += 1
                    elif destino == "carrona":
                        self._stats_sonido_caza_fallback_carrona += 1
                    else:
                        self._stats_sonido_caza_fallback_nulo += 1
                    return self._acercarse_a(pos_x, pos_y, *objetivo_sonido)
            # Cohesion de manada, ultimo fallback antes del paso aleatorio
            # (2026-09-10, sustituye al aullido de caza -- ver docstring de
            # esta funcion y CLAUDE.md). Sin ningun sonido audible que
            # seguir tampoco, un cazador que pertenece HOY a una Manada
            # deriva hacia su centro -- mismo mecanismo silencioso que ya
            # usa _calcular_deambular para el sesgo gregario, aplicado
            # aqui solo cuando no hay presa ni pista de sonido.
            if mundo is not None:
                manada = manada_de(mundo, cazador_id)
                if manada is not None:
                    dist_centro = abs(manada.centro[0] - pos_x) + abs(manada.centro[1] - pos_y)
                    if dist_centro > self.dist_deseada_conspecifico:
                        self._stats_manada_cohesion_fallback_caza += 1
                        return self._acercarse_a(pos_x, pos_y, *manada.centro)
            return self._paso_aleatorio()

        presas.sort()
        _, px, py = presas[0]
        return self._acercarse_a(pos_x, pos_y, px, py)

    def _clasificar_destino_sonido(
        self,
        gestor: GestorEntidades,
        cazador_id: int,
        tx: int,
        ty: int,
        radio: int,
        zona_idx: int,
        peso_minimo_viable: float,
        peso_maximo_presa: float,
    ) -> str:
        """Clasifica que encontraria el cazador en la celda del sonido --
        solo observacion para la verificacion obligatoria contra
        BOSQUE_AUTO_TICKS (spec 4b): "caza" si hay una presa valida (mismos
        filtros de peso y zona que _calcular_caza) dentro del radio de
        percepcion efectivo del destino, "carrona" si hay una Necromasa
        comestible dentro del radio, "nada" si no hay ninguna. Ningun camino
        de juego lee este resultado: son solo contadores de observacion.

        2026-09-08 (nucleo/indice_espacial.py): usa self._indice_actual
        si esta disponible para ambos escaneos, en vez de O(N) sobre
        toda la poblacion/toda la necromasa del mundo -- sin el,
        comportamiento identico a antes.
        """
        fuente_presa = (
            self._indice_actual.en_radio(tx, ty, zona_idx, radio)
            if self._indice_actual is not None
            else gestor.entidades_con(Posicion, DimensionesFisicas)
        )
        for eid in fuente_presa:
            if eid == cazador_id:
                continue
            pos_p = gestor.obtener_componente(eid, Posicion)
            dims_p = gestor.obtener_componente(eid, DimensionesFisicas)
            if not (pos_p and dims_p) or pos_p.zona_idx != zona_idx:
                continue
            if dims_p.peso >= peso_maximo_presa or dims_p.peso < peso_minimo_viable:
                continue
            dist = abs(pos_p.x - tx) + abs(pos_p.y - ty)
            radio_efectivo = radio_efectivo_por_peso(
                radio, dims_p.peso, self.peso_referencia_deteccion_plena
            )
            if dist <= radio_efectivo:
                return "caza"

        fuente_necromasa = (
            self._indice_actual.en_radio(tx, ty, zona_idx, radio)
            if self._indice_actual is not None
            else gestor.entidades_con(Necromasa, Posicion)
        )
        for nid in fuente_necromasa:
            pos_n = gestor.obtener_componente(nid, Posicion)
            nec_comp = gestor.obtener_componente(nid, Necromasa)
            if (
                pos_n and nec_comp and pos_n.zona_idx == zona_idx
                and nec_comp.masas.get("tejido_blando", 0.0) > 0.05
            ):
                dist = abs(pos_n.x - tx) + abs(pos_n.y - ty)
                if dist <= radio:
                    return "carrona"
        return "nada"

    def _calcular_forrajeo(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        entidad_id: int,
        zona: Any,
        especie: Especie,
        pos_x: int,
        pos_y: int,
        radio: int,
        mem: MemoriaEspacial | None,
        cap_mental: CapacidadMental | None,
        zona_idx: int = 0,
    ) -> tuple[int, int]:
        """Busca comida: evalúa necromasa, flora, alacena de cocina común
        (2026-09-08) y memoria.

        mundo/entidad_id (2026-09-08, cocinas comunes -- ver
        docs/superpowers/specs/2026-09-08-cocinas-comunes-design.md):
        necesarios para localizar la cocina común del asentamiento."""
        cfg_esp = self.config.get("rangos_raciales", {}).get(especie.value, {})
        dieta = cfg_esp.get("dieta", [])

        # 1. Percepción directa de Necromasa o Recursos vegetales en el vecindario
        candidatos = []
        
        # A. Necromasa cercana (2026-09-08, nucleo/indice_espacial.py):
        # usa self._indice_actual si esta disponible, en vez de O(N)
        # sobre toda la necromasa del mundo -- sin el, comportamiento
        # identico a antes.
        fuente_necromasa = (
            self._indice_actual.en_radio(pos_x, pos_y, zona_idx, radio)
            if self._indice_actual is not None
            else gestor.entidades_con(Necromasa, Posicion)
        )
        for nid in fuente_necromasa:
            pos_n = gestor.obtener_componente(nid, Posicion)
            nec_comp = gestor.obtener_componente(nid, Necromasa)
            # Solo vale la pena viajar hasta aquí si queda tejido_blando
            # comestible -- un montón de hueso no es un objetivo de
            # forrajeo (mismo criterio que
            # sistema_recursos.py:_resolver_comer, que solo consume de
            # 'tejido_blando').
            if (
                pos_n and nec_comp and pos_n.zona_idx == zona_idx
                and nec_comp.masas.get("tejido_blando", 0.0) > 0.05
            ):
                dist = abs(pos_n.x - pos_x) + abs(pos_n.y - pos_y)
                if dist <= radio:
                    candidatos.append((dist, pos_n.x, pos_n.y))

        # B. Recursos botánicos en celdas
        for dy in range(-radio, radio + 1):
            for dx in range(-radio, radio + 1):
                nx, ny = pos_x + dx, pos_y + dy
                if 0 <= nx < zona.ancho and 0 <= ny < zona.alto:
                    celda = zona.obtener_celda(nx, ny)
                    hay_comida = any(
                        cant > 0.0 and (not dieta or r in dieta)
                        for r, cant in celda.recursos.items()
                    )
                    if hay_comida:
                        dist = abs(dx) + abs(dy)
                        candidatos.append((dist, nx, ny))

        # C. Alacena de cocina común del asentamiento (2026-09-08, ver
        # docs/superpowers/specs/2026-09-08-cocinas-comunes-design.md)
        # -- SOLO consciente (fauna no tiene asentamiento ni cocina). NO
        # está acotada por `radio`: se sabe dónde está la cocina propia
        # del asentamiento igual que ya pasa con el salón común/almacén,
        # no es percepción sensorial del entorno inmediato -- compite
        # por distancia con los candidatos de arriba en igualdad de
        # condiciones (Diego: "la más cercana gana, sin prioridad
        # especial").
        if cap_mental is not None and cap_mental.consciencia >= self.umbral_consciencia_agencia:
            cid_cocina = self._cocina_de(gestor, mundo, entidad_id)
            if cid_cocina is not None:
                cocina = gestor.obtener_componente(cid_cocina, Construccion)
                pos_cocina = gestor.obtener_componente(cid_cocina, Posicion)
                if cocina is not None and cocina.provisiones and pos_cocina is not None:
                    dist = abs(pos_cocina.x - pos_x) + abs(pos_cocina.y - pos_y)
                    candidatos.append((dist, pos_cocina.x, pos_cocina.y))

        if candidatos:
            candidatos.sort()
            _, tx, ty = candidatos[0]
            return self._acercarse_a(pos_x, pos_y, tx, ty)

        # 2. Búsqueda en memoria espacial amortiguada por distancia
        if mem is not None and cap_mental is not None:
            objetivo = objetivo_recordado(
                mem, "comida", pos_x, pos_y, cap_mental, self.rng, self.config
            )
            if objetivo is not None:
                return self._acercarse_a(pos_x, pos_y, *objetivo)

        return self._paso_aleatorio()

    def _calcular_hidratacion(
        self,
        zona: Any,
        pos_x: int,
        pos_y: int,
        altura: float,
        radio: int,
        mem: MemoriaEspacial | None,
        cap_mental: CapacidadMental | None,
    ) -> tuple[int, int]:
        """Busca fuentes de agua potable y vadeables en radio de percepción o memoria."""
        candidatos = []
        for dy in range(-radio, radio + 1):
            for dx in range(-radio, radio + 1):
                nx, ny = pos_x + dx, pos_y + dy
                if 0 <= nx < zona.ancho and 0 <= ny < zona.alto:
                    celda = zona.obtener_celda(nx, ny)
                    if hay_agua_potable(celda) and profundidad_agua_potable(celda) <= altura:
                        dist = abs(dx) + abs(dy)
                        candidatos.append((dist, nx, ny))

        if candidatos:
            candidatos.sort()
            _, tx, ty = candidatos[0]
            return self._acercarse_a(pos_x, pos_y, tx, ty)

        if mem is not None and cap_mental is not None:
            objetivo = objetivo_recordado(
                mem, "agua", pos_x, pos_y, cap_mental, self.rng, self.config
            )
            if objetivo is not None:
                return self._acercarse_a(pos_x, pos_y, *objetivo)

        return self._paso_aleatorio()

    def _calcular_pareja(
        self,
        gestor: GestorEntidades,
        entidad_id: int,
        especie: Especie,
        pos_x: int,
        pos_y: int,
        radio: int,
        zona_idx: int = 0,
    ) -> tuple[int, int]:
        """Avanza hacia una pareja reproductora compatible acotada al radio sensorial."""
        rep_propia = gestor.obtener_componente(entidad_id, Reproduccion)
        if rep_propia is None:
            return self._paso_aleatorio()

        candidatos = []
        # 2026-09-08 (nucleo/indice_espacial.py): en_radio ya acota a la
        # zona/celda correctas -- el resto del filtrado (sexo, especie,
        # gestacion) sigue exactamente igual sobre la lista local.
        fuente = (
            self._indice_actual.en_radio(pos_x, pos_y, zona_idx, radio)
            if self._indice_actual is not None
            else gestor.entidades_con(Reproduccion, Posicion, Identidad)
        )
        for eid in fuente:
            if eid == entidad_id:
                continue
            pos_c = gestor.obtener_componente(eid, Posicion)
            if pos_c is None or pos_c.zona_idx != zona_idx:
                continue

            dist = abs(pos_c.x - pos_x) + abs(pos_c.y - pos_y)
            if dist > radio:
                continue

            ident = gestor.obtener_componente(eid, Identidad)
            rep = gestor.obtener_componente(eid, Reproduccion)
            gest = gestor.obtener_componente(eid, Gestacion)

            if (
                ident
                and rep
                and ident.especie == especie
                and rep.sexo != rep_propia.sexo
                and gest is None
            ):
                candidatos.append((dist, pos_c.x, pos_c.y))

        if candidatos:
            candidatos.sort()
            _, px, py = candidatos[0]
            return self._acercarse_a(pos_x, pos_y, px, py)

        return self._paso_aleatorio()

    def _buscar_conspecifico_mas_cercano(
        self,
        gestor: GestorEntidades,
        entidad_id: int,
        especie: Especie,
        pos_x: int,
        pos_y: int,
        radio: int,
        zona_idx: int = 0,
    ) -> tuple[int, int] | None:
        """
        Posición del individuo de la MISMA especie más cercano dentro del
        radio de percepción (cualquier sexo/edad -- a diferencia de
        _calcular_pareja, esto es agrupamiento social, no búsqueda de
        pareja reproductiva). None si no percibe ninguno. Mismo patrón de
        búsqueda lineal ya usado en _calcular_caza/_calcular_pareja de este
        archivo -- O(N) por individuo, límite conocido de escalabilidad
        si la población crece en órdenes de magnitud.

        2026-09-08: si self._indice_actual está disponible (ver
        nucleo/indice_espacial.py), se usa indice.en_radio en vez del
        escaneo O(N) sobre toda la población -- el límite arriba
        documentado queda resuelto cuando ejecutar() ya construyó el
        índice; sin él (llamada aislada en tests), comportamiento
        idéntico a antes.
        """
        candidatos = []
        fuente = (
            self._indice_actual.en_radio(pos_x, pos_y, zona_idx, radio)
            if self._indice_actual is not None
            else gestor.entidades_con(Identidad, Posicion)
        )
        for eid in fuente:
            if eid == entidad_id:
                continue
            ident_c = gestor.obtener_componente(eid, Identidad)
            if ident_c is None or ident_c.especie != especie:
                continue
            pos_c = gestor.obtener_componente(eid, Posicion)
            if pos_c is None or pos_c.zona_idx != zona_idx:
                continue
            dist = abs(pos_c.x - pos_x) + abs(pos_c.y - pos_y)
            if dist <= radio:
                candidatos.append((dist, pos_c.x, pos_c.y))

        if not candidatos:
            return None
        candidatos.sort()
        _, cx, cy = candidatos[0]
        return (cx, cy)

    def _calcular_deambular(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        entidad_id: int,
        especie: Especie,
        pos_x: int,
        pos_y: int,
        radio: int,
        mem: MemoriaEspacial | None,
        cap_mental: CapacidadMental | None,
        temperamento: Temperamento | None,
        zona_idx: int = 0,
    ) -> tuple[int, int]:
        """
        Cascada de sesgos sobre el paso de dispersión, evaluados en este
        orden: SESGO DE TERRITORIO -> SESGO GREGARIO -> paso aleatorio.
        Territorio es el filtro PRIMARIO; gregario actúa como sesgo
        secundario, solo cuando el territorio no aplica (fauna consciente
        exenta, sin memoria todavía, o ya lo bastante cerca de lo
        conocido) -- coherente con la jerarquía tipo Maslow que ya
        gobierna el resto de la Utility AI (sistema_decision.py:
        seguridad/necesidades físicas por delante de lo social).

        SESGO DE TERRITORIO: sin objetivo activo (COMER/BEBER/CAZAR/HUIR/
        BUSCAR_PAREJA), una criatura no debería dispersarse sin rumbo si
        ya conoce dónde hay recursos -- eso es plausible para un
        individuo consciente que delibera (gnomo), pero no para fauna sin
        agencia: lo esperable en fauna real es permanecer dentro de su
        área de campeo (home range) en torno a comida/agua/seguridad
        conocidas, no vagar uniformemente. Gating por
        CapacidadMental.consciencia (decision.umbral_consciencia_agencia,
        PROVISIONAL): por debajo del umbral, la criatura queda sujeta al
        sesgo de territorio; por encima (hoy, solo gnomo: rango racial
        0.6-0.9), se asume que su deambular puede reflejar decisiones no
        reducibles a "quedarse cerca de lo conocido". Mecanismo de gating
        GENERAL, no un caso especial de especie: el día que otra especie
        tenga consciencia alta, quedará exenta automáticamente sin tocar
        este código (leyes neutras, nunca teleológicas). Reutiliza
        nucleo.memoria.objetivo_recordado.

        SESGO GREGARIO: con probabilidad = Temperamento.sociabilidad
        DIRECTA, sin escalar, la criatura busca un objetivo social y
        avanza hacia él si está a más de
        social.distancia_deseada_conspecifico. Sin gating por
        consciencia -- a diferencia del sesgo de territorio, el
        agrupamiento social es plausible tanto para gnomo como para el
        resto. Si la tirada de sociabilidad no dispara el sesgo, o no hay
        ningún objetivo perceptible, se cae al paso aleatorio.

        Cohesión de manada (2026-09-07, ver nucleo/manada.py y spec
        docs/superpowers/specs/2026-09-07-manada-fauna-design.md): si la
        entidad pertenece HOY a una Manada (recalculada a diario,
        cualquier especie), el objetivo social es su CENTRO -- produce
        grupos más compactos y estables que perseguir siempre al vecino
        más cercano, que puede formar cadenas dispersas. Sin manada
        (solitario o recién disperso), cae al comportamiento anterior:
        el conespecífico más cercano vía
        _buscar_conspecifico_mas_cercano.
        """
        if (
            mem is not None
            and cap_mental is not None
            and cap_mental.consciencia < self.umbral_consciencia_agencia
        ):
            objetivo: tuple[int, int] | None = None
            mejor_dist: int | None = None
            for tipo_recuerdo in ("comida", "agua"):
                candidato = objetivo_recordado(
                    mem, tipo_recuerdo, pos_x, pos_y, cap_mental, self.rng, self.config
                )
                if candidato is None:
                    continue
                dist_candidato = abs(candidato[0] - pos_x) + abs(candidato[1] - pos_y)
                if mejor_dist is None or dist_candidato < mejor_dist:
                    objetivo = candidato
                    mejor_dist = dist_candidato

            if objetivo is not None and mejor_dist is not None and mejor_dist > self.dist_deseada_territorio:
                return self._acercarse_a(pos_x, pos_y, *objetivo)

        if temperamento is not None and self.rng.random() < temperamento.sociabilidad:
            manada = manada_de(mundo, entidad_id)
            objetivo_social = (
                manada.centro if manada is not None
                else self._buscar_conspecifico_mas_cercano(
                    gestor, entidad_id, especie, pos_x, pos_y, radio, zona_idx
                )
            )
            if objetivo_social is not None:
                dist = abs(objetivo_social[0] - pos_x) + abs(objetivo_social[1] - pos_y)
                if dist > self.dist_deseada_conspecifico:
                    return self._acercarse_a(pos_x, pos_y, *objetivo_social)

        return self._paso_aleatorio()

    def _calcular_dormir(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        entidad_id: int,
        especie: Especie,
        pos_x: int,
        pos_y: int,
        radio: int,
        mem: MemoriaEspacial | None,
        cap_mental: CapacidadMental | None,
        temperamento: Temperamento | None,
        zona_idx: int = 0,
        tick_actual: int = 0,
    ) -> tuple[int, int]:
        """
        REFUGIO INSTINTIVO: buscar comodidad, seguridad, un entorno
        seguro con los tuyos -- el mismo impulso que la construcción
        consciente de refugio, pero sin depender de consciencia.

        Dos capas, en este orden, NINGUNA inventa memoria compartida:

        1. REFUGIO RECORDADO (individual): tipo de recuerdo nuevo
           "refugio" en MemoriaEspacial, misma maquinaria genérica que ya
           usan "comida"/"agua" (nucleo/memoria.py, sin cambios) -- se
           registra en sistema_necesidades.py cuando la criatura duerme
           sin amenaza cerca. Si hay uno conocido y no se está ya cerca,
           se camina hacia él.
        2. SIN refugio conocido todavía (individuos jóvenes, por
           ejemplo): se reutiliza el MISMO sesgo gregario que ya usa
           _calcular_deambular -- buscar al conspecífico más cercano con
           probabilidad = sociabilidad directa, sin escalar. No es
           "recordar el refugio de la manada", es "si no sé dónde dormir
           seguro, no duermo solo" -- el resultado práctico (una manada
           tiende a dormir agrupada porque ya se mueve junta por el mismo
           sesgo) emerge sin memoria compartida.

        Sin refugio conocido y sin conspecífico cerca (o sin sociabilidad
        que dispare el sesgo): se queda quieta, exactamente el
        comportamiento de siempre.

        Sin bono numérico añadido a propósito: el beneficio de dormir en
        refugio es puramente conductual -- una celda se recuerda como
        refugio precisamente porque no hubo amenaza la vez anterior, así
        que volver ahí ya reduce la exposición por definición, sin
        inventar un multiplicador nuevo sobre Necesidades.seguridad.
        """
        if mem is not None and cap_mental is not None:
            objetivo_refugio = objetivo_recordado(
                mem, "refugio", pos_x, pos_y, cap_mental, self.rng, self.config
            )
            if objetivo_refugio is not None:
                dist = abs(objetivo_refugio[0] - pos_x) + abs(objetivo_refugio[1] - pos_y)
                if dist > self.dist_deseada_territorio:
                    return self._acercarse_a(pos_x, pos_y, *objetivo_refugio)
                if temperamento is not None:
                    self._resolver_posible_intruso(
                        gestor, mundo, entidad_id, pos_x, pos_y, zona_idx, temperamento,
                        tick_actual,
                    )
                return (0, 0)

        if temperamento is not None and self.rng.random() < temperamento.sociabilidad:
            objetivo_conspecifico = self._buscar_conspecifico_mas_cercano(
                gestor, entidad_id, especie, pos_x, pos_y, radio, zona_idx
            )
            if objetivo_conspecifico is not None:
                dist = abs(objetivo_conspecifico[0] - pos_x) + abs(objetivo_conspecifico[1] - pos_y)
                if dist > self.dist_deseada_conspecifico:
                    return self._acercarse_a(pos_x, pos_y, *objetivo_conspecifico)

        return (0, 0)


    def _bono_arma_empunada(self, gestor: GestorEntidades, entidad_id: int) -> float:
        """Componente ofensivo del arma que esta entidad tiene empunada
        AHORA (Agarre.objetos), para el indice de asertividad social de
        nucleo/conflicto.py -- efecto_ofensivo_por_nivel[nivel] *
        agresividad del portador. 0 si no empuna nada o no tiene
        Temperamento/Agarre. Solo la empunadura cuenta (lo que este en
        Inventario sin sacar no intimida a nadie todavia); el componente
        base del arma deliberadamente no participa aqui (ver
        nucleo/conflicto.py:indice_asertividad_social)."""
        agarre = gestor.obtener_componente(entidad_id, Agarre)
        temp = gestor.obtener_componente(entidad_id, Temperamento)
        if agarre is None or temp is None:
            return 0.0
        nivel = mayor_nivel_arma(
            agarre.objetos, self.catalogo_materiales, self.recetas_armas
        )
        return bono_ofensivo_arma(nivel, temp.agresividad, self.config_armas)

    def _aplicar_afinidad(
        self,
        gestor: GestorEntidades,
        autor_id: int,
        otro_id: int,
        delta: float,
        tick_actual: int,
    ) -> None:
        """Generico: ajusta la afinidad de `autor_id` hacia `otro_id` en
        `delta` (positivo o negativo).

        Extraido de _aplicar_rencor (2026-09-06, ocio consciente) para
        reutilizarse tambien en SOCIALIZAR -- ver spec
        docs/superpowers/specs/2026-09-06-ocio-consciente-socializar-design.md.
        SOLO ESCRIBE afinidad, nunca la lee en ningun punto de decision (no
        modula comportamiento aqui).

        Mismo criterio que el nombre propio: un individuo NO consciente
        (fauna) nunca ejecuta ajustar_afinidad sobre su propio Relaciones
        en este circulo -- su componente se queda vacio indefinidamente,
        coherente con "fauna aplazada, no descartada". Un consciente SÍ
        escribe aunque la otra parte no sea consciente.
        """
        cap_mental = gestor.obtener_componente(autor_id, CapacidadMental)
        if (
            cap_mental is None
            or cap_mental.consciencia < self.umbral_consciencia_agencia
        ):
            return
        relaciones = gestor.obtener_componente(autor_id, Relaciones)
        if relaciones is None:
            return
        capacidad = capacidad_vinculos(cap_mental, self.config)
        ajustar_afinidad(
            relaciones,
            otro_id,
            delta,
            tick_actual,
            capacidad,
        )

    def _aplicar_rencor(
        self,
        gestor: GestorEntidades,
        autor_id: int,
        otro_id: int,
        tick_actual: int,
    ) -> None:
        """Ajusta la afinidad (rencor) de `autor_id` hacia `otro_id`.

        (2026-09-04, nucleo/relaciones.py) -- wrapper delgado de
        _aplicar_afinidad con el delta negativo del rencor por refugio
        ocupado (refactor 2026-09-06, ocio consciente -- el comportamiento
        es exactamente el de antes).
        """
        self._aplicar_afinidad(
            gestor, autor_id, otro_id, self.delta_rencor_disputa, tick_actual,
        )

    def _resolver_conflicto_entre(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        a_id: int,
        b_id: int,
        temperamento_a: Temperamento,
        temperamento_b: Temperamento,
        tick_actual: int,
        pos_x: int = 0,
        pos_y: int = 0,
        zona_idx: int = 0,
        urgencia_a: float | None = None,
        urgencia_b: float | None = None,
    ) -> ResultadoDisputa:
        """Extraido de _resolver_posible_intruso (conflicto por refugio
        ocupado, 2026-08-31) -- 2026-09-06, conflicto verbal: lo usa el
        refugio ocupado (wrapper), CRISIS_VIOLENTA con contacto real y el
        roce social. Calcula urgencia (1 - Necesidades.seguridad) POR
        DEFECTO, mismo_grupo (via asentamiento_de), son_familia (via
        es_familia_directa) y bono_arma (via _bono_arma_empunada) para
        ambas partes, resuelve con resolver_disputa, y aplica las
        consecuencias (drenaje de Necesidades.seguridad + rencor via
        _aplicar_rencor) segun el desenlace -- CEDE_A/CEDE_B/ENFRENTAMIENTO/
        COMPARTE, mismas cuatro ramas que _resolver_posible_intruso ya
        tenia. Simetrico: no importa cual de los dos se pase como 'a' o
        'b', el resultado y las consecuencias son coherentes en ambos
        sentidos. Devuelve el ResultadoDisputa para que el llamador decida
        si necesita reaccionar a el (hoy lo usa robo, ver _procesar_robo).

        urgencia_a/urgencia_b (2026-09-07, robo -- ver docs/superpowers/
        specs/2026-09-07-robo-compartir-confianza-design.md): override
        opcional -- "la urgencia de la propia necesidad en juego" es
        semantica libre a proposito (ver nucleo/conflicto.py:
        indice_asertividad_social), cada consumidor decide que mide. Sin
        pasarlos, comportamiento IDENTICO al de siempre (deficit de
        seguridad); robo pasa la urgencia real del ladron (su propia
        hambre), no su miedo.

        Fix 2026-09-07: si este par (a_id, b_id) ya se resolvio en este
        mismo tick por CUALQUIERA de sus disparadores, no se vuelve a
        resolver -- devuelve COMPARTE (sentinel neutro, ningun consumidor
        lee el valor de retorno hoy salvo robo) sin aplicar ningun efecto
        de nuevo."""
        clave_par = frozenset((a_id, b_id))
        if clave_par in self._pares_conflicto_resueltos_este_tick:
            return ResultadoDisputa.COMPARTE
        self._pares_conflicto_resueltos_este_tick.add(clave_par)

        nec_a = gestor.obtener_componente(a_id, Necesidades)
        nec_b = gestor.obtener_componente(b_id, Necesidades)
        if urgencia_a is None:
            urgencia_a = 1.0 - (nec_a.seguridad if nec_a else 1.0)
        if urgencia_b is None:
            urgencia_b = 1.0 - (nec_b.seguridad if nec_b else 1.0)

        asen_a = asentamiento_de(mundo, a_id)
        mismo_grupo = asen_a is not None and b_id in asen_a.miembros

        # Armas primitivas v2 (2026-09-03, ver nucleo/armas.py): el
        # componente ofensivo del arma EMPUNIADA de cada parte se suma al
        # indice de asertividad de quien la porte -- primer consumidor
        # real de robo/agravio generico para nucleo/conflicto.py. Quien
        # sujeta el refugio con un hacha_primitiva en la mano se impone
        # mas; la ley es neutra, el arma no impone un caracter, modula la
        # magnitud de la disputa.
        bono_arma_a = self._bono_arma_empunada(gestor, a_id)
        bono_arma_b = self._bono_arma_empunada(gestor, b_id)

        # Parentesco directo (2026-09-04, nucleo/parentesco.py, circulo 5
        # del arco "hilo individual"): padre/madre-hijo o hermanos suman
        # cohesion en resolver_disputa, mismo mecanismo que mismo_grupo.
        son_familia = es_familia_directa(a_id, b_id, gestor)

        resultado = resolver_disputa(
            temperamento_a,
            urgencia_a,
            temperamento_b,
            urgencia_b,
            mismo_grupo,
            self.config_conflicto,
            bono_arma_a=bono_arma_a,
            bono_arma_b=bono_arma_b,
            son_familia=son_familia,
        )

        if resultado == ResultadoDisputa.COMPARTE:
            return resultado
        if resultado == ResultadoDisputa.CEDE_B:
            # B cede: A se impone, B paga el coste de la intimidacion.
            if nec_b is not None:
                nec_b.seguridad = max(
                    0.0, nec_b.seguridad - self.drenaje_seguridad_perdedor
                )
            # Rencor (2026-09-04): B (perdedor) cedio; B, si es consciente,
            # acumula rencor hacia A. A no cambia.
            self._aplicar_rencor(gestor, b_id, a_id, tick_actual)
            return resultado
        if resultado == ResultadoDisputa.CEDE_A:
            # A cede: paga el coste, no reclama nada este tick.
            if nec_a is not None:
                nec_a.seguridad = max(
                    0.0, nec_a.seguridad - self.drenaje_seguridad_perdedor
                )
            # Rencor (2026-09-04): A (perdedor) cedio; A, si es consciente,
            # acumula rencor hacia B. B no cambia.
            self._aplicar_rencor(gestor, a_id, b_id, tick_actual)
            return resultado
        # ENFRENTAMIENTO: empate renido entre dos partes asertivas,
        # ambos pagan el coste del enfrentamiento.
        if nec_a is not None:
            nec_a.seguridad = max(
                0.0, nec_a.seguridad - self.drenaje_seguridad_enfrentamiento
            )
        if nec_b is not None:
            nec_b.seguridad = max(
                0.0, nec_b.seguridad - self.drenaje_seguridad_enfrentamiento
            )
        # Rencor (2026-09-04): ambas partes acumulan rencor mutuo, cada una
        # solo si ES consciente -- un gnomo consciente que se enfrenta a un
        # lobo no-consciente acumula rencor hacia el aunque el lobo no
        # acumule nada de vuelta.
        self._aplicar_rencor(gestor, a_id, b_id, tick_actual)
        self._aplicar_rencor(gestor, b_id, a_id, tick_actual)
        # Sonido fisico (2026-09-06, circulo 4a): SOLO el desenlace
        # ENFRENTAMIENTO emite sonido -- CEDE_A/CEDE_B/COMPARTE no son
        # pelea real y no emiten nada. Magnitud = peso combinado de ambas
        # partes (DimensionesFisicas, no se consultaba antes en esta
        # funcion).
        dims_a = gestor.obtener_componente(a_id, DimensionesFisicas)
        dims_b = gestor.obtener_componente(b_id, DimensionesFisicas)
        if dims_a is not None and dims_b is not None:
            zona_encuentro = mundo.territorio.zonas[zona_idx]
            emitir_sonido(zona_encuentro, pos_x, pos_y, tick_actual, dims_a.peso + dims_b.peso)
        return resultado

    def _resolver_posible_intruso(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        propietario_id: int,
        pos_x: int,
        pos_y: int,
        zona_idx: int,
        temperamento: Temperamento,
        tick_actual: int = 0,
    ) -> None:
        """
        CONFLICTO POR REFUGIO OCUPADO -- primer consumidor de
        nucleo/conflicto.py. Tambien primer consumidor de
        nucleo/relaciones.py (rencor persistente, 2026-09-04): ademas del
        drenaje de seguridad ya existente, cada desenlace escribe afinidad
        NEGATIVA sobre el Relaciones de la parte CONSCIENTE.
        tick_actual: para ultima_actualizacion_tick de los vinculos.

        Desde 2026-09-06 (conflicto verbal) es un wrapper DELGADO: conserva
        integra la localizacion del refugio propio (Construccion real con
        completado_alguna_vez, no un punto de memoria instintivo sin dueno)
        y del intruso en la misma celda+zona; en cuanto identifica
        `intruso_id`, delega el resto en `_resolver_conflicto_entre`, el
        resolutor compartido con CRISIS_VIOLENTA y el roce social.

        zona_idx: "misma celda" no basta con comparar (x, y) -- con
        varias zonas (superficie + cuevas) dos entidades en zonas
        DISTINTAS pueden compartir coordenadas numericas por pura
        coincidencia, mismo hallazgo que ya obligo a filtrar
        almacen_cercano/agrupar_por_proximidad por zona. Se filtra tanto
        la propia Construccion como cualquier candidato a intruso.

        No desplaza al intruso directamente: esta funcion resuelve el
        movimiento de UNA sola entidad por iteracion (el propietario),
        no puede mover a otra desde aqui. La consecuencia de perder es
        un drenaje de Necesidades.seguridad -- el MISMO campo que ya
        drena cualquier amenaza (nucleo/amenaza.py) -- que sube la
        utilidad_huir del perdedor en su propia proxima decision: el
        perdedor tiende a irse por su cuenta a traves del mecanismo de
        huida ya existente, sin teletransportarlo desde aqui.
        """
        cid = construccion_propia(gestor, propietario_id, "refugio")
        if cid is None:
            return
        con_pos = gestor.obtener_componente(cid, Posicion)
        construccion = gestor.obtener_componente(cid, Construccion)
        if (
            con_pos is None
            or construccion is None
            or not construccion.completado_alguna_vez
            or con_pos.x != pos_x
            or con_pos.y != pos_y
            or con_pos.zona_idx != zona_idx
        ):
            return

        # 2026-09-08 (nucleo/indice_espacial.py): en_celda ya filtra por
        # celda/zona exacta -- se añaden los guards de Temperamento/
        # Identidad que el escaneo O(N) original garantizaba implicito.
        intruso_id: int | None = None
        fuente_intruso = (
            self._indice_actual.en_celda(pos_x, pos_y, zona_idx)
            if self._indice_actual is not None
            else gestor.entidades_con(Posicion, Temperamento, Identidad)
        )
        for otro_id in fuente_intruso:
            if otro_id == propietario_id:
                continue
            pos_otro = gestor.obtener_componente(otro_id, Posicion)
            if pos_otro is None or pos_otro.x != pos_x or pos_otro.y != pos_y or pos_otro.zona_idx != zona_idx:
                continue
            if (
                gestor.obtener_componente(otro_id, Temperamento) is None
                or gestor.obtener_componente(otro_id, Identidad) is None
            ):
                continue
            intruso_id = otro_id
            break
        if intruso_id is None:
            return

        temperamento_intruso = gestor.obtener_componente(intruso_id, Temperamento)
        if temperamento_intruso is None:
            return

        self._resolver_conflicto_entre(
            gestor, mundo, propietario_id, intruso_id,
            temperamento, temperamento_intruso, tick_actual,
            pos_x, pos_y, zona_idx,
        )

    def _calcular_construir(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        entidad_id: int,
        especie: Especie,
        pos_x: int,
        pos_y: int,
        radio: int,
        mem: MemoriaEspacial | None,
        cap_mental: CapacidadMental | None,
        temperamento: Temperamento | None,
        zona_idx: int = 0,
    ) -> tuple[int, int]:
        """
        REFUGIO/ALMACÉN CONSTRUIDO (ver componentes/construccion.py,
        nucleo/construccion.py, nucleo/asentamiento.py). Localiza el
        objetivo de construcción actual de esta entidad
        (objetivo_construccion_actual: refugio propio mientras no esté
        terminado, si no el almacén del asentamiento del que sea
        miembro). Si no existe todavía, lo crea: el almacén en el CENTRO
        del asentamiento -- hay que llegar hasta ahí primero, no se crea
        donde a cada gnomo le pille. Una vez existe, camina hacia él
        igual que _calcular_dormir camina hacia el refugio recordado.

        SESGO DE AGRUPAMIENTO para un refugio nuevo (2026-09-04, mismo
        criterio de leyes neutras que ya usa _calcular_dormir -- ninguna
        regla decide que "debe" formarse un asentamiento, solo se
        reutilizan dos mecanismos que el motor ya tiene en otro sitio,
        aplicados aquí por primera vez):
        1. REFUGIO RECORDADO (individual, `objetivo_recordado(mem,
           "refugio", ...)`, MISMA memoria que ya usa _calcular_dormir --
           no distingue de quién es el refugio, se registra en
           sistema_recursos.py al completar CUALQUIER construcción propia
           y en sistema_necesidades.py cada vez que la criatura duerme
           sin amenaza cerca, sea o no su propio refugio). Si hay un
           recuerdo y está lejos, se camina hacia él en vez de construir
           donde se esté.
        2. SIN refugio recordado todavía (individuo joven, recién
           independizado): mismo sesgo gregario que ya usa
           _calcular_deambular/_calcular_dormir -- buscar al conspecífico
           más cercano con probabilidad = sociabilidad propia, sin
           escalar. Si está lejos, se camina hacia él antes de construir.

        Sin ninguno de los dos (o ya lo bastante cerca), se construye en
        la posición ACTUAL -- comportamiento original, sin lógica de
        selección de sitio más allá de este sesgo.

        CAPACIDAD POR CELDA (ver config/materiales.yaml sección
        construccion y nucleo/construccion.py:
        espacio_disponible_para_construir): antes de crear una
        Construccion nueva se comprueba que su huella_m2 quepa en el
        espacio libre de la celda -- si no cabe, no se crea este tick.
        Deliberadamente sin ninguna búsqueda de una celda vecina con
        hueco: el individuo simplemente lo reintentará en su próxima
        posición según el resto de su comportamiento (sesgo gregario,
        deambular) ya lo mueva. Para el almacén esto puede significar
        quedarse parado en el centro del asentamiento sin poder construir
        si esa celda exacta está llena -- límite conocido, no resuelto
        aquí (ver CLAUDE.md).

        La transferencia real de materiales (Inventario ->
        Construccion.materiales) NO ocurre aquí -- sistema_recursos.py la
        resuelve una vez la entidad está en la misma celda, mismo reparto
        de responsabilidades que COMER/BEBER (este sistema decide hacia
        dónde ir, sistema_recursos.py decide qué pasa al llegar).
        """
        # indice=None deliberado (bug real encontrado en auditoria de
        # codigo, 2026-09-11): el indice congelado al principio del tick
        # dejaba a almacen_cercano/construccion_completada_de_asentamiento
        # sin ver una construccion comunal recien creada por OTRO miembro
        # este mismo tick, permitiendo que dos gnomos llegaran al centro
        # del asentamiento y crearan cada uno su propio almacen/salon/
        # cocina duplicado en la misma celda -- justo lo que el propio
        # docstring de almacen_cercano ("busqueda EN VIVO") decia evitar.
        # Coste acotado: solo entidades que ejecutan CONSTRUIR este tick.
        objetivo = objetivo_construccion_actual(
            gestor, mundo, entidad_id, self.radio_cluster_asentamiento,
            indice=None,
        )
        if objetivo is None:
            return (0, 0)
        tipo, cid, pos_creacion = objetivo

        if cid is not None:
            con_pos = gestor.obtener_componente(cid, Posicion)
            if con_pos is None or (con_pos.x == pos_x and con_pos.y == pos_y):
                return (0, 0)
            return self._acercarse_a(pos_x, pos_y, con_pos.x, con_pos.y)

        if tipo == "refugio":
            objetivo_refugio = None
            if mem is not None and cap_mental is not None:
                objetivo_refugio = objetivo_recordado(
                    mem, "refugio", pos_x, pos_y, cap_mental, self.rng, self.config
                )
            if objetivo_refugio is not None:
                dist = abs(objetivo_refugio[0] - pos_x) + abs(objetivo_refugio[1] - pos_y)
                if dist > self.dist_deseada_territorio:
                    return self._acercarse_a(pos_x, pos_y, *objetivo_refugio)
            elif temperamento is not None and self.rng.random() < temperamento.sociabilidad:
                objetivo_conspecifico = self._buscar_conspecifico_mas_cercano(
                    gestor, entidad_id, especie, pos_x, pos_y, radio, zona_idx
                )
                if objetivo_conspecifico is not None:
                    dist = abs(objetivo_conspecifico[0] - pos_x) + abs(objetivo_conspecifico[1] - pos_y)
                    if dist > self.dist_deseada_conspecifico:
                        return self._acercarse_a(pos_x, pos_y, *objetivo_conspecifico)

            if espacio_disponible_para_construir(
                gestor, pos_x, pos_y, zona_idx, self.config
            ) < huella_m2_para("refugio", self.config_construccion):
                return (0, 0)
            crear_construccion(
                gestor, pos_x, pos_y, "refugio", propietario_id=entidad_id, zona_idx=zona_idx
            )
            return (0, 0)

        # Comunal (almacen/salon_comun/cocina), todavia no existe: hay
        # que llegar al centro del asentamiento antes de poder crearlo.
        #
        # BUG REAL (2026-09-09, ver herramientas/harness_calibracion.py):
        # este bloque creaba SIEMPRE tipo="almacen" hardcodeado, sin
        # mirar `tipo` -- desde que cocinas comunes (2026-09-08) hizo
        # que objetivo_construccion_actual pudiera devolver
        # "salon_comun"/"cocina" con cid=None, cada intento de empezar
        # cualquiera de los dos creaba en su lugar OTRO almacen
        # duplicado en la misma celda (nunca registrado como
        # salon_comun/cocina en ninguna consulta por tipo, y confundiendo
        # a objetivo_construccion_actual con dos "almacen" a la vez).
        # Explica por si solo por que salon_comun/cocina nunca llegaban
        # a acumular ni 1kg de material en ninguna semilla medida.
        cx, cy = pos_creacion
        if (cx, cy) != (pos_x, pos_y):
            return self._acercarse_a(pos_x, pos_y, cx, cy)
        if espacio_disponible_para_construir(
            gestor, pos_x, pos_y, zona_idx, self.config
        ) < huella_m2_para(tipo, self.config_construccion):
            return (0, 0)
        crear_construccion(gestor, pos_x, pos_y, tipo, propietario_id=None, zona_idx=zona_idx)
        return (0, 0)

    def _acercarse_a(self, ox: int, oy: int, tx: int, ty: int) -> tuple[int, int]:
        """Calcula el paso unitario Manhattan más directo hacia el objetivo."""
        dx = 0 if ox == tx else (1 if tx > ox else -1)
        dy = 0 if oy == ty else (1 if ty > oy else -1)
        if dx != 0 and dy != 0:
            return (dx, 0) if self.rng.random() < 0.5 else (0, dy)
        return dx, dy

    def _paso_aleatorio(self) -> tuple[int, int]:
        """Genera un paso unitario aleatorio en 4 direcciones ortogonales o espera."""
        return self.rng.choice([(0, 1), (0, -1), (1, 0), (-1, 0), (0, 0)])