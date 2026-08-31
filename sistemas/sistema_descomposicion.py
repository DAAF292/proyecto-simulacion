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

from componentes.construccion import Construccion
from componentes.necromasa import Necromasa
from componentes.posicion import Posicion
from nucleo.construccion import masa_minima_para, progreso_construccion
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
        # Deterioro de construcciones (2026-08-30, "nada dura para
        # siempre" -- ver conversación de diseño con Diego). A diferencia
        # de Necromasa, SIN fallback de 0.08: piedra/arcilla/tierra/
        # hierro/cobre no declaran tasa_descomposicion_dia en el catálogo
        # (geológicamente estables) y deben quedarse así -- una
        # construcción de piedra no debe decaer solo porque el material
        # no tiene una tasa explícita, al contrario que un cadáver (100%
        # orgánico, ahí sí tiene sentido que "sin tasa" signifique "tasa
        # genérica de materia orgánica").
        self.config_construccion: dict[str, Any] = self.config.get("construccion", {})

    def ejecutar(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        reloj: Reloj,
        bus_eventos: BusEventos,
    ) -> None:
        """
        Ejecuta la degradación sobre todas las entidades Necromasa en el mundo,
        y el deterioro pasivo de las Construccion existentes.
        Invocado a cadencia de día (Fase de cierre de ciclo).
        """
        self._descomponer_construcciones(gestor, mundo, reloj, bus_eventos)

        # (2026-08-30, Circulo 1 de profundidad) factor de humedad
        # calculado UNA VEZ POR ZONA (cada ZonaBioma tiene su propio
        # clima_actual), luego aplicado a cada Necromasa segun la zona a
        # la que pertenezca -- no una unica variable global derivada de
        # zonas[0] aplicada por igual a toda entidad exista donde exista.
        factores_humedad_por_zona: dict[int, float] = {}
        for indice_zona, zona_i in enumerate(mundo.territorio.zonas):
            clima_actual = getattr(zona_i, "clima_actual", None)
            nombre_clima = clima_actual.value if clima_actual is not None else "despejado"
            factores_humedad_por_zona[indice_zona] = (
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

            zona = mundo.territorio.zonas[pos.zona_idx]
            factor_humedad = factores_humedad_por_zona[pos.zona_idx]
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

    def _descomponer_construcciones(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        reloj: Reloj,
        bus_eventos: BusEventos,
    ) -> None:
        """
        Deterioro pasivo de Construccion.materiales -- "nada dura para
        siempre" (2026-08-30, ver conversación de diseño con Diego).
        MISMA ley que la descomposición de Necromasa (arriba): cada
        material a SU PROPIA tasa_descomposicion_dia del catálogo, sin el
        fallback genérico de Necromasa (ver _cachear_configuracion) --
        piedra/arcilla/tierra/hierro/cobre no decaen por esta vía,
        madera/fibra/hierba_seca sí, honestamente, sin forzar
        uniformidad donde la física real no la tiene.

        Sin transferencia a fertilidad ni agua_tisular -- una
        construcción no es un cadáver, no hay pool que alimentar.
        `progreso` se RECALCULA tras el deterioro (no solo los
        materiales): si una construcción YA terminada decae lo bastante,
        vuelve a caer por debajo de 1.0 -- consecuencia deliberada, no un
        efecto colateral: hace que objetivo_construccion_actual la trate
        de nuevo como necesitada de reparación (un refugio decae fuera
        del clúster de asentamiento en SistemaAsentamiento, que filtra
        por progreso>=1.0, hasta que alguien la repare), sin escribir
        ninguna lógica de "reparación" nueva -- reutiliza el mismo camino
        que ya construye desde cero.

        Al degradarse por completo (todos los materiales por debajo del
        umbral), la construcción colapsa: se elimina la entidad. La
        memoria "refugio"/"asentamiento" de quien la recordaba NO se
        purga aquí -- sigue apuntando a un sitio ya vacío, hueco
        conocido y señalado, no resuelto en esta pieza.
        """
        masa_minima_cache: dict[str, float] = {}

        for cid in sorted(gestor.entidades_con(Construccion, Posicion)):
            construccion = gestor.obtener_componente(cid, Construccion)
            pos = gestor.obtener_componente(cid, Posicion)
            if construccion is None or pos is None or not construccion.materiales:
                continue

            for material, masa in list(construccion.materiales.items()):
                if masa <= 0.0:
                    continue
                tasa = float(
                    self.catalogo_materiales.get(material, {}).get("tasa_descomposicion_dia", 0.0)
                )
                if tasa <= 0.0:
                    continue
                construccion.materiales[material] = max(0.0, masa - masa * tasa)

            if construccion.tipo not in masa_minima_cache:
                masa_minima_cache[construccion.tipo] = masa_minima_para(
                    construccion.tipo, self.config_construccion
                )
            construccion.progreso = progreso_construccion(
                construccion.materiales, self.catalogo_materiales, masa_minima_cache[construccion.tipo]
            )

            if all(masa <= self.umbral_purga_masa for masa in construccion.materiales.values()):
                bus_eventos.emitir(
                    Evento(
                        tipo="ConstruccionColapsada",
                        severidad=Severidad.NOTABLE if construccion.tipo == "refugio" else Severidad.HISTORICO,
                        tick=reloj.tick_actual,
                        entidad_id=cid,
                        datos={"x": pos.x, "y": pos.y, "tipo": construccion.tipo, "causa": "deterioro"},
                    )
                )
                gestor.eliminar_entidad(cid)