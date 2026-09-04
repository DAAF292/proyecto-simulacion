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

from componentes.agarre import Agarre
from componentes.capacidad_mental import CapacidadMental
from componentes.construccion import Construccion
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Especie, Identidad
from componentes.intencion import Accion, Intencion
from componentes.memoria_espacial import MemoriaEspacial
from componentes.necesidades import Necesidades
from componentes.necromasa import Necromasa
from componentes.pool_fisico import PoolFisico
from componentes.posicion import Posicion
from componentes.temperamento import Temperamento
# Gestacion vive en su propio módulo (componentes/gestacion.py, ver su
# docstring) para no mezclar el rasgo fijo de por vida (Reproduccion) con
# el estado de un embarazo concreto.
from componentes.gestacion import Gestacion
from componentes.reproduccion import Reproduccion
from nucleo.agua import hay_agua_potable, profundidad_agua_potable
from nucleo.amenaza import posicion_amenaza_mas_cercana
from nucleo.armas import bono_ofensivo_arma, mayor_nivel_arma
from nucleo.asentamiento import asentamiento_de
from nucleo.conflicto import ResultadoDisputa, resolver_disputa
from nucleo.construccion import (
    construccion_propia,
    espacio_disponible_para_construir,
    huella_m2_para,
    objetivo_construccion_actual,
)
from nucleo.entidad import GestorEntidades, crear_construccion
from nucleo.memoria import objetivo_recordado
from nucleo.mundo import Mundo
from nucleo.percepcion import radio_efectivo_por_peso, radio_individual
from nucleo.relieve import costo_resistencia_por_pendiente, pendiente_maxima_transitable


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
        # Retenido como dict, no como escalar suelto, para pasarlo tal
        # cual a nucleo.relieve.costo_resistencia_por_pendiente() en
        # _aplicar_movimiento -- evita reimplementar inline la formula de
        # una funcion ya centralizada (mismo riesgo de divergencia que el
        # proyecto se advierte a si mismo en nucleo/percepcion.py y
        # nucleo/disposicion.py).
        self.cfg_relieve: dict[str, Any] = cfg_rel

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
        # Almacén de asentamiento -- ver nucleo/asentamiento.py y
        # nucleo/construccion.py:objetivo_construccion_actual.
        self.radio_cluster_asentamiento: int = int(
            self.config.get("asentamiento", {}).get("radio_cluster_celdas", 6)
        )
        # Conflicto por refugio ocupado -- ver nucleo/conflicto.py.
        self.config_conflicto: dict[str, Any] = self.config.get("conflicto", {})
        self.drenaje_seguridad_perdedor: float = float(
            self.config_conflicto.get("drenaje_seguridad_perdedor", 0.3)
        )
        self.drenaje_seguridad_enfrentamiento: float = float(
            self.config_conflicto.get("drenaje_seguridad_enfrentamiento", 0.2)
        )
        # Capacidad de construcción por celda -- ver
        # config/materiales.yaml sección construccion y
        # nucleo/construccion.py:espacio_disponible_para_construir.
        self.config_construccion: dict[str, Any] = self.config.get("construccion", {})
        # Armas primitivas v2 (2026-09-03, ver config/armas.yaml y
        # nucleo/armas.py): catalogo y recetas para calcular el componente
        # ofensivo del arma empunada en las disputas (nucleo/conflicto.py).
        self.config_armas: dict[str, Any] = self.config.get("armas", {})
        self.catalogo_materiales: dict[str, Any] = self.config.get("materiales", {})
        self.recetas_armas: list[dict[str, Any]] = self.config_armas.get("recetas", [])

        # Coste de forrajeo vs. beneficio -- ver docstring de
        # _calcular_caza.
        cfg_dep = self.config.get("depredacion", {})
        self.fraccion_minima_peso_presa: float = float(
            cfg_dep.get("fraccion_minima_peso_presa", 0.001)
        )
        self.peso_referencia_deteccion_plena: float = float(
            cfg_dep.get("peso_referencia_deteccion_plena", 0.1)
        )
        # (2026-09-04) umbral y bono de agresividad PROPIOS de la amenaza
        # -- ver el comentario de config/combate.yaml. Mismos valores que
        # usa el drenaje de seguridad en sistema_necesidades.py y el deseo
        # de empunar arma en sistema_decision.py -- una sola nocion de
        # amenaza en todo el motor.
        self.umbral_disposicion_amenaza: float = float(
            cfg_dep.get("umbral_amenaza_percibida", 0.65)
        )
        self.peso_agresividad_amenaza: float = float(
            cfg_dep.get("peso_agresividad_amenaza", 0.3)
        )

    def ejecutar(self, gestor: GestorEntidades, mundo: Mundo) -> None:
        """
        Ejecuta el paso de movimiento para todas las criaturas con Intencion y Posicion.
        """
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
            temperamento = gestor.obtener_componente(eid, Temperamento)

            if intencion is None or pos is None or dims is None or ident is None:
                continue

            # Zona resuelta POR ENTIDAD, no una unica variable fija a
            # zonas[0] -- dos entidades en la misma llamada a ejecutar()
            # pueden estar en zonas distintas (ver
            # componentes/posicion.py:zona_idx).
            zona = mundo.territorio.zonas[pos.zona_idx]

            # Bloqueo temporal por extenuación muscular extrema
            if pf is not None and pf.resistencia <= self.umbral_agotamiento:
                continue

            radio = radio_individual(dims.agudeza_sensorial, self.radio_min, self.radio_max)
            accion = intencion.accion

            dx, dy = 0, 0

            if accion == Accion.DORMIR:
                dx, dy = self._calcular_dormir(
                    gestor, mundo, eid, ident.especie, pos.x, pos.y, radio, mem, cap_mental,
                    temperamento, pos.zona_idx,
                )
            elif accion == Accion.HUIR:
                dx, dy = self._calcular_huida(
                    gestor, zona, eid, pos.x, pos.y, dims.peso, radio, pos.zona_idx
                )
            elif accion == Accion.CAZAR:
                dx, dy = self._calcular_caza(
                    gestor, eid, pos.x, pos.y, dims.peso, radio, pos.zona_idx
                )
            elif accion == Accion.COMER:
                dx, dy = self._calcular_forrajeo(
                    gestor, zona, ident.especie, pos.x, pos.y, radio, mem, cap_mental, pos.zona_idx
                )
            elif accion == Accion.BEBER:
                dx, dy = self._calcular_hidratacion(
                    zona, pos.x, pos.y, dims.altura, radio, mem, cap_mental
                )
            elif accion == Accion.BUSCAR_PAREJA:
                dx, dy = self._calcular_pareja(
                    gestor, eid, ident.especie, pos.x, pos.y, radio, pos.zona_idx
                )
            elif accion == Accion.CONSTRUIR:
                dx, dy = self._calcular_construir(gestor, mundo, eid, pos.x, pos.y, pos.zona_idx)
            elif accion == Accion.DEAMBULAR:
                dx, dy = self._calcular_deambular(
                    gestor, eid, ident.especie, pos.x, pos.y, radio, mem, cap_mental,
                    temperamento, pos.zona_idx,
                )
            elif accion == Accion.HUIDA_ERRATICA:
                dx, dy = self._calcular_huida_erratica(
                    gestor, eid, pos.x, pos.y, radio, pos.zona_idx
                )
            elif accion == Accion.CRISIS_VIOLENTA:
                dx, dy = self._calcular_crisis_violenta(
                    gestor, eid, pos.x, pos.y, radio, pos.zona_idx
                )
            # Accion.CATATONIA: sin rama a proposito, mismo criterio que
            # Accion.ALIVIARSE (arriba, tampoco tiene rama) -- dx=dy=0 por
            # defecto es literalmente la definicion de catatonia ("se
            # queda quieto, sin actuar", componentes/intencion.py), no un
            # descuido. Accion.RECOLECTAR y Accion.ENCENDER_FUEGO
            # tampoco tienen rama, mismo motivo: se resuelven donde ya se
            # está (sistemas/sistema_recursos.py), sin desplazamiento
            # propio.

            if dx != 0 or dy != 0:
                self._aplicar_movimiento(gestor, mundo, zona, eid, pos, dims, pf, dx, dy, accion)

    def _aplicar_movimiento(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
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

        # TRANSICION DE ZONA -- mecanismo de "portal", no una decision de
        # la Utility AI: pisar la celda de acceso es en si mismo el
        # cruce, igual que una escalera de Dwarf Fortress -- ninguna
        # especie necesita "elegir" bajar, es un rasgo fisico del terreno
        # (leyes neutras, nunca teleologicas -- principio 5). Se
        # comprueba ANTES de las restricciones de agua/relieve de mas
        # abajo porque son restricciones DE LA CELDA DE ORIGEN de esta
        # misma zona, no tienen sentido aplicadas al destino en otra
        # zona. territorio.accesos_subterraneos es una LISTA (una entrada
        # por cueva, ver nucleo/territorio.py:AccesoSubterraneo) --
        # busqueda lineal O(N) sobre un puñado de cuevas por mundo, mismo
        # limite de escalabilidad ya aceptado en el resto del motor a
        # esta escala.
        territorio = mundo.territorio
        if pos.zona_idx == 0:
            for acceso in territorio.accesos_subterraneos:
                if (nx, ny) == acceso.superficie:
                    pos.zona_idx = acceso.zona_idx
                    pos.x, pos.y = acceso.entrada
                    return
        else:
            for acceso in territorio.accesos_subterraneos:
                if pos.zona_idx == acceso.zona_idx and (nx, ny) == acceso.entrada:
                    pos.zona_idx = 0
                    pos.x, pos.y = acceso.superficie
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
                # Llama a la funcion centralizada de nucleo/relieve.py en
                # vez de reimplementar la misma formula inline -- coste
                # BRUTO devuelto por la funcion, dividido por
                # resistencia_maxima aqui (mismo criterio que
                # sistema_capacidad_fisica.py, documentado en el propio
                # docstring de costo_resistencia_por_pendiente).
                coste_total += costo_resistencia_por_pendiente(
                    celda_orig.elevacion, celda_dest.elevacion, self.cfg_relieve
                ) / max(0.1, dims.resistencia_maxima)
            # HUIDA_ERRATICA/CRISIS_VIOLENTA usan el mismo coste de
            # esfuerzo sostenido que CAZAR/HUIR: son fisicamente el mismo
            # tipo de movimiento urgente (correr en panico o embestir con
            # agresividad), no caminar tranquilo.
            if accion in (Accion.CAZAR, Accion.HUIR, Accion.HUIDA_ERRATICA, Accion.CRISIS_VIOLENTA):
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
        peso_propio: float,
        radio: int,
        zona_idx: int = 0,
    ) -> tuple[int, int]:
        """Calcula el vector opuesto a la amenaza más cercana percibida."""
        amenaza_pos = posicion_amenaza_mas_cercana(
            gestor, zona, entidad_id, pos_x, pos_y, radio,
            peso_propio, self.umbral_disposicion_amenaza, zona_idx=zona_idx,
            peso_agresividad_candidato=self.peso_agresividad_amenaza,
        )
        if amenaza_pos is None:
            return self._paso_aleatorio()

        ax, ay = amenaza_pos
        dx = 0 if ax == pos_x else (1 if pos_x > ax else -1)
        dy = 0 if ay == pos_y else (1 if pos_y > ay else -1)
        return dx, dy

    # HUIDA_ERRATICA y CRISIS_VIOLENTA (crisis mental,
    # sistema_decision.py) reaccionan a CUALQUIER entidad cercana, no a
    # una amenaza calculada por disposicion (a diferencia de HUIR arriba)
    # -- de ahi que necesiten su propia busqueda en vez de reutilizar
    # posicion_amenaza_mas_cercana.
    def _entidad_cercana_cualquiera(
        self,
        gestor: GestorEntidades,
        entidad_id: int,
        pos_x: int,
        pos_y: int,
        radio: int,
        zona_idx: int = 0,
    ) -> tuple[int, int] | None:
        """Posicion de la entidad con Posicion mas cercana dentro del
        radio, de CUALQUIER tipo (cualquier especie, criatura o
        necromasa), sin filtro de amenaza ni de disposicion por tamano
        -- una crisis mental no razona sobre quien es peligroso o presa,
        reacciona a la presencia en si."""
        mejor: tuple[int, int] | None = None
        mejor_dist = radio + 1
        for otro_id in gestor.entidades_con(Posicion):
            if otro_id == entidad_id:
                continue
            pos_o = gestor.obtener_componente(otro_id, Posicion)
            if pos_o is None or pos_o.zona_idx != zona_idx:
                continue
            dist = abs(pos_o.x - pos_x) + abs(pos_o.y - pos_y)
            if dist <= radio and dist < mejor_dist:
                mejor = (pos_o.x, pos_o.y)
                mejor_dist = dist
        return mejor

    def _calcular_huida_erratica(
        self,
        gestor: GestorEntidades,
        entidad_id: int,
        pos_x: int,
        pos_y: int,
        radio: int,
        zona_idx: int = 0,
    ) -> tuple[int, int]:
        """HUIDA_ERRATICA: huye de cualquiera cercano, sin evaluar si es
        una amenaza real (valentia baja ante la crisis, no ante un
        peligro concreto) -- mismo patron de direccion que
        _calcular_huida, sobre un objetivo encontrado por
        _entidad_cercana_cualquiera en vez de posicion_amenaza_mas_cercana."""
        objetivo = self._entidad_cercana_cualquiera(gestor, entidad_id, pos_x, pos_y, radio, zona_idx)
        if objetivo is None:
            return self._paso_aleatorio()
        ox, oy = objetivo
        dx = 0 if ox == pos_x else (1 if pos_x > ox else -1)
        dy = 0 if oy == pos_y else (1 if pos_y > oy else -1)
        return dx, dy

    def _calcular_crisis_violenta(
        self,
        gestor: GestorEntidades,
        entidad_id: int,
        pos_x: int,
        pos_y: int,
        radio: int,
        zona_idx: int = 0,
    ) -> tuple[int, int]:
        """CRISIS_VIOLENTA: se acerca a cualquiera cercano -- sin
        mecanica de dano todavia, deliberado (componentes/intencion.py):
        es un gesto de movimiento, no una resolucion de ataque. Captura
        real sigue exigiendo Intencion.CAZAR en sistema_depredacion.py,
        sin cambios aqui."""
        objetivo = self._entidad_cercana_cualquiera(gestor, entidad_id, pos_x, pos_y, radio, zona_idx)
        if objetivo is None:
            return self._paso_aleatorio()
        return self._acercarse_a(pos_x, pos_y, *objetivo)

    def _calcular_caza(
        self,
        gestor: GestorEntidades,
        cazador_id: int,
        pos_x: int,
        pos_y: int,
        peso_cazador: float,
        radio: int,
        zona_idx: int = 0,
    ) -> tuple[int, int]:
        """
        Avanza hacia la presa válida más cercana dentro del radio sensorial.

        Dos filtros de "presa válida", ambos PROVISIONALES:

        1. Viabilidad energética (fraccion_minima_peso_presa=0.001): una
           presa por debajo de ese porcentaje del peso del cazador no
           compensa el coste de perseguirla -- se descarta ANTES de
           caminar hacia ella, no solo al resolver el ataque. Elegido
           para no tocar ninguna de las cuatro especies actuales (el lobo
           más ligero, 60kg, exige solo 0.06kg -- muy por debajo de la
           ardilla más ligera, 0.3kg): salvaguarda para fauna futura
           mucho más pequeña, no un ajuste que deba notarse hoy. Se
           aplica también en sistema_depredacion.py:_es_presa_valida,
           para el caso en que coincidan en la misma celda por casualidad
           sin haber caminado el cazador hacia ella.

        2. Detectabilidad por tamaño absoluto (nucleo.percepcion.
           radio_efectivo_por_peso, peso_referencia_deteccion_plena=0.1kg):
           el radio de percepción no solo depende de la agudeza sensorial
           de quien mira, también del tamaño de lo mirado -- un objetivo
           por debajo del peso de referencia reduce el radio efectivo
           SOLO para esa búsqueda de presa, calculado por candidato (cada
           uno tiene su propio radio efectivo según su propio peso).
           0.1kg está por debajo de la ardilla (0.3-0.6kg), así que hoy
           este filtro no cambia nada observable, solo prepara el
           terreno para fauna mucho más pequeña.
        """
        peso_minimo_viable = peso_cazador * self.fraccion_minima_peso_presa
        presas = []
        for eid in gestor.entidades_con(Posicion, DimensionesFisicas):
            if eid == cazador_id:
                continue
            pos_p = gestor.obtener_componente(eid, Posicion)
            dims_p = gestor.obtener_componente(eid, DimensionesFisicas)
            if not (pos_p and dims_p) or pos_p.zona_idx != zona_idx:
                continue
            if dims_p.peso >= peso_cazador or dims_p.peso < peso_minimo_viable:
                continue
            dist = abs(pos_p.x - pos_x) + abs(pos_p.y - pos_y)
            radio_efectivo = radio_efectivo_por_peso(
                radio, dims_p.peso, self.peso_referencia_deteccion_plena
            )
            if dist <= radio_efectivo:
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
        zona_idx: int = 0,
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
            # Solo vale la pena viajar hasta aquí si queda tejido_blando
            # comestible -- un montón de hueso no es un objetivo de
            # forrajeo (mismo criterio que
            # sistema_recursos.py:_resolver_comer, que solo consume de
            # 'tejido_blando').
            if (
                pos_n and nec_comp and pos_n.zona_idx == zona_idx
                and nec_comp.masas.get("tejido_blando", 0.0) > 0.05
            ):
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
        zona_idx: int = 0,
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
            if pos_c is None or pos_c.zona_idx != zona_idx:
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

    def _buscar_conspecifico_mas_cercano(
        self,
        gestor: GestorEntidades,
        entidad_id: int,
        especie: Especie,
        pos_x: int,
        pos_y: int,
        radio: int,
        zona_idx: int = 0,
    ) -> tuple[int, int] | None:
        """
        Posición del individuo de la MISMA especie más cercano dentro del
        radio de percepción (cualquier sexo/edad -- a diferencia de
        _calcular_pareja, esto es agrupamiento social, no búsqueda de
        pareja reproductiva). None si no percibe ninguno. Mismo patrón de
        búsqueda lineal ya usado en _calcular_caza/_calcular_pareja de este
        archivo -- O(N) por individuo, límite conocido de escalabilidad
        si la población crece en órdenes de magnitud.
        """
        candidatos = []
        for eid in gestor.entidades_con(Identidad, Posicion):
            if eid == entidad_id:
                continue
            ident_c = gestor.obtener_componente(eid, Identidad)
            if ident_c is None or ident_c.especie != especie:
                continue
            pos_c = gestor.obtener_componente(eid, Posicion)
            if pos_c is None or pos_c.zona_idx != zona_idx:
                continue
            dist = abs(pos_c.x - pos_x) + abs(pos_c.y - pos_y)
            if dist <= radio:
                candidatos.append((dist, pos_c.x, pos_c.y))

        if not candidatos:
            return None
        candidatos.sort()
        _, cx, cy = candidatos[0]
        return (cx, cy)

    def _calcular_deambular(
        self,
        gestor: GestorEntidades,
        entidad_id: int,
        especie: Especie,
        pos_x: int,
        pos_y: int,
        radio: int,
        mem: MemoriaEspacial | None,
        cap_mental: CapacidadMental | None,
        temperamento: Temperamento | None,
        zona_idx: int = 0,
    ) -> tuple[int, int]:
        """
        Cascada de sesgos sobre el paso de dispersión, evaluados en este
        orden: SESGO DE TERRITORIO -> SESGO GREGARIO -> paso aleatorio.
        Territorio es el filtro PRIMARIO; gregario actúa como sesgo
        secundario, solo cuando el territorio no aplica (fauna consciente
        exenta, sin memoria todavía, o ya lo bastante cerca de lo
        conocido) -- coherente con la jerarquía tipo Maslow que ya
        gobierna el resto de la Utility AI (sistema_decision.py:
        seguridad/necesidades físicas por delante de lo social).

        SESGO DE TERRITORIO: sin objetivo activo (COMER/BEBER/CAZAR/HUIR/
        BUSCAR_PAREJA), una criatura no debería dispersarse sin rumbo si
        ya conoce dónde hay recursos -- eso es plausible para un
        individuo consciente que delibera (gnomo), pero no para fauna sin
        agencia: lo esperable en fauna real es permanecer dentro de su
        área de campeo (home range) en torno a comida/agua/seguridad
        conocidas, no vagar uniformemente. Gating por
        CapacidadMental.consciencia (decision.umbral_consciencia_agencia,
        PROVISIONAL): por debajo del umbral, la criatura queda sujeta al
        sesgo de territorio; por encima (hoy, solo gnomo: rango racial
        0.6-0.9), se asume que su deambular puede reflejar decisiones no
        reducibles a "quedarse cerca de lo conocido". Mecanismo de gating
        GENERAL, no un caso especial de especie: el día que otra especie
        tenga consciencia alta, quedará exenta automáticamente sin tocar
        este código (leyes neutras, nunca teleológicas). Reutiliza
        nucleo.memoria.objetivo_recordado.

        SESGO GREGARIO: con probabilidad = Temperamento.sociabilidad
        DIRECTA, sin escalar, la criatura busca al conspecífico más
        cercano en su radio de percepción y avanza hacia él si está a más
        de social.distancia_deseada_conspecifico. Sin gating por
        consciencia -- a diferencia del sesgo de territorio, el
        agrupamiento social es plausible tanto para gnomo como para el
        resto. Si la tirada de sociabilidad no dispara el sesgo, o no hay
        ningún conspecífico perceptible, se cae al paso aleatorio.
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

        if temperamento is not None and self.rng.random() < temperamento.sociabilidad:
            objetivo_conspecifico = self._buscar_conspecifico_mas_cercano(
                gestor, entidad_id, especie, pos_x, pos_y, radio, zona_idx
            )
            if objetivo_conspecifico is not None:
                dist = abs(objetivo_conspecifico[0] - pos_x) + abs(objetivo_conspecifico[1] - pos_y)
                if dist > self.dist_deseada_conspecifico:
                    return self._acercarse_a(pos_x, pos_y, *objetivo_conspecifico)

        return self._paso_aleatorio()

    def _calcular_dormir(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        entidad_id: int,
        especie: Especie,
        pos_x: int,
        pos_y: int,
        radio: int,
        mem: MemoriaEspacial | None,
        cap_mental: CapacidadMental | None,
        temperamento: Temperamento | None,
        zona_idx: int = 0,
    ) -> tuple[int, int]:
        """
        REFUGIO INSTINTIVO: buscar comodidad, seguridad, un entorno
        seguro con los tuyos -- el mismo impulso que la construcción
        consciente de refugio, pero sin depender de consciencia.

        Dos capas, en este orden, NINGUNA inventa memoria compartida:

        1. REFUGIO RECORDADO (individual): tipo de recuerdo nuevo
           "refugio" en MemoriaEspacial, misma maquinaria genérica que ya
           usan "comida"/"agua" (nucleo/memoria.py, sin cambios) -- se
           registra en sistema_necesidades.py cuando la criatura duerme
           sin amenaza cerca. Si hay uno conocido y no se está ya cerca,
           se camina hacia él.
        2. SIN refugio conocido todavía (individuos jóvenes, por
           ejemplo): se reutiliza el MISMO sesgo gregario que ya usa
           _calcular_deambular -- buscar al conspecífico más cercano con
           probabilidad = sociabilidad directa, sin escalar. No es
           "recordar el refugio de la manada", es "si no sé dónde dormir
           seguro, no duermo solo" -- el resultado práctico (una manada
           tiende a dormir agrupada porque ya se mueve junta por el mismo
           sesgo) emerge sin memoria compartida.

        Sin refugio conocido y sin conspecífico cerca (o sin sociabilidad
        que dispare el sesgo): se queda quieta, exactamente el
        comportamiento de siempre.

        Sin bono numérico añadido a propósito: el beneficio de dormir en
        refugio es puramente conductual -- una celda se recuerda como
        refugio precisamente porque no hubo amenaza la vez anterior, así
        que volver ahí ya reduce la exposición por definición, sin
        inventar un multiplicador nuevo sobre Necesidades.seguridad.
        """
        if mem is not None and cap_mental is not None:
            objetivo_refugio = objetivo_recordado(
                mem, "refugio", pos_x, pos_y, cap_mental, self.rng, self.config
            )
            if objetivo_refugio is not None:
                dist = abs(objetivo_refugio[0] - pos_x) + abs(objetivo_refugio[1] - pos_y)
                if dist > self.dist_deseada_territorio:
                    return self._acercarse_a(pos_x, pos_y, *objetivo_refugio)
                if temperamento is not None:
                    self._resolver_posible_intruso(
                        gestor, mundo, entidad_id, pos_x, pos_y, zona_idx, temperamento
                    )
                return (0, 0)

        if temperamento is not None and self.rng.random() < temperamento.sociabilidad:
            objetivo_conspecifico = self._buscar_conspecifico_mas_cercano(
                gestor, entidad_id, especie, pos_x, pos_y, radio, zona_idx
            )
            if objetivo_conspecifico is not None:
                dist = abs(objetivo_conspecifico[0] - pos_x) + abs(objetivo_conspecifico[1] - pos_y)
                if dist > self.dist_deseada_conspecifico:
                    return self._acercarse_a(pos_x, pos_y, *objetivo_conspecifico)

        return (0, 0)


    def _bono_arma_empunada(self, gestor: GestorEntidades, entidad_id: int) -> float:
        """Componente ofensivo del arma que esta entidad tiene empunada
        AHORA (Agarre.objetos), para el indice de asertividad social de
        nucleo/conflicto.py -- efecto_ofensivo_por_nivel[nivel] *
        agresividad del portador. 0 si no empuna nada o no tiene
        Temperamento/Agarre. Solo la empunadura cuenta (lo que este en
        Inventario sin sacar no intimida a nadie todavia); el componente
        base del arma deliberadamente no participa aqui (ver
        nucleo/conflicto.py:indice_asertividad_social)."""
        agarre = gestor.obtener_componente(entidad_id, Agarre)
        temp = gestor.obtener_componente(entidad_id, Temperamento)
        if agarre is None or temp is None:
            return 0.0
        nivel = mayor_nivel_arma(
            agarre.objetos, self.catalogo_materiales, self.recetas_armas
        )
        return bono_ofensivo_arma(nivel, temp.agresividad, self.config_armas)

    def _resolver_posible_intruso(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        propietario_id: int,
        pos_x: int,
        pos_y: int,
        zona_idx: int,
        temperamento: Temperamento,
    ) -> None:
        """
        CONFLICTO POR REFUGIO OCUPADO -- primer consumidor de
        nucleo/conflicto.py. Solo aplica a un refugio CONSTRUIDO propio y
        ya habitado alguna vez (Construccion real con
        completado_alguna_vez, no un punto de memoria instintivo sin
        dueño) -- un refugio instintivo es solo un sitio vacío recordado,
        no hay nada que "ocupar" en sentido de propiedad. Nada impide
        físicamente a otro gnomo o a un animal entrar (es una
        construcción sencilla, sin cerradura) -- esta función no capa esa
        posibilidad, solo le da consecuencia.

        zona_idx: "misma celda" no basta con comparar (x, y) -- con
        varias zonas (superficie + cuevas) dos entidades en zonas
        DISTINTAS pueden compartir coordenadas numéricas por pura
        coincidencia, mismo hallazgo que ya obligó a filtrar
        almacen_cercano/agrupar_por_proximidad por zona. Se filtra tanto
        la propia Construccion como cualquier candidato a intruso.

        No desplaza al intruso directamente: esta función resuelve el
        movimiento de UNA sola entidad por iteración (el propietario),
        no puede mover a otra desde aquí. La consecuencia de perder es
        un drenaje de Necesidades.seguridad -- el MISMO campo que ya
        drena cualquier amenaza (nucleo/amenaza.py) -- que sube la
        utilidad_huir del perdedor en su propia próxima decisión: el
        perdedor tiende a irse por su cuenta a través del mecanismo de
        huida ya existente, sin teletransportarlo desde aquí.
        """
        cid = construccion_propia(gestor, propietario_id, "refugio")
        if cid is None:
            return
        con_pos = gestor.obtener_componente(cid, Posicion)
        construccion = gestor.obtener_componente(cid, Construccion)
        if (
            con_pos is None
            or construccion is None
            or not construccion.completado_alguna_vez
            or con_pos.x != pos_x
            or con_pos.y != pos_y
            or con_pos.zona_idx != zona_idx
        ):
            return

        intruso_id: int | None = None
        for otro_id in gestor.entidades_con(Posicion, Temperamento, Identidad):
            if otro_id == propietario_id:
                continue
            pos_otro = gestor.obtener_componente(otro_id, Posicion)
            if (
                pos_otro is not None
                and pos_otro.x == pos_x
                and pos_otro.y == pos_y
                and pos_otro.zona_idx == zona_idx
            ):
                intruso_id = otro_id
                break
        if intruso_id is None:
            return

        temperamento_intruso = gestor.obtener_componente(intruso_id, Temperamento)
        if temperamento_intruso is None:
            return

        nec_propietario = gestor.obtener_componente(propietario_id, Necesidades)
        nec_intruso = gestor.obtener_componente(intruso_id, Necesidades)
        urgencia_propietario = 1.0 - (nec_propietario.seguridad if nec_propietario else 1.0)
        urgencia_intruso = 1.0 - (nec_intruso.seguridad if nec_intruso else 1.0)

        asen_propietario = asentamiento_de(mundo, propietario_id)
        mismo_grupo = asen_propietario is not None and intruso_id in asen_propietario.miembros

        # Armas primitivas v2 (2026-09-03, ver nucleo/armas.py): el
        # componente ofensivo del arma EMPUÑADA de cada parte se suma al
        # índice de asertividad de quien la porte -- primer consumidor
        # real de robo/agravio genérico para nucleo/conflicto.py. Quien
        # sujeta el refugio con un hacha_primitiva en la mano se impone
        # más; la ley es neutra, el arma no impone un carácter, modula la
        # magnitud de la disputa.
        bono_arma_propietario = self._bono_arma_empunada(gestor, propietario_id)
        bono_arma_intruso = self._bono_arma_empunada(gestor, intruso_id)

        resultado = resolver_disputa(
            temperamento,
            urgencia_propietario,
            temperamento_intruso,
            urgencia_intruso,
            mismo_grupo,
            self.config_conflicto,
            bono_arma_a=bono_arma_propietario,
            bono_arma_b=bono_arma_intruso,
        )

        if resultado == ResultadoDisputa.COMPARTE:
            return
        if resultado == ResultadoDisputa.CEDE_B:
            # El intruso cede: el propietario se impone, el intruso paga
            # el coste de la intimidación.
            if nec_intruso is not None:
                nec_intruso.seguridad = max(
                    0.0, nec_intruso.seguridad - self.drenaje_seguridad_perdedor
                )
            return
        if resultado == ResultadoDisputa.CEDE_A:
            # El propietario cede en su propio refugio: paga el coste,
            # no lo reclama de verdad este tick.
            if nec_propietario is not None:
                nec_propietario.seguridad = max(
                    0.0, nec_propietario.seguridad - self.drenaje_seguridad_perdedor
                )
            return
        # ENFRENTAMIENTO: empate reñido entre dos partes asertivas,
        # ambos pagan el coste del enfrentamiento.
        if nec_propietario is not None:
            nec_propietario.seguridad = max(
                0.0, nec_propietario.seguridad - self.drenaje_seguridad_enfrentamiento
            )
        if nec_intruso is not None:
            nec_intruso.seguridad = max(
                0.0, nec_intruso.seguridad - self.drenaje_seguridad_enfrentamiento
            )

    def _calcular_construir(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        entidad_id: int,
        pos_x: int,
        pos_y: int,
        zona_idx: int = 0,
    ) -> tuple[int, int]:
        """
        REFUGIO/ALMACÉN CONSTRUIDO (ver componentes/construccion.py,
        nucleo/construccion.py, nucleo/asentamiento.py). Localiza el
        objetivo de construcción actual de esta entidad
        (objetivo_construccion_actual: refugio propio mientras no esté
        terminado, si no el almacén del asentamiento del que sea
        miembro). Si no existe todavía, lo crea: el refugio en la
        posición ACTUAL de quien construye (sin lógica de selección de
        sitio, esa pregunta sigue abierta); el almacén en el CENTRO del
        asentamiento -- hay que llegar hasta ahí primero, no se crea
        donde a cada gnomo le pille. Una vez existe, camina hacia él
        igual que _calcular_dormir camina hacia el refugio recordado.

        CAPACIDAD POR CELDA (ver config/materiales.yaml sección
        construccion y nucleo/construccion.py:
        espacio_disponible_para_construir): antes de crear una
        Construccion nueva se comprueba que su huella_m2 quepa en el
        espacio libre de la celda -- si no cabe, no se crea este tick.
        Deliberadamente sin ninguna búsqueda de una celda vecina con
        hueco: el individuo simplemente lo reintentará en su próxima
        posición según el resto de su comportamiento (sesgo gregario,
        deambular) ya lo mueva. Para el almacén esto puede significar
        quedarse parado en el centro del asentamiento sin poder construir
        si esa celda exacta está llena -- límite conocido, no resuelto
        aquí (ver CLAUDE.md).

        La transferencia real de materiales (Inventario ->
        Construccion.materiales) NO ocurre aquí -- sistema_recursos.py la
        resuelve una vez la entidad está en la misma celda, mismo reparto
        de responsabilidades que COMER/BEBER (este sistema decide hacia
        dónde ir, sistema_recursos.py decide qué pasa al llegar).
        """
        objetivo = objetivo_construccion_actual(
            gestor, mundo, entidad_id, self.radio_cluster_asentamiento
        )
        if objetivo is None:
            return (0, 0)
        tipo, cid, pos_creacion = objetivo

        if cid is not None:
            con_pos = gestor.obtener_componente(cid, Posicion)
            if con_pos is None or (con_pos.x == pos_x and con_pos.y == pos_y):
                return (0, 0)
            return self._acercarse_a(pos_x, pos_y, con_pos.x, con_pos.y)

        if tipo == "refugio":
            if espacio_disponible_para_construir(
                gestor, pos_x, pos_y, zona_idx, self.config
            ) < huella_m2_para("refugio", self.config_construccion):
                return (0, 0)
            crear_construccion(
                gestor, pos_x, pos_y, "refugio", propietario_id=entidad_id, zona_idx=zona_idx
            )
            return (0, 0)

        # almacén, todavía no existe: hay que llegar al centro del
        # asentamiento antes de poder crearlo.
        cx, cy = pos_creacion
        if (cx, cy) != (pos_x, pos_y):
            return self._acercarse_a(pos_x, pos_y, cx, cy)
        if espacio_disponible_para_construir(
            gestor, pos_x, pos_y, zona_idx, self.config
        ) < huella_m2_para("almacen", self.config_construccion):
            return (0, 0)
        crear_construccion(gestor, pos_x, pos_y, "almacen", propietario_id=None, zona_idx=zona_idx)
        return (0, 0)

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