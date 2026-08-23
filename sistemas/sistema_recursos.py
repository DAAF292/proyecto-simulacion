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

from componentes.capacidad_mental import CapacidadMental
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Identidad
from componentes.intencion import Accion, Intencion
from componentes.memoria_espacial import MemoriaEspacial
from componentes.necesidades import Necesidades
from componentes.necromasa import Necromasa
from componentes.posicion import Posicion
from nucleo.agua import hay_agua_potable
from nucleo.celda import Celda
from nucleo.entidad import GestorEntidades
from nucleo.eventos import BusEventos
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
        self._cachear_configuracion()

    def _cachear_configuracion(self) -> None:
        """Extrae coeficientes de consumo, hidratación y fertilidad."""
        cfg_cons = self.config.get("consumo", {})
        self.tasa_consumo_comer: float = float(cfg_cons.get("tasa_consumo_al_comer", 0.5))
        self.tasa_consumo_beber: float = float(cfg_cons.get("tasa_consumo_al_beber", 0.2))

        cfg_abono = self.config.get("abono", {})
        self.incremento_fertilidad: float = float(
            cfg_abono.get("incremento_fertilidad_por_aliviarse", 0.2)
        )
        self.techo_fertilidad: float = float(cfg_abono.get("techo_fertilidad", 1.0))

        cfg_charco = self.config.get("charcos", {})
        self.tasa_evaporacion_charco: float = float(
            cfg_charco.get("tasa_evaporacion_charco_por_tick", 0.0006)
        )
        self.tasa_agotamiento_charco: float = float(
            cfg_charco.get("tasa_agotamiento_charco_al_beber", 0.01)
        )

        cfg_dep = self.config.get("depredacion", {})
        self.eficiencia_biomasa_saciedad: float = float(
            cfg_dep.get("eficiencia_biomasa_saciedad", 1.5)
        )
        self.eficiencia_biomasa_hidratacion: float = float(
            cfg_dep.get("eficiencia_biomasa_hidratacion", 0.5)
        )

        # Mapa de valores nutricionales e hídricos por recurso vegetal
        self.nutricion_flora: dict[str, float] = {}
        self.hidratacion_flora: dict[str, float] = {}
        for esp_data in self.config.get("flora", {}).get("especies", {}).values():
            for rec in esp_data.get("recursos", []):
                nom = rec.get("nombre")
                if nom:
                    self.nutricion_flora[nom] = float(rec.get("valor_nutricional", 0.2))
                    self.hidratacion_flora[nom] = float(rec.get("valor_hidratacion", 0.05))

    def ejecutar(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        reloj: Reloj,
        bus_eventos: BusEventos,
    ) -> None:
        """
        Punto de entrada tick a tick de la Fase 3.
        Actualiza charcos ambientales y resuelve las intenciones COMER, BEBER y ALIVIARSE.
        """
        zona = mundo.territorio.zonas[0]
        self._actualizar_charcos(zona)

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

            celda = zona.obtener_celda(pos.x, pos.y)

            if intencion.accion == Accion.COMER:
                self._resolver_comer(gestor, eid, ident, nec, mem, cap_mental, celda, pos.x, pos.y)
            elif intencion.accion == Accion.BEBER:
                self._resolver_beber(nec, mem, cap_mental, celda, pos.x, pos.y)
            elif intencion.accion == Accion.ALIVIARSE:
                self._resolver_aliviarse(nec, celda)

    def _actualizar_charcos(self, zona: Any) -> None:
        """Modula la evaporación o generación de charcos según la meteorología activa."""
        clima_actual = getattr(zona, "clima_actual", None)
        nombre_clima = clima_actual.value if clima_actual is not None else "despejado"

        tasa_gen = float(
            self.config.get("clima", {})
            .get("efectos", {})
            .get(nombre_clima, {})
            .get("tasa_generacion_charco_por_tick", 0.0)
        )
        techo_charco = float(self.config.get("charcos", {}).get("techo_profundidad_charco", 0.03))

        for y in range(zona.alto):
            for x in range(zona.ancho):
                celda = zona.obtener_celda(x, y)
                if tasa_gen > 0.0:
                    celda.profundidad_charco = min(techo_charco, celda.profundidad_charco + tasa_gen)
                elif celda.profundidad_charco > 0.0:
                    celda.profundidad_charco = max(0.0, celda.profundidad_charco - self.tasa_evaporacion_charco)

    def _registrar_recuerdo_si_procede(
        self,
        mem: MemoriaEspacial | None,
        cap_mental: CapacidadMental | None,
        tipo: str,
        pos_x: int,
        pos_y: int,
    ) -> None:
        """
        (2026-08-23) Los tres puntos de esta clase que anotaban un
        recuerdo llamaban a `mem.anadir_recuerdo(tipo, (x, y))`, un método
        que MemoriaEspacial nunca tuvo -- es un dataclass con un único
        campo `recuerdos: dict` (ver su docstring). La API real vive en
        nucleo/memoria.py: registrar_recuerdo(memoria, tipo, x, y,
        capacidad), con la capacidad derivada de CapacidadMental.memoria
        (capacidad_memoria()). Centralizado aquí en vez de repetir las
        mismas tres líneas en cada punto de llamada.
        """
        if mem is None or cap_mental is None:
            return
        capacidad = capacidad_memoria(cap_mental, self.config)
        registrar_recuerdo(mem, tipo, pos_x, pos_y, capacidad)

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
    ) -> None:
        """
        Resuelve la ingesta de biomasa: evalúa primero necromasa presente (carroñeo)
        y posteriormente forraje vegetal compatible con la dieta de la especie.
        """
        # 1. Evaluación de Carroñeo (Necromasa en la celda)
        candidatos_necromasa = [
            nid for nid in gestor.entidades_con(Necromasa, Posicion)
            if gestor.obtener_componente(nid, Posicion).x == pos_x  # type: ignore
            and gestor.obtener_componente(nid, Posicion).y == pos_y  # type: ignore
        ]

        if candidatos_necromasa:
            nec_id = min(candidatos_necromasa)
            nec_comp = gestor.obtener_componente(nec_id, Necromasa)

            if nec_comp is not None and nec_comp.masa_organica > 0.05:
                delta_m = min(nec_comp.masa_organica, self.tasa_consumo_comer)
                nec_comp.masa_organica = max(0.0, nec_comp.masa_organica - delta_m)
                nec_comp.agua_tisular = max(0.0, nec_comp.agua_tisular - (delta_m * 0.65))

                # Transferencia nutricional
                nec.saciedad = min(1.0, nec.saciedad + (delta_m * self.eficiencia_biomasa_saciedad))
                nec.hidratacion = min(1.0, nec.hidratacion + (delta_m * self.eficiencia_biomasa_hidratacion))

                self._registrar_recuerdo_si_procede(mem, cap_mental, "comida", pos_x, pos_y)

                if nec_comp.masa_organica <= 0.05:
                    gestor.eliminar_entidad(nec_id)
                return

        # 2. Evaluación de Forrajeo Vegetal
        cfg_esp = self.config.get("rangos_raciales", {}).get(identidad.especie.value, {})
        dieta = cfg_esp.get("dieta", [])

        recursos_disponibles = [
            r for r, cant in celda.recursos.items()
            if cant > 0.0 and (not dieta or r in dieta)
        ]

        if recursos_disponibles:
            nombre_rec = recursos_disponibles[0]
            cant_actual = celda.recursos[nombre_rec]
            consumo = min(cant_actual, self.tasa_consumo_comer)
            celda.recursos[nombre_rec] = max(0.0, cant_actual - consumo)

            val_nut = self.nutricion_flora.get(nombre_rec, 0.2)
            val_hid = self.hidratacion_flora.get(nombre_rec, 0.05)

            nec.saciedad = min(1.0, nec.saciedad + (consumo * val_nut))
            nec.hidratacion = min(1.0, nec.hidratacion + (consumo * val_hid))

            self._registrar_recuerdo_si_procede(mem, cap_mental, "comida", pos_x, pos_y)
        else:
            # (2026-08-23, diagnóstico de extinción local semilla 1) Sin
            # esto, un individuo que llega aquí guiado por un recuerdo de
            # "comida" (nucleo/memoria.py:objetivo_recordado, consultado
            # en sistema_movimiento.py:_calcular_forrajeo SOLO cuando la
            # percepción directa no encuentra nada en el radio -- es
            # decir, exactamente cuando el entorno inmediato ya está
            # agotado) y encuentra la celda igual de vacía, no tenía
            # ninguna consecuencia: el recuerdo stale se queda en la cola
            # FIFO tal cual, objetivo_recordado() sigue devolviendo la
            # MISMA coordenada por ser la más cercana en la lista, y el
            # individuo puede quedar atrapado volviendo sobre el mismo
            # sitio muerto en vez de que la memoria se corrija y el
            # próximo intento explore otra cosa. purgar_recuerdo_invalido
            # ya existía en nucleo/memoria.py con esta finalidad exacta
            # ("invalida de inmediato una coordenada si el recurso ya no
            # existe al visitarlo") pero no se llamaba desde ningún sitio
            # -- pieza diseñada, nunca conectada, misma clase de deuda que
            # agudeza_sensorial antes de esta sesión.
            if mem is not None:
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
            if mem is not None:
                purgar_recuerdo_invalido(mem, "agua", pos_x, pos_y)
            return

        nec.hidratacion = min(1.0, nec.hidratacion + self.tasa_consumo_beber)

        # Si bebe de un charco efímero en tierra firme, drena el charco
        if not celda.tiene_agua and celda.profundidad_charco > 0.0:
            celda.profundidad_charco = max(0.0, celda.profundidad_charco - self.tasa_agotamiento_charco)

        self._registrar_recuerdo_si_procede(mem, cap_mental, "agua", pos_x, pos_y)

    def _resolver_aliviarse(self, nec: Necesidades, celda: Celda) -> None:
        """Evacua residuos orgánicos corporales incrementando la fertilidad del suelo."""
        tasa_alivio = float(self.config.get("necesidades", {}).get("defecto", {}).get("tasa_alivio_al_aliviarse", 0.5))
        nec.aliviado = min(1.0, nec.aliviado + tasa_alivio)
        celda.fertilidad = min(self.techo_fertilidad, celda.fertilidad + self.incremento_fertilidad)