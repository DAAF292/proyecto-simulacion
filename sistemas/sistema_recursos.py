"""
sistemas/sistema_recursos.py

Sistema de forrajeo, hidratación, carroñeo y fertilización del suelo (Fase 3: Metabolismo).
Gestiona la ingesta de recursos vegetales o necromasa mediante Accion.COMER,
la absorción de agua permanente o charcos efímeros mediante Accion.BEBER,
la evacuación de desechos biológicos (abono) y el ciclo térmico de charcos.
"""

from __future__ import annotations

import random
from typing import Any

from componentes.agarre import Agarre
from componentes.capacidad_mental import CapacidadMental
from componentes.construccion import Construccion
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.fogata import Fogata
from componentes.identidad import Identidad
from componentes.intencion import Accion, Intencion
from componentes.inventario import Inventario
from componentes.memoria_espacial import MemoriaEspacial
from componentes.necesidades import Necesidades
from componentes.necromasa import Necromasa
from componentes.planta import Planta
from componentes.posicion import Posicion
from componentes.semillas import Semillas
from componentes.vocacion import Vocacion
from nucleo.agua import fraccion_escurrida_por_pendiente, hay_agua_potable, pendiente_local
from nucleo.armas import (
    celda_ofrece_material_arma,
    mayor_nivel_arma,
    mejor_receta_completable,
    recolectar_material_arma_de_celda,
    tiene_arma_nivel2_o_mas,
)
from nucleo.herramientas import tiene_herramienta
from nucleo.celda import Celda
from nucleo.construccion import (
    construccion_de_tipo_en,
    masa_minima_para,
    objetivo_construccion_actual,
    progreso_construccion,
    transferir_a_construccion,
)
from nucleo.comida import elaborar_recurso, es_elaborado, recurso_base
from nucleo.entidad import GestorEntidades, crear_fogata, procesar_deceso
from nucleo.espacio import plantas_competidoras_en
from nucleo.eventos import BusEventos, Evento, Severidad
from nucleo.fuego import celda_tiene_combustible, fogata_en
from nucleo.flora import intentar_colonizar_celda
from nucleo.indice_espacial import construir_indice_espacial
from nucleo.inventario import (
    descartar_contenidos_para_liberar,
    espacio_disponible_kg,
    espacio_disponible_provisiones_kg,
)
from nucleo.memoria import capacidad_memoria, purgar_recuerdo_invalido, registrar_recuerdo
from nucleo.mundo import Mundo
from nucleo.reloj import Reloj


class SistemaRecursos:
    """
    Resuelve el consumo metabólico directo de entidades sobre recursos del terreno
    o detritos orgánicos presentes en la misma celda.
    """

    def __init__(self, config: dict[str, Any], rng: random.Random) -> None:
        self.config = config
        self.rng = rng
        # Observación para BOSQUE_AUTO_TICKS (2026-09-07, ver spec
        # docs/superpowers/specs/2026-09-07-provisiones-alimento-design.md):
        # cuántas veces se dispara de verdad la entrada (guardar
        # excedente) y la salida (comer de la despensa). El spec ya avisa
        # de que el disparador es deliberadamente estrecho -- solo
        # observación, ningún camino de decisión los lee.
        self._stats_provisiones_guardadas: int = 0
        self._stats_provisiones_consumidas: int = 0
        # Cocinar + intoxicacion (2026-09-08, ver docs/superpowers/specs/
        # 2026-09-08-como-cocinar-design.md). Solo observacion.
        self._stats_cocinar_resuelto: int = 0
        self._stats_muertes_intoxicacion: int = 0
        # Alacena de cocina comun (2026-09-08, ver docs/superpowers/specs/
        # 2026-09-08-cocinas-comunes-design.md). Solo observacion.
        self._stats_alacena_consumida: int = 0
        # IndiceEspacial del tick en curso (2026-09-08) -- ver
        # sistema_movimiento.py:_indice_actual para el mismo patron.
        self._indice_actual = None
        self._cachear_configuracion()

    def _cachear_configuracion(self) -> None:
        """Extrae coeficientes de consumo, hidratación y fertilidad."""
        cfg_cons = self.config.get("consumo", {})
        self.tasa_consumo_comer: float = float(cfg_cons.get("tasa_consumo_al_comer", 0.5))
        self.tasa_consumo_beber: float = float(cfg_cons.get("tasa_consumo_al_beber", 0.2))
        # tasa_consumo_al_comer_por_especie (2026-09-10, ver config/
        # fisiologia.yaml): solo para forraje vegetal (Accion.COMER),
        # anclado al tiempo real de alimentación de cada especie -- NO
        # afecta al carroñeo (self.tasa_consumo_comer sigue siendo el
        # universal ahí) ni a tasa_consumo_beber (beber ya es rápido y
        # universal en la realidad, sin relación con el peso).
        self.tasa_consumo_comer_por_especie: dict[str, float] = {
            k: float(v) for k, v in cfg_cons.get("tasa_consumo_al_comer_por_especie", {}).items()
        }
        # Cocinar (2026-09-08, ver docs/superpowers/specs/
        # 2026-09-08-como-cocinar-design.md). PROVISIONAL.
        self.tasa_cocinar_kg_tick: float = float(cfg_cons.get("tasa_cocinar_kg_tick", 0.5))
        # factor_bono_tasa_cocina_comun (2026-09-08, cocinas comunes --
        # ver docs/superpowers/specs/2026-09-08-cocinas-comunes-design.md):
        # cocinar en una cocina comun es mas rapido que con una Fogata
        # individual. PROVISIONAL.
        self.factor_bono_tasa_cocina_comun: float = float(
            cfg_cons.get("factor_bono_tasa_cocina_comun", 2.0)
        )

        cfg_abono = self.config.get("abono", {})
        self.incremento_fertilidad: float = float(
            cfg_abono.get("incremento_fertilidad_por_aliviarse", 0.2)
        )
        self.techo_fertilidad: float = float(cfg_abono.get("techo_fertilidad", 1.0))

        self.cfg_charco = self.config.get("charcos", {})
        self.tasa_evaporacion_charco: float = float(
            self.cfg_charco.get("tasa_evaporacion_charco_por_tick", 0.0006)
        )
        self.tasa_agotamiento_charco: float = float(
            self.cfg_charco.get("tasa_agotamiento_charco_al_beber", 0.01)
        )
        # Drenaje de la reserva de humedad de subsuelo, mucho mas lento
        # que la evaporacion de un charco a proposito -- ver
        # config/materiales.yaml, nucleo/celda.py:tipo_sustrato/
        # humedad_subsuelo y config/hidrologia.yaml seccion charcos.
        self.tasa_drenaje_subsuelo: float = float(
            self.cfg_charco.get("tasa_drenaje_humedad_subsuelo_por_tick", 0.001)
        )
        self.catalogo_materiales: dict[str, Any] = self.config.get("materiales", {})
        # Refugio construido -- ver nucleo/construccion.py.
        self.config_construccion: dict[str, Any] = self.config.get("construccion", {})
        self.tasa_aporte_construccion: float = float(
            self.config_construccion.get("tasa_aporte_construccion_kg_tick", 1.0)
        )
        # RECOLECTAR -- ver nucleo/construccion.py.
        self.tasa_recoleccion: float = float(
            self.config_construccion.get("tasa_recoleccion_kg_tick", 1.0)
        )
        self.fraccion_carga_maxima: float = float(
            self.config.get("inventario", {}).get("fraccion_carga_maxima", 0.25)
        )
        # Provisiones de alimento (2026-09-07, ver
        # docs/superpowers/specs/2026-09-07-provisiones-alimento-design.md):
        # capacidad TOTALMENTE INDEPENDIENTE de fraccion_carga_maxima.
        self.fraccion_provisiones_maxima: float = float(
            self.config.get("inventario", {}).get("fraccion_provisiones_maxima", 0.05)
        )
        self.saciedad_minima_para_guardar_provisiones: float = float(
            self.config.get("necesidades", {}).get("defecto", {}).get(
                "saciedad_minima_para_guardar_provisiones", 0.9
            )
        )
        self.umbral_purga_provisiones: float = float(
            self.config.get("descomposicion", {}).get("umbral_purga_masa", 0.05)
        )
        # Almacén de asentamiento -- ver nucleo/asentamiento.py y
        # nucleo/construccion.py:objetivo_construccion_actual.
        self.radio_cluster_asentamiento: int = int(
            self.config.get("asentamiento", {}).get("radio_cluster_celdas", 6)
        )
        # Agarre -- ver componentes/agarre.py y config/poblacion.yaml
        # seccion rangos_raciales.<especie>.puntos_agarre.
        self.rangos_raciales: dict[str, Any] = self.config.get("rangos_raciales", {})
        # Fuego controlado -- ver componentes/fogata.py, nucleo/fuego.py
        # y config/fuego.yaml.
        cfg_fuego = self.config.get("fuego", {})
        self.probabilidad_encender_fuego: float = float(
            cfg_fuego.get("probabilidad_encender_fuego", 0.4)
        )
        self.masa_yesca_consumida: float = float(cfg_fuego.get("masa_yesca_consumida_kg", 0.5))
        self.combustible_inicial_fogata: float = float(
            cfg_fuego.get("combustible_inicial_fogata_kg", 5.0)
        )
        self.tasa_consumo_fogata: float = float(
            cfg_fuego.get("tasa_consumo_combustible_fogata_kg_tick", 0.1)
        )
        self.piedras_necesarias_fuego: int = int(cfg_fuego.get("piedras_necesarias", 2))
        # Mismo umbral que ya exime del sesgo de territorio y gatea
        # CONSTRUIR/RECOLECTAR de material -- ver sistema_decision.py.
        self.umbral_consciencia_agencia: float = float(
            self.config.get("decision", {}).get("umbral_consciencia_agencia", 0.3)
        )
        # Toxicidad de crudo + comida elaborada (2026-09-08, ver
        # docs/superpowers/specs/2026-09-08-como-cocinar-design.md).
        # PROVISIONALES.
        self.probabilidad_muerte_intoxicacion_base: float = float(
            self.config.get("necesidades", {}).get("defecto", {}).get(
                "probabilidad_muerte_intoxicacion_base", 0.001
            )
        )
        self.factor_mejora_elaboracion: float = float(
            self.config.get("elaboracion", {}).get("factor_mejora_elaboracion", 1.5)
        )

        cfg_dep = self.config.get("depredacion", {})
        self.eficiencia_biomasa_saciedad: float = float(
            cfg_dep.get("eficiencia_biomasa_saciedad", 1.5)
        )
        self.eficiencia_biomasa_hidratacion: float = float(
            cfg_dep.get("eficiencia_biomasa_hidratacion", 0.5)
        )

        # Ver config/constantes.yaml sección memoria: probabilidad de
        # purga por visita fallida, no purga inmediata al primer fallo.
        cfg_mem = self.config.get("memoria", {})
        self.prob_purgar_recuerdo_agotado: float = float(
            cfg_mem.get("prob_purgar_recuerdo_agotado", 0.05)
        )

        # Mapa de valores nutricionales e hídricos por recurso vegetal
        self.especies_flora: dict[str, Any] = self.config.get("flora", {}).get("especies", {})
        self.nutricion_flora: dict[str, float] = {}
        self.hidratacion_flora: dict[str, float] = {}
        # toxico_crudo_flora (2026-09-08, ver docs/superpowers/specs/
        # 2026-09-08-como-cocinar-design.md): mismo bucle que nutricion_
        # flora/hidratacion_flora, no uno aparte.
        self.toxico_crudo_flora: dict[str, bool] = {}
        for esp_data in self.especies_flora.values():
            for rec in esp_data.get("recursos", []):
                nom = rec.get("nombre")
                if nom:
                    self.nutricion_flora[nom] = float(rec.get("valor_nutricional", 0.2))
                    self.hidratacion_flora[nom] = float(rec.get("valor_hidratacion", 0.05))
                    self.toxico_crudo_flora[nom] = bool(rec.get("toxico_crudo", False))

        # especie_por_recurso: {nombre_recurso: especie_que_lo_produce}
        # (2026-09-03, pieza 3 -- cupo de espacio compartido por celda).
        # La pista competidora no escribe Celda.tipo_recurso, así que
        # COMER/RECOLECTAR no pueden saber qué especie produce un recurso
        # mirando solo la celda: este mapa permite (a) exigir una entidad
        # Planta competidora real en la posición para recursos competidores,
        # y (b) recuperar la especie para el hook de zoocoria.
        self.especie_por_recurso: dict[str, str] = {}
        for especie, esp_data in self.especies_flora.items():
            for rec in esp_data.get("recursos", []):
                nom = rec.get("nombre")
                if nom and nom not in self.especie_por_recurso:
                    self.especie_por_recurso[nom] = especie

        # Zoocoria (2026-09-02, ver componentes/semillas.py y
        # docs/superpowers/specs/2026-09-01-propagacion-flora-design.md).
        self.umbral_minimo_idoneidad_colonizacion: float = float(
            self.config.get("flora", {}).get("umbral_minimo_idoneidad_colonizacion", 0.2)
        )
        self.probabilidad_recogida_semilla_zoocoria: float = float(
            self.config.get("flora", {}).get("probabilidad_recogida_semilla_zoocoria", 0.3)
        )
        self.probabilidad_plantar_semilla_en_aliviarse: float = float(
            self.config.get("flora", {}).get("probabilidad_plantar_semilla_en_aliviarse", 0.5)
        )

        # Armas primitivas v2 (2026-09-03, ver config/armas.yaml): recetas y
        # efectos por nivel, y el peso de cada objeto discreto (tambien
        # piedra_suelta, que viaja de Agarre a Inventario al encenderse la
        # fogata).
        self.config_armas: dict[str, Any] = self.config.get("armas", {})
        self.recetas_armas: list[dict[str, Any]] = self.config_armas.get("recetas", [])
        self.peso_objeto_kg: dict[str, float] = self.config.get("peso_objeto_kg", {})
        # Herramientas (2026-09-11, circulo 2 del arco "fabricacion y uso
        # de herramientas" -- ver docs/superpowers/specs/
        # 2026-09-11-fabricacion-herramientas-design.md y
        # config/herramientas.yaml). Bonos PROVISIONALES, sin calibrar.
        self.config_herramientas: dict[str, Any] = self.config.get("herramientas", {})
        self.recetas_herramientas: list[dict[str, Any]] = self.config_herramientas.get("recetas", [])
        self.factor_bono_tasa_recolectar_con_herramienta: float = float(
            self.config_herramientas.get("factor_bono_tasa_recolectar_con_herramienta", 1.5)
        )
        self.factor_bono_tasa_aporte_construccion_con_herramienta: float = float(
            self.config_herramientas.get(
                "factor_bono_tasa_aporte_construccion_con_herramienta", 1.3
            )
        )
        # Observacion (2026-09-11), solo _stats -- confirma que la pieza
        # se ejerce de verdad en juego libre.
        self._stats_herramientas_fabricadas: int = 0
        # Observacion (2026-09-11, "cargar con prioridad" -- ver
        # nucleo/inventario.py:descartar_contenidos_para_liberar): kg
        # totales descartados por un consciente para liberar sitio a
        # material de arma/herramienta que su intencion activa necesita.
        self._stats_material_descartado_por_prioridad_kg: float = 0.0

    def ejecutar(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        reloj: Reloj,
        bus_eventos: BusEventos,
        indice=None,
    ) -> None:
        """
        Punto de entrada tick a tick de la Fase 3.
        Actualiza charcos ambientales y resuelve las intenciones COMER, BEBER y ALIVIARSE.

        indice (2026-09-08, nucleo/indice_espacial.py): IndiceEspacial ya
        construido, opcional -- se guarda en self y lo consulta
        _resolver_comer para el carroñeo de Necromasa. Sin indice, se
        construye uno interno (mismo comportamiento).
        """
        self._indice_actual = indice if indice is not None else construir_indice_espacial(gestor)
        # Charcos/humedad de subsuelo son estado POR ZONA (cada
        # ZonaBioma es autonoma, con su propio clima_actual) -- se
        # actualizan todas las zonas del territorio, no solo la
        # superficie.
        for zona_i in mundo.territorio.zonas:
            self._actualizar_charcos(zona_i)

        entidades = sorted(gestor.entidades_con(Intencion, Posicion, Necesidades, Identidad))

        for eid in entidades:
            intencion = gestor.obtener_componente(eid, Intencion)
            pos = gestor.obtener_componente(eid, Posicion)
            nec = gestor.obtener_componente(eid, Necesidades)
            ident = gestor.obtener_componente(eid, Identidad)
            mem = gestor.obtener_componente(eid, MemoriaEspacial)
            cap_mental = gestor.obtener_componente(eid, CapacidadMental)

            if intencion is None or pos is None or nec is None or ident is None:
                continue

            zona = mundo.territorio.zonas[pos.zona_idx]
            celda = zona.obtener_celda(pos.x, pos.y)
            # consciente: usado tanto por RECOLECTAR (ya lo necesitaba)
            # como por el contador de Vocacion (2026-09-11, ver
            # componentes/vocacion.py) -- solo individuos conscientes
            # practican de verdad las 4 cubetas vocacionales hoy.
            consciente = (
                cap_mental is not None and cap_mental.consciencia >= self.umbral_consciencia_agencia
            )

            if intencion.accion == Accion.COMER:
                self._resolver_comer(
                    gestor, eid, ident, nec, mem, cap_mental, celda, pos.x, pos.y, pos.zona_idx,
                    bus_eventos, reloj.tick_actual,
                )
            elif intencion.accion == Accion.BEBER:
                self._resolver_beber(nec, mem, cap_mental, celda, pos.x, pos.y)
            elif intencion.accion == Accion.ALIVIARSE:
                self._resolver_aliviarse(gestor, eid, nec, celda, pos.x, pos.y, pos.zona_idx)
            elif intencion.accion == Accion.CONSTRUIR:
                inv = gestor.obtener_componente(eid, Inventario)
                self._resolver_construir(
                    gestor, mundo, eid, mem, cap_mental, inv, pos.x, pos.y, reloj.tick_actual, bus_eventos
                )
                self._incrementar_vocacion(gestor, eid, consciente, "conteo_constructor")
            elif intencion.accion == Accion.RECOLECTAR:
                inv = gestor.obtener_componente(eid, Inventario)
                dims = gestor.obtener_componente(eid, DimensionesFisicas)
                agarre = gestor.obtener_componente(eid, Agarre)
                self._resolver_recolectar(
                    inv, dims, celda, agarre, ident.especie.value, consciente,
                    recolectar_arma=intencion.recolectar_motivo_arma,
                    recolectar_herramienta=intencion.recolectar_motivo_herramienta,
                    recolectar_fuego=intencion.recolectar_motivo_fuego,
                    gestor=gestor, pos_x=pos.x, pos_y=pos.y, zona_idx=pos.zona_idx,
                )
                self._incrementar_vocacion(gestor, eid, consciente, "conteo_forrajero")
            elif intencion.accion == Accion.ENCENDER_FUEGO:
                agarre_fuego = gestor.obtener_componente(eid, Agarre)
                self._resolver_encender_fuego(
                    gestor, celda, pos.x, pos.y, pos.zona_idx, bus_eventos, reloj.tick_actual,
                    agarre_fuego,
                )
            elif intencion.accion == Accion.COCINAR:
                self._resolver_cocinar(gestor, eid, pos.x, pos.y, pos.zona_idx)
                self._incrementar_vocacion(gestor, eid, consciente, "conteo_cocinero")
            elif intencion.accion == Accion.FABRICAR:
                inv = gestor.obtener_componente(eid, Inventario)
                agarre_fabricar = gestor.obtener_componente(eid, Agarre)
                self._resolver_fabricar(
                    gestor, eid, inv, pos.x, pos.y, pos.zona_idx, bus_eventos, reloj.tick_actual,
                    intencion.fabricar_categoria, agarre=agarre_fabricar,
                )
                self._incrementar_vocacion(gestor, eid, consciente, "conteo_artesano")

        # Fogatas: consumo de combustible propio y extincion (ver
        # componentes/fogata.py) -- independiente de la Accion de nadie,
        # mismo criterio que _actualizar_charcos: se procesa cada tick
        # para TODA fogata existente, no solo para quien la encendio.
        self._consumir_fogatas(gestor)

    def _incrementar_vocacion(self, gestor, eid: int, consciente: bool, campo: str) -> None:
        """Contador de práctica real (2026-09-11, ver componentes/
        vocacion.py) -- incrementado en el DESPACHO de la acción (no
        tras confirmar éxito del resolver), mismo criterio que el resto
        de contadores de observación de este sistema: representa "ticks
        dedicados a esta labor", no "kg conseguidos" -- solo consciente,
        fauna nunca practica estas 4 acciones hoy."""
        if not consciente:
            return
        voc = gestor.obtener_componente(eid, Vocacion)
        if voc is None:
            return
        setattr(voc, campo, getattr(voc, campo) + 1)

    def _actualizar_charcos(self, zona: Any) -> None:
        """Genera/evapora charco y llena/drena humedad de subsuelo según el
        material y la pendiente local de cada celda (ver
        config/materiales.yaml y el docstring de
        Celda.tipo_sustrato/humedad_subsuelo).

        La lluvia que no logra infiltrarse en el sustrato
        (tasa_infiltracion del material, amortiguada según cuánto hueco
        le queda a humedad_subsuelo -- terreno ya saturado encharca más,
        no menos) ni escurre por la pendiente
        (nucleo/agua.py:fraccion_escurrida_por_pendiente) se queda en
        superficie como charco; la que sí se infiltra alimenta
        humedad_subsuelo, topada por la capacidad_retencion del material y
        con su propio drenaje mucho más lento que la evaporación de un
        charco.
        """
        clima_actual = getattr(zona, "clima_actual", None)
        nombre_clima = clima_actual.value if clima_actual is not None else "despejado"

        tasa_gen = float(
            self.config.get("clima", {})
            .get("efectos", {})
            .get(nombre_clima, {})
            .get("tasa_generacion_charco_por_tick", 0.0)
        )
        techo_charco = float(self.cfg_charco.get("techo_profundidad_charco", 0.03))

        for y in range(zona.alto):
            for x in range(zona.ancho):
                celda = zona.obtener_celda(x, y)
                # El charco es agua EFIMERA sobre tierra firme: sobre una
                # celda de agua permanente el campo no significa nada
                # (hay_agua_potable/profundidad_agua_potable ya miran
                # ambas capas) y solo ensuciaria el estado persistido. Lo
                # mismo aplica a humedad_subsuelo -- fijada en generacion
                # al tope de su material (nucleo/zona_bioma.py), nunca
                # simulada tick a tick para estas celdas.
                if celda.tiene_agua:
                    continue

                material = self.catalogo_materiales.get(celda.tipo_sustrato, {})
                tasa_infiltracion = float(material.get("tasa_infiltracion", 0.0))
                capacidad_retencion = float(material.get("capacidad_retencion", 0.0))

                if tasa_gen > 0.0:
                    if capacidad_retencion > 0.0:
                        hueco_restante = max(0.0, capacidad_retencion - celda.humedad_subsuelo)
                        infiltracion_efectiva = tasa_infiltracion * (hueco_restante / capacidad_retencion)
                    else:
                        infiltracion_efectiva = 0.0

                    pendiente = pendiente_local(zona, x, y)
                    escurrida = fraccion_escurrida_por_pendiente(pendiente, self.cfg_charco)
                    fraccion_encharca = max(0.0, 1.0 - infiltracion_efectiva - escurrida)

                    celda.humedad_subsuelo = min(
                        capacidad_retencion,
                        celda.humedad_subsuelo + tasa_gen * infiltracion_efectiva,
                    )
                    celda.profundidad_charco = min(
                        techo_charco, celda.profundidad_charco + tasa_gen * fraccion_encharca
                    )
                else:
                    if celda.profundidad_charco > 0.0:
                        celda.profundidad_charco = max(
                            0.0, celda.profundidad_charco - self.tasa_evaporacion_charco
                        )
                    if celda.humedad_subsuelo > 0.0:
                        celda.humedad_subsuelo = max(
                            0.0, celda.humedad_subsuelo - self.tasa_drenaje_subsuelo
                        )

    def _registrar_recuerdo_si_procede(
        self,
        mem: MemoriaEspacial | None,
        cap_mental: CapacidadMental | None,
        tipo: str,
        pos_x: int,
        pos_y: int,
    ) -> None:
        """
        Registra un recuerdo vía nucleo/memoria.py:registrar_recuerdo
        (memoria, tipo, x, y, capacidad), con la capacidad derivada de
        CapacidadMental.memoria (capacidad_memoria()). Centralizado aquí
        en vez de repetir las mismas líneas en cada punto de llamada.
        """
        if mem is None or cap_mental is None:
            return
        capacidad = capacidad_memoria(cap_mental, self.config)
        registrar_recuerdo(mem, tipo, pos_x, pos_y, capacidad)

    def _resolver_construir(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        entidad_id: int,
        mem: MemoriaEspacial | None,
        cap_mental: CapacidadMental | None,
        inv: Inventario | None,
        pos_x: int,
        pos_y: int,
        tick_actual: int,
        bus_eventos: BusEventos,
    ) -> None:
        """
        REFUGIO/ALMACÉN CONSTRUIDO (ver componentes/construccion.py,
        nucleo/construccion.py, nucleo/asentamiento.py).
        sistema_movimiento.py ya llevó a la entidad hasta su objetivo de
        construcción actual (refugio propio o, una vez resuelto, el
        almacén del asentamiento del que sea miembro --
        objetivo_construccion_actual, creándolo si hacía falta); aquí,
        estando en la misma celda, se transfieren materiales aptos del
        Inventario y se actualiza progreso.

        Al cruzar 1.0 por primera vez: para refugio, se registra la
        posición como recuerdo "refugio" -- MISMA maquinaria que el
        refugio instintivo (nucleo/memoria.py, sin cambios ni caso
        especial), la memoria apunta al SITIO, no a la entidad
        Construccion. Para almacén no hay recuerdo individual que
        registrar (SistemaAsentamiento ya registra la memoria comunitaria
        "asentamiento" a diario para todos los miembros). Se emite un
        Evento en la transición (mismo criterio que CrisisMental, no en
        cada tick que sigue terminado): NOTABLE para refugio (logro
        individual), HISTÓRICO para almacén (hito de la comunidad entera).
        """
        if inv is None:
            return
        objetivo = objetivo_construccion_actual(
            gestor, mundo, entidad_id, self.radio_cluster_asentamiento
        )
        if objetivo is None:
            return
        _tipo_objetivo, cid, _ = objetivo
        if cid is None:
            return
        con_pos = gestor.obtener_componente(cid, Posicion)
        if con_pos is None or con_pos.x != pos_x or con_pos.y != pos_y:
            return
        construccion = gestor.obtener_componente(cid, Construccion)
        if construccion is None or construccion.progreso >= 1.0:
            return

        # Herramienta fabricada (2026-09-11): bono multiplicativo a la
        # tasa de aporte, mismo criterio que RECOLECTAR -- portarla
        # basta, sin exigir Agarre (ver config/herramientas.yaml).
        tasa_aporte_efectiva = self.tasa_aporte_construccion
        if tiene_herramienta(inv.objetos, self.recetas_herramientas):
            tasa_aporte_efectiva *= self.factor_bono_tasa_aporte_construccion_con_herramienta
        transferir_a_construccion(
            inv.contenidos,
            construccion.materiales,
            self.catalogo_materiales,
            tasa_aporte_efectiva,
        )
        masa_minima = masa_minima_para(construccion.tipo, self.config_construccion)
        construccion.progreso = progreso_construccion(
            construccion.materiales, self.catalogo_materiales, masa_minima
        )

        if construccion.progreso >= 1.0:
            construccion.completado_alguna_vez = True
            if construccion.tipo == "refugio":
                self._registrar_recuerdo_si_procede(mem, cap_mental, "refugio", pos_x, pos_y)
                evento_tipo, severidad = "RefugioConstruido", Severidad.NOTABLE
            else:
                evento_tipo, severidad = "AlmacenConstruido", Severidad.HISTORICO
            bus_eventos.emitir(
                Evento(
                    tipo=evento_tipo,
                    severidad=severidad,
                    tick=tick_actual,
                    entidad_id=entidad_id,
                    datos={"x": pos_x, "y": pos_y, "tipo": construccion.tipo},
                )
            )

    def _resolver_recolectar(
        self,
        inv: Inventario | None,
        dims: DimensionesFisicas | None,
        celda: Celda,
        agarre: Agarre | None = None,
        especie: str | None = None,
        consciente: bool = False,
        recolectar_arma: bool = False,
        recolectar_herramienta: bool = False,
        recolectar_fuego: bool = False,
        gestor: GestorEntidades | None = None,
        pos_x: int = 0,
        pos_y: int = 0,
        zona_idx: int = 0,
    ) -> None:
        """
        RECOLECTAR (ver componentes/intencion.py y nucleo/construccion.py).
        Convierte tipo_sustrato de la celda actual (piedra/arcilla/tierra
        -- propiedad estática de la celda, siempre presente, no
        depletable, ver nucleo/celda.py) en material del Inventario
        propio, topado por la capacidad de carga
        (nucleo/inventario.py:espacio_disponible_kg). Sin desplazamiento:
        se resuelve donde ya se está, el sustrato está bajo los pies de
        cualquiera.

        AGARRE / OBJETOS ARMA, DOS MECANISMOS CON CAUSA (ver
        componentes/agarre.py, config/fuego.yaml y config/armas.yaml):

        1. PIEDRA_SUELTA CON CAUSA (fuego): un individuo CONSCIENTE que
           todavía no tiene sus piedras_necesarias_fuego
           (sistema_decision.py ya elevó la utilidad de RECOLECTAR
           heredando el valor de ENCENDER_FUEGO -- nunca una razón propia)
           intenta agarrar piedra_suelta ESPECÍFICAMENTE, si la celda
           actual la tiene. Un individuo que jamás ha necesitado fuego
           (confort_termico siempre alto) nunca llega a esta rama con
           utilidad real, así que nunca desarrolla interés en buscar
           piedra tampoco. Se recoge SOLO cuando ese eslabón fue el
           MOTIVO real que ganó el RECOLECTAR de este tick, marcado en
           Intencion.recolectar_motivo_fuego (el parámetro
           recolectar_fuego de este método, 2026-09-12 -- mismo criterio
           que arma/herramienta más abajo, retrofitado aquí: antes de
           este fix, Vía 1 se disparaba siempre que hubiera hueco en
           Agarre, interceptando piedra_suelta aunque el motivo real de
           RECOLECTAR fuera otro).

        2. MATERIAL ARMA CON CAUSA (armas primitivas v2): mientras el
           individuo no tenga NINGÚN arma de nivel ≥2 fabricada (ni en
           Inventario ni en Agarre), sistema_decision.py eleva la utilidad
           de RECOLECTAR heredando el valor que tendría la categoria
           "arma" de FABRICAR (1.0 - seguridad) cuando la celda actual ofrece un recurso
           apto_arma. La resolución SOLO recoge ese material (como OBJETO
           DISCRETO a Inventario.objetos -- un palo entero, una piedra
           entera, topado por la capacidad de carga por peso) cuando ese
           eslabón fue el MOTIVO del RECOLECTAR de este tick, marcado por
           sistema_decision.py en Intencion.recolectar_motivo_arma (el
           parámetro recolectar_arma de este método) -- nunca un RECOLECTAR
           elegido por construcción. piedra_suelta como fuente del
           material "piedra": las recetas hablan de "piedra", no de
           "piedra_suelta", que es un recurso del suelo, no un material
           del catálogo.

        La "Vía 2" original de este método (agarre genérico sin causa, un
        palo o una roca "porque se lo encuentra") se retiró por completo
        en armas primitivas v2 -- violaba el principio 5 del proyecto
        (leyes neutras, nunca teleológicas): ninguna acción debería
        ocurrir sin un motivo real que la desencadene. El único bonus
        defensivo por objeto crudo pasa a depender de la decisión causal
        de empuñar (sistema_decision.py), no de agarrar cualquier cosa
        del suelo sin motivo.

        Ambos mecanismos deliberadamente GRATUITOS y simbólicos: no
        descuentan nada del recurso de la celda (ni piedra_suelta ni un
        palo de flora se agotan por recoger una unidad). El material de
        arma se recoge como objeto discreto de peso propio, no a granel.

        MADERA/FIBRA/HIERBA_SECA: sistema_flora.py ya deposita estos
        materiales en Celda.recursos con el MISMO mecanismo de
        producción diaria que ya usa la comida (madera bajo manzano,
        fibra bajo cactus, hierba_seca bajo hierba_silvestre) -- aquí
        solo hace falta recogerlos, sin ninguna acción de tala/siega que
        destruya la Planta. Genérico por catálogo, no una lista de
        nombres fija: cualquier clave de Celda.recursos que sea un
        material apto_construccion cuenta.

        Si la celda actual tiene una veta de mineral con masa restante
        (ver nucleo/cueva.py y componentes/celda.py:masa_mineral_restante),
        se extrae ESO en vez de tipo_sustrato -- a diferencia del
        sustrato, la veta es finita y se agota de verdad. Ningún cambio
        hace falta en sistema_decision.py: RECOLECTAR ya gatea
        genéricamente por "masa apta de construcción pendiente"
        (nucleo/construccion.py:material_suficiente_para), hierro/cobre
        ya son apto_construccion=true en el catálogo -- para la Utility
        AI, extraer mineral, madera o sustrato es indistinguible, solo
        cambia qué clave del Inventario crece.

        Orden de prioridad dentro de esta única celda -- mineral (más
        escaso y finito) > material de flora (finito por día, regenera) >
        sustrato (siempre disponible, nunca se agota): ninguna Utility AI
        lo decide, es simplemente qué hay de más a menos especial en el
        sitio donde ya se está.

        3. MATERIAL HERRAMIENTA CON CAUSA (2026-09-11, circulo 2 del arco
           "fabricacion y uso de herramientas"): mismo eslabon heredado
           que la Via 2 de arriba, mismos materiales (madera/piedra
           reutilizados, ver nucleo/herramientas.py) -- solo que gateado
           por "ya tiene herramienta fabricada" en vez de "ya tiene arma
           nivel>=2", y disparado por Intencion.recolectar_motivo_herramienta
           (el parametro recolectar_herramienta de este metodo). La Via 2
           y esta Via 3 comparten `_via_material_crudo` -- el mismo
           mecanismo fisico de "agarrar un palo o una piedra enteros",
           cada una con su propio gate de "ya posee".

        La herramienta ya fabricada (Inventario.objetos) aplica un bono
        multiplicativo a la tasa de recoleccion a granel de este mismo
        metodo (mineral/flora/sustrato, mas abajo) -- ver
        factor_bono_tasa_recolectar_con_herramienta.
        """
        if inv is None or dims is None:
            return

        # Vía 1: piedra_suelta CON CAUSA (fuego) -- ver docstring arriba.
        # Gateada por recolectar_fuego (2026-09-12, "prioridad consciente"
        # -- ver CLAUDE.md): hasta esta pieza, esta Vía se disparaba
        # SIEMPRE que hubiera hueco en Agarre y faltaran piedras, con
        # independencia de si fuego fue de verdad el motivo que ganó el
        # RECOLECTAR de este tick -- interceptaba casi cualquier
        # piedra_suelta disponible antes de que Vía 2/3 (arma/herramienta)
        # pudieran considerarla como material "piedra". Mismo patrón
        # exacto que ya exigían Vía 2/3 desde su diseño original, solo que
        # nunca se retrofitó aquí.
        if (
            recolectar_fuego
            and consciente
            and agarre is not None
            and especie is not None
        ):
            puntos_agarre_total = int(self.rangos_raciales.get(especie, {}).get("puntos_agarre", 0))
            piedras_agarradas = agarre.objetos.count("piedra_suelta")
            if (
                len(agarre.objetos) < puntos_agarre_total
                and piedras_agarradas < self.piedras_necesarias_fuego
                and celda.recursos.get("piedra_suelta", 0.0) > 0.0
            ):
                agarre.objetos.append("piedra_suelta")
                return

        # Vía 2: material apto_arma CON CAUSA (armas primitivas v2) -- ver
        # docstring arriba. Mismo eslabón heredado que ENCENDER_FUEGO:
        # sistema_decision.py eleva la utilidad de RECOLECTAR con el valor
        # de la categoria "arma" de FABRICAR (1.0 - seguridad) mientras no tenga arma de
        # nivel ≥2 y la celda ofrezca material apto_arma -- y solo cuando
        # ese eslabón fue el MOTIVO del RECOLECTAR elegido (marcado en
        # Intencion.recolectar_motivo_arma) se recoge material de arma.
        # Un RECOLECTAR motivado por construccion nunca carga un palo
        # "porque se lo encuentra": el crudo para fabricar vive en
        # Inventario, mismo patrón causal que CONSTRUIR.
        if recolectar_arma:
            objetos_totales = list(inv.objetos)
            if agarre is not None:
                objetos_totales.extend(agarre.objetos)
            ya_tiene_arma = tiene_arma_nivel2_o_mas(
                objetos_totales, self.catalogo_materiales, self.recetas_armas
            )
            if self._via_material_crudo(
                inv, dims, celda, gestor, pos_x, pos_y, zona_idx, ya_tiene_arma
            ):
                return

        # Vía 3: material apto_arma CON CAUSA (herramienta, 2026-09-11) --
        # ver docstring arriba. Mismos materiales que la Vía 2, mismo
        # helper compartido, gateada por "ya posee una herramienta
        # fabricada" en vez de "ya posee arma nivel>=2".
        if recolectar_herramienta:
            objetos_totales_h = list(inv.objetos)
            if agarre is not None:
                objetos_totales_h.extend(agarre.objetos)
            ya_tiene_herramienta = tiene_herramienta(objetos_totales_h, self.recetas_herramientas)
            if self._via_material_crudo(
                inv, dims, celda, gestor, pos_x, pos_y, zona_idx, ya_tiene_herramienta
            ):
                return

        # Herramienta fabricada (2026-09-11): bono multiplicativo a la
        # tasa de recoleccion a granel (mineral/flora/sustrato, abajo) --
        # portarla basta, no exige tenerla empuñada (ver
        # config/herramientas.yaml).
        tasa_recoleccion_efectiva = self.tasa_recoleccion
        objetos_para_bono = list(inv.objetos)
        if agarre is not None:
            objetos_para_bono.extend(agarre.objetos)
        if tiene_herramienta(objetos_para_bono, self.recetas_herramientas):
            tasa_recoleccion_efectiva *= self.factor_bono_tasa_recolectar_con_herramienta

        espacio = espacio_disponible_kg(
            inv.contenidos, dims.peso, self.fraccion_carga_maxima, inv.objetos, self.peso_objeto_kg
        )
        if espacio <= 0.0:
            return

        if celda.deposito_mineral and celda.masa_mineral_restante > 0.0:
            material = celda.deposito_mineral
            cantidad = min(tasa_recoleccion_efectiva, espacio, celda.masa_mineral_restante)
            inv.contenidos[material] = inv.contenidos.get(material, 0.0) + cantidad
            celda.masa_mineral_restante -= cantidad
            if celda.masa_mineral_restante <= 0.0:
                celda.masa_mineral_restante = 0.0
                celda.deposito_mineral = ""
            return

        for nombre, cantidad_disponible in celda.recursos.items():
            if cantidad_disponible <= 0.0:
                continue
            info = self.catalogo_materiales.get(nombre, {})
            if not info.get("apto_construccion", False):
                continue
            # Pista competidora (2026-09-03): un material producido por una
            # especie competidora solo se recolecta si hay una Planta real
            # de esa especie en esta celda+zona (la fuente de verdad de la
            # pista competidora es la entidad Planta, no Celda.recursos).
            if not self._hay_recurso_competidor_disponible(
                gestor, pos_x, pos_y, zona_idx, nombre
            ):
                continue
            cantidad = min(tasa_recoleccion_efectiva, espacio, cantidad_disponible)
            inv.contenidos[nombre] = inv.contenidos.get(nombre, 0.0) + cantidad
            celda.recursos[nombre] = cantidad_disponible - cantidad
            return

        material = celda.tipo_sustrato
        if not material:
            return
        info = self.catalogo_materiales.get(material, {})
        if not info.get("apto_construccion", False):
            return
        cantidad = min(tasa_recoleccion_efectiva, espacio)
        inv.contenidos[material] = inv.contenidos.get(material, 0.0) + cantidad

    def _via_material_crudo(
        self,
        inv: Inventario,
        dims: DimensionesFisicas,
        celda: Celda,
        gestor: GestorEntidades | None,
        pos_x: int,
        pos_y: int,
        zona_idx: int,
        ya_posee: bool,
    ) -> bool:
        """Vía compartida de recolección de material crudo apto_arma como
        objeto discreto -- Vía 2 (arma) y Vía 3 (herramienta, 2026-09-11),
        mismos materiales, cada una con su propio gate de "ya posee" (arma
        nivel>=2 fabricada, o herramienta fabricada). Extraída de la Vía 2
        original de armas primitivas v2 sin cambiar su comportamiento.

        Devuelve True si `_resolver_recolectar` debe terminar AQUÍ este
        tick (se recogió algo, o se determinó que la pista competidora no
        ofrece nada real que recoger); False si debe seguir probando la
        recolección a granel de más abajo (celda sin material crudo, o
        sigue sin espacio de carga tras descartar bulto -- en ese caso cae
        a granel en vez de perder el tick entero).

        PRIORIDAD CONSCIENTE (2026-09-11, hallazgo real del diagnóstico
        multi-semilla de este mismo círculo -- ver CLAUDE.md): si no hay
        espacio de carga para el objeto, un ser consciente con esta
        intención ya GANADORA este tick (Vía 2/3 solo se llama con
        recolectar_arma/recolectar_herramienta ya causalmente motivados
        por sistema_decision.py) se desprende de bulto de `contenidos`
        (nucleo/inventario.py:descartar_contenidos_para_liberar) -- lo
        mínimo necesario para que quepa, nunca más -- en vez de renunciar
        a su intención sin más. Nunca toca `inv.objetos` (armas ya
        fabricadas o material ya recolectado para esta misma intención)."""
        if ya_posee or not celda_ofrece_material_arma(celda, self.catalogo_materiales):
            return False
        material = recolectar_material_arma_de_celda(celda, self.catalogo_materiales)
        if material is None:
            return False
        # Pista competidora (2026-09-03): el crudo apto_arma de una
        # especie competidora solo existe si hay una Planta real de esa
        # especie en la celda -- mismo criterio que el bucle de
        # materiales a granel.
        if gestor is not None and not self._hay_recurso_competidor_disponible(
            gestor, pos_x, pos_y, zona_idx, material
        ):
            return True
        peso_objeto = float(self.peso_objeto_kg.get(material, 0.0))
        espacio = espacio_disponible_kg(
            inv.contenidos, dims.peso, self.fraccion_carga_maxima, inv.objetos, self.peso_objeto_kg,
        )
        if espacio < peso_objeto:
            descartado = descartar_contenidos_para_liberar(inv.contenidos, peso_objeto - espacio)
            self._stats_material_descartado_por_prioridad_kg += descartado
            espacio = espacio_disponible_kg(
                inv.contenidos, dims.peso, self.fraccion_carga_maxima, inv.objetos, self.peso_objeto_kg,
            )
        if espacio >= peso_objeto:
            inv.objetos.append(material)
            return True
        return False

    def _hay_recurso_competidor_disponible(
        self,
        gestor: GestorEntidades | None,
        pos_x: int,
        pos_y: int,
        zona_idx: int,
        nombre_rec: str,
    ) -> bool:
        """True si el recurso `nombre_rec` puede consumirse en (pos_x, pos_y,
        zona_idx) seg\u00fan la pista en la que viva su especie productora.

        - Recurso que no produce ninguna especie competidora (o sin gestor
          que consultar): True -- comportamiento hist\u00f3rico sin cambios.
        - Recurso de una especie con compite_espacio_fisico=true: True solo
          si hay al menos una entidad Planta de esa especie en esa
          celda+zona. Si hay varias, basta la primera por orden de
          iteraci\u00f3n (sin l\u00f3gica de selecci\u00f3n "\u00f3ptima", coherente con el
          resto del motor) -- el consumo va contra el pool compartido
          Celda.recursos, as\u00ed que el id concreto no cambia el mecanismo.
        """
        if gestor is None:
            return True
        especie_origen = self.especie_por_recurso.get(nombre_rec)
        if especie_origen is None:
            return True
        cfg_esp = self.especies_flora.get(especie_origen, {})
        if not cfg_esp.get("compite_espacio_fisico", False):
            return True
        for pid in plantas_competidoras_en(gestor, pos_x, pos_y, zona_idx, self.especies_flora):
            planta = gestor.obtener_componente(pid, Planta)
            if planta is not None and planta.especie == especie_origen:
                return True
        return False

    def _resolver_encender_fuego(
        self,
        gestor: GestorEntidades,
        celda: Celda,
        pos_x: int,
        pos_y: int,
        zona_idx: int,
        bus_eventos: BusEventos,
        tick_actual: int,
        agarre: Agarre | None = None,
    ) -> None:
        """
        ENCENDER_FUEGO (ver componentes/agarre.py, componentes/fogata.py,
        nucleo/fuego.py). sistema_decision.py ya comprobó las
        precondiciones (piedras en Agarre, combustible en la celda, sin
        Fogata ya presente) antes de elegir esta Accion -- aquí solo se
        resuelve la tirada de éxito y, si prende, se consume la yesca y
        se crea la Fogata. Sin desplazamiento, igual que
        RECOLECTAR/ALIVIARSE -- se resuelve donde ya se está.

        Solo se consume yesca de Celda.recursos -- mismo catálogo
        apto_construccion + combustibilidad que ya usa RECOLECTAR para
        material de flora. En cuanto la fogata se enciende con éxito, las
        piedras de percusión dejan de ser necesarias en la mano y se
        DESCARTAN -- no son un arma (nucleo/armas.py las excluye a
        propósito) ni material de construcción (fuera del catálogo
        apto_construccion), así que no tienen ningún uso futuro real.

        CORREGIDO (2026-09-11, bug real encontrado en auditoría de
        funcionalidades): la versión anterior las movía a
        Inventario.objetos en vez de descartarlas, con un tope de
        transferencia (`< piedras_necesarias_fuego` YA presentes en el
        inventario) pensado para no acumular sin límite. Ese tope tenía
        un efecto secundario no anticipado -- verificado con un arnés
        dedicado, no solo razonado: tras el PRIMER fuego de cualquier
        individuo, el inventario ya alcanza ese tope, así que las
        piedras de CUALQUIER fuego posterior dejan de poder transferirse
        y se quedan atascadas en Agarre para siempre, ocupando de forma
        permanente los puntos de agarre (2 en gnomo -- el 100% de su
        capacidad) sin que el individuo pueda volver a empuñar un arma
        en lo que le queda de vida. Descartarlas sin más (nunca pasan
        por Inventario) evita el problema de raíz, sin ningún tope que
        gestionar.
        """
        if self.rng.random() >= self.probabilidad_encender_fuego:
            return  # golpear piedra contra piedra no siempre prende

        for nombre, cantidad_disponible in celda.recursos.items():
            if cantidad_disponible <= 0.0:
                continue
            info = self.catalogo_materiales.get(nombre, {})
            if not (info.get("apto_construccion", False) and info.get("combustibilidad", 0.0) > 0.0):
                continue
            consumido = min(self.masa_yesca_consumida, cantidad_disponible)
            celda.recursos[nombre] = cantidad_disponible - consumido
            if agarre is not None:
                agarre.objetos = [o for o in agarre.objetos if o != "piedra_suelta"]
            fid = crear_fogata(gestor, pos_x, pos_y, self.combustible_inicial_fogata, zona_idx=zona_idx)
            bus_eventos.emitir(
                Evento(
                    tipo="FuegoEncendido",
                    severidad=Severidad.NOTABLE,
                    tick=tick_actual,
                    entidad_id=fid,
                    datos={"x": pos_x, "y": pos_y, "zona_idx": zona_idx},
                )
            )
            return

    def _resolver_cocinar(
        self,
        gestor: GestorEntidades,
        entidad_id: int,
        pos_x: int,
        pos_y: int,
        zona_idx: int,
    ) -> None:
        """Cocinar (2026-09-08, ver docs/superpowers/specs/
        2026-09-08-como-cocinar-design.md): transforma hasta
        tasa_cocinar_kg_tick del primer recurso crudo no vacío de
        Inventario.provisiones en su versión "_elaborada" -- defensivo
        (la compuerta ya lo filtra en sistema_decision.py, pero no
        vuelve a comprobar Fogata aquí: si deja de haberla a mitad de
        cocinar, este tick concreto ya se resuelve igual, mismo criterio
        que el resto del motor no re-verifica condiciones de entrada
        dentro de la resolución).

        Cocina común (2026-09-08, ver docs/superpowers/specs/
        2026-09-08-cocinas-comunes-design.md): si la celda tiene una
        cocina, cocinar es más rápido (factor_bono_tasa_cocina_comun) Y
        el resultado se deposita en la alacena comunal
        (Construccion.provisiones) en vez del inventario personal de
        quien cocina."""
        inv = gestor.obtener_componente(entidad_id, Inventario)
        if inv is None or not inv.provisiones:
            return
        recurso_crudo = next(
            (r for r in inv.provisiones if not es_elaborado(r) and inv.provisiones[r] > 0.0),
            None,
        )
        if recurso_crudo is None:
            return
        cid_cocina = construccion_de_tipo_en(
            gestor, pos_x, pos_y, zona_idx, "cocina", indice=self._indice_actual
        )
        if cid_cocina is not None:
            cocina = gestor.obtener_componente(cid_cocina, Construccion)
            tasa = self.tasa_cocinar_kg_tick * self.factor_bono_tasa_cocina_comun
            transformado = elaborar_recurso(
                inv.provisiones, recurso_crudo, tasa, destino=cocina.provisiones,
            )
        else:
            transformado = elaborar_recurso(inv.provisiones, recurso_crudo, self.tasa_cocinar_kg_tick)
        if transformado > 0.0:
            self._stats_cocinar_resuelto += 1

    def _resolver_fabricar(
        self,
        gestor: GestorEntidades,
        entidad_id: int,
        inv: Inventario | None,
        pos_x: int,
        pos_y: int,
        zona_idx: int,
        bus_eventos: BusEventos,
        tick_actual: int,
        categoria: str,
        agarre: Agarre | None = None,
    ) -> None:
        """
        FABRICAR (2026-09-11, renombrada desde FABRICAR_ARMA -- ver
        componentes/intencion.py y config/armas.yaml). Ramifica por
        `categoria` (Intencion.fabricar_categoria, ya decidida por el
        resolutor interno de sistema_decision.py) -- "arma" y
        "herramienta" (2026-09-11, circulo 2 del arco "fabricacion y uso
        de herramientas") son las dos implementadas hoy; cualquier otra
        cae al no-op de abajo (no deberia poder llegar aqui salvo que se
        anada una categoria nueva a sistema_decision.py sin su propia
        resolucion todavia).

        Ambas categorias comparten el mismo patron determinista (tallar
        no es un suceso de azar, a diferencia de encender fuego): busca
        la mejor receta completable AHORA con lo que ya se porta
        (prioriza el nivel más alto alcanzable con el material disponible
        en este instante -- no espera a conseguir un material mejor,
        reacciona al presente, coherente con que el resto de la Utility
        AI no planifica a futuro), consume los materiales crudos de esa
        receta, añade el nombre del objeto resultante a Inventario.objetos
        y emite un Evento (NOTABLE). Sin desplazamiento, igual que
        RECOLECTAR/ALIVIARSE -- se resuelve donde ya se está.

        Los materiales se buscan en Inventario.objetos Y en Agarre.objetos
        (lo que la criatura tiene en la mano es tan suyo como lo que lleva
        en el inventario): el reflejo empunyar/guardar de sistema_decision.py
        ya pudo haber movido el crudo a Agarre este mismo tick por inseguridad,
        y sin mirar ambas fuentes una criatura asustada que empuña el único
        palo que tiene nunca llegaria a fabricar -- se quedaria en un ciclo
        de recolectar/huir sin cerrar el circulo (hallazgo real, ver
        tests/test_armas_primitivas_v2.py). El objeto resultante siempre
        nace en Inventario.objetos.
        """
        if inv is None:
            return
        objetos_portados = list(inv.objetos)
        if agarre is not None:
            objetos_portados.extend(agarre.objetos)
        if categoria == "arma":
            recetas = self.recetas_armas
        elif categoria == "herramienta":
            recetas = self.recetas_herramientas
        else:
            return
        receta = mejor_receta_completable(objetos_portados, recetas)
        if receta is None:
            return
        for material in receta.get("materiales", []):
            if material in inv.objetos:
                inv.objetos.remove(material)
            elif agarre is not None and material in agarre.objetos:
                agarre.objetos.remove(material)
        nombre_objeto = str(receta.get("nombre", ""))
        inv.objetos.append(nombre_objeto)
        if categoria == "arma":
            nivel = int(receta.get("nivel", 0))
            bus_eventos.emitir(
                Evento(
                    tipo="ArmaFabricada",
                    severidad=Severidad.NOTABLE,
                    tick=tick_actual,
                    entidad_id=entidad_id,
                    datos={
                        "x": pos_x, "y": pos_y, "zona_idx": zona_idx,
                        "arma": nombre_objeto, "nivel": nivel,
                    },
                )
            )
        else:
            self._stats_herramientas_fabricadas += 1
            bus_eventos.emitir(
                Evento(
                    tipo="HerramientaFabricada",
                    severidad=Severidad.NOTABLE,
                    tick=tick_actual,
                    entidad_id=entidad_id,
                    datos={
                        "x": pos_x, "y": pos_y, "zona_idx": zona_idx,
                        "herramienta": nombre_objeto,
                    },
                )
            )

    def _consumir_fogatas(self, gestor: GestorEntidades) -> None:
        """Cada Fogata existente quema su propio combustible cada tick,
        independiente de quién la encendió o de si alguien sigue cerca --
        una hoguera no se apaga porque el gnomo se vaya. Sin acción de
        avivar/alimentar todavía (ver componentes/fogata.py): se elimina
        sola al agotarse, mismo patrón que la descomposición de Necromasa."""
        for fid in list(gestor.entidades_con(Fogata)):
            fogata = gestor.obtener_componente(fid, Fogata)
            fogata.combustible_restante -= self.tasa_consumo_fogata
            if fogata.combustible_restante <= 0.0:
                gestor.eliminar_entidad(fid)

    def _valor_nutricional_efectivo(self, nombre: str) -> float:
        """valor_nutricional del recurso, multiplicado por
        factor_mejora_elaboracion si `nombre` es la versión "_elaborada"
        (2026-09-08, ver docs/superpowers/specs/
        2026-09-08-como-cocinar-design.md). Los recursos de Celda nunca
        llevan el sufijo -- solo Inventario.provisiones puede tener algo
        cocinado -- así que esto es un no-op para el forraje de celda."""
        valor = self.nutricion_flora.get(recurso_base(nombre), 0.2)
        if es_elaborado(nombre):
            valor *= self.factor_mejora_elaboracion
        return valor

    def _valor_hidratacion_efectiva(self, nombre: str) -> float:
        """Análogo a _valor_nutricional_efectivo para valor_hidratacion."""
        valor = self.hidratacion_flora.get(recurso_base(nombre), 0.05)
        if es_elaborado(nombre):
            valor *= self.factor_mejora_elaboracion
        return valor

    def _resolver_comer(
        self,
        gestor: GestorEntidades,
        entidad_id: int,
        identidad: Identidad,
        nec: Necesidades,
        mem: MemoriaEspacial | None,
        cap_mental: CapacidadMental | None,
        celda: Celda,
        pos_x: int,
        pos_y: int,
        zona_idx: int = 0,
        bus_eventos: BusEventos | None = None,
        tick_actual: int = 0,
    ) -> None:
        """
        Resuelve la ingesta de biomasa: evalúa primero necromasa presente (carroñeo)
        y posteriormente forraje vegetal compatible con la dieta de la especie.

        bus_eventos/tick_actual (2026-09-08, toxicidad de crudo -- ver
        docs/superpowers/specs/2026-09-08-como-cocinar-design.md):
        necesarios para poder matar por intoxicación (procesar_deceso)
        sin salir de este método. Opcionales con default para no romper
        tests dirigidos existentes que llaman a este método directamente
        sin pasar bus_eventos -- sin él, la muerte por intoxicación
        simplemente no se resuelve (defensivo, nunca debería ocurrir en
        juego real: ejecutar() siempre los pasa).
        """
        # 1. Evaluación de Carroñeo (Necromasa en la celda). zona_idx:
        # "en la celda" exige tambien estar en la misma zona -- ver
        # componentes/posicion.py.
        #
        # 2026-09-08 (nucleo/indice_espacial.py): usa self._indice_actual
        # si esta disponible (indice.en_celda ya filtra por celda/zona)
        # en vez del escaneo O(N) sobre toda la necromasa del mundo --
        # sin el, comportamiento identico a antes.
        candidatos_necromasa = []
        fuente_necromasa = (
            self._indice_actual.en_celda(pos_x, pos_y, zona_idx)
            if self._indice_actual is not None
            else gestor.entidades_con(Necromasa, Posicion)
        )
        for nid in fuente_necromasa:
            pos_n = gestor.obtener_componente(nid, Posicion)
            if pos_n is None or gestor.obtener_componente(nid, Necromasa) is None:
                continue
            if pos_n.x == pos_x and pos_n.y == pos_y and pos_n.zona_idx == zona_idx:
                candidatos_necromasa.append(nid)

        if candidatos_necromasa:
            nec_id = min(candidatos_necromasa)
            nec_comp = gestor.obtener_componente(nec_id, Necromasa)

            # El carroñeo solo consume 'tejido_blando' -- un carroñero no
            # roe el esqueleto entero. El hueso queda intacto y la
            # entidad NUNCA
            # se borra aquí mientras quede hueso (borrarla es
            # responsabilidad exclusiva de sistema_descomposicion.py, que
            # sí espera a que TODOS los materiales se mineralicen).
            masa_blanda = nec_comp.masas.get("tejido_blando", 0.0) if nec_comp is not None else 0.0
            if nec_comp is not None and masa_blanda > 0.05:
                delta_m = min(masa_blanda, self.tasa_consumo_comer)
                nec_comp.masas["tejido_blando"] = max(0.0, masa_blanda - delta_m)
                nec_comp.agua_tisular = max(0.0, nec_comp.agua_tisular - (delta_m * 0.65))

                # Transferencia nutricional
                nec.saciedad = min(1.0, nec.saciedad + (delta_m * self.eficiencia_biomasa_saciedad))
                nec.hidratacion = min(1.0, nec.hidratacion + (delta_m * self.eficiencia_biomasa_hidratacion))

                self._registrar_recuerdo_si_procede(mem, cap_mental, "comida", pos_x, pos_y)

                if all(m <= 0.05 for m in nec_comp.masas.values()):
                    gestor.eliminar_entidad(nec_id)
                return

        # 2. Evaluación de Forrajeo Vegetal
        cfg_esp = self.config.get("rangos_raciales", {}).get(identidad.especie.value, {})
        dieta = cfg_esp.get("dieta", [])
        # Tasa de ingesta propia de esta especie (config/fisiologia.yaml:
        # consumo.tasa_consumo_al_comer_por_especie) -- fallback al valor
        # universal si la especie no tiene entrada (p.ej. lobo, que no
        # forrajea vegetal en la práctica). Usada en TODA esta sección de
        # forrajeo vegetal (celda, provisiones, alacena) -- el carroñeo de
        # arriba sigue usando self.tasa_consumo_comer sin cambios.
        tasa_comer_especie = self.tasa_consumo_comer_por_especie.get(
            identidad.especie.value, self.tasa_consumo_comer
        )

        recursos_disponibles = []
        for r, cant in celda.recursos.items():
            if cant <= 0.0 or (dieta and r not in dieta):
                continue
            # Pista competidora (2026-09-03): el recurso de una especie que
            # compite por espacio solo es comestible si hay una Planta real
            # de esa especie en esta celda+zona -- la fuente de verdad de
            # esa pista es la entidad Planta, no Celda.recursos.
            if not self._hay_recurso_competidor_disponible(gestor, pos_x, pos_y, zona_idx, r):
                continue
            recursos_disponibles.append(r)

        if recursos_disponibles:
            nombre_rec = recursos_disponibles[0]
            cant_actual = celda.recursos[nombre_rec]
            consumo = min(cant_actual, tasa_comer_especie)
            celda.recursos[nombre_rec] = max(0.0, cant_actual - consumo)

            consciente = (
                cap_mental is not None
                and cap_mental.consciencia >= self.umbral_consciencia_agencia
            )

            val_nut = self._valor_nutricional_efectivo(nombre_rec)
            val_hid = self._valor_hidratacion_efectiva(nombre_rec)

            nec.saciedad = min(1.0, nec.saciedad + (consumo * val_nut))
            nec.hidratacion = min(1.0, nec.hidratacion + (consumo * val_hid))

            # Toxicidad de crudo (2026-09-08, ver docs/superpowers/specs/
            # 2026-09-08-como-cocinar-design.md) -- GATEADA A CONSCIENTE:
            # sin este gate, conejo/caballo (que tambien comen raices/
            # bayas_espinosas) quedarian expuestos a un vector de muerte
            # sin ninguna forma de cocinar jamas. Los recursos de celda
            # nunca llevan el sufijo "_elaborada" (solo Inventario.
            # provisiones puede tener algo cocinado), asi que aqui
            # siempre se evalua el recurso crudo tal cual.
            if (
                consciente
                and bus_eventos is not None
                and self.toxico_crudo_flora.get(nombre_rec, False)
            ):
                dims_tox = gestor.obtener_componente(entidad_id, DimensionesFisicas)
                resistencia = dims_tox.resistencia_enfermedad if dims_tox is not None else 0.0
                prob = self.probabilidad_muerte_intoxicacion_base * (1.0 - resistencia)
                if dims_tox is not None and self.rng.random() < prob:
                    procesar_deceso(
                        gestor=gestor,
                        bus_eventos=bus_eventos,
                        tick_actual=tick_actual,
                        entidad_id=entidad_id,
                        pos_x=pos_x,
                        pos_y=pos_y,
                        dims=dims_tox,
                        ident=identidad,
                        causa="intoxicacion",
                        zona_idx=zona_idx,
                    )
                    self._stats_muertes_intoxicacion += 1
                    return

            self._registrar_recuerdo_si_procede(mem, cap_mental, "comida", pos_x, pos_y)

            # Zoocoria (2026-09-02, pieza 5/5 de "tipos de propagación"
            # -- ver docs/superpowers/specs/
            # 2026-09-01-propagacion-flora-design.md): comer fruto de una
            # especie zoocora puede dejar una semilla "recogida" -- se
            # planta más tarde, en otro sitio, al ALIVIARSE (ver
            # _resolver_aliviarse). Para especies no-competidoras
            # celda.tipo_recurso ya ES la especie (comportamiento sin
            # cambios); para la pista competidora celda.tipo_recurso ya no
            # se escribe, así que la especie se recupera del mapa
            # recurso->especie sólo cuando esa especie compite por espacio.
            especie_origen = self.especie_por_recurso.get(nombre_rec)
            especie_para_semilla = celda.tipo_recurso
            if (
                especie_origen is not None
                and self.especies_flora.get(especie_origen, {}).get("compite_espacio_fisico", False)
            ):
                especie_para_semilla = especie_origen
            especie_cfg_comida = self.especies_flora.get(especie_para_semilla, {})
            if especie_cfg_comida.get("tipo_propagacion") == "zoocoria":
                semillas = gestor.obtener_componente(entidad_id, Semillas)
                if (
                    semillas is not None
                    and semillas.especie_transportada == ""
                    and self.rng.random() < self.probabilidad_recogida_semilla_zoocoria
                ):
                    semillas.especie_transportada = especie_para_semilla

            # Provisiones (2026-09-07, ver docs/superpowers/specs/
            # 2026-09-07-provisiones-alimento-design.md): si queda
            # comida en la celda tras el consumo Y la entidad ya esta
            # bien alimentada, un consciente guarda el excedente para
            # comer mas tarde -- instinto de conservacion, no una
            # decision calculada (ley binaria, sin variar por
            # inteligencia/voluntad individual). Bolsillo TOTALMENTE
            # INDEPENDIENTE de Inventario.contenidos -- nunca compite
            # con materiales de construccion. (`consciente` ya calculado
            # arriba, reutilizado tambien por el chequeo de toxicidad.)
            sobra_en_celda = celda.recursos.get(nombre_rec, 0.0)
            if (
                consciente
                and nec.saciedad >= self.saciedad_minima_para_guardar_provisiones
                and sobra_en_celda > 0.0
            ):
                inv = gestor.obtener_componente(entidad_id, Inventario)
                dims = gestor.obtener_componente(entidad_id, DimensionesFisicas)
                if inv is not None and dims is not None:
                    espacio = espacio_disponible_provisiones_kg(
                        inv.provisiones, dims.peso, self.fraccion_provisiones_maxima
                    )
                    a_guardar = min(sobra_en_celda, tasa_comer_especie, espacio)
                    if a_guardar > 0.0:
                        inv.provisiones[nombre_rec] = (
                            inv.provisiones.get(nombre_rec, 0.0) + a_guardar
                        )
                        celda.recursos[nombre_rec] = max(0.0, sobra_en_celda - a_guardar)
                        self._stats_provisiones_guardadas += 1
        else:
            # Provisiones -- comer de la propia despensa cuando la celda
            # actual no tiene nada de la dieta propia, ANTES de dar el
            # sitio por agotado. Sin registrar memoria de "comida" aqui
            # (no se comio en ningun sitio concreto) ni disparar
            # zoocoria (eso es solo para fruta comida donde crece).
            inv = gestor.obtener_componente(entidad_id, Inventario)
            if inv is not None and inv.provisiones:
                consciente = (
                    cap_mental is not None
                    and cap_mental.consciencia >= self.umbral_consciencia_agencia
                )
                # Preferencia por lo elaborado (2026-09-08): para CADA r
                # de la dieta, en su orden ya establecido, se prueba
                # primero f"{r}_elaborada" y luego r crudo, antes de
                # pasar al siguiente r -- no es una busqueda global de
                # "cualquier elaborada en todo el inventario".
                recurso_guardado = next(
                    (
                        candidato
                        for r in dieta
                        for candidato in (f"{r}_elaborada", r)
                        if inv.provisiones.get(candidato, 0.0) > 0.0
                    ),
                    None,
                )
                if recurso_guardado is not None:
                    disponible = inv.provisiones[recurso_guardado]
                    consumo = min(disponible, tasa_comer_especie)
                    val_nut = self._valor_nutricional_efectivo(recurso_guardado)
                    val_hid = self._valor_hidratacion_efectiva(recurso_guardado)
                    nec.saciedad = min(1.0, nec.saciedad + (consumo * val_nut))
                    nec.hidratacion = min(1.0, nec.hidratacion + (consumo * val_hid))
                    restante = disponible - consumo
                    if restante <= self.umbral_purga_provisiones:
                        del inv.provisiones[recurso_guardado]
                    else:
                        inv.provisiones[recurso_guardado] = restante
                    self._stats_provisiones_consumidas += 1

                    # Toxicidad de crudo (2026-09-08) -- mismo gate de
                    # consciencia que en el forraje de celda (aunque en
                    # la practica esta rama ya es consciente-only, dado
                    # que solo un consciente puede tener provisiones);
                    # la version "_elaborada" nunca tira esta probabilidad.
                    if (
                        consciente
                        and bus_eventos is not None
                        and not es_elaborado(recurso_guardado)
                        and self.toxico_crudo_flora.get(recurso_guardado, False)
                    ):
                        dims_tox = gestor.obtener_componente(entidad_id, DimensionesFisicas)
                        resistencia = (
                            dims_tox.resistencia_enfermedad if dims_tox is not None else 0.0
                        )
                        prob = self.probabilidad_muerte_intoxicacion_base * (1.0 - resistencia)
                        if dims_tox is not None and self.rng.random() < prob:
                            procesar_deceso(
                                gestor=gestor,
                                bus_eventos=bus_eventos,
                                tick_actual=tick_actual,
                                entidad_id=entidad_id,
                                pos_x=pos_x,
                                pos_y=pos_y,
                                dims=dims_tox,
                                ident=identidad,
                                causa="intoxicacion",
                                zona_idx=zona_idx,
                            )
                            self._stats_muertes_intoxicacion += 1
                    return

            # Alacena de cocina común (2026-09-08, ver docs/superpowers/
            # specs/2026-09-08-cocinas-comunes-design.md): tercera
            # fuente, tras celda y despensa personal -- solo si esta
            # entidad está FÍSICAMENTE en la celda de una cocina común
            # (sistema_movimiento.py:_calcular_forrajeo ya decidió
            # caminar hasta aquí si hacía falta). Sin chequeo de
            # toxicidad: la alacena solo puede contener claves
            # "_elaborada" (únicas que elaborar_recurso escribe) y
            # cocinar ya elimina la toxicidad por completo. Sin filtro
            # de dieta propia -- simplificación aceptada mientras solo
            # exista una especie consciente (gnomo).
            cid_cocina = construccion_de_tipo_en(
                gestor, pos_x, pos_y, zona_idx, "cocina", indice=self._indice_actual
            )
            if cid_cocina is not None:
                cocina = gestor.obtener_componente(cid_cocina, Construccion)
                if cocina is not None and cocina.provisiones:
                    recurso_alacena = next(
                        (r for r in cocina.provisiones if cocina.provisiones[r] > 0.0),
                        None,
                    )
                    if recurso_alacena is not None:
                        disponible = cocina.provisiones[recurso_alacena]
                        consumo = min(disponible, tasa_comer_especie)
                        val_nut = self._valor_nutricional_efectivo(recurso_alacena)
                        val_hid = self._valor_hidratacion_efectiva(recurso_alacena)
                        nec.saciedad = min(1.0, nec.saciedad + (consumo * val_nut))
                        nec.hidratacion = min(1.0, nec.hidratacion + (consumo * val_hid))
                        restante = disponible - consumo
                        if restante <= self.umbral_purga_provisiones:
                            del cocina.provisiones[recurso_alacena]
                        else:
                            cocina.provisiones[recurso_alacena] = restante
                        self._stats_alacena_consumida += 1
                        return
            # Sin esto, un individuo que llega aquí guiado por un
            # recuerdo de "comida" (nucleo/memoria.py:objetivo_recordado,
            # consultado en sistema_movimiento.py:_calcular_forrajeo SOLO
            # cuando la percepción directa no encuentra nada en el radio
            # -- es decir, exactamente cuando el entorno inmediato ya
            # está agotado) y encuentra la celda igual de vacía, no tiene
            # ninguna consecuencia: el recuerdo stale se queda en la cola
            # FIFO tal cual, objetivo_recordado() sigue devolviendo la
            # MISMA coordenada por ser la más cercana en la lista, y el
            # individuo puede quedar atrapado volviendo sobre el mismo
            # sitio muerto en vez de que la memoria se corrija y el
            # próximo intento explore otra cosa. Purga PROBABILÍSTICA, no
            # inmediata al primer fallo: prob_purgar_recuerdo_agotado
            # (PROVISIONAL, ver config/constantes.yaml sección memoria)
            # da varios reintentos esperados antes de rendirse -- un
            # recuerdo descartado de golpe podría, con margen, haber
            # vuelto a dar fruto tras la regeneración diaria de
            # sistema_flora.py.
            if mem is not None and self.rng.random() < self.prob_purgar_recuerdo_agotado:
                purgar_recuerdo_invalido(mem, "comida", pos_x, pos_y)

    def _resolver_beber(
        self,
        nec: Necesidades,
        mem: MemoriaEspacial | None,
        cap_mental: CapacidadMental | None,
        celda: Celda,
        pos_x: int,
        pos_y: int,
    ) -> None:
        """Satisface la hidratación sobre aguas permanentes o charcos efímeros."""
        if not hay_agua_potable(celda):
            # Mismo razonamiento que en _resolver_comer: si llegó aquí
            # guiado por un recuerdo de "agua" que ya no es válido (charco
            # efímero evaporado, por ejemplo), purgarlo evita que
            # objetivo_recordado() lo siga devolviendo como el más cercano.
            # Probabilística, no inmediata: da margen a que el agua
            # vuelva (lluvia, charco que se rellena) antes de descartar
            # el recuerdo.
            if mem is not None and self.rng.random() < self.prob_purgar_recuerdo_agotado:
                purgar_recuerdo_invalido(mem, "agua", pos_x, pos_y)
            return

        nec.hidratacion = min(1.0, nec.hidratacion + self.tasa_consumo_beber)

        # Si bebe de un charco efímero en tierra firme, drena el charco
        if not celda.tiene_agua and celda.profundidad_charco > 0.0:
            celda.profundidad_charco = max(0.0, celda.profundidad_charco - self.tasa_agotamiento_charco)

        self._registrar_recuerdo_si_procede(mem, cap_mental, "agua", pos_x, pos_y)

    def _resolver_aliviarse(
        self,
        gestor: GestorEntidades,
        entidad_id: int,
        nec: Necesidades,
        celda: Celda,
        pos_x: int,
        pos_y: int,
        zona_idx: int,
    ) -> None:
        """Evacua residuos orgánicos corporales incrementando la fertilidad del suelo.

        Zoocoria (2026-09-02, pieza 5/5 de "tipos de propagación" -- ver
        docs/superpowers/specs/2026-09-01-propagacion-flora-design.md):
        si el individuo lleva una semilla recogida (Semillas.especie_
        transportada, ver _resolver_comer), este es también el evento
        que puede depositarla -- desacoplado del ciclo diario de
        SistemaFlora, lo dispara el comportamiento del animal (COMER,
        luego ALIVIARSE en otro momento y lugar), no la planta. La
        semilla se limpia SIEMPRE (éxito o fallo de idoneidad) -- se
        deposita igual, prenda o no.
        """
        tasa_alivio = float(self.config.get("necesidades", {}).get("defecto", {}).get("tasa_alivio_al_aliviarse", 0.5))
        nec.aliviado = min(1.0, nec.aliviado + tasa_alivio)
        celda.fertilidad = min(self.techo_fertilidad, celda.fertilidad + self.incremento_fertilidad)

        semillas = gestor.obtener_componente(entidad_id, Semillas)
        if semillas is not None and semillas.especie_transportada != "":
            especie = semillas.especie_transportada
            if self.rng.random() < self.probabilidad_plantar_semilla_en_aliviarse:
                especie_cfg = self.especies_flora.get(especie, {})
                capacidad_retencion = float(
                    self.catalogo_materiales.get(celda.tipo_sustrato, {}).get("capacidad_retencion", 0.0)
                )
                intentar_colonizar_celda(
                    gestor, celda, capacidad_retencion, especie, especie_cfg,
                    self.umbral_minimo_idoneidad_colonizacion, pos_x, pos_y, zona_idx,
                    config=self.config,
                )
            semillas.especie_transportada = ""
