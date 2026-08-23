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
from componentes.temperamento import Temperamento
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
from nucleo.percepcion import radio_efectivo_por_peso, radio_individual
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

        # Coste de forrajeo vs. beneficio (2026-08-23, pregunta de Diego:
        # "un lobo intenta depredar una mosca si se introduce" -- ver
        # docstring de _calcular_caza para el diagnóstico completo).
        cfg_dep = self.config.get("depredacion", {})
        self.fraccion_minima_peso_presa: float = float(
            cfg_dep.get("fraccion_minima_peso_presa", 0.001)
        )
        self.peso_referencia_deteccion_plena: float = float(
            cfg_dep.get("peso_referencia_deteccion_plena", 0.1)
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
            temperamento = gestor.obtener_componente(eid, Temperamento)

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
                    gestor, eid, ident.especie, pos.x, pos.y, radio, mem, cap_mental, temperamento
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
        """
        Avanza hacia la presa válida más cercana dentro del radio sensorial.

        DOS FILTROS AÑADIDOS (2026-08-23, pregunta de Diego: "un lobo
        intenta depredar una mosca si se introduce" -- confirmado real:
        antes de este cambio, la única condición para ser "presa válida"
        aquí era peso_p < peso_cazador, sin ningún suelo. sistema_
        depredacion.py:_es_presa_valida sí tenía un umbral de disposición,
        pero esa magnitud CRECE sin techo cuanto más pequeña es la presa
        -- una mosca frente a un lobo lo habría superado con más margen
        que un conejo, exactamente al revés de lo que hace falta).

        1. Viabilidad energética (fraccion_minima_peso_presa, PROVISIONAL
           =0.001): una presa por debajo de ese porcentaje del peso del
           cazador no compensa el coste de perseguirla -- se descarta
           ANTES de caminar hacia ella, no solo al resolver el ataque.
           Elegido para no tocar ninguna de las cuatro especies actuales
           (el lobo más ligero, 60kg, exige solo 0.06kg -- muy por debajo
           de la ardilla más ligera, 0.3kg): esto es una salvaguarda para
           fauna futura mucho más pequeña, no un ajuste que deba notarse
           hoy. Se aplica también en sistema_depredacion.py:
           _es_presa_valida, para el caso en que coincidan en la misma
           celda por casualidad sin haber caminado el cazador hacia ella.

        2. Detectabilidad por tamaño absoluto (nucleo.percepcion.
           radio_efectivo_por_peso, peso_referencia_deteccion_plena
           PROVISIONAL=0.1kg): el radio de percepción hasta hoy solo
           dependía de la agudeza sensorial de quien mira, nunca del
           tamaño de lo mirado -- una mosca y un gnomo eran igual de
           fáciles de detectar a la misma distancia. Un objetivo por
           debajo del peso de referencia reduce el radio efectivo SOLO
           para esa búsqueda de presa, calculado por candidato (cada uno
           tiene su propio radio efectivo según su propio peso). Mismo
           criterio de no tocar a las especies actuales: 0.1kg está por
           debajo de la ardilla (0.3-0.6kg), así que hoy este filtro no
           cambia nada observable, solo prepara el terreno para fauna
           mucho más pequeña.

        Ninguno de los dos umbrales se ha calibrado con el harness
        completo -- ver commit para el barrido de verificación de que,
        en efecto, no perturban la dinámica poblacional de hoy.
        """
        peso_minimo_viable = peso_cazador * self.fraccion_minima_peso_presa
        presas = []
        for eid in gestor.entidades_con(Posicion, DimensionesFisicas):
            if eid == cazador_id:
                continue
            pos_p = gestor.obtener_componente(eid, Posicion)
            dims_p = gestor.obtener_componente(eid, DimensionesFisicas)
            if not (pos_p and dims_p):
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

    def _buscar_conspecifico_mas_cercano(
        self,
        gestor: GestorEntidades,
        entidad_id: int,
        especie: Especie,
        pos_x: int,
        pos_y: int,
        radio: int,
    ) -> tuple[int, int] | None:
        """
        Posición del individuo de la MISMA especie más cercano dentro del
        radio de percepción (cualquier sexo/edad -- a diferencia de
        _calcular_pareja, esto es agrupamiento social, no búsqueda de
        pareja reproductiva). None si no percibe ninguno. Mismo patrón de
        búsqueda lineal ya usado en _calcular_caza/_calcular_pareja de este
        archivo -- O(N) por individuo, aceptable a la escala de población
        actual (decenas de individuos), señalado como límite conocido de
        escalabilidad si la población crece en órdenes de magnitud.
        """
        candidatos = []
        for eid in gestor.entidades_con(Identidad, Posicion):
            if eid == entidad_id:
                continue
            ident_c = gestor.obtener_componente(eid, Identidad)
            if ident_c is None or ident_c.especie != especie:
                continue
            pos_c = gestor.obtener_componente(eid, Posicion)
            if pos_c is None:
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
    ) -> tuple[int, int]:
        """
        Cascada de sesgos sobre el paso de dispersión, evaluados en este
        orden: SESGO DE TERRITORIO -> SESGO GREGARIO -> paso aleatorio.

        ORDEN INVERTIDO (2026-08-23, decisión de Diego): la primera
        versión de esta cascada (misma tarde de hoy) probaba el gregario
        primero, por una reconstrucción razonada mía sin respaldo directo
        de Diego -- ver commit anterior. Consultado explícitamente sobre
        cuál debía ir primero, Diego no tenía un criterio cerrado pero
        señaló el norte del proyecto: "nuestra atención es crear la
        simulación lo más apegada a la realidad". Bajo ese criterio, la
        fidelidad al área de campeo (sitio conocido con comida/agua/
        seguridad) es el instinto más fuerte y mejor documentado en fauna
        real -- un animal no abandona su territorio conocido por
        aproximarse a un congénere de paso; el agrupamiento social real
        ocurre DENTRO del área de campeo compartida, no en lugar de ella.
        Además, invertir el orden hace esta cascada consistente con la
        jerarquía tipo Maslow que ya gobierna el resto de la Utility AI
        (sistema_decision.py: seguridad/necesidades físicas por delante de
        lo social) en vez de contradecirla en el único punto donde no se
        aplicaba. Territorio ahora es el filtro PRIMARIO; gregario actúa
        como sesgo secundario, solo cuando el territorio no aplica (fauna
        consciente exenta, sin memoria todavía, o ya lo bastante cerca de
        lo conocido).

        SESGO DE TERRITORIO (2026-08-22, propuesta de Diego, confirmada:
        "a nivel biológico lo común es mantenerse cerca de las fuentes de
        alimentación, agua y seguridad"). Sin objetivo activo (COMER/
        BEBER/CAZAR/HUIR/BUSCAR_PAREJA), una criatura no debería
        dispersarse sin rumbo si ya conoce dónde hay recursos -- eso es
        plausible para un individuo consciente que delibera (gnomo), pero
        no para fauna sin agencia: lo esperable en fauna real es
        permanecer dentro de su área de campeo (home range) en torno a
        comida/agua/seguridad conocidas, no vagar uniformemente. Gating
        por CapacidadMental.consciencia (decision.umbral_consciencia_
        agencia, PROVISIONAL=0.3): reutiliza el atributo declarado desde
        el Bloque F1 y sin consumidor hasta el 22-08 (ver componentes/
        capacidad_mental.py) para diferenciar el grado de agencia -- por
        debajo del umbral, la criatura queda sujeta al sesgo de
        territorio; por encima (hoy, solo gnomo: rango racial 0.6-0.9), se
        asume que su deambular puede reflejar decisiones no reducibles a
        "quedarse cerca de lo conocido". Mecanismo de gating GENERAL, no
        un caso especial de especie: el día que otra especie tenga
        consciencia alta, quedará exenta automáticamente sin tocar este
        código (leyes neutras, nunca teleológicas). Reutiliza
        nucleo.memoria.objetivo_recordado.

        SESGO GREGARIO (reconstruido 2026-08-23 desde su propia
        documentación -- ver nota de reconstrucción más abajo): con
        probabilidad = Temperamento.sociabilidad DIRECTA, sin escalar (así
        lo describe sistema_reproduccion.py al contrastarse con
        factor_base_concepcion: "el sesgo gregario de sociabilidad... SI
        usa sociabilidad directa, sin escalar"), la criatura busca al
        conspecífico más cercano en su radio de percepción y avanza hacia
        él si está a más de social.distancia_deseada_conspecifico. Sin
        gating por consciencia -- a diferencia del sesgo de territorio,
        el agrupamiento social no se documentó nunca como exclusivo de
        fauna sin agencia; es plausible tanto para gnomo como para el
        resto. Si la tirada de sociabilidad no dispara el sesgo, o no hay
        ningún conspecífico perceptible, se cae al paso aleatorio.

        NOTA DE RECONSTRUCCIÓN (2026-08-23): el sesgo gregario existió y
        se confirmó con Diego en algún momento anterior a hoy -- consta,
        con esas palabras, en el docstring de componentes/temperamento.py
        ("el sesgo gregario en deambular, surgido de una pregunta directa
        de Diego") y en el de sistema_reproduccion.py ("SistemaMovimiento
        ya se encarga de acercar a los coespecíficos"). No sobrevivió al
        refactor de necromasa/pipeline trifásico del 22-08 -- mismo patrón
        de pérdida por colisión de ediciones diagnosticado ese mismo día
        para nacer_criatura, solo que este caso no lanzaba ninguna
        excepción (la clave de config quedaba leída y sin usar), así que
        no se detectó hasta auditar el código funcionalidad por
        funcionalidad. La existencia del sesgo gregario en sí SÍ está
        confirmada por Diego (esas citas); el ORDEN de la cascada frente a
        territorio es ahora también decisión suya, tomada arriba.
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
                gestor, entidad_id, especie, pos_x, pos_y, radio
            )
            if objetivo_conspecifico is not None:
                dist = abs(objetivo_conspecifico[0] - pos_x) + abs(objetivo_conspecifico[1] - pos_y)
                if dist > self.dist_deseada_conspecifico:
                    return self._acercarse_a(pos_x, pos_y, *objetivo_conspecifico)

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