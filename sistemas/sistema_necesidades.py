"""
sistemas/sistema_necesidades.py

Sistema de metabolismo y necesidades biológicas (Fase 3: Metabolismo y Resolución).
Gestiona el desgaste pasivo de necesidades, la reposición de energía por sueño,
el drenaje de oxigenación por inmersión, la resolución estocástica de mortalidad
(inanición, deshidratación, asfixia) y la instanciación de restos orgánicos (necromasa).
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
from nucleo.entidad import GestorEntidades, crear_necromasa
from nucleo.eventos import BusEventos, Evento, Severidad
from nucleo.mundo import Mundo
from nucleo.reloj import Reloj


class SistemaNecesidades:
    """
    Procesa el ciclo metabólico tick a tick para todas las entidades vivas
    que posean componentes de Necesidades e Identidad.
    """

    def __init__(self, config: dict[str, Any], rng: random.Random) -> None:
        self.config = config
        self.rng = rng
        self._cachear_configuracion()

    def _cachear_configuracion(self) -> None:
        """Extrae y tipa los parámetros de configuración para acceso O(1)."""
        cfg_nec = self.config.get("necesidades", {})
        self.cfg_defecto = cfg_nec.get("defecto", {})
        self.cfg_especies = {
            k: v for k, v in cfg_nec.items() if k != "defecto" and isinstance(v, dict)
        }

        self.tasa_recuperacion_dormir: float = float(
            cfg_nec.get("tasa_recuperacion_energia_al_dormir", 0.05)
        )
        self.tasa_perdida_oxigenacion: float = float(
            cfg_nec.get("tasa_perdida_oxigenacion_por_inmersion", 0.5)
        )
        self.prob_muerte_ahogamiento: float = float(
            cfg_nec.get("probabilidad_muerte_ahogamiento", 0.5)
        )
        self.prob_muerte_deshidratacion: float = float(
            cfg_nec.get("probabilidad_muerte_deshidratacion", 0.005)
        )

        cfg_clima = self.config.get("clima", {}).get("efectos", {})
        self.ajustes_confort: dict[str, float] = {
            clima: float(datos.get("ajuste_confort", 0.0))
            for clima, datos in cfg_clima.items()
        }

    def _obtener_parametro(self, especie_str: str, clave: str) -> float:
        """Resuelve un parámetro metabólico consultando el override racial o el bloque por defecto."""
        if especie_str in self.cfg_especies and clave in self.cfg_especies[especie_str]:
            return float(self.cfg_especies[especie_str][clave])
        return float(self.cfg_defecto.get(clave, 0.0))

    def ejecutar(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        reloj: Reloj,
        bus_eventos: BusEventos,
    ) -> None:
        """
        Ejecuta la actualización metabólica sobre todas las entidades con Necesidades.
        Debe invocarse en la Fase 3 del tick, posterior a SistemaDecision y SistemaMovimiento.
        """
        zona = mundo.territorio.zonas[0]
        clima_actual = getattr(zona, "clima_actual", None)
        nombre_clima = clima_actual.value if clima_actual is not None else "despejado"
        ajuste_confort = self.ajustes_confort.get(nombre_clima, 0.0)

        entidades = sorted(gestor.entidades_con(Necesidades, Identidad))

        for entidad_id in entidades:
            nec = gestor.obtener_componente(entidad_id, Necesidades)
            identidad = gestor.obtener_componente(entidad_id, Identidad)
            intencion = gestor.obtener_componente(entidad_id, Intencion)
            pos = gestor.obtener_componente(entidad_id, Posicion)
            dims = gestor.obtener_componente(entidad_id, DimensionesFisicas)

            if nec is None or identidad is None:
                continue

            especie_str = identidad.especie.value

            # 1. Parámetros de desgaste racial
            tasa_hambre = self._obtener_parametro(especie_str, "tasa_perdida_saciedad_por_tick")
            tasa_energia = self._obtener_parametro(especie_str, "tasa_perdida_energia_por_tick")
            tasa_hidratacion = self._obtener_parametro(especie_str, "tasa_perdida_hidratacion_por_tick")
            tasa_aliviado = self._obtener_parametro(especie_str, "tasa_perdida_aliviado_por_tick")
            tasa_reproductivo = self._obtener_parametro(especie_str, "tasa_perdida_impulso_reproductivo_por_tick")
            prob_muerte_saciedad = self._obtener_parametro(especie_str, "probabilidad_muerte_saciedad_critica")

            # 2. Desgaste metabólico pasivo
            nec.saciedad = max(0.0, nec.saciedad - tasa_hambre)
            nec.hidratacion = max(0.0, nec.hidratacion - tasa_hidratacion)
            nec.aliviado = max(0.0, nec.aliviado - tasa_aliviado)
            nec.impulso_reproductivo = max(0.0, nec.impulso_reproductivo - tasa_reproductivo)

            # 3. Resolución de Energía / Sueño (Sincronía Fase 1 -> Fase 3)
            if intencion is not None and intencion.accion == Accion.DORMIR:
                nec.energia = min(1.0, nec.energia + self.tasa_recuperacion_dormir)
            else:
                nec.energia = max(0.0, nec.energia - tasa_energia)

            # 4. Modulación de Confort Térmico por Clima
            if ajuste_confort != 0.0:
                nec.confort_termico = max(0.0, min(1.0, nec.confort_termico + ajuste_confort))

            # 5. Oxigenación e Inmersión en Agua Profunda
            if pos is not None and dims is not None:
                celda = zona.obtener_celda(pos.x, pos.y)
                prof_agua = profundidad_agua_potable(celda)
                
                # Asfixia si la cota de agua excede la estatura corporal
                if prof_agua > dims.altura:
                    nec.oxigenacion = max(0.0, nec.oxigenacion - self.tasa_perdida_oxigenacion)
                else:
                    nec.oxigenacion = 1.0

            # 6. Evaluación de Mortalidad Estocástica
            muerto = False
            causa_muerte = ""

            if nec.oxigenacion <= 0.0 and self.rng.random() < self.prob_muerte_ahogamiento:
                muerto = True
                causa_muerte = "ahogamiento"
            elif nec.hidratacion <= 0.0 and self.rng.random() < self.prob_muerte_deshidratacion:
                muerto = True
                causa_muerte = "deshidratacion"
            elif nec.saciedad <= 0.0 and self.rng.random() < prob_muerte_saciedad:
                muerto = True
                causa_muerte = "inanicion"

            if muerto:
                self._procesar_muerte(gestor, bus_eventos, reloj, entidad_id, identidad, pos, dims, causa_muerte)

    def _procesar_muerte(
        self,
        gestor: GestorEntidades,
        bus_eventos: BusEventos,
        reloj: Reloj,
        entidad_id: int,
        identidad: Identidad,
        pos: Posicion | None,
        dims: DimensionesFisicas | None,
        causa: str,
    ) -> None:
        """
        Emite el evento canónico de defunción, deposita la biomasa inerte
        en el grid mediante crear_necromasa y purga al agente biológico del gestor.
        """
        # Instanciar restos orgánicos en el sustrato antes de eliminar el agente vivo
        if pos is not None and dims is not None:
            masa_seca = dims.peso * 0.35
            agua_tisular = dims.peso * 0.65
            crear_necromasa(
                gestor=gestor,
                pos_x=pos.x,
                pos_y=pos.y,
                masa_organica=masa_seca,
                agua_tisular=agua_tisular,
                origen_especie=identidad.especie.value,
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
                    "especie": identidad.especie.value,
                    "nombre": identidad.nombre,
                },
            )
        )
        gestor.eliminar_entidad(entidad_id)