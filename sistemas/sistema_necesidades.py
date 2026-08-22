"""
sistemas/sistema_necesidades.py

Sistema metabólico y de balance fisiológico interno (Fase 3).
Gestiona el decaimiento de necesidades básicas, la recuperación por sueño,
la deriva térmica ambiental, la asfixia por inmersión y la mortalidad metabólica
con depósito de necromasa y emisión de eventos espaciales.
"""

from __future__ import annotations

import random
from typing import Any

from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Identidad
from componentes.intencion import Accion, Intencion
from componentes.necesidades import Necesidades
from componentes.posicion import Posicion
from nucleo.agua import profundidad_agua_potable
from nucleo.clima import estacion_actual
from nucleo.entidad import GestorEntidades, crear_necromasa
from nucleo.eventos import BusEventos, Evento, Severidad
from nucleo.mundo import Mundo
from nucleo.reloj import Reloj


class SistemaNecesidades:
    """
    Actualiza el estado metabólico de todas las criaturas vivas en la Fase 3.
    """

    def __init__(self, config: dict[str, Any], rng: random.Random) -> None:
        self.config = config
        self.rng = rng
        self._cachear_configuracion()

    def _cachear_configuracion(self) -> None:
        """Extrae tasas de decaimiento y probabilidades críticas."""
        self.cfg_nec = self.config.get("necesidades", {})
        self.defecto = self.cfg_nec.get("defecto", {})

        self.tasa_recup_energia: float = float(
            self.defecto.get("tasa_recuperacion_energia_al_dormir", 0.05)
        )
        self.tasa_drenaje_oxigeno: float = float(
            self.defecto.get("tasa_perdida_oxigenacion_por_inmersion", 0.5)
        )
        self.tasa_recup_oxigeno: float = float(
            self.defecto.get("tasa_recuperacion_oxigenacion", 1.0)
        )
        self.tasa_deriva_termica: float = float(
            self.defecto.get("tasa_deriva_confort_termico", 0.03)
        )
        self.tasa_recup_seguridad: float = float(
            self.defecto.get("tasa_recuperacion_seguridad", 0.05)
        )

        self.prob_muerte_inanicion: float = float(
            self.defecto.get("probabilidad_muerte_saciedad_critica", 0.005)
        )
        self.prob_muerte_deshidratacion: float = float(
            self.defecto.get("probabilidad_muerte_deshidratacion", 0.005)
        )
        self.prob_muerte_ahogamiento: float = float(
            self.defecto.get("probabilidad_muerte_ahogamiento", 0.5)
        )

    def ejecutar(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        reloj: Reloj,
        bus_eventos: BusEventos,
    ) -> None:
        """Procesa el decaimiento metabólico y resuelve la mortalidad fisiológica."""
        zona = mundo.territorio.zonas[0]
        entidades = sorted(
            gestor.entidades_con(Necesidades, Posicion, DimensionesFisicas, Identidad)
        )

        for eid in entidades:
            nec = gestor.obtener_componente(eid, Necesidades)
            pos = gestor.obtener_componente(eid, Posicion)
            dims = gestor.obtener_componente(eid, DimensionesFisicas)
            ident = gestor.obtener_componente(eid, Identidad)
            intencion = gestor.obtener_componente(eid, Intencion)

            if nec is None or pos is None or dims is None or ident is None:
                continue

            celda = zona.obtener_celda(pos.x, pos.y)
            cfg_esp = self.cfg_nec.get(ident.especie.value, self.defecto)

            # 1. Decaimiento continuo de Saciedad, Hidratación, Aliviado y Energía
            tasa_hambre = float(
                cfg_esp.get(
                    "tasa_perdida_saciedad_por_tick",
                    self.defecto.get("tasa_perdida_saciedad_por_tick", 0.012),
                )
            )
            tasa_sed = float(
                cfg_esp.get(
                    "tasa_perdida_hidratacion_por_tick",
                    self.defecto.get("tasa_perdida_hidratacion_por_tick", 0.004),
                )
            )
            tasa_alivio = float(
                cfg_esp.get(
                    "tasa_perdida_aliviado_por_tick",
                    self.defecto.get("tasa_perdida_aliviado_por_tick", 0.01),
                )
            )
            tasa_energia = float(
                cfg_esp.get(
                    "tasa_perdida_energia_por_tick",
                    self.defecto.get("tasa_perdida_energia_por_tick", 0.01),
                )
            )

            nec.saciedad = max(0.0, nec.saciedad - tasa_hambre)
            nec.hidratacion = max(0.0, nec.hidratacion - tasa_sed)
            nec.aliviado = max(0.0, nec.aliviado - tasa_alivio)

            # 2. Resolución de Sueño vs Fatiga
            if intencion is not None and intencion.accion == Accion.DORMIR:
                nec.energia = min(1.0, nec.energia + self.tasa_recup_energia)
            else:
                nec.energia = max(0.0, nec.energia - tasa_energia)

            # 3. Asfixia por inmersión
            prof_agua = profundidad_agua_potable(celda)
            if prof_agua > dims.altura:
                nec.oxigenacion = max(0.0, nec.oxigenacion - self.tasa_drenaje_oxigeno)
            else:
                nec.oxigenacion = min(1.0, nec.oxigenacion + self.tasa_recup_oxigeno)

            # 4. Deriva de Confort Térmico estacional
            # (2026-08-23) Reloj.estacion es un int CRECIENTE, no cíclico
            # (informe de diseño en nucleo/reloj.py: "dia/estacion/anio son
            # unidades derivadas") -- hay que reducirlo al ciclo de 4 y
            # convertirlo al Enum Estacion vía nucleo.clima.estacion_actual()
            # antes de poder leer .value; este código le pedía .value
            # directamente a un int.
            obj_termico = float(
                self.config.get("estaciones", {})
                .get(estacion_actual(reloj.estacion).value, {})
                .get("objetivo_confort_termico", 0.5)
            )
            if nec.confort_termico < obj_termico:
                nec.confort_termico = min(
                    obj_termico, nec.confort_termico + self.tasa_deriva_termica
                )
            elif nec.confort_termico > obj_termico:
                nec.confort_termico = max(
                    obj_termico, nec.confort_termico - self.tasa_deriva_termica
                )

            # 5. Recuperación pasiva de Seguridad
            if nec.seguridad < 1.0:
                nec.seguridad = min(1.0, nec.seguridad + self.tasa_recup_seguridad)

            # 6. Decaimiento de impulso reproductivo
            tasa_rep = float(
                self.defecto.get("tasa_perdida_impulso_reproductivo_por_tick", 0.005)
            )
            nec.impulso_reproductivo = max(0.0, nec.impulso_reproductivo - tasa_rep)

            # 7. Evaluación de Mortalidad Metabólica
            causa_muerte = None

            if nec.oxigenacion <= 0.0:
                if self.rng.random() < self.prob_muerte_ahogamiento:
                    causa_muerte = "ahogamiento"
            elif nec.saciedad <= 0.0:
                if self.rng.random() < self.prob_muerte_inanicion:
                    causa_muerte = "inanicion"
            elif nec.hidratacion <= 0.0:
                if self.rng.random() < self.prob_muerte_deshidratacion:
                    causa_muerte = "deshidratacion"

            if causa_muerte is not None:
                self._resolver_deceso(
                    gestor=gestor,
                    bus_eventos=bus_eventos,
                    reloj=reloj,
                    entidad_id=eid,
                    pos_x=pos.x,
                    pos_y=pos.y,
                    dims=dims,
                    ident=ident,
                    causa=causa_muerte,
                )

    def _resolver_deceso(
        self,
        gestor: GestorEntidades,
        bus_eventos: BusEventos,
        reloj: Reloj,
        entidad_id: int,
        pos_x: int,
        pos_y: int,
        dims: DimensionesFisicas,
        ident: Identidad,
        causa: str,
    ) -> None:
        """Instancia la necromasa, emite el evento Muerte con coordenadas y purga la entidad."""
        masa_seca = dims.peso * 0.35
        agua_tisular = dims.peso * 0.65

        crear_necromasa(
            gestor=gestor,
            pos_x=pos_x,
            pos_y=pos_y,
            masa_organica=masa_seca,
            agua_tisular=agua_tisular,
            origen_especie=ident.especie.value,
            tasa_putrefaccion=0.05,
        )

        bus_eventos.emitir(
            Evento(
                tipo="Muerte",
                severidad=Severidad.HISTORICO,
                tick=reloj.tick_actual,
                entidad_id=entidad_id,
                datos={
                    "causa": causa,
                    "especie": ident.especie.value,
                    "nombre": ident.nombre,
                    "x": pos_x,
                    "y": pos_y,
                },
            )
        )
        gestor.eliminar_entidad(entidad_id)