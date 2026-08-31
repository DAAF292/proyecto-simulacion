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
from componentes.construccion import Construccion
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Identidad
from componentes.intencion import Accion, Intencion
from componentes.inventario import Inventario
from componentes.memoria_espacial import MemoriaEspacial
from componentes.necesidades import Necesidades
from componentes.necromasa import Necromasa
from componentes.posicion import Posicion
from nucleo.agua import fraccion_escurrida_por_pendiente, hay_agua_potable, pendiente_local
from nucleo.celda import Celda
from nucleo.construccion import (
    masa_minima_para,
    objetivo_construccion_actual,
    progreso_construccion,
    transferir_a_construccion,
)
from nucleo.entidad import GestorEntidades
from nucleo.eventos import BusEventos, Evento, Severidad
from nucleo.inventario import espacio_disponible_kg
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

        self.cfg_charco = self.config.get("charcos", {})
        self.tasa_evaporacion_charco: float = float(
            self.cfg_charco.get("tasa_evaporacion_charco_por_tick", 0.0006)
        )
        self.tasa_agotamiento_charco: float = float(
            self.cfg_charco.get("tasa_agotamiento_charco_al_beber", 0.01)
        )
        # CÍRCULO 1 de materiales físicos (2026-08-30, ver
        # config/materiales.yaml y nucleo/celda.py:tipo_sustrato/
        # humedad_subsuelo): drenaje de la reserva de humedad de subsuelo,
        # mucho mas lento que la evaporacion de un charco a proposito --
        # ver comentario de config/hidrologia.yaml seccion charcos.
        self.tasa_drenaje_subsuelo: float = float(
            self.cfg_charco.get("tasa_drenaje_humedad_subsuelo_por_tick", 0.001)
        )
        self.catalogo_materiales: dict[str, Any] = self.config.get("materiales", {})
        # Refugio construido -- Pieza 2 (2026-08-30, ver nucleo/construccion.py).
        self.config_construccion: dict[str, Any] = self.config.get("construccion", {})
        self.tasa_aporte_construccion: float = float(
            self.config_construccion.get("tasa_aporte_construccion_kg_tick", 1.0)
        )
        # Círculo C -- RECOLECTAR (2026-08-30, ver nucleo/construccion.py).
        self.tasa_recoleccion: float = float(
            self.config_construccion.get("tasa_recoleccion_kg_tick", 1.0)
        )
        self.fraccion_carga_maxima: float = float(
            self.config.get("inventario", {}).get("fraccion_carga_maxima", 0.25)
        )
        # Almacén de asentamiento (2026-08-30, Círculo E -- ver
        # nucleo/asentamiento.py y nucleo/construccion.py:objetivo_construccion_actual).
        self.radio_cluster_asentamiento: int = int(
            self.config.get("asentamiento", {}).get("radio_cluster_celdas", 6)
        )

        cfg_dep = self.config.get("depredacion", {})
        self.eficiencia_biomasa_saciedad: float = float(
            cfg_dep.get("eficiencia_biomasa_saciedad", 1.5)
        )
        self.eficiencia_biomasa_hidratacion: float = float(
            cfg_dep.get("eficiencia_biomasa_hidratacion", 0.5)
        )

        # (2026-08-23) Ver config/constantes.yaml sección memoria para el
        # razonamiento completo: probabilidad de purga por visita fallida,
        # no purga inmediata al primer fallo -- refinamiento pedido por
        # Diego tras observar que la purga inmediata mejoraba 4 de 5
        # semillas de referencia pero extinguía la quinta.
        cfg_mem = self.config.get("memoria", {})
        self.prob_purgar_recuerdo_agotado: float = float(
            cfg_mem.get("prob_purgar_recuerdo_agotado", 0.05)
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
        # (2026-08-30, Circulo 1 de profundidad) charcos/humedad de
        # subsuelo son estado POR ZONA (cada ZonaBioma es autonoma, con su
        # propio clima_actual) -- se actualizan todas las zonas del
        # territorio, no solo la superficie.
        for zona_i in mundo.territorio.zonas:
            self._actualizar_charcos(zona_i)

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

            zona = mundo.territorio.zonas[pos.zona_idx]
            celda = zona.obtener_celda(pos.x, pos.y)

            if intencion.accion == Accion.COMER:
                self._resolver_comer(
                    gestor, eid, ident, nec, mem, cap_mental, celda, pos.x, pos.y, pos.zona_idx
                )
            elif intencion.accion == Accion.BEBER:
                self._resolver_beber(nec, mem, cap_mental, celda, pos.x, pos.y)
            elif intencion.accion == Accion.ALIVIARSE:
                self._resolver_aliviarse(nec, celda)
            elif intencion.accion == Accion.CONSTRUIR:
                inv = gestor.obtener_componente(eid, Inventario)
                self._resolver_construir(
                    gestor, mundo, eid, mem, cap_mental, inv, pos.x, pos.y, reloj.tick_actual, bus_eventos
                )
            elif intencion.accion == Accion.RECOLECTAR:
                inv = gestor.obtener_componente(eid, Inventario)
                dims = gestor.obtener_componente(eid, DimensionesFisicas)
                self._resolver_recolectar(inv, dims, celda)

    def _actualizar_charcos(self, zona: Any) -> None:
        """Genera/evapora charco y llena/drena humedad de subsuelo según el
        material y la pendiente local de cada celda -- CÍRCULO 1 de
        materiales físicos (2026-08-30, ver config/materiales.yaml y el
        docstring de Celda.tipo_sustrato/humedad_subsuelo).

        ANTES (hasta 2026-08-29): toda celda sin agua permanente encharcaba
        y evaporaba con la MISMA tasa uniforme, sin relación con el
        material del terreno ni con su pendiente -- "decreto climático"
        señalado por Diego. Ahora la lluvia que no logra infiltrarse en el
        sustrato (tasa_infiltracion del material, amortiguada según cuánto
        hueco le queda a humedad_subsuelo -- terreno ya saturado encharca
        más, no menos) ni escurre por la pendiente
        (nucleo/agua.py:fraccion_escurrida_por_pendiente) se queda en
        superficie como charco; la que sí se infiltra alimenta
        humedad_subsuelo, topada por la capacidad_retencion del material y
        con su propio drenaje mucho más lento que la evaporación de un
        charco (la memoria hídrica profunda que faltaba desde el
        principio).
        """
        clima_actual = getattr(zona, "clima_actual", None)
        nombre_clima = clima_actual.value if clima_actual is not None else "despejado"

        tasa_gen = float(
            self.config.get("clima", {})
            .get("efectos", {})
            .get(nombre_clima, {})
            .get("tasa_generacion_charco_por_tick", 0.0)
        )
        techo_charco = float(self.cfg_charco.get("techo_profundidad_charco", 0.03))

        for y in range(zona.alto):
            for x in range(zona.ancho):
                celda = zona.obtener_celda(x, y)
                # (2026-08-29) El charco es agua EFIMERA sobre tierra firme:
                # sobre una celda de agua permanente el campo no significa
                # nada (hay_agua_potable/profundidad_agua_potable ya miran
                # ambas capas) y solo ensuciaria el estado persistido. Lo
                # mismo aplica a humedad_subsuelo -- fijada en generacion
                # al tope de su material (nucleo/zona_bioma.py), nunca
                # simulada tick a tick para estas celdas.
                if celda.tiene_agua:
                    continue

                material = self.catalogo_materiales.get(celda.tipo_sustrato, {})
                tasa_infiltracion = float(material.get("tasa_infiltracion", 0.0))
                capacidad_retencion = float(material.get("capacidad_retencion", 0.0))

                if tasa_gen > 0.0:
                    if capacidad_retencion > 0.0:
                        hueco_restante = max(0.0, capacidad_retencion - celda.humedad_subsuelo)
                        infiltracion_efectiva = tasa_infiltracion * (hueco_restante / capacidad_retencion)
                    else:
                        infiltracion_efectiva = 0.0

                    pendiente = pendiente_local(zona, x, y)
                    escurrida = fraccion_escurrida_por_pendiente(pendiente, self.cfg_charco)
                    fraccion_encharca = max(0.0, 1.0 - infiltracion_efectiva - escurrida)

                    celda.humedad_subsuelo = min(
                        capacidad_retencion,
                        celda.humedad_subsuelo + tasa_gen * infiltracion_efectiva,
                    )
                    celda.profundidad_charco = min(
                        techo_charco, celda.profundidad_charco + tasa_gen * fraccion_encharca
                    )
                else:
                    if celda.profundidad_charco > 0.0:
                        celda.profundidad_charco = max(
                            0.0, celda.profundidad_charco - self.tasa_evaporacion_charco
                        )
                    if celda.humedad_subsuelo > 0.0:
                        celda.humedad_subsuelo = max(
                            0.0, celda.humedad_subsuelo - self.tasa_drenaje_subsuelo
                        )

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

    def _resolver_construir(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        entidad_id: int,
        mem: MemoriaEspacial | None,
        cap_mental: CapacidadMental | None,
        inv: Inventario | None,
        pos_x: int,
        pos_y: int,
        tick_actual: int,
        bus_eventos: BusEventos,
    ) -> None:
        """
        REFUGIO/ALMACÉN CONSTRUIDO -- Pieza 2 de interacción física
        (2026-08-30, ver componentes/construccion.py, nucleo/construccion.py,
        nucleo/asentamiento.py y la conversación de diseño con Diego).
        sistema_movimiento.py ya llevó a la entidad hasta su objetivo de
        construcción actual (refugio propio o, una vez resuelto, el
        almacén del asentamiento del que sea miembro -- Círculo E,
        2026-08-30, objetivo_construccion_actual -- creándolo si hacía
        falta); aquí, estando en la misma celda, se transfieren
        materiales aptos del Inventario y se actualiza progreso.

        Al cruzar 1.0 por primera vez: para refugio, se registra la
        posición como recuerdo "refugio" -- MISMA maquinaria que el
        refugio instintivo (nucleo/memoria.py, sin cambios ni caso
        especial), la memoria apunta al SITIO, no a la entidad
        Construccion. Para almacén no hay recuerdo individual que
        registrar (SistemaAsentamiento ya registra la memoria comunitaria
        "asentamiento" a diario para todos los miembros). Se emite un
        Evento en la transición (mismo criterio que CrisisMental, no en
        cada tick que sigue terminado): NOTABLE para refugio (logro
        individual), HISTÓRICO para almacén (hito de la comunidad entera).
        """
        if inv is None:
            return
        objetivo = objetivo_construccion_actual(
            gestor, mundo, entidad_id, self.radio_cluster_asentamiento
        )
        if objetivo is None:
            return
        _tipo_objetivo, cid, _ = objetivo
        if cid is None:
            return
        con_pos = gestor.obtener_componente(cid, Posicion)
        if con_pos is None or con_pos.x != pos_x or con_pos.y != pos_y:
            return
        construccion = gestor.obtener_componente(cid, Construccion)
        if construccion is None or construccion.progreso >= 1.0:
            return

        transferir_a_construccion(
            inv.contenidos,
            construccion.materiales,
            self.catalogo_materiales,
            self.tasa_aporte_construccion,
        )
        masa_minima = masa_minima_para(construccion.tipo, self.config_construccion)
        construccion.progreso = progreso_construccion(
            construccion.materiales, self.catalogo_materiales, masa_minima
        )

        if construccion.progreso >= 1.0:
            construccion.completado_alguna_vez = True
            if construccion.tipo == "refugio":
                self._registrar_recuerdo_si_procede(mem, cap_mental, "refugio", pos_x, pos_y)
                evento_tipo, severidad = "RefugioConstruido", Severidad.NOTABLE
            else:
                evento_tipo, severidad = "AlmacenConstruido", Severidad.HISTORICO
            bus_eventos.emitir(
                Evento(
                    tipo=evento_tipo,
                    severidad=severidad,
                    tick=tick_actual,
                    entidad_id=entidad_id,
                    datos={"x": pos_x, "y": pos_y, "tipo": construccion.tipo},
                )
            )

    def _resolver_recolectar(
        self,
        inv: Inventario | None,
        dims: DimensionesFisicas | None,
        celda: Celda,
    ) -> None:
        """
        RECOLECTAR -- Círculo C de interacción física (2026-08-30, ver
        componentes/intencion.py y nucleo/construccion.py). Convierte
        tipo_sustrato de la celda actual (piedra/arcilla/tierra --
        propiedad estática de la celda, siempre presente, no depletable,
        ver nucleo/celda.py) en material del Inventario propio, topado
        por la capacidad de carga (nucleo/inventario.py:
        espacio_disponible_kg). Sin desplazamiento: se resuelve donde ya
        se está, el sustrato está bajo los pies de cualquiera.

        MADERA/FIBRA/HIERBA_SECA (2026-08-31, propuesta de Diego: "los
        árboles dejan caer ramas que los gnomos recogen o arrancan
        hierba directamente sin mecanismos complejos de tala y siega").
        sistema_flora.py ya deposita estos materiales en Celda.recursos
        con el MISMO mecanismo de producción diaria que ya usa la comida
        (madera bajo manzano, fibra bajo cactus, hierba_seca bajo
        hierba_silvestre) -- aquí solo hace falta recogerlos, sin ninguna
        acción de tala/siega que destruya la Planta. Genérico por
        catálogo, no una lista de nombres fija: cualquier clave de
        Celda.recursos que sea un material apto_construccion cuenta,
        igual que el resto del motor decide qué es "apto" consultando
        config/materiales.yaml en vez de comprobar nombres a mano.

        CÍRCULO 2 de profundidad (2026-08-30, ver nucleo/cueva.py y
        componentes/celda.py:masa_mineral_restante): si la celda actual
        tiene una veta de mineral con masa restante, se extrae ESO en vez
        de tipo_sustrato -- a diferencia del sustrato, la veta es finita y
        se agota de verdad. Ningún cambio hace falta en sistema_decision.py:
        RECOLECTAR ya gatea genéricamente por "masa apta de construcción
        pendiente" (nucleo/construccion.py:material_suficiente_para),
        hierro/cobre ya son apto_construccion=true en el catálogo -- para
        la Utility AI, extraer mineral, madera o sustrato es indistinguible,
        solo cambia qué clave del Inventario crece.

        Orden de prioridad dentro de esta única celda -- mineral (más
        escaso y finito) > material de flora (finito por día, regenera) >
        sustrato (siempre disponible, nunca se agota): ninguna Utility AI
        lo decide, es simplemente qué hay de más a menos especial en el
        sitio donde ya se está.
        """
        if inv is None or dims is None:
            return
        espacio = espacio_disponible_kg(inv.contenidos, dims.peso, self.fraccion_carga_maxima)
        if espacio <= 0.0:
            return

        if celda.deposito_mineral and celda.masa_mineral_restante > 0.0:
            material = celda.deposito_mineral
            cantidad = min(self.tasa_recoleccion, espacio, celda.masa_mineral_restante)
            inv.contenidos[material] = inv.contenidos.get(material, 0.0) + cantidad
            celda.masa_mineral_restante -= cantidad
            if celda.masa_mineral_restante <= 0.0:
                celda.masa_mineral_restante = 0.0
                celda.deposito_mineral = ""
            return

        for nombre, cantidad_disponible in celda.recursos.items():
            if cantidad_disponible <= 0.0:
                continue
            info = self.catalogo_materiales.get(nombre, {})
            if not info.get("apto_construccion", False):
                continue
            cantidad = min(self.tasa_recoleccion, espacio, cantidad_disponible)
            inv.contenidos[nombre] = inv.contenidos.get(nombre, 0.0) + cantidad
            celda.recursos[nombre] = cantidad_disponible - cantidad
            return

        material = celda.tipo_sustrato
        if not material:
            return
        info = self.catalogo_materiales.get(material, {})
        if not info.get("apto_construccion", False):
            return
        cantidad = min(self.tasa_recoleccion, espacio)
        inv.contenidos[material] = inv.contenidos.get(material, 0.0) + cantidad

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
        zona_idx: int = 0,
    ) -> None:
        """
        Resuelve la ingesta de biomasa: evalúa primero necromasa presente (carroñeo)
        y posteriormente forraje vegetal compatible con la dieta de la especie.
        """
        # 1. Evaluación de Carroñeo (Necromasa en la celda). zona_idx
        # (2026-08-30, Circulo 1 de profundidad): "en la celda" exige
        # tambien estar en la misma zona -- ver componentes/posicion.py.
        candidatos_necromasa = []
        for nid in gestor.entidades_con(Necromasa, Posicion):
            pos_n = gestor.obtener_componente(nid, Posicion)
            if pos_n.x == pos_x and pos_n.y == pos_y and pos_n.zona_idx == zona_idx:
                candidatos_necromasa.append(nid)

        if candidatos_necromasa:
            nec_id = min(candidatos_necromasa)
            nec_comp = gestor.obtener_componente(nec_id, Necromasa)

            # CÍRCULO 2 de materiales físicos (2026-08-30): el carroñeo
            # solo consume 'tejido_blando' -- un carroñero no roe el
            # esqueleto entero. El hueso queda intacto y la entidad NUNCA
            # se borra aquí mientras quede hueso (borrarla es
            # responsabilidad exclusiva de sistema_descomposicion.py, que
            # sí espera a que TODOS los materiales se mineralicen).
            masa_blanda = nec_comp.masas.get("tejido_blando", 0.0) if nec_comp is not None else 0.0
            if nec_comp is not None and masa_blanda > 0.05:
                delta_m = min(masa_blanda, self.tasa_consumo_comer)
                nec_comp.masas["tejido_blando"] = max(0.0, masa_blanda - delta_m)
                nec_comp.agua_tisular = max(0.0, nec_comp.agua_tisular - (delta_m * 0.65))

                # Transferencia nutricional
                nec.saciedad = min(1.0, nec.saciedad + (delta_m * self.eficiencia_biomasa_saciedad))
                nec.hidratacion = min(1.0, nec.hidratacion + (delta_m * self.eficiencia_biomasa_hidratacion))

                self._registrar_recuerdo_si_procede(mem, cap_mental, "comida", pos_x, pos_y)

                if all(m <= 0.05 for m in nec_comp.masas.values()):
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
            #
            # CORRECCION 2026-08-23: la primera versión de este cambio
            # purgaba al primer fallo, sin excepción. Mejoraba 4 de 5
            # semillas de referencia de forma sustancial, pero extinguía
            # una quinta -- descartaba de golpe un recuerdo que, con
            # margen, habría vuelto a dar fruto tras la regeneración
            # diaria de sistema_flora.py. prob_purgar_recuerdo_agotado
            # (PROVISIONAL, ver config/constantes.yaml sección memoria)
            # da varios reintentos esperados antes de rendirse, en vez de
            # uno solo.
            if mem is not None and self.rng.random() < self.prob_purgar_recuerdo_agotado:
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
            # Probabilística, no inmediata (ver prob_purgar_recuerdo_agotado
            # en config/constantes.yaml y el comentario equivalente en
            # _resolver_comer): da margen a que el agua vuelva (lluvia,
            # charco que se rellena) antes de descartar el recuerdo.
            if mem is not None and self.rng.random() < self.prob_purgar_recuerdo_agotado:
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