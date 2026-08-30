"""
sistemas/sistema_descomposicion.py

Sistema de degradación pasiva de restos orgánicos (Capa 1/2: Ciclo de Materia).
Evalúa la lisis bacteriana y descomposición de necromasa a cadencia de día,
transfiriendo masa orgánica a la fertilidad edáfica del suelo y liberando agua tisular.

CÍRCULO 2 de materiales físicos (2026-08-30, ver componentes/necromasa.py
y config/materiales.yaml): un cadáver deja de ser una única masa
homogénea que se mineraliza a una tasa uniforme -- cada material de
Necromasa.masas (tejido_blando, hueso...) se descompone a SU PROPIA
tasa_descomposicion_dia (catálogo de materiales), no a
descomposicion.constante_degradacion_base (retirada). Consecuencia
directa: el hueso (0.002/día, un orden de magnitud más lento que
tejido_blando 0.08/día) sobrevive mucho después de que la carne ya se
mineralizó por completo -- el resto tangible que Diego pedía. La
mineralización completa (purga de la entidad) ya no se dispara cuando
UNA masa llega al umbral, sino cuando TODAS lo hacen -- si no, el hueso
desaparecería en cuanto la carne terminara, exactamente lo contrario de
lo que se pretende.
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
        """Extrae y tipa los coeficientes de degradación edáfica desde constantes.yaml."""
        cfg_abono = self.config.get("abono", {})
        self.techo_fertilidad: float = float(cfg_abono.get("techo_fertilidad", 1.0))

        cfg_charco = self.config.get("charcos", {})
        self.techo_profundidad_charco: float = float(
            cfg_charco.get("techo_profundidad_charco", 0.03)
        )

        cfg_desc = self.config.get("descomposicion", {})
        self.masa_referencia_fertilidad: float = float(
            cfg_desc.get("masa_referencia_fertilidad", 10.0)
        )
        self.umbral_purga_masa: float = float(
            cfg_desc.get("umbral_purga_masa", 0.05)
        )
        self.factor_humedad_lluvia: float = float(
            cfg_desc.get("factor_humedad_lluvia", 1.3)
        )
        self.factor_humedad_seco: float = float(
            cfg_desc.get("factor_humedad_seco", 0.8)
        )

        self.metros_por_celda: float = float(
            self.config.get("mundo", {}).get("metros_por_celda", 10)
        )
        # CÍRCULO 2 de materiales físicos (2026-08-30): catálogo de
        # materiales para la tasa_descomposicion_dia propia de cada
        # material de Necromasa.masas. Fallback (material desconocido o
        # catálogo vacío en un test): mismo valor que tenía la antigua
        # constante_degradacion_base, para no romper comportamiento donde
        # el catálogo no está disponible.
        self.catalogo_materiales: dict[str, Any] = self.config.get("materiales", {})
        self.tasa_descomposicion_por_defecto: float = 0.08

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

        factor_humedad = (
            self.factor_humedad_lluvia
            if nombre_clima in ("lluvioso", "tormenta")
            else self.factor_humedad_seco
        )
        factor_temperatura = 1.0

        entidades_necromasa = sorted(gestor.entidades_con(Necromasa, Posicion))

        for nec_id in entidades_necromasa:
            nec = gestor.obtener_componente(nec_id, Necromasa)
            pos = gestor.obtener_componente(nec_id, Posicion)

            if nec is None or pos is None:
                continue

            celda = zona.obtener_celda(pos.x, pos.y)

            # 1-2. Tasa efectiva de degradación y transferencia de biomasa
            # a fertilidad -- CADA material de nec.masas a SU PROPIA tasa
            # (catálogo de materiales), no una única tasa uniforme para
            # todo el cadáver. tasa_tejido_blando se guarda aparte para la
            # lisis hídrica del paso 3 (el agua tisular vive sobre todo en
            # tejido blando, el hueso apenas retiene agua).
            delta_masa_total = 0.0
            tasa_tejido_blando = 0.0
            for material, masa in nec.masas.items():
                if masa <= 0.0:
                    continue
                tasa_base = float(
                    self.catalogo_materiales.get(material, {}).get(
                        "tasa_descomposicion_dia", self.tasa_descomposicion_por_defecto
                    )
                )
                tasa_efectiva = min(
                    1.0,
                    tasa_base * factor_temperatura * factor_humedad * (1.0 + nec.tasa_putrefaccion),
                )
                if material == "tejido_blando":
                    tasa_tejido_blando = tasa_efectiva

                delta_masa = masa * tasa_efectiva
                nec.masas[material] = max(0.0, masa - delta_masa)
                delta_masa_total += delta_masa

            aporte_fertilidad = delta_masa_total / self.masa_referencia_fertilidad
            celda.fertilidad = min(
                self.techo_fertilidad, celda.fertilidad + aporte_fertilidad
            )

            # 3. Lisis hídrica y liberación a superficie -- al ritmo de
            # tejido_blando especificamente (ver docstring de
            # Necromasa.agua_tisular).
            if nec.agua_tisular > 0.0:
                delta_agua = nec.agua_tisular * tasa_tejido_blando
                nec.agua_tisular = max(0.0, nec.agua_tisular - delta_agua)

                aporte_charco_m = (delta_agua * 0.001) / (self.metros_por_celda ** 2)
                # (2026-08-29) Mismo criterio que _actualizar_charcos en
                # sistema_recursos.py: la lisis hídrica solo aporta charco
                # sobre tierra firme; el agua de un cuerpo permanente se
                # incorpora a él, no a un campo de charco que ahí no
                # significa nada. La lisis en sí (el gasto de agua_tisular)
                # opera igual en ambas.
                if not celda.tiene_agua:
                    celda.profundidad_charco = min(
                        self.techo_profundidad_charco,
                        celda.profundidad_charco + aporte_charco_m,
                    )

            # 4. Mineralización completa -- TODOS los materiales por
            # debajo del umbral, no solo uno: si no, el hueso se borraría
            # en cuanto el tejido blando terminara, justo lo contrario de
            # "persiste como resto tangible".
            if all(masa <= self.umbral_purga_masa for masa in nec.masas.values()):
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