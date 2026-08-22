"""
sistemas/sistema_desastres.py

Sistema de desastres naturales y dinámicas de perturbación ambiental (Corte de Día / Fase 2).
Gestiona la ignición de incendios condicionada por clima a cadencia diaria,
la propagación/extinción por tick, el daño térmico a criaturas vivas con depósito
de necromasa calcinada y la conversión de flora quemada en ceniza edáfica.
"""

from __future__ import annotations

import random
from typing import Any

from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Identidad
from componentes.planta import Planta
from componentes.pool_fisico import PoolFisico
from componentes.posicion import Posicion
from nucleo.bioma import TipoTerreno
from nucleo.entidad import GestorEntidades, crear_necromasa
from nucleo.eventos import BusEventos, Evento, Severidad
from nucleo.mundo import Mundo
from nucleo.reloj import Reloj


class SistemaDesastres:
    """
    Simula eventos catastróficos locales y su propagación física en el grid.
    """

    def __init__(self, config: dict[str, Any], rng: random.Random) -> None:
        self.config = config
        self.rng = rng
        self._cachear_configuracion()

    def _cachear_configuracion(self) -> None:
        """Extrae y tipa los parámetros de ignición, propagación y daño por fuego."""
        cfg_des = self.config.get("desastres", {})
        self.prob_ignicion_base: float = float(
            cfg_des.get("prob_ignicion_base_bosque", 0.0015)
        )
        self.prob_propagacion: float = float(
            cfg_des.get("prob_propagacion_por_tick", 0.08)
        )
        self.prob_extincion: float = float(
            cfg_des.get("prob_extincion_por_tick", 0.35)
        )
        self.dano_por_tick_en_llamas: float = float(
            cfg_des.get("dano_por_tick_en_llamas", 0.15)
        )
        self.aporte_ceniza_planta: float = float(
            cfg_des.get("aporte_ceniza_planta", 0.15)
        )
        self.fraccion_masa_seca_quemada: float = float(
            cfg_des.get("fraccion_masa_seca_quemada", 0.20)
        )
        self.fraccion_agua_tisular_quemada: float = float(
            cfg_des.get("fraccion_agua_tisular_quemada", 0.05)
        )
        self.tasa_putrefaccion_calcinada: float = float(
            cfg_des.get("tasa_putrefaccion_calcinada", 0.15)
        )

        cfg_clima = cfg_des.get("multiplicador_riesgo_por_clima", {})
        self.mult_riesgo_clima: dict[str, float] = {
            "despejado": float(cfg_clima.get("despejado", 1.5)),
            "lluvioso": float(cfg_clima.get("lluvioso", 0.2)),
            "tormenta": float(cfg_clima.get("tormenta", 1.0)),
        }

        self.techo_fertilidad: float = float(
            self.config.get("abono", {}).get("techo_fertilidad", 1.0)
        )

    def ejecutar(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        reloj: Reloj,
        bus_eventos: BusEventos,
    ) -> None:
        """
        Punto de entrada para la evaluación diaria de ignición.
        Invocado al inicio de cada día en el orquestador principal.
        """
        zona = mundo.territorio.zonas[0]
        clima_actual = getattr(zona, "clima_actual", None)
        nombre_clima = clima_actual.value if clima_actual is not None else "despejado"
        mult_clima = self.mult_riesgo_clima.get(nombre_clima, 1.0)

        prob_efectiva = self.prob_ignicion_base * mult_clima

        for y in range(zona.alto):
            for x in range(zona.ancho):
                celda = zona.obtener_celda(x, y)
                if celda.tipo_terreno == TipoTerreno.BOSQUE and not celda.en_llamas:
                    if self.rng.random() < prob_efectiva:
                        celda.en_llamas = True
                        bus_eventos.emitir(
                            Evento(
                                tipo="IncendioIniciado",
                                severidad=Severidad.HISTORICO,
                                tick=reloj.tick_actual,
                                datos={"x": x, "y": y, "clima": nombre_clima},
                            )
                        )

    def procesar_fuego_tick(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        reloj: Reloj,
        bus_eventos: BusEventos,
    ) -> None:
        """
        Propaga llamas, extingue focos y aplica daño térmico a criaturas y flora.
        Debe ejecutarse a cadencia de tick en la Fase 2 del ciclo.
        """
        zona = mundo.territorio.zonas[0]
        celdas_en_llamas: list[tuple[int, int]] = []

        for y in range(zona.alto):
            for x in range(zona.ancho):
                celda = zona.obtener_celda(x, y)
                if celda.en_llamas:
                    celdas_en_llamas.append((x, y))

        if not celdas_en_llamas:
            return

        nuevos_focos: list[tuple[int, int]] = []
        extinciones: list[tuple[int, int]] = []

        direcciones = [(0, 1), (0, -1), (1, 0), (-1, 0)]

        for fx, fy in celdas_en_llamas:
            if self.rng.random() < self.prob_extincion:
                extinciones.append((fx, fy))

            for dx, dy in direcciones:
                nx, ny = fx + dx, fy + dy
                if 0 <= nx < zona.ancho and 0 <= ny < zona.alto:
                    vecina = zona.obtener_celda(nx, ny)
                    if (
                        vecina.tipo_terreno == TipoTerreno.BOSQUE
                        and not vecina.en_llamas
                        and (nx, ny) not in nuevos_focos
                    ):
                        if self.rng.random() < self.prob_propagacion:
                            nuevos_focos.append((nx, ny))

        for ex, ey in extinciones:
            zona.obtener_celda(ex, ey).en_llamas = False

        for nx, ny in nuevos_focos:
            zona.obtener_celda(nx, ny).en_llamas = True

        # 1. Flora en llamas -> Ceniza mineralizada
        plantas_a_purgar: list[int] = []
        for planta_id in sorted(gestor.entidades_con(Planta, Posicion)):
            pos_p = gestor.obtener_componente(planta_id, Posicion)
            if pos_p is not None:
                celda_p = zona.obtener_celda(pos_p.x, pos_p.y)
                if celda_p.en_llamas:
                    celda_p.fertilidad = min(
                        self.techo_fertilidad,
                        celda_p.fertilidad + self.aporte_ceniza_planta,
                    )
                    plantas_a_purgar.append(planta_id)

        for pid in plantas_a_purgar:
            gestor.eliminar_entidad(pid)

        # 2. Criaturas vivas en llamas -> Necromasa calcinada
        criaturas = sorted(
            gestor.entidades_con(Posicion, PoolFisico, DimensionesFisicas, Identidad)
        )
        for cid in criaturas:
            pos_c = gestor.obtener_componente(cid, Posicion)
            pool_c = gestor.obtener_componente(cid, PoolFisico)
            dims_c = gestor.obtener_componente(cid, DimensionesFisicas)
            ident_c = gestor.obtener_componente(cid, Identidad)

            if pos_c is None or pool_c is None or dims_c is None or ident_c is None:
                continue

            celda_c = zona.obtener_celda(pos_c.x, pos_c.y)
            if celda_c.en_llamas:
                dano_neto = self.dano_por_tick_en_llamas * dims_c.vitalidad_maxima
                pool_c.vitalidad = max(0.0, pool_c.vitalidad - dano_neto)

                if pool_c.vitalidad <= 0.0:
                    masa_seca_quemada = dims_c.peso * self.fraccion_masa_seca_quemada
                    agua_tisular_restante = (
                        dims_c.peso * self.fraccion_agua_tisular_quemada
                    )
                    crear_necromasa(
                        gestor=gestor,
                        pos_x=pos_c.x,
                        pos_y=pos_c.y,
                        masa_organica=masa_seca_quemada,
                        agua_tisular=agua_tisular_restante,
                        origen_especie=ident_c.especie.value,
                        tasa_putrefaccion=self.tasa_putrefaccion_calcinada,
                    )

                    bus_eventos.emitir(
                        Evento(
                            tipo="Muerte",
                            severidad=Severidad.HISTORICO,
                            tick=reloj.tick_actual,
                            entidad_id=cid,
                            datos={
                                "causa": "incendio",
                                "especie": ident_c.especie.value,
                                "nombre": ident_c.nombre,
                            },
                        )
                    )
                    gestor.eliminar_entidad(cid)
                else:
                    bus_eventos.emitir(
                        Evento(
                            tipo="Herida",
                            severidad=Severidad.NOTABLE,
                            tick=reloj.tick_actual,
                            entidad_id=cid,
                            datos={
                                "causa": "fuego",
                                "vitalidad_restante": pool_c.vitalidad,
                            },
                        )
                    )