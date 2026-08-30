"""
sistemas/sistema_necesidades.py

Sistema metabólico y de balance fisiológico interno (Fase 3).
Gestiona el decaimiento de necesidades básicas, la recuperación por sueño,
la deriva térmica ambiental, la asfixia por inmersión y la mortalidad metabólica
con depósito de necromasa y emisión de eventos espaciales.

PERIODO DE PLENITUD (2026-08-29, incremento 2 del diseño de microsueños,
confirmado por Diego junto con la ley B de compromiso de satisfaccion de
sistema_decision.py): una necesidad que alcanza la plenitud (1.0) no decae
durante necesidades.defecto.ticks_plenitud ticks; pasado el periodo, decae
con su tasa lineal de siempre. Es la saciedad post-ingesta biologica: el
estomago lleno suprime la señal de hambre un tiempo, y el hambre emerge
despues gradualmente -- "como algo y estoy lleno durante un tiempo y luego
empieza un hambre gradual" (Diego, sesion de diseño). Sin este periodo el
decay arrancaba el tick siguiente a la plenitud, y la urgencia volvia a
manifestarse de inmediato.

Decisiones de diseño de la pieza:
  - Cubre las CUATRO necesidades fisicas con accion de satisfaccion asociada
    (saciedad, energia, hidratacion, aliviado) -- el mismo universo que el
    compromiso de sistema_decision.py. Seguridad (recuperacion pasiva
    ambiental), impulso reproductivo (reset por concepcion) y oxigenacion
    (transitoria de inmersion) se quedan fuera: su plenitud no llega por
    una accion de satisfaccion.
  - El armado es por TRANSICION de estado (valor registrado del tick
    anterior < 1.0 <= valor actual), no por introspeccion de la accion: si
    una comida llena la hidratacion por su valor_hidratacion, el periodo de
    hidratacion se arma igual -- es la ley fisica, no un guion de accion.
    El default del valor previo es 1.0, asi que los recien nacidos/spawn
    (todas las necesidades a 1.0) NO arman periodo y empiezan a decaer como
    siempre.
  - El tick de la transicion registra 1.0 exacto (el decay del propio tick
    se suprime): ver PLENITUD EFECTIVA en sistema_decision.py -- este
    comportamiento deja de ser un artefacto y pasa a ser la definicion.
  - Para energia, la recuperacion por sueño sigue operando siempre; el
    periodo solo suprime la fatiga despierta, y dormir no consume el
    contador (un sueño dentro del periodo deja el periodo intacto).
  - Timers internos del sistema, NO persistidos (tras cargar partida, el
    decay reanuda hasta la proxima saciedad -- misma clase que oxigenacion)
    y purgados por tick para las entidades eliminadas.
  - ticks_plenitud=0 lo desactiva por completo (decaimiento clasico),
    lo que permite comparar ley B sola contra ley B + plenitud con el
    arnes de diagnostico.

DRENAJE REAL DE SEGURIDAD POR AMENAZA (2026-08-29, fix de auditoria):
Necesidades.seguridad se inicializaba a 1.0 y esta funcion solo la subia
(recuperacion pasiva, paso 5 mas abajo) -- ninguna linea de todo el
repositorio la bajaba nunca, pese a que config/constantes.yaml ya
declaraba necesidades.defecto.tasa_perdida_seguridad_por_amenaza=0.3 sin
que nadie la leyera, y pese a que el propio docstring de
nucleo/amenaza.py listaba a este modulo como consumidor del drenaje.
Consecuencia en cascada (antes de este fix): utilidad_huir = 1.0 -
seguridad (sistema_decision.py) era 0.0 SIEMPRE, por debajo de la
utilidad fija de deambular -- HUIR no podia ganar el argmax nunca, y el
drenaje de estabilidad mental "por amenaza sostenida"
(sistema_capacidad_mental.py) tampoco tenia jamas efecto real. Corregido
aqui: cada tick se busca la amenaza mas cercana (misma funcion que ya
usa HUIR en sistema_movimiento.py, nucleo.amenaza.
posicion_amenaza_mas_cercana, criatura mayor o celda en llamas dentro
del radio de percepcion) -- si hay alguna, seguridad drena
tasa_perdida_seguridad_por_amenaza; si no, se recupera pasivamente como
ya hacia. PROVISIONAL: la tasa de drenaje (0.3) estaba declarada de
antemano en config pero nunca se habia calibrado contra el motor en
marcha porque nunca se habia ejecutado -- pendiente de observar contra
el harness completo si produce huidas razonables o excesivas.
"""

from __future__ import annotations

import random
from typing import Any

from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Identidad
from componentes.intencion import Accion, Intencion
from componentes.necesidades import Necesidades
from componentes.posicion import Posicion
from componentes.temperamento import Temperamento
from nucleo.agua import profundidad_agua_potable
from nucleo.amenaza import posicion_amenaza_mas_cercana
from nucleo.clima import Clima, estacion_actual, objetivo_confort_termico
from nucleo.disposicion import contar_conspecificos_cercanos
from nucleo.entidad import GestorEntidades, crear_necromasa
from nucleo.eventos import BusEventos, Evento, Severidad
from nucleo.mundo import Mundo
from nucleo.percepcion import radio_individual
from nucleo.reloj import Reloj


class SistemaNecesidades:
    """
    Actualiza el estado metabólico de todas las criaturas vivas en la Fase 3.
    """

    def __init__(self, config: dict[str, Any], rng: random.Random) -> None:
        self.config = config
        self.rng = rng
        # PERIODO DE PLENITUD (2026-08-29, ver docstring del modulo): estado
        # transitorio del sistema, NO persistido -- tras cargar una partida,
        # las necesidades reanudan su decay normal hasta la proxima saciedad
        # (misma clase que oxigenacion: se recalcula a partir del estado vivo).
        self._plenitud_prev: dict[tuple[int, str], float] = {}
        self._plenitud_restante: dict[tuple[int, str], int] = {}
        self._cachear_configuracion()

    def _cachear_configuracion(self) -> None:
        """Extrae tasas de decaimiento y probabilidades críticas."""
        self.cfg_nec = self.config.get("necesidades", {})
        self.defecto = self.cfg_nec.get("defecto", {})

        self.tasa_recup_energia: float = float(
            self.defecto.get("tasa_recuperacion_energia_al_dormir", 0.05)
        )
        self.tasa_drenaje_oxigeno: float = float(
            self.defecto.get("tasa_perdida_oxigenacion_por_inmersion", 0.5)
        )
        self.tasa_recup_oxigeno: float = float(
            self.defecto.get("tasa_recuperacion_oxigenacion", 1.0)
        )
        self.tasa_deriva_termica: float = float(
            self.defecto.get("tasa_deriva_confort_termico", 0.03)
        )
        self.tasa_recup_seguridad: float = float(
            self.defecto.get("tasa_recuperacion_seguridad", 0.05)
        )
        # DRENAJE REAL DE SEGURIDAD POR AMENAZA (2026-08-29, ver docstring
        # del modulo): tasa ya declarada en config, nunca leida hasta este
        # fix.
        self.tasa_drenaje_seguridad: float = float(
            self.defecto.get("tasa_perdida_seguridad_por_amenaza", 0.3)
        )
        cfg_per = self.config.get("percepcion", {})
        self.radio_min: int = int(cfg_per.get("radio_minimo_celdas", 0))
        self.radio_max: int = int(cfg_per.get("radio_maximo_celdas", 4))
        # Mismo umbral de disposicion que usa HUIR en sistema_movimiento.py
        # (ver su comentario de fix hermano): se reutiliza
        # depredacion.umbral_disposicion_caza en vez de inventar una
        # constante nueva -- misma magnitud (disposicion logaritmica por
        # peso), aplicada en sentido contrario.
        self.umbral_disposicion_amenaza: float = float(
            self.config.get("depredacion", {}).get("umbral_disposicion_caza", 0.5)
        )

        # GREGARISMO -- Pieza 1, bono de defensa en grupo (2026-08-30, ver
        # nucleo/disposicion.py:contar_conspecificos_cercanos y el
        # comentario de config/constantes.yaml seccion social para el
        # diseno completo). Generico para las 4 especies, no solo lobo.
        cfg_social = self.config.get("social", {})
        self.radio_apoyo_grupal: int = int(cfg_social.get("radio_apoyo_grupal", 3))
        self.bono_defensa_por_aliado: float = float(
            cfg_social.get("bono_defensa_por_aliado", 0.0)
        )
        self.bono_defensa_maximo: float = float(
            cfg_social.get("bono_defensa_maximo", 0.0)
        )

        self.prob_muerte_inanicion: float = float(
            self.defecto.get("probabilidad_muerte_saciedad_critica", 0.005)
        )
        self.prob_muerte_deshidratacion: float = float(
            self.defecto.get("probabilidad_muerte_deshidratacion", 0.005)
        )
        self.prob_muerte_ahogamiento: float = float(
            self.defecto.get("probabilidad_muerte_ahogamiento", 0.5)
        )

        # PERIODO DE PLENITUD (2026-08-29, diseno con Diego tras el
        # diagnostico de microsuenos): ticks sin decay tras alcanzar la
        # plenitud. 0 lo desactiva. PROVISIONAL, ver config/constantes.yaml.
        self.ticks_plenitud: int = int(self.defecto.get("ticks_plenitud", 0))

    def _registrar_plenitud(self, eid: int, nombre: str, valor_actual: float) -> None:
        """
        Arma el periodo de plenitud si la necesidad acaba de tocar el techo
        (transicion: valor registrado del tick anterior < 1.0 <= valor actual).
        Actualiza siempre el valor previo del tick. Con ticks_plenitud=0 no
        arma nunca y el comportamiento es identico al decaimiento clasico.
        """
        key = (eid, nombre)
        prev = self._plenitud_prev.get(key, 1.0)
        if self.ticks_plenitud > 0 and prev < 1.0 <= valor_actual:
            self._plenitud_restante[key] = self.ticks_plenitud
        self._plenitud_prev[key] = valor_actual

    def _decay_con_plenitud(self, eid: int, nombre: str, valor_actual: float, tasa: float) -> float:
        """
        Decaimiento de una necesidad con periodo de plenitud (2026-08-29,
        ver docstring del modulo): si el periodo esta activo, el valor se
        mantiene sin decay un tick y el contador corre; si no, decae con su
        tasa. La transicion a plenitud se evalua sobre el valor PRE-decay de
        este tick (post-recuperacion de sistema_recursos.py, que corre antes
        en la Fase 3) contra el valor registrado al final del tick anterior
        -- asi el tick de la transicion registra 1.0 exacto, sin el recorte
        del decay del mismo tick (el artefacto de pipeline que hace
        inalcanzable el 1.0 registrado para las necesidades que se
        recuperan y decaen en el mismo tick, ver PLENITUD EFECTIVA en
        sistema_decision.py).
        """
        self._registrar_plenitud(eid, nombre, valor_actual)
        key = (eid, nombre)
        restante = self._plenitud_restante.get(key, 0)
        if restante > 0:
            self._plenitud_restante[key] = restante - 1
            return valor_actual
        return max(0.0, valor_actual - tasa)

    def ejecutar(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        reloj: Reloj,
        bus_eventos: BusEventos,
    ) -> None:
        """Procesa el decaimiento metabólico y resuelve la mortalidad fisiológica."""
        zona = mundo.territorio.zonas[0]
        entidades = sorted(
            gestor.entidades_con(Necesidades, Posicion, DimensionesFisicas, Identidad)
        )

        for eid in entidades:
            nec = gestor.obtener_componente(eid, Necesidades)
            pos = gestor.obtener_componente(eid, Posicion)
            dims = gestor.obtener_componente(eid, DimensionesFisicas)
            ident = gestor.obtener_componente(eid, Identidad)
            intencion = gestor.obtener_componente(eid, Intencion)
            temperamento = gestor.obtener_componente(eid, Temperamento)

            if nec is None or pos is None or dims is None or ident is None:
                continue

            celda = zona.obtener_celda(pos.x, pos.y)
            cfg_esp = self.cfg_nec.get(ident.especie.value, self.defecto)

            # Tasas de decaimiento por especie (lectura de config)
            tasa_hambre = float(
                cfg_esp.get(
                    "tasa_perdida_saciedad_por_tick",
                    self.defecto.get("tasa_perdida_saciedad_por_tick", 0.012),
                )
            )
            tasa_sed = float(
                cfg_esp.get(
                    "tasa_perdida_hidratacion_por_tick",
                    self.defecto.get("tasa_perdida_hidratacion_por_tick", 0.004),
                )
            )
            tasa_alivio = float(
                cfg_esp.get(
                    "tasa_perdida_aliviado_por_tick",
                    self.defecto.get("tasa_perdida_aliviado_por_tick", 0.01),
                )
            )
            tasa_energia = float(
                cfg_esp.get(
                    "tasa_perdida_energia_por_tick",
                    self.defecto.get("tasa_perdida_energia_por_tick", 0.01),
                )
            )

            # 1. Decaimiento continuo de Saciedad, Hidratación y Aliviado,
            #    cada uno con su PERIODO DE PLENITUD (2026-08-29, ver
            #    _decay_con_plenitud y docstring del modulo).
            nec.saciedad = self._decay_con_plenitud(eid, "saciedad", nec.saciedad, tasa_hambre)
            nec.hidratacion = self._decay_con_plenitud(
                eid, "hidratacion", nec.hidratacion, tasa_sed
            )
            nec.aliviado = self._decay_con_plenitud(eid, "aliviado", nec.aliviado, tasa_alivio)

            # 2. Resolución de Sueño vs Fatiga (con periodo de plenitud: la
            #    recuperacion por sueno sigue operando siempre; el periodo
            #    solo suprime la fatiga despierta y no se consume durmiendo).
            if intencion is not None and intencion.accion == Accion.DORMIR:
                nec.energia = min(1.0, nec.energia + self.tasa_recup_energia)
                self._registrar_plenitud(eid, "energia", nec.energia)
            else:
                nec.energia = self._decay_con_plenitud(
                    eid, "energia", nec.energia, tasa_energia
                )

            # 3. Asfixia por inmersión
            prof_agua = profundidad_agua_potable(celda)
            if prof_agua > dims.altura:
                nec.oxigenacion = max(0.0, nec.oxigenacion - self.tasa_drenaje_oxigeno)
            else:
                nec.oxigenacion = min(1.0, nec.oxigenacion + self.tasa_recup_oxigeno)

            # 4. Deriva de Confort Térmico estacional + clima del día
            # (2026-08-23) Reloj.estacion es un int CRECIENTE, no cíclico
            # (informe de diseño en nucleo/reloj.py: "dia/estacion/anio son
            # unidades derivadas") -- hay que reducirlo al ciclo de 4 y
            # convertirlo al Enum Estacion vía nucleo.clima.estacion_actual()
            # antes de poder leer .value; este código le pedía .value
            # directamente a un int.
            # (2026-08-29, fix de auditoria) nucleo.clima.objetivo_confort_termico()
            # ya combina estación (base) + clima del día (ajuste_confort) --
            # decisión de diseño ya documentada en su propio docstring
            # ("confort_termico sigue MISMO estatus que seguridad al
            # introducirse"), nunca conectada: este código solo leía la
            # base estacional, ignorando el clima por completo pese a que
            # config ya trae ajuste_confort para los tres climas. Mismo
            # patrón defensivo que sistema_recursos.py/sistema_flora.py
            # para leer zona.clima_actual (puede no existir en un mundo
            # recién creado antes del primer sorteo de clima).
            clima_actual = getattr(zona, "clima_actual", None) or Clima.DESPEJADO
            obj_termico = objetivo_confort_termico(
                estacion_actual(reloj.estacion), clima_actual,
                self.config.get("estaciones", {}), self.config.get("clima", {}),
            )
            if nec.confort_termico < obj_termico:
                nec.confort_termico = min(
                    obj_termico, nec.confort_termico + self.tasa_deriva_termica
                )
            elif nec.confort_termico > obj_termico:
                nec.confort_termico = max(
                    obj_termico, nec.confort_termico - self.tasa_deriva_termica
                )

            # 5. Seguridad: drena si hay amenaza percibida, se recupera si no
            #    (2026-08-29, ver DRENAJE REAL DE SEGURIDAD POR AMENAZA en el
            #    docstring del modulo -- antes de este fix solo se recuperaba,
            #    nunca drenaba).
            radio_amenaza = radio_individual(dims.agudeza_sensorial, self.radio_min, self.radio_max)
            amenaza_pos = posicion_amenaza_mas_cercana(
                gestor, zona, eid, pos.x, pos.y, radio_amenaza,
                dims.peso, self.umbral_disposicion_amenaza,
            )
            if amenaza_pos is not None:
                # GREGARISMO -- Pieza 1, bono de defensa en grupo
                # (2026-08-30, ver docstring del modulo y comentario de
                # config/constantes.yaml seccion social): seguridad en
                # numeros -- conespecificos cercanos (cualquiera, no solo
                # cazando) reducen el drenaje, escalados por la
                # sociabilidad DIRECTA del propio individuo amenazado.
                # Nunca anula el drenaje por completo (bono_defensa_maximo
                # topa la reduccion): seguir habiendo una amenaza real es
                # una amenaza real, con independencia de cuantos aliados
                # haya alrededor.
                sociabilidad_propia = temperamento.sociabilidad if temperamento else 0.0
                drenaje_efectivo = self.tasa_drenaje_seguridad
                if sociabilidad_propia > 0.0 and self.bono_defensa_por_aliado > 0.0:
                    aliados_cercanos = contar_conspecificos_cercanos(
                        gestor, eid, ident.especie, pos.x, pos.y,
                        self.radio_apoyo_grupal, solo_cazando=False,
                    )
                    reduccion = min(
                        self.bono_defensa_maximo,
                        aliados_cercanos * self.bono_defensa_por_aliado * sociabilidad_propia,
                    )
                    drenaje_efectivo = self.tasa_drenaje_seguridad * (1.0 - reduccion)
                nec.seguridad = max(0.0, nec.seguridad - drenaje_efectivo)
            elif nec.seguridad < 1.0:
                nec.seguridad = min(1.0, nec.seguridad + self.tasa_recup_seguridad)

            # 6. Decaimiento de impulso reproductivo
            tasa_rep = float(
                self.defecto.get("tasa_perdida_impulso_reproductivo_por_tick", 0.005)
            )
            nec.impulso_reproductivo = max(0.0, nec.impulso_reproductivo - tasa_rep)

            # 7. Evaluación de Mortalidad Metabólica
            causa_muerte = None

            if nec.oxigenacion <= 0.0:
                if self.rng.random() < self.prob_muerte_ahogamiento:
                    causa_muerte = "ahogamiento"
            elif nec.saciedad <= 0.0:
                if self.rng.random() < self.prob_muerte_inanicion:
                    causa_muerte = "inanicion"
            elif nec.hidratacion <= 0.0:
                if self.rng.random() < self.prob_muerte_deshidratacion:
                    causa_muerte = "deshidratacion"

            if causa_muerte is not None:
                self._resolver_deceso(
                    gestor=gestor,
                    bus_eventos=bus_eventos,
                    reloj=reloj,
                    entidad_id=eid,
                    pos_x=pos.x,
                    pos_y=pos.y,
                    dims=dims,
                    ident=ident,
                    causa=causa_muerte,
                )

        # Purga de timers de plenitud de entidades que ya no existen
        # (muertes de este tick incluidas -- sus keys se limpian en el tick
        # siguiente, un tick de residuo es inofensivo). `entidades` es el
        # snapshot del inicio del tick: los nacidos este tick (reproduccion,
        # mas tarde en la Fase 3) no tienen keys todavia y no hacen falta.
        vivos = set(entidades)
        self._plenitud_prev = {
            k: v for k, v in self._plenitud_prev.items() if k[0] in vivos
        }
        self._plenitud_restante = {
            k: v for k, v in self._plenitud_restante.items() if k[0] in vivos
        }

    def _resolver_deceso(
        self,
        gestor: GestorEntidades,
        bus_eventos: BusEventos,
        reloj: Reloj,
        entidad_id: int,
        pos_x: int,
        pos_y: int,
        dims: DimensionesFisicas,
        ident: Identidad,
        causa: str,
    ) -> None:
        """Instancia la necromasa, emite el evento Muerte con coordenadas y purga la entidad."""
        masa_seca = dims.peso * 0.35
        agua_tisular = dims.peso * 0.65

        crear_necromasa(
            gestor=gestor,
            pos_x=pos_x,
            pos_y=pos_y,
            masa_organica=masa_seca,
            agua_tisular=agua_tisular,
            origen_especie=ident.especie.value,
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
                    "especie": ident.especie.value,
                    "nombre": ident.nombre,
                    "x": pos_x,
                    "y": pos_y,
                },
            )
        )
        gestor.eliminar_entidad(entidad_id)