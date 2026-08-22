"""
sistemas/sistema_descomposicion.py

Sistema de degradación pasiva de restos orgánicos (Capa 1/2: Ciclo de Materia).
Evalúa la lisis bacteriana y descomposición de necromasa a cadencia de día,
transfiriendo masa orgánica a la fertilidad edáfica del suelo y liberando agua tisular.
"""

from __future__ import annotations

import random
from typing import Any

from componentes.necromasa import Necromasa
from componentes.posicion import Posicion
from nucleo.entidad import GestorEntidades
from nucleo.eventos import BusEventos, Evento, Severidad
from nucleo.mundo import Mundo
from nucleo.reloj import Reloj


class SistemaDescomposicion:
    """
    Procesa la transformación termodinámica de cadáveres y detritos en nutrientes
    edáficos y humedad superficial bajo modulación climática.
    """

    def __init__(self, config: dict[str, Any], rng: random.Random) -> None:
        self.config = config
        self.rng = rng
        self._cachear_configuracion()

    def _cachear_configuracion(self) -> None:
        """Extrae y tipa los coeficientes de degradación edáfica."""
        cfg_abono = self.config.get("abono", {})
        self.techo_fertilidad: float = float(cfg_abono.get("techo_fertilidad", 1.0))
        
        cfg_charco = self.config.get("charcos", {})
        self.techo_profundidad_charco: float = float(
            cfg_charco.get("techo_profundidad_charco", 0.03)
        )

        # Parámetros físicos de descomposición
        self.constante_degradacion_base: float = 0.08  # 8% diario base
        self.masa_referencia_fertilidad: float = 10.0   # 10 kg saturan fertilidad base
        self.umbral_purga_masa: float = 0.05           # 50 gramos (mineralización)

    def ejecutar(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        reloj: Reloj,
        bus_eventos: BusEventos,
    ) -> None:
        """
        Ejecuta la degradación sobre todas las entidades Necromasa en el mundo.
        Invocado a cadencia de día (Fase de cierre de ciclo).
        """
        zona = mundo.territorio.zonas[0]
        clima_actual = getattr(zona, "clima_actual", None)
        nombre_clima = clima_actual.value if clima_actual is not None else "despejado"

        # Factores ambientales (Temperatura y Humedad)
        factor_humedad = 1.3 if nombre_clima in ("lluvioso", "tormenta") else 0.8
        factor_temperatura = 1.0  # Base neutra estacional

        entidades_necromasa = sorted(gestor.entidades_con(Necromasa, Posicion))

        for nec_id in entidades_necromasa:
            nec = gestor.obtener_componente(nec_id, Necromasa)
            pos = gestor.obtener_componente(nec_id, Posicion)

            if nec is None or pos is None:
                continue

            celda = zona.obtener_celda(pos.x, pos.y)

            # 1. Cálculo de tasa efectiva de degradación
            tasa_efectiva = (
                self.constante_degradacion_base
                * factor_temperatura
                * factor_humedad
                * (1.0 + nec.tasa_putrefaccion)
            )
            tasa_efectiva = min(1.0, tasa_efectiva)

            # 2. Transferencia de biomasa seca a fertilidad edáfica
            delta_masa = nec.masa_organica * tasa_efectiva
            nec.masa_organica = max(0.0, nec.masa_organica - delta_masa)

            aporte_fertilidad = delta_masa / self.masa_referencia_fertilidad
            celda.fertilidad = min(
                self.techo_fertilidad, celda.fertilidad + aporte_fertilidad
            )

            # 3. Liberación de agua tisular a la superficie
            if nec.agua_tisular > 0.0:
                delta_agua = nec.agua_tisular * tasa_efectiva
                nec.agua_tisular = max(0.0, nec.agua_tisular - delta_agua)
                
                # Conversión de litros a metros equivalentes sobre celda (escala aproximada)
                aporte_charco_m = (delta_agua * 0.001) / float(
                    self.config.get("mundo", {}).get("metros_por_celda", 10) ** 2
                )
                celda.profundidad_charco = min(
                    self.techo_profundidad_charco,
                    celda.profundidad_charco + aporte_charco_m,
                )

            # 4. Mineralización completa y purga de la entidad inerte
            if nec.masa_organica <= self.umbral_purga_masa:
                bus_eventos.emitir(
                    Evento(
                        tipo="DescomposicionCompleta",
                        severidad=Severidad.RUIDO,
                        tick=reloj.tick_actual,
                        entidad_id=nec_id,
                        datos={
                            "x": pos.x,
                            "y": pos.y,
                            "origen_especie": nec.origen_especie,
                        },
                    )
                )
                gestor.eliminar_entidad(nec_id)