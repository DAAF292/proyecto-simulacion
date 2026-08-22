"""
sistemas/sistema_movimiento.py

Sistema de cinemática y traslación espacial (Fase 2: Acción y Contacto Físico).
Gestiona el desplazamiento de entidades en el grid según su Intencion,
resolviendo percepción directa, memoria espacial y deambulación, aplicando
filtros de relieve, impasibilidad por agua profunda y drenaje de resistencia
por esfuerzo físico sostenido (sprint en caza/huida y ascenso en pendiente).
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
from componentes.planta import Planta
from componentes.pool_fisico import PoolFisico
from componentes.posicion import Posicion
from componentes.reproduccion import Reproduccion, Sexo
from nucleo.agua import hay_agua_potable, profundidad_agua_potable
from nucleo.amenaza import posicion_amenaza_mas_cercana
from nucleo.bioma import TipoTerreno
from nucleo.disposicion import id_presa_mas_cercana
from nucleo.entidad import GestorEntidades
from nucleo.memoria import (
    capacidad_memoria,
    objetivo_recordado,
    purgar_recuerdo_invalido,
    registrar_recuerdo,
)
from nucleo.mundo import Mundo
from nucleo.percepcion import radio_individual
from nucleo.relieve import pendiente_maxima_transitable


class SistemaMovimiento:
    """
    Ejecuta el movimiento de entidades vivas aplicando cinemática,
    restricciones topográficas y fricción por gasto de resistencia física.
    """

    def __init__(self, config: dict[str, Any], rng: random.Random) -> None:
        self.config = config
        self.rng = rng
        self._cachear_configuracion()

    def _cachear_configuracion(self) -> None:
        """Extrae y tipa los coeficientes cinemáticos y de esfuerzo."""
        cfg_mov = self.config.get("movimiento", {})
        self.coste_resistencia_pendiente: float = float(
            cfg_mov.get("coste_resistencia_pendiente", 0.05)
        )
        self.coste_resistencia_sprint: float = float(
            cfg_mov.get("coste_resistencia_sprint", 0.08)
        )
        self.umbral_resistencia_agotamiento: float = float(
            cfg_mov.get("umbral_resistencia_agotamiento", 0.05)
        )

        cfg_dep = self.config.get("depredacion", {})
        self.umbral_disposicion_caza: float = float(
            cfg_dep.get("umbral_disposicion_caza", 0.5)
        )

        # Mapeo de dietas por especie
        cfg_flora = self.config.get("flora", {}).get("especies", {})
        self.dietas_especie: dict[str, list[str]] = {}
        for esp_nombre, esp_datos in cfg_flora.items():
            pass  # El filtrado se consulta por especie de criatura

        cfg_especies = self.config.get("rangos_raciales", {})
        self.dietas_criatura: dict[str, list[str]] = {
            esp: datos.get("dieta", [])
            for esp, datos in cfg_especies.items()
        }

    def ejecutar(self, gestor: GestorEntidades, mundo: Mundo) -> None:
        """
        Ejecuta el desplazamiento de todas las entidades con Posición e Intención.
        Debe ejecutarse en la Fase 2 del tick, posterior a SistemaDecision.
        """
        zona = mundo.territorio.zonas[0]
        entidades = sorted(gestor.entidades_con(Posicion, Intencion))

        for entidad_id in entidades:
            pos = gestor.obtener_componente(entidad_id, Posicion)
            intencion = gestor.obtener_componente(entidad_id, Intencion)
            dims = gestor.obtener_componente(entidad_id, DimensionesFisicas)
            pool_fisico = gestor.obtener_componente(entidad_id, PoolFisico)
            identidad = gestor.obtener_componente(entidad_id, Identidad)
            memoria_comp = gestor.obtener_componente(entidad_id, MemoriaEspacial)
            cap_mental = gestor.obtener_componente(entidad_id, CapacidadMental)

            if pos is None or intencion is None or dims is None or pool_fisico is None:
                continue

            if intencion.accion == Accion.DORMIR:
                continue

            # Determinación de si la acción implica esfuerzo anaeróbico (sprint)
            es_sprint = intencion.accion in (Accion.CAZAR, Accion.HUIR)

            # Si está extenuado, no puede realizar acciones de alta exigencia física
            if es_sprint and pool_fisico.resistencia <= self.umbral_resistencia_agotamiento:
                continue

            radio = radio_individual(dims, self.config)
            especie_str = identidad.especie.value if identidad else ""
            dieta = self.dietas_criatura.get(especie_str, [])

            if intencion.accion == Accion.COMER:
                self._procesar_comer(
                    gestor, zona, entidad_id, pos, dims, pool_fisico,
                    radio, dieta, memoria_comp, cap_mental, es_sprint
                )
            elif intencion.accion == Accion.BEBER:
                self._procesar_beber(
                    zona, entidad_id, pos, dims, pool_fisico,
                    radio, memoria_comp, cap_mental, es_sprint
                )
            elif intencion.accion == Accion.CAZAR:
                self._procesar_cazar(
                    gestor, zona, entidad_id, pos, dims, pool_fisico,
                    radio, es_sprint
                )
            elif intencion.accion == Accion.HUIR:
                self._procesar_huir(
                    gestor, zona, entidad_id, pos, dims, pool_fisico,
                    radio, es_sprint
                )
            elif intencion.accion == Accion.BUSCAR_PAREJA:
                self._procesar_buscar_pareja(
                    gestor, zona, entidad_id, pos, dims, pool_fisico,
                    radio, es_sprint
                )
            elif intencion.accion == Accion.DEAMBULAR:
                self._deambular(zona, pos, dims, pool_fisico, es_sprint=False)

    def _procesar_comer(
        self,
        gestor: GestorEntidades,
        zona: Any,
        entidad_id: int,
        pos: Posicion,
        dims: DimensionesFisicas,
        pool: PoolFisico,
        radio: int,
        dieta: list[str],
        memoria_comp: MemoriaEspacial | None,
        cap_mental: CapacidadMental | None,
        es_sprint: bool,
    ) -> None:
        """Resuelve la aproximación a alimento mediante percepción, memoria o deambulación."""
        celda_actual = zona.obtener_celda(pos.x, pos.y)
        if self._tiene_alimento_valido(celda_actual, dieta):
            if memoria_comp is not None and cap_mental is not None:
                cap = capacidad_memoria(cap_mental, self.config)
                registrar_recuerdo(memoria_comp, "comida", pos.x, pos.y, cap)
            return

        # 1. Percepción directa
        obj_percibido = self._buscar_alimento_en_radio(zona, pos, radio, dieta)
        if obj_percibido is not None:
            self._mover_hacia(zona, pos, dims, pool, obj_percibido[0], obj_percibido[1], es_sprint)
            return

        # 2. Memoria espacial
        if memoria_comp is not None and cap_mental is not None and memoria_comp.recuerdos.get("comida"):
            obj_mem = objetivo_recordado(memoria_comp, "comida", pos.x, pos.y, cap_mental, self.rng, self.config)
            if obj_mem is not None:
                # Si llegó a la celda recordada y ya no hay comida, purgar recuerdo
                if pos.x == obj_mem[0] and pos.y == obj_mem[1]:
                    purgar_recuerdo_invalido(memoria_comp, "comida", pos.x, pos.y)
                else:
                    self._mover_hacia(zona, pos, dims, pool, obj_mem[0], obj_mem[1], es_sprint)
                    return

        # 3. Deambulación
        self._deambular(zona, pos, dims, pool, es_sprint=False)

    def _procesar_beber(
        self,
        zona: Any,
        entidad_id: int,
        pos: Posicion,
        dims: DimensionesFisicas,
        pool: PoolFisico,
        radio: int,
        memoria_comp: MemoriaEspacial | None,
        cap_mental: CapacidadMental | None,
        es_sprint: bool,
    ) -> None:
        """Resuelve la aproximación a fuentes de agua potable."""
        celda_actual = zona.obtener_celda(pos.x, pos.y)
        if hay_agua_potable(celda_actual):
            if memoria_comp is not None and cap_mental is not None:
                cap = capacidad_memoria(cap_mental, self.config)
                registrar_recuerdo(memoria_comp, "agua", pos.x, pos.y, cap)
            return

        obj_percibido = self._buscar_agua_en_radio(zona, pos, radio, dims.altura)
        if obj_percibido is not None:
            self._mover_hacia(zona, pos, dims, pool, obj_percibido[0], obj_percibido[1], es_sprint)
            return

        if memoria_comp is not None and cap_mental is not None and memoria_comp.recuerdos.get("agua"):
            obj_mem = objetivo_recordado(memoria_comp, "agua", pos.x, pos.y, cap_mental, self.rng, self.config)
            if obj_mem is not None:
                if pos.x == obj_mem[0] and pos.y == obj_mem[1]:
                    purgar_recuerdo_invalido(memoria_comp, "agua", pos.x, pos.y)
                else:
                    self._mover_hacia(zona, pos, dims, pool, obj_mem[0], obj_mem[1], es_sprint)
                    return

        self._deambular(zona, pos, dims, pool, es_sprint=False)

    def _procesar_cazar(
        self,
        gestor: GestorEntidades,
        zona: Any,
        entidad_id: int,
        pos: Posicion,
        dims: DimensionesFisicas,
        pool: PoolFisico,
        radio: int,
        es_sprint: bool,
    ) -> None:
        """Persigue a la presa más cercana dentro del radio perceptual."""
        id_presa = id_presa_mas_cercana(
            gestor, entidad_id, radio, self.umbral_disposicion_caza
        )
        if id_presa is not None:
            pos_presa = gestor.obtener_componente(id_presa, Posicion)
            if pos_presa is not None:
                self._mover_hacia(zona, pos, dims, pool, pos_presa.x, pos_presa.y, es_sprint)
                return

        self._deambular(zona, pos, dims, pool, es_sprint=False)

    def _procesar_huir(
        self,
        gestor: GestorEntidades,
        zona: Any,
        entidad_id: int,
        pos: Posicion,
        dims: DimensionesFisicas,
        pool: PoolFisico,
        radio: int,
        es_sprint: bool,
    ) -> None:
        """Se aleja de la amenaza directa más cercana."""
        amenaza_pos = posicion_amenaza_mas_cercana(
            gestor, zona, entidad_id, radio, self.umbral_disposicion_caza
        )
        if amenaza_pos is not None:
            self._huir_de(zona, pos, dims, pool, amenaza_pos[0], amenaza_pos[1], es_sprint)
            return

        self._deambular(zona, pos, dims, pool, es_sprint=False)

    def _procesar_buscar_pareja(
        self,
        gestor: GestorEntidades,
        zona: Any,
        entidad_id: int,
        pos: Posicion,
        dims: DimensionesFisicas,
        pool: PoolFisico,
        radio: int,
        es_sprint: bool,
    ) -> None:
        """Aproxima a un individuo compatible de su misma especie para cortejo/reproducción."""
        pos_pareja = self._buscar_pareja_en_radio(gestor, entidad_id, pos, radio)
        if pos_pareja is not None:
            self._mover_hacia(zona, pos, dims, pool, pos_pareja[0], pos_pareja[1], es_sprint)
            return

        self._deambular(zona, pos, dims, pool, es_sprint=False)

    def _mover_hacia(
        self,
        zona: Any,
        pos: Posicion,
        dims: DimensionesFisicas,
        pool: PoolFisico,
        obj_x: int,
        obj_y: int,
        es_sprint: bool,
    ) -> None:
        """Calcula el paso Manhattan óptimo hacia el objetivo."""
        dx = obj_x - pos.x
        dy = obj_y - pos.y

        pasos_candidatos: list[tuple[int, int]] = []
        if abs(dx) >= abs(dy):
            if dx != 0:
                pasos_candidatos.append((1 if dx > 0 else -1, 0))
            if dy != 0:
                pasos_candidatos.append((0, 1 if dy > 0 else -1))
        else:
            if dy != 0:
                pasos_candidatos.append((0, 1 if dy > 0 else -1))
            if dx != 0:
                pasos_candidatos.append((1 if dx > 0 else -1, 0))

        for step_x, step_y in pasos_candidatos:
            if self._mover_si_posible(zona, pos, dims, pool, pos.x + step_x, pos.y + step_y, es_sprint):
                return

    def _huir_de(
        self,
        zona: Any,
        pos: Posicion,
        dims: DimensionesFisicas,
        pool: PoolFisico,
        amenaza_x: int,
        amenaza_y: int,
        es_sprint: bool,
    ) -> None:
        """Calcula el paso Manhattan que maximiza la distancia respecto a la amenaza."""
        dx = pos.x - amenaza_x
        dy = pos.y - amenaza_y

        candidatos = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        # Ordenar priorizando mayor incremento de distancia euclídea/Manhattan
        candidatos.sort(
            key=lambda c: (pos.x + c[0] - amenaza_x) ** 2 + (pos.y + c[1] - amenaza_y) ** 2,
            reverse=True,
        )

        for step_x, step_y in candidatos:
            if self._mover_si_posible(zona, pos, dims, pool, pos.x + step_x, pos.y + step_y, es_sprint):
                return

    def _deambular(
        self,
        zona: Any,
        pos: Posicion,
        dims: DimensionesFisicas,
        pool: PoolFisico,
        es_sprint: bool = False,
    ) -> None:
        """Paso aleatorio no dirigido que evita cuerpos de agua que excedan la altura corporal."""
        direcciones = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        self.rng.shuffle(direcciones)

        for dx, dy in direcciones:
            dest_x, dest_y = pos.x + dx, pos.y + dy
            if 0 <= dest_x < zona.ancho and 0 <= dest_y < zona.alto:
                celda_dest = zona.obtener_celda(dest_x, dest_y)
                if profundidad_agua_potable(celda_dest) <= dims.altura:
                    if self._mover_si_posible(zona, pos, dims, pool, dest_x, dest_y, es_sprint):
                        return

    def _mover_si_posible(
        self,
        zona: Any,
        pos: Posicion,
        dims: DimensionesFisicas,
        pool: PoolFisico,
        dest_x: int,
        dest_y: int,
        es_sprint: bool,
    ) -> bool:
        """
        Filtro cinemático unificado:
          1. Valida límites del mapa.
          2. Bloquea celdas inundadas que excedan la altura de la entidad.
          3. Valida pendiente máxima según Fuerza física.
          4. Aplica drenaje de Resistencia por sprint y desnivel.
          5. Ejecuta la traslación espacial si hay suficiencia física.
        """
        if not (0 <= dest_x < zona.ancho and 0 <= dest_y < zona.alto):
            return False

        celda_origen = zona.obtener_celda(pos.x, pos.y)
        celda_dest = zona.obtener_celda(dest_x, dest_y)

        # Restricción de agua profunda (asfixia)
        prof_agua = profundidad_agua_potable(celda_dest)
        if prof_agua > dims.altura:
            prof_origen = profundidad_agua_potable(celda_origen)
            # Solo permite moverse si ya estaba dentro, para facilitar la salida
            if prof_agua >= prof_origen:
                return False

        # Restricción biomecánica de relieve y gravedad
        delta_elev = celda_dest.elevacion - celda_origen.elevacion
        pend_max = pendiente_maxima_transitable(dims, self.config)

        if delta_elev > pend_max:
            return False

        # Cálculo de fricción y gasto de energía muscular (PoolFisico.resistencia)
        coste_total = 0.0

        if es_sprint:
            coste_total += self.coste_resistencia_sprint

        if delta_elev > 0.0:
            fraccion_pendiente = delta_elev / pend_max if pend_max > 0.0 else 1.0
            coste_total += fraccion_pendiente * self.coste_resistencia_pendiente

        if coste_total > 0.0:
            # Drenaje escalado a la resistencia máxima individual
            drenaje_neto = coste_total * dims.resistencia_maxima
            pool.resistencia = max(0.0, pool.resistencia - drenaje_neto)

        # Traslación efectiva
        pos.x = dest_x
        pos.y = dest_y
        return True

    def _tiene_alimento_valido(self, celda: Any, dieta: list[str]) -> bool:
        """Verifica si la celda contiene biomasa comestible aceptada por la dieta."""
        if not celda.recursos:
            return False
        if not dieta:  # Dieta omnívora irrestricta (ej. Gnomo)
            return any(cant > 0.0 for cant in celda.recursos.values())
        return any(celda.recursos.get(rec, 0.0) > 0.0 for rec in dieta)

    def _buscar_alimento_en_radio(
        self, zona: Any, pos: Posicion, radio: int, dieta: list[str]
    ) -> tuple[int, int] | None:
        """Localiza la celda con alimento más cercana dentro de la envolvente sensorial."""
        mejor_pos: tuple[int, int] | None = None
        menor_dist = float("inf")

        for dy in range(-radio, radio + 1):
            for dx in range(-radio, radio + 1):
                nx, ny = pos.x + dx, pos.y + dy
                if 0 <= nx < zona.ancho and 0 <= ny < zona.alto:
                    dist = abs(dx) + abs(dy)
                    if dist <= radio and dist < menor_dist:
                        celda = zona.obtener_celda(nx, ny)
                        if self._tiene_alimento_valido(celda, dieta):
                            menor_dist = dist
                            mejor_pos = (nx, ny)
        return mejor_pos

    def _buscar_agua_en_radio(
        self, zona: Any, pos: Posicion, radio: int, altura: float
    ) -> tuple[int, int] | None:
        """Localiza la fuente de agua potable vadeable más cercana en el radio."""
        mejor_pos: tuple[int, int] | None = None
        menor_dist = float("inf")

        for dy in range(-radio, radio + 1):
            for dx in range(-radio, radio + 1):
                nx, ny = pos.x + dx, pos.y + dy
                if 0 <= nx < zona.ancho and 0 <= ny < zona.alto:
                    dist = abs(dx) + abs(dy)
                    if dist <= radio and dist < menor_dist:
                        celda = zona.obtener_celda(nx, ny)
                        if hay_agua_potable(celda) and profundidad_agua_potable(celda) <= altura:
                            menor_dist = dist
                            mejor_pos = (nx, ny)
        return mejor_pos

    def _buscar_pareja_en_radio(
        self, gestor: GestorEntidades, entidad_id: int, pos: Posicion, radio: int
    ) -> tuple[int, int] | None:
        """Localiza al consorte potencial coespecífico más próximo."""
        mi_identidad = gestor.obtener_componente(entidad_id, Identidad)
        mi_repro = gestor.obtener_componente(entidad_id, Reproduccion)
        if mi_identidad is None or mi_repro is None:
            return None

        mejor_pos: tuple[int, int] | None = None
        menor_dist = float("inf")

        for otra_id in gestor.entidades_con(Posicion, Identidad, Reproduccion):
            if otra_id == entidad_id:
                continue
            otra_identidad = gestor.obtener_componente(otra_id, Identidad)
            otra_repro = gestor.obtener_componente(otra_id, Reproduccion)
            otra_pos = gestor.obtener_componente(otra_id, Posicion)

            if (
                otra_identidad is not None
                and otra_repro is not None
                and otra_pos is not None
                and otra_identidad.especie == mi_identidad.especie
                and otra_repro.sexo != mi_repro.sexo
            ):
                dist = abs(otra_pos.x - pos.x) + abs(otra_pos.y - pos.y)
                if dist <= radio and dist < menor_dist:
                    menor_dist = dist
                    mejor_pos = (otra_pos.x, otra_pos.y)

        return mejor_pos