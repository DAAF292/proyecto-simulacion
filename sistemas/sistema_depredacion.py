"""
sistemas/sistema_depredacion.py

Sistema de resolución de depredación y combate interespecífico (Fase 2).
Resuelve el contacto físico en la misma celda entre cazador y presa,
computando probabilidad de captura, daño a la vitalidad, transferencia
de biomasa proporcional y depósito de necromasa residual en el grid.
"""

from __future__ import annotations

import random
from typing import Any

from componentes.agarre import Agarre
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Identidad
from componentes.intencion import Accion, Intencion
from componentes.necesidades import Necesidades
from componentes.pool_fisico import PoolFisico
from componentes.posicion import Posicion
from componentes.temperamento import Temperamento
from nucleo.disposicion import contar_conspecificos_cercanos
from nucleo.disposicion import magnitud_disposicion_por_peso as magnitud_disposicion_por_tamano
# La función real en nucleo/disposicion.py se llama
# magnitud_disposicion_por_peso -- se importa con alias local
# (magnitud_disposicion_por_tamano) para no reescribir las llamadas de
# abajo, sin cambiar ningún comportamiento.
from nucleo.entidad import GestorEntidades, componer_necromasa, crear_necromasa
from nucleo.armas import bono_defensivo_arma, mayor_nivel_arma
from nucleo.eventos import BusEventos, Evento, Severidad


class SistemaDepredacion:
    """
    Evalúa colisiones espaciales de combate y resuelve capturas, heridas,
    balances metabólicos por transferencia de biomasa y depósito de restos.
    """

    def __init__(self, config: dict[str, Any], rng: random.Random) -> None:
        self.config = config
        self.rng = rng
        self._cachear_configuracion()

    def _cachear_configuracion(self) -> None:
        """Extrae y tipa los parámetros de combate y rendimiento biológico."""
        cfg_dep = self.config.get("depredacion", {})
        self.captura_prob_min: float = float(cfg_dep.get("captura_prob_min", 0.05))
        self.captura_prob_max: float = float(cfg_dep.get("captura_prob_max", 0.5))
        self.factor_agresividad_resistencia: float = float(
            cfg_dep.get("factor_agresividad_resistencia", 0.2)
        )
        # Armas primitivas v2 (2026-09-03, ver config/armas.yaml y
        # nucleo/armas.py): el efecto defensivo de lo que la presa tenga
        # empunado ya no es binario (reduccion_prob_captura_por_agarre,
        # retirado) sino efecto_base_por_nivel[nivel] +
        # efecto_ofensivo_por_nivel[nivel] * agresividad_presa -- escala
        # con el nivel del arma y con el temperamento del portador.
        self.config_armas: dict[str, Any] = self.config.get("armas", {})
        self.catalogo_materiales: dict[str, Any] = self.config.get("materiales", {})
        self.recetas_armas: list[dict[str, Any]] = self.config_armas.get("recetas", [])
        self.umbral_disposicion_caza: float = float(
            cfg_dep.get("umbral_disposicion_caza", 0.5)
        )
        # Viabilidad energética mínima: mismo umbral que el de
        # movimiento (ver sistema_movimiento.py:_calcular_caza), para que
        # un cazador y una presa que coincidan en la misma celda por
        # casualidad -- sin que el cazador haya caminado hacia ella --
        # se rijan por el mismo criterio de "vale la pena" en vez de que
        # el ataque resuelva algo que el movimiento ya habría descartado.
        self.fraccion_minima_peso_presa: float = float(
            cfg_dep.get("fraccion_minima_peso_presa", 0.001)
        )
        self.eficiencia_biomasa_saciedad: float = float(
            cfg_dep.get("eficiencia_biomasa_saciedad", 1.5)
        )
        self.eficiencia_biomasa_hidratacion: float = float(
            cfg_dep.get("eficiencia_biomasa_hidratacion", 0.5)
        )
        self.factor_dano_base: float = float(cfg_dep.get("factor_dano_base", 0.4))
        # Ver nucleo/entidad.py:componer_necromasa.
        cfg_desc = self.config.get("descomposicion", {})
        self.fraccion_masa_seca: float = float(
            cfg_desc.get("fraccion_masa_seca_por_defecto", 0.35)
        )
        self.fraccion_agua_tisular: float = float(
            cfg_desc.get("fraccion_agua_tisular_por_defecto", 0.65)
        )
        self.fraccion_hueso: float = float(
            cfg_desc.get("fraccion_hueso_de_masa_seca", 0.15)
        )
        # Bono de caza en grupo -- ver
        # nucleo/disposicion.py:contar_conspecificos_cercanos.
        self.radio_apoyo_grupal: int = int(
            self.config.get("social", {}).get("radio_apoyo_grupal", 3)
        )
        self.bono_caza_por_aliado: float = float(
            cfg_dep.get("bono_caza_por_aliado", 0.0)
        )
        self.bono_caza_maximo: float = float(cfg_dep.get("bono_caza_maximo", 0.0))

    def ejecutar(self, gestor: GestorEntidades, bus_eventos: BusEventos) -> None:
        """
        Procesa los encuentros de depredación en el tick actual.
        Debe invocarse en la Fase 2, posterior a SistemaMovimiento.
        """
        # La clave de agrupacion incluye zona_idx -- dos entidades con el
        # mismo (x, y) en zonas distintas NO comparten celda (ver
        # componentes/posicion.py).
        posiciones_mapa: dict[tuple[int, int, int], list[int]] = {}
        for entidad_id in sorted(gestor.entidades_con(Posicion, DimensionesFisicas)):
            pos = gestor.obtener_componente(entidad_id, Posicion)
            if pos is not None:
                clave = (pos.x, pos.y, pos.zona_idx)
                if clave not in posiciones_mapa:
                    posiciones_mapa[clave] = []
                posiciones_mapa[clave].append(entidad_id)

        entidades_eliminadas: set[int] = set()

        for (x, y, zona_idx), entidades in posiciones_mapa.items():
            if len(entidades) < 2:
                continue

            cazadores = [
                eid for eid in entidades
                if eid not in entidades_eliminadas
                and self._es_cazador_activo(gestor, eid)
            ]

            for cazador_id in cazadores:
                if cazador_id in entidades_eliminadas:
                    continue

                presas_candidatas = [
                    eid for eid in entidades
                    if eid != cazador_id
                    and eid not in entidades_eliminadas
                    and self._es_presa_valida(gestor, cazador_id, eid)
                ]

                if not presas_candidatas:
                    continue

                presa_id = min(presas_candidatas)
                muerte_presa = self._resolver_ataque(
                    gestor, bus_eventos, cazador_id, presa_id, x, y, zona_idx
                )

                if muerte_presa:
                    entidades_eliminadas.add(presa_id)

    def _es_cazador_activo(self, gestor: GestorEntidades, entidad_id: int) -> bool:
        """Verifica si la entidad está ejecutando activamente la acción de cazar."""
        intencion = gestor.obtener_componente(entidad_id, Intencion)
        return intencion is not None and intencion.accion == Accion.CAZAR

    def _es_presa_valida(
        self, gestor: GestorEntidades, cazador_id: int, presa_id: int
    ) -> bool:
        """Evalúa si la presa es sustancialmente menor según la ley logarítmica de peso."""
        dims_cazador = gestor.obtener_componente(cazador_id, DimensionesFisicas)
        dims_presa = gestor.obtener_componente(presa_id, DimensionesFisicas)

        if dims_cazador is None or dims_presa is None:
            return False

        if dims_cazador.peso <= dims_presa.peso:
            return False

        if dims_presa.peso < dims_cazador.peso * self.fraccion_minima_peso_presa:
            return False

        disposicion = magnitud_disposicion_por_tamano(dims_cazador.peso, dims_presa.peso)
        return disposicion >= self.umbral_disposicion_caza

    def _resolver_ataque(
        self,
        gestor: GestorEntidades,
        bus_eventos: BusEventos,
        cazador_id: int,
        presa_id: int,
        pos_x: int,
        pos_y: int,
        zona_idx: int = 0,
    ) -> bool:
        """
        Calcula el desenlace del ataque, aplica daño a la vitalidad de la presa,
        transfiere biomasa al cazador y deposita el remanente como necromasa.
        """
        dims_cazador = gestor.obtener_componente(cazador_id, DimensionesFisicas)
        dims_presa = gestor.obtener_componente(presa_id, DimensionesFisicas)
        temp_cazador = gestor.obtener_componente(cazador_id, Temperamento)
        temp_presa = gestor.obtener_componente(presa_id, Temperamento)
        pool_presa = gestor.obtener_componente(presa_id, PoolFisico)
        agarre_presa = gestor.obtener_componente(presa_id, Agarre)
        nec_cazador = gestor.obtener_componente(cazador_id, Necesidades)
        ident_cazador = gestor.obtener_componente(cazador_id, Identidad)
        ident_presa = gestor.obtener_componente(presa_id, Identidad)

        if (
            dims_cazador is None
            or dims_presa is None
            or pool_presa is None
            or ident_cazador is None
            or ident_presa is None
        ):
            return False

        # 1. Probabilidad estocástica de éxito del ataque
        disp = magnitud_disposicion_por_tamano(dims_cazador.peso, dims_presa.peso)
        agr = temp_cazador.agresividad if temp_cazador else 0.5
        val = temp_presa.valentia if temp_presa else 0.5

        prob_exito = disp + (agr - val) * self.factor_agresividad_resistencia

        # Bono de caza en grupo: cuenta conespecificos del propio
        # cazador, cazando activamente, dentro del radio de apoyo grupal
        # -- escalado por la sociabilidad DIRECTA del propio cazador.
        sociabilidad_cazador = temp_cazador.sociabilidad if temp_cazador else 0.0
        if sociabilidad_cazador > 0.0 and self.bono_caza_por_aliado > 0.0:
            aliados_cazando = contar_conspecificos_cercanos(
                gestor, cazador_id, ident_cazador.especie, pos_x, pos_y,
                self.radio_apoyo_grupal, solo_cazando=True, zona_idx=zona_idx,
            )
            bono_grupo = min(
                self.bono_caza_maximo,
                aliados_cazando * self.bono_caza_por_aliado * sociabilidad_cazador,
            )
            prob_exito += bono_grupo

        # Arma empunada de la presa (armas primitivas v2, ver
        # nucleo/armas.py): nivel de lo que la presa tenga en la mano (0
        # si nada), y el efecto real escala con ese nivel y con la
        # agresividad de la propia presa -- un individuo poco agresivo
        # apenas nota el salto ofensivo, pero conserva el obstáculo
        # fisico base de tener algo en la mano.
        nivel_arma_presa = mayor_nivel_arma(
            agarre_presa.objetos if agarre_presa is not None else [],
            self.catalogo_materiales,
            self.recetas_armas,
        )
        agresividad_presa = temp_presa.agresividad if temp_presa else 0.0
        if nivel_arma_presa > 0:
            prob_exito -= bono_defensivo_arma(nivel_arma_presa, agresividad_presa, self.config_armas)

        prob_exito = max(self.captura_prob_min, min(self.captura_prob_max, prob_exito))

        if self.rng.random() >= prob_exito:
            return False

        # 2. Impacto sobre el pool de Vitalidad
        dano_proporcional = self.factor_dano_base * (dims_cazador.fuerza / max(0.1, dims_presa.fuerza))
        dano_neto = dano_proporcional * dims_presa.vitalidad_maxima
        pool_presa.vitalidad = max(0.0, pool_presa.vitalidad - dano_neto)

        # 3. Resolución de estado de salud intermedio: Herida
        if pool_presa.vitalidad > 0.0:
            bus_eventos.emitir(
                Evento(
                    tipo="Herida",
                    severidad=Severidad.NOTABLE,
                    tick=0,
                    entidad_id=presa_id,
                    datos={
                        "atacante_id": cazador_id,
                        "vitalidad_restante": pool_presa.vitalidad,
                    },
                )
            )
            return False

        # 4. Captura letal: Balance de masa y transferencia metabólica
        masas_totales, agua_tisular_total = componer_necromasa(
            dims_presa.peso, self.fraccion_masa_seca, self.fraccion_hueso,
            self.fraccion_agua_tisular,
        )

        fraccion_consumida = 0.0
        if nec_cazador is not None:
            deficit_saciedad = 1.0 - nec_cazador.saciedad
            ratio_biomasa = dims_presa.peso / max(0.1, dims_cazador.peso)
            aporte_maximo = ratio_biomasa * self.eficiencia_biomasa_saciedad

            if aporte_maximo > 0.0:
                aporte_real = min(deficit_saciedad, aporte_maximo)
                fraccion_consumida = min(1.0, aporte_real / aporte_maximo)
            else:
                fraccion_consumida = 1.0

            nec_cazador.saciedad = min(1.0, nec_cazador.saciedad + aporte_maximo)
            aporte_hidrico = ratio_biomasa * self.eficiencia_biomasa_hidratacion * fraccion_consumida
            nec_cazador.hidratacion = min(1.0, nec_cazador.hidratacion + aporte_hidrico)

        # 5. Depósito de biomasa no consumida como Necromasa. El cazador
        # solo come tejido blando -- un depredador no roe el esqueleto
        # entero de su presa -- así que fraccion_consumida reduce SOLO
        # 'tejido_blando'; el hueso queda intacto con independencia de
        # cuánta carne se comió.
        masas_residuales = {
            "tejido_blando": masas_totales["tejido_blando"] * (1.0 - fraccion_consumida),
            "hueso": masas_totales["hueso"],
        }
        agua_residual = agua_tisular_total * (1.0 - fraccion_consumida)

        if sum(masas_residuales.values()) > 0.05:
            crear_necromasa(
                gestor=gestor,
                pos_x=pos_x,
                pos_y=pos_y,
                masas=masas_residuales,
                agua_tisular=agua_residual,
                origen_especie=ident_presa.especie.value,
                tasa_putrefaccion=0.05,
                zona_idx=zona_idx,
            )

        # 6. Emisión de defunción y purga de la entidad biológica activa
        bus_eventos.emitir(
            Evento(
                tipo="Muerte",
                severidad=Severidad.HISTORICO,
                tick=0,
                entidad_id=presa_id,
                datos={
                    "causa": "depredacion",
                    "cazador_id": cazador_id,
                    "especie": ident_presa.especie.value,
                    "nombre": ident_presa.nombre,
                    "x": pos_x,
                    "y": pos_y,
                    "zona_idx": zona_idx,
                },
            )
        )
        gestor.eliminar_entidad(presa_id)
        return True