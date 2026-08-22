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

from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Identidad
from componentes.intencion import Accion, Intencion
from componentes.necesidades import Necesidades
from componentes.pool_fisico import PoolFisico
from componentes.posicion import Posicion
from componentes.temperamento import Temperamento
from nucleo.disposicion import magnitud_disposicion_por_tamano
from nucleo.entidad import GestorEntidades, crear_necromasa
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
        self.umbral_disposicion_caza: float = float(
            cfg_dep.get("umbral_disposicion_caza", 0.5)
        )
        self.eficiencia_biomasa_saciedad: float = float(
            cfg_dep.get("eficiencia_biomasa_saciedad", 1.5)
        )
        self.eficiencia_biomasa_hidratacion: float = float(
            cfg_dep.get("eficiencia_biomasa_hidratacion", 0.5)
        )
        self.factor_dano_base: float = float(cfg_dep.get("factor_dano_base", 0.4))

    def ejecutar(self, gestor: GestorEntidades, bus_eventos: BusEventos) -> None:
        """
        Procesa los encuentros de depredación en el tick actual.
        Debe invocarse en la Fase 2, posterior a SistemaMovimiento.
        """
        posiciones_mapa: dict[tuple[int, int], list[int]] = {}
        for entidad_id in sorted(gestor.entidades_con(Posicion, DimensionesFisicas)):
            pos = gestor.obtener_componente(entidad_id, Posicion)
            if pos is not None:
                clave = (pos.x, pos.y)
                if clave not in posiciones_mapa:
                    posiciones_mapa[clave] = []
                posiciones_mapa[clave].append(entidad_id)

        entidades_eliminadas: set[int] = set()

        for (x, y), entidades in posiciones_mapa.items():
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
                    gestor, bus_eventos, cazador_id, presa_id, x, y
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
        masa_seca_total = dims_presa.peso * 0.35
        agua_tisular_total = dims_presa.peso * 0.65

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

        # 5. Depósito de biomasa no consumida como Necromasa
        masa_residual = masa_seca_total * (1.0 - fraccion_consumida)
        agua_residual = agua_tisular_total * (1.0 - fraccion_consumida)

        if masa_residual > 0.05:
            crear_necromasa(
                gestor=gestor,
                pos_x=pos_x,
                pos_y=pos_y,
                masa_organica=masa_residual,
                agua_tisular=agua_residual,
                origen_especie=ident_presa.especie.value,
                tasa_putrefaccion=0.05,
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
                },
            )
        )
        gestor.eliminar_entidad(presa_id)
        return True