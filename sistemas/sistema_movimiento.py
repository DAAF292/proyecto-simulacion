"""
sistemas/sistema_movimiento.py

Sistema de cinemática, fricción espacial y desplazamiento local (Fase 2).
Resuelve el movimiento ortogonal condicionado por intenciones (COMER, BEBER,
CAZAR, HUIR, BUSCAR_PAREJA, DEAMBULAR), aplicando restricciones de relieve,
profundidad de agua y drenaje de resistencia por sprint y desnivel positivo.
"""

from __future__ import annotations

import random
from typing import Any

from componentes.capacidad_mental import CapacidadMental
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Especie, Identidad
from componentes.intencion import Accion, Intencion
from componentes.memoria_espacial import MemoriaEspacial
from componentes.necesidades import Necesidades
from componentes.necromasa import Necromasa
from componentes.pool_fisico import PoolFisico
from componentes.posicion import Posicion
# NOTA (2026-08-23): Gestacion se separó a su propio módulo
# (componentes/gestacion.py, ver su docstring) para no mezclar el rasgo
# fijo de por vida (Reproduccion) con el estado de un embarazo concreto.
# Este import seguía apuntando al módulo antiguo tras esa separación.
from componentes.gestacion import Gestacion
from componentes.reproduccion import Reproduccion
from nucleo.agua import hay_agua_potable, profundidad_agua_potable
from nucleo.amenaza import posicion_amenaza_mas_cercana
from nucleo.entidad import GestorEntidades
from nucleo.memoria import objetivo_recordado
from nucleo.mundo import Mundo
from nucleo.percepcion import radio_individual
from nucleo.relieve import pendiente_maxima_transitable


class SistemaMovimiento:
    """
    Ejecuta el desplazamiento físico de las entidades sobre el grid en la Fase 2.
    """

    def __init__(self, config: dict[str, Any], rng: random.Random) -> None:
        self.config = config
        self.rng = rng
        self._cachear_configuracion()

    def _cachear_configuracion(self) -> None:
        """Extrae parámetros de percepción, relieve, fricción y costes."""
        cfg_per = self.config.get("percepcion", {})
        self.radio_min: int = int(cfg_per.get("radio_minimo_celdas", 0))
        self.radio_max: int = int(cfg_per.get("radio_maximo_celdas", 4))

        cfg_rel = self.config.get("relieve", {})
        self.pend_min: float = float(cfg_rel.get("pendiente_minima_transitable", 0.05))
        self.pend_max: float = float(cfg_rel.get("pendiente_maxima_transitable", 0.22))
        self.costo_pendiente: float = float(
            cfg_rel.get("costo_resistencia_por_unidad_pendiente", 0.3)
        )

        cfg_mov = self.config.get("movimiento", {})
        self.coste_sprint: float = float(cfg_mov.get("coste_resistencia_sprint", 0.08))
        self.umbral_agotamiento: float = float(
            cfg_mov.get("umbral_resistencia_agotamiento", 0.05)
        )

        cfg_mem = self.config.get("memoria", {})
        self.factor_error_memoria: float = float(
            cfg_mem.get("factor_error_por_distancia", 0.3)
        )

        self.dist_deseada_conspecifico: int = int(
            self.config.get("social", {}).get("distancia_deseada_conspecifico", 1)
        )
        self.dist_deseada_territorio: int = int(
            self.config.get("social", {}).get("distancia_deseada_territorio", 1)
        )
        self.umbral_consciencia_agencia: float = float(
            self.config.get("decision", {}).get("umbral_consciencia_agencia", 0.3)
        )

    def ejecutar(self, gestor: GestorEntidades, mundo: Mundo) -> None:
        """
        Ejecuta el paso de movimiento para todas las criaturas con Intencion y Posicion.
        """
        zona = mundo.territorio.zonas[0]
        entidades = sorted(
            gestor.entidades_con(Intencion, Posicion, DimensionesFisicas, Identidad)
        )

        for eid in entidades:
            intencion = gestor.obtener_componente(eid, Intencion)
            pos = gestor.obtener_componente(eid, Posicion)
            dims = gestor.obtener_componente(eid, DimensionesFisicas)
            ident = gestor.obtener_componente(eid, Identidad)
            pf = gestor.obtener_componente(eid, PoolFisico)
            mem = gestor.obtener_componente(eid, MemoriaEspacial)
            cap_mental = gestor.obtener_componente(eid, CapacidadMental)

            if intencion is None or pos is None or dims is None or ident is None:
                continue

            # Bloqueo temporal por extenuación muscular extrema
            if pf is not None and pf.resistencia <= self.umbral_agotamiento:
                continue

            radio = radio_individual(dims.agudeza_sensorial, self.radio_min, self.radio_max)
            accion = intencion.accion

            dx, dy = 0, 0

            if accion == Accion.DORMIR:
                continue
            elif accion == Accion.HUIR:
                dx, dy = self._calcular_huida(gestor, zona, eid, pos.x, pos.y, radio)
            elif accion == Accion.CAZAR:
                dx, dy = self._calcular_caza(gestor, eid, pos.x, pos.y, dims.peso, radio)
            elif accion == Accion.COMER:
                dx, dy = self._calcular_forrajeo(
                    gestor, zona, ident.especie, pos.x, pos.y, radio, mem, cap_mental
                )
            elif accion == Accion.BEBER:
                dx, dy = self._calcular_hidratacion(
                    zona, pos.x, pos.y, dims.altura, radio, mem, cap_mental
                )
            elif accion == Accion.BUSCAR_PAREJA:
                dx, dy = self._calcular_pareja(gestor, eid, ident.especie, pos.x, pos.y, radio)
            elif accion == Accion.DEAMBULAR:
                dx, dy = self._calcular_deambular(
                    gestor, eid, ident.especie, pos.x, pos.y, mem, cap_mental
                )

            if dx != 0 or dy != 0:
                self._aplicar_movimiento(gestor, zona, eid, pos, dims, pf, dx, dy, accion)

    def _aplicar_movimiento(
        self,
        gestor: GestorEntidades,
        zona: Any,
        entidad_id: int,
        pos: Posicion,
        dims: DimensionesFisicas,
        pf: PoolFisico | None,
        dx: int,
        dy: int,
        accion: Accion,
    ) -> None:
        """Valida restricciones de terreno y aplica el gasto metabólico de resistencia."""
        nx, ny = pos.x + dx, pos.y + dy

        if not (0 <= nx < zona.ancho and 0 <= ny < zona.alto):
            return

        celda_orig = zona.obtener_celda(pos.x, pos.y)
        celda_dest = zona.obtener_celda(nx, ny)

        # 1. Chequeo de profundidad de agua frente a la estatura corporal
        prof_agua = profundidad_agua_potable(celda_dest)
        if prof_agua > dims.altura and profundidad_agua_potable(celda_orig) <= dims.altura:
            return

        # 2. Chequeo de relieve y pendiente máxima transitable
        delta_elev = celda_dest.elevacion - celda_orig.elevacion
        pend_max = pendiente_maxima_transitable(dims.fuerza, self.pend_min, self.pend_max)

        if delta_elev > pend_max:
            return

        # 3. Drenaje de resistencia física (únicamente en desnivel positivo y sprint)
        if pf is not None:
            coste_total = 0.0
            if delta_elev > 0.0:
                coste_total += (delta_elev * self.costo_pendiente) / max(0.1, dims.resistencia_maxima)
            if accion in (Accion.CAZAR, Accion.HUIR):
                coste_total += self.coste_sprint / max(0.1, dims.resistencia_maxima)

            pf.resistencia = max(0.0, pf.resistencia - coste_total)

        # 4. Actualización atómica de coordenadas espaciales
        pos.x = nx
        pos.y = ny

    def _calcular_huida(
        self,
        gestor: GestorEntidades,
        zona: Any,
        entidad_id: int,
        pos_x: int,
        pos_y: int,
        radio: int,
    ) -> tuple[int, int]:
        """Calcula el vector opuesto a la amenaza más cercana percibida."""
        amenaza_pos = posicion_amenaza_mas_cercana(gestor, zona, entidad_id, pos_x, pos_y, radio)
        if amenaza_pos is None:
            return self._paso_aleatorio()

        ax, ay = amenaza_pos
        dx = 0 if ax == pos_x else (1 if pos_x > ax else -1)
        dy = 0 if ay == pos_y else (1 if pos_y > ay else -1)
        return dx, dy

    def _calcular_caza(
        self,
        gestor: GestorEntidades,
        cazador_id: int,
        pos_x: int,
        pos_y: int,
        peso_cazador: float,
        radio: int,
    ) -> tuple[int, int]:
        """Avanza hacia la presa válida más cercana dentro del radio sensorial."""
        presas = []
        for eid in gestor.entidades_con(Posicion, DimensionesFisicas):
            if eid == cazador_id:
                continue
            pos_p = gestor.obtener_componente(eid, Posicion)
            dims_p = gestor.obtener_componente(eid, DimensionesFisicas)
            if pos_p and dims_p and dims_p.peso < peso_cazador:
                dist = abs(pos_p.x - pos_x) + abs(pos_p.y - pos_y)
                if dist <= radio:
                    presas.append((dist, pos_p.x, pos_p.y))

        if not presas:
            return self._paso_aleatorio()

        presas.sort()
        _, px, py = presas[0]
        return self._acercarse_a(pos_x, pos_y, px, py)

    def _calcular_forrajeo(
        self,
        gestor: GestorEntidades,
        zona: Any,
        especie: Especie,
        pos_x: int,
        pos_y: int,
        radio: int,
        mem: MemoriaEspacial | None,
        cap_mental: CapacidadMental | None,
    ) -> tuple[int, int]:
        """Busca comida: evalúa necromasa y flora en radio sensorial y memoria."""
        cfg_esp = self.config.get("rangos_raciales", {}).get(especie.value, {})
        dieta = cfg_esp.get("dieta", [])

        # 1. Percepción directa de Necromasa o Recursos vegetales en el vecindario
        candidatos = []
        
        # A. Necromasa cercana
        for nid in gestor.entidades_con(Necromasa, Posicion):
            pos_n = gestor.obtener_componente(nid, Posicion)
            nec_comp = gestor.obtener_componente(nid, Necromasa)
            if pos_n and nec_comp and nec_comp.masa_organica > 0.05:
                dist = abs(pos_n.x - pos_x) + abs(pos_n.y - pos_y)
                if dist <= radio:
                    candidatos.append((dist, pos_n.x, pos_n.y))

        # B. Recursos botánicos en celdas
        for dy in range(-radio, radio + 1):
            for dx in range(-radio, radio + 1):
                nx, ny = pos_x + dx, pos_y + dy
                if 0 <= nx < zona.ancho and 0 <= ny < zona.alto:
                    celda = zona.obtener_celda(nx, ny)
                    hay_comida = any(
                        cant > 0.0 and (not dieta or r in dieta)
                        for r, cant in celda.recursos.items()
                    )
                    if hay_comida:
                        dist = abs(dx) + abs(dy)
                        candidatos.append((dist, nx, ny))

        if candidatos:
            candidatos.sort()
            _, tx, ty = candidatos[0]
            return self._acercarse_a(pos_x, pos_y, tx, ty)

        # 2. Búsqueda en memoria espacial amortiguada por distancia
        # (2026-08-23) corregido: llamaba a `mem.obtener_recuerdos(tipo)`
        # (método que MemoriaEspacial no tiene) y luego a
        # `objetivo_recordado()` con una firma posicional que no coincidía
        # con la real de nucleo/memoria.py -- código muerto que crashearía
        # en cuanto se alcanzara (solo no lo había hecho porque el
        # candidato directo por percepción casi siempre existe antes).
        if mem is not None and cap_mental is not None:
            objetivo = objetivo_recordado(
                mem, "comida", pos_x, pos_y, cap_mental, self.rng, self.config
            )
            if objetivo is not None:
                return self._acercarse_a(pos_x, pos_y, *objetivo)

        return self._paso_aleatorio()

    def _calcular_hidratacion(
        self,
        zona: Any,
        pos_x: int,
        pos_y: int,
        altura: float,
        radio: int,
        mem: MemoriaEspacial | None,
        cap_mental: CapacidadMental | None,
    ) -> tuple[int, int]:
        """Busca fuentes de agua potable y vadeables en radio de percepción o memoria."""
        candidatos = []
        for dy in range(-radio, radio + 1):
            for dx in range(-radio, radio + 1):
                nx, ny = pos_x + dx, pos_y + dy
                if 0 <= nx < zona.ancho and 0 <= ny < zona.alto:
                    celda = zona.obtener_celda(nx, ny)
                    if hay_agua_potable(celda) and profundidad_agua_potable(celda) <= altura:
                        dist = abs(dx) + abs(dy)
                        candidatos.append((dist, nx, ny))

        if candidatos:
            candidatos.sort()
            _, tx, ty = candidatos[0]
            return self._acercarse_a(pos_x, pos_y, tx, ty)

        if mem is not None and cap_mental is not None:
            objetivo = objetivo_recordado(
                mem, "agua", pos_x, pos_y, cap_mental, self.rng, self.config
            )
            if objetivo is not None:
                return self._acercarse_a(pos_x, pos_y, *objetivo)

        return self._paso_aleatorio()

    def _calcular_pareja(
        self,
        gestor: GestorEntidades,
        entidad_id: int,
        especie: Especie,
        pos_x: int,
        pos_y: int,
        radio: int,
    ) -> tuple[int, int]:
        """Avanza hacia una pareja reproductora compatible acotada al radio sensorial."""
        rep_propia = gestor.obtener_componente(entidad_id, Reproduccion)
        if rep_propia is None:
            return self._paso_aleatorio()

        candidatos = []
        for eid in gestor.entidades_con(Reproduccion, Posicion, Identidad):
            if eid == entidad_id:
                continue
            pos_c = gestor.obtener_componente(eid, Posicion)
            if pos_c is None:
                continue

            dist = abs(pos_c.x - pos_x) + abs(pos_c.y - pos_y)
            if dist > radio:
                continue

            ident = gestor.obtener_componente(eid, Identidad)
            rep = gestor.obtener_componente(eid, Reproduccion)
            gest = gestor.obtener_componente(eid, Gestacion)

            if (
                ident
                and rep
                and ident.especie == especie
                and rep.sexo != rep_propia.sexo
                and gest is None
            ):
                candidatos.append((dist, pos_c.x, pos_c.y))

        if candidatos:
            candidatos.sort()
            _, px, py = candidatos[0]
            return self._acercarse_a(pos_x, pos_y, px, py)

        return self._paso_aleatorio()

    def _calcular_deambular(
        self,
        gestor: GestorEntidades,
        entidad_id: int,
        especie: Especie,
        pos_x: int,
        pos_y: int,
        mem: MemoriaEspacial | None,
        cap_mental: CapacidadMental | None,
    ) -> tuple[int, int]:
        """
        Paso de dispersión aleatoria, salvo SESGO DE TERRITORIO (2026-08-22,
        propuesta de Diego, confirmada: "a nivel biológico lo común es
        mantenerse cerca de las fuentes de alimentación, agua y seguridad").

        Sin objetivo activo (COMER/BEBER/CAZAR/HUIR/BUSCAR_PAREJA), una
        criatura no debería dispersarse sin rumbo si ya conoce dónde hay
        recursos -- eso es plausible para un individuo consciente que
        delibera (gnomo), pero no para fauna sin agencia: lo esperable en
        fauna real es permanecer dentro de su área de campeo (home range)
        en torno a comida/agua/seguridad conocidas, no vagar uniformemente.

        Gating por CapacidadMental.consciencia (decision.umbral_consciencia_
        agencia, PROVISIONAL=0.3): reutiliza el atributo declarado desde el
        Bloque F1 y sin consumidor hasta ahora (ver componentes/
        capacidad_mental.py) para diferenciar el grado de agencia -- por
        debajo del umbral, la criatura queda sujeta al sesgo de territorio;
        por encima (hoy, solo gnomo: rango racial 0.6-0.9), se asume que su
        deambular puede reflejar decisiones no reducibles a "quedarse cerca
        de lo conocido" y se deja el paso aleatorio intacto. Es un mecanismo
        de gating GENERAL, no un caso especial de especie: el día que otra
        especie tenga consciencia alta, quedará exenta automáticamente sin
        tocar este código (leyes neutras, nunca teleológicas).

        Reutiliza nucleo.memoria.objetivo_recordado tal cual existe hoy
        (memoria, tipo, pos_x, pos_y, cap_mental, rng, config) -- misma
        función que usan ahora _calcular_forrajeo/_calcular_hidratacion más
        arriba en este archivo (corregidas el 2026-08-23, mismo cambio:
        llamaban a `mem.obtener_recuerdos(tipo)`, método que MemoriaEspacial
        nunca tuvo, seguido de una llamada a objetivo_recordado con una
        firma posicional que no coincidía con la real -- código muerto que
        habría crasheado en cuanto se alcanzara. Se detectó al escribir
        este método y se corrigió también allí, no solo aquí).
        """
        if (
            mem is not None
            and cap_mental is not None
            and cap_mental.consciencia < self.umbral_consciencia_agencia
        ):
            objetivo: tuple[int, int] | None = None
            mejor_dist: int | None = None
            for tipo_recuerdo in ("comida", "agua"):
                candidato = objetivo_recordado(
                    mem, tipo_recuerdo, pos_x, pos_y, cap_mental, self.rng, self.config
                )
                if candidato is None:
                    continue
                dist_candidato = abs(candidato[0] - pos_x) + abs(candidato[1] - pos_y)
                if mejor_dist is None or dist_candidato < mejor_dist:
                    objetivo = candidato
                    mejor_dist = dist_candidato

            if objetivo is not None and mejor_dist is not None and mejor_dist > self.dist_deseada_territorio:
                return self._acercarse_a(pos_x, pos_y, *objetivo)

        return self._paso_aleatorio()

    def _acercarse_a(self, ox: int, oy: int, tx: int, ty: int) -> tuple[int, int]:
        """Calcula el paso unitario Manhattan más directo hacia el objetivo."""
        dx = 0 if ox == tx else (1 if tx > ox else -1)
        dy = 0 if oy == ty else (1 if ty > oy else -1)
        if dx != 0 and dy != 0:
            return (dx, 0) if self.rng.random() < 0.5 else (0, dy)
        return dx, dy

    def _paso_aleatorio(self) -> tuple[int, int]:
        """Genera un paso unitario aleatorio en 4 direcciones ortogonales o espera."""
        return self.rng.choice([(0, 1), (0, -1), (1, 0), (-1, 0), (0, 0)])