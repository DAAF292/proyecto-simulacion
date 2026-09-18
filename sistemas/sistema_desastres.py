"""
sistemas/sistema_desastres.py

Sistema de desastres naturales y dinámicas de perturbación ambiental.
Incendio (Corte de Día para ignición, cadencia de tick para propagación/
daño): condicionado por clima, propaga/extingue por tick, daño térmico a
criaturas con necromasa calcinada, conversión de flora en ceniza.

Ampliado 2026-09-18 (ver docs/superpowers/specs/
2026-09-18-desastres-naturales-design.md) con tres piezas más, todas
reutilizando mecanismos ya existentes en vez de inventar donde no hace
falta:
- Rayo (cadencia de tick, solo con Clima.TORMENTA): impacto instantáneo
  en una celda al azar de la zona, daño directo a quien esté ahí, puede
  iniciar un foco de incendio si cae en bosque.
- Sequía (ley emergente por zona, sin entidad de "evento" propia):
  contador de días secos consecutivos -- reduce fertilidad y seca
  charcos, amplifica inanición/deshidratación ya existentes en vez de
  inventar una muerte nueva.
- Inundación (mismo patrón de contador, días húmedos consecutivos):
  desborda charcos hacia celdas vecinas al entrar (reutiliza el
  ahogamiento ya existente) y daña construcciones orgánicas mientras
  dura (vulnerabilidad_agua, simétrico a combustibilidad).

También recalibrado el mismo día: prob_propagacion_por_tick/
prob_extincion_por_tick del incendio -- verificado con el motor real
que antes NUNCA mataba fauna (la amenaza ambiental por celda.en_llamas
daba tiempo de sobra a huir de un fuego que se apagaba solo en pocos
ticks); la flora SÍ moría (no puede huir), confirmado aparte.
"""

from __future__ import annotations

import random
from typing import Any

from componentes.construccion import Construccion
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Identidad
from componentes.planta import Planta
from componentes.pool_fisico import PoolFisico
from componentes.posicion import Posicion
from nucleo.agua import hay_agua_potable
from nucleo.bioma import TipoTerreno
from nucleo.clima import Clima
from nucleo.construccion import masa_minima_para, progreso_construccion
from nucleo.entidad import GestorEntidades, componer_necromasa, crear_necromasa, procesar_deceso
from nucleo.eventos import BusEventos, Evento, Severidad
from nucleo.mundo import Mundo
from nucleo.reloj import Reloj
from nucleo.zona_bioma import vecinos


class SistemaDesastres:
    """
    Simula eventos catastróficos locales y su propagación física en el grid.
    """

    def __init__(self, config: dict[str, Any], rng: random.Random) -> None:
        self.config = config
        self.rng = rng
        self._cachear_configuracion()

    def _cachear_configuracion(self) -> None:
        """Extrae y tipa los parámetros de ignición, propagación y daño por fuego."""
        cfg_des = self.config.get("desastres", {})
        self.prob_ignicion_base: float = float(
            cfg_des.get("prob_ignicion_base_bosque", 0.0015)
        )
        self.prob_propagacion: float = float(
            cfg_des.get("prob_propagacion_por_tick", 0.08)
        )
        self.prob_extincion: float = float(
            cfg_des.get("prob_extincion_por_tick", 0.35)
        )
        self.dano_por_tick_en_llamas: float = float(
            cfg_des.get("dano_por_tick_en_llamas", 0.15)
        )
        self.aporte_ceniza_planta: float = float(
            cfg_des.get("aporte_ceniza_planta", 0.15)
        )
        self.fraccion_masa_seca_quemada: float = float(
            cfg_des.get("fraccion_masa_seca_quemada", 0.20)
        )
        self.fraccion_agua_tisular_quemada: float = float(
            cfg_des.get("fraccion_agua_tisular_quemada", 0.05)
        )
        self.tasa_putrefaccion_calcinada: float = float(
            cfg_des.get("tasa_putrefaccion_calcinada", 0.15)
        )
        # Ver nucleo/entidad.py:componer_necromasa: mismo reparto
        # tejido_blando/hueso que el resto de decesos, aplicado sobre la
        # masa seca calcinada -- no se modela que el fuego destruya el
        # tejido blando de forma preferencial (simplificación deliberada,
        # ver config/flora.yaml seccion descomposicion).
        self.fraccion_hueso: float = float(
            self.config.get("descomposicion", {}).get("fraccion_hueso_de_masa_seca", 0.15)
        )

        cfg_clima = cfg_des.get("multiplicador_riesgo_por_clima", {})
        self.mult_riesgo_clima: dict[str, float] = {
            "despejado": float(cfg_clima.get("despejado", 1.5)),
            "lluvioso": float(cfg_clima.get("lluvioso", 0.2)),
            "tormenta": float(cfg_clima.get("tormenta", 1.0)),
        }

        self.techo_fertilidad: float = float(
            self.config.get("abono", {}).get("techo_fertilidad", 1.0)
        )
        # Fuego sobre construcciones: reutiliza dano_por_tick_en_llamas
        # (ya calibrado como ritmo de daño por fuego) escalado por la
        # combustibilidad de CADA material -- piedra/arcilla/tierra/
        # hierro/cobre tienen combustibilidad 0.0, no arden nunca; madera/
        # fibra/hierba_seca sí, más rápido cuanto más inflamable. NO es
        # el mismo consumidor que el comentario ya existente en
        # config/materiales.yaml sobre combustibilidad ("sustituirá el
        # hardcode... único bioma inflamable es Bosque") -- ese sigue
        # pendiente, es sobre qué bioma/terreno puede arrancar a arder,
        # no sobre qué le pasa a una construcción ya en llamas.
        self.config_construccion: dict[str, Any] = self.config.get("construccion", {})
        self.umbral_purga_masa: float = float(
            self.config.get("descomposicion", {}).get("umbral_purga_masa", 0.05)
        )
        self.catalogo_materiales: dict[str, Any] = self.config.get("materiales", {})

        # Rayo (2026-09-18, ver docs/superpowers/specs/
        # 2026-09-18-desastres-naturales-design.md).
        self.prob_impacto_rayo: float = float(
            cfg_des.get("probabilidad_impacto_rayo_por_tick", 0.02)
        )
        self.dano_rayo: float = float(cfg_des.get("dano_rayo", 0.6))
        self.prob_rayo_inicia_incendio: float = float(
            cfg_des.get("probabilidad_rayo_inicia_incendio", 0.3)
        )
        # Fracciones de descomposicion NORMALES (no las de "calcinada" de
        # arriba) -- un rayo mata de un golpe, no calcina tick a tick.
        # Mismo origen que sistema_necesidades.py:_resolver_deceso.
        cfg_desc = self.config.get("descomposicion", {})
        self.fraccion_masa_seca_normal: float = float(
            cfg_desc.get("fraccion_masa_seca_por_defecto", 0.35)
        )
        self.fraccion_agua_tisular_normal: float = float(
            cfg_desc.get("fraccion_agua_tisular_por_defecto", 0.65)
        )

        # Sequia (2026-09-18).
        self.dias_secos_para_sequia: int = int(cfg_des.get("dias_secos_para_sequia", 8))
        self.penalizacion_fertilidad_sequia: float = float(
            cfg_des.get("penalizacion_fertilidad_sequia_por_dia", 0.02)
        )
        self.factor_secado_charco_sequia: float = float(
            cfg_des.get("factor_secado_charco_sequia", 0.01)
        )

        # Inundacion (2026-09-18).
        self.dias_humedos_para_inundacion: int = int(
            cfg_des.get("dias_humedos_para_inundacion", 5)
        )
        self.incremento_charco_desborde: float = float(
            cfg_des.get("incremento_charco_desborde", 0.15)
        )
        self.tasa_dano_inundacion: float = float(
            cfg_des.get("tasa_dano_inundacion_por_tick", 0.1)
        )
        self.techo_charco: float = float(
            self.config.get("charcos", {}).get("techo_profundidad_charco", 0.03)
        )

    def ejecutar(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        reloj: Reloj,
        bus_eventos: BusEventos,
    ) -> None:
        """
        Punto de entrada para la evaluación diaria de ignición.
        Invocado al inicio de cada día en el orquestador principal.
        """
        # Se evalua ignicion en TODAS las zonas del territorio -- cada
        # ZonaBioma tiene su propio clima_actual y su propio grid, la ley
        # de ignicion no distingue superficie de subsuelo (una zona sin
        # bosque no se ve afectada porque el filtro de tipo_terreno sigue
        # aplicando).
        for zona_idx, zona in enumerate(mundo.territorio.zonas):
            clima_actual = getattr(zona, "clima_actual", None)
            nombre_clima = clima_actual.value if clima_actual is not None else "despejado"
            mult_clima = self.mult_riesgo_clima.get(nombre_clima, 1.0)

            prob_efectiva = self.prob_ignicion_base * mult_clima

            for y in range(zona.alto):
                for x in range(zona.ancho):
                    celda = zona.obtener_celda(x, y)
                    if celda.tipo_terreno == TipoTerreno.BOSQUE and not celda.en_llamas:
                        if self.rng.random() < prob_efectiva:
                            celda.en_llamas = True
                            zona.celdas_en_llamas.add((x, y))
                            bus_eventos.emitir(
                                Evento(
                                    tipo="IncendioIniciado",
                                    severidad=Severidad.HISTORICO,
                                    tick=reloj.tick_actual,
                                    datos={"x": x, "y": y, "zona_idx": zona_idx, "clima": nombre_clima},
                                )
                            )

            self._actualizar_sequia(zona, zona_idx, nombre_clima, reloj, bus_eventos)
            self._actualizar_inundacion(zona, zona_idx, nombre_clima, reloj, bus_eventos)

    # Climas SECOS/HUMEDOS (2026-09-18): clasificacion propia de este
    # sistema, no un atributo de Clima -- ventisca cuenta como HUMEDO
    # (nieve es precipitacion, aunque enfrie) pese a compartir el
    # "penaliza-fertilidad" de la sequia con despejado/ola_calor por
    # motivos climaticos distintos.
    _CLIMAS_SECOS = {"despejado", "ola_calor"}
    _CLIMAS_HUMEDOS = {"lluvioso", "tormenta", "ventisca"}

    def _actualizar_sequia(
        self, zona: Any, zona_idx: int, nombre_clima: str, reloj: Reloj, bus_eventos: BusEventos,
    ) -> None:
        if nombre_clima in self._CLIMAS_SECOS:
            zona.dias_secos_consecutivos += 1
        else:
            zona.dias_secos_consecutivos = 0

        deberia_estar_en_sequia = zona.dias_secos_consecutivos >= self.dias_secos_para_sequia
        if deberia_estar_en_sequia and not zona.en_sequia:
            zona.en_sequia = True
            bus_eventos.emitir(
                Evento(
                    tipo="SequiaIniciada", severidad=Severidad.NOTABLE, tick=reloj.tick_actual,
                    datos={"zona_idx": zona_idx},
                )
            )
        elif not deberia_estar_en_sequia and zona.en_sequia:
            zona.en_sequia = False
            bus_eventos.emitir(
                Evento(
                    tipo="SequiaTerminada", severidad=Severidad.NOTABLE, tick=reloj.tick_actual,
                    datos={"zona_idx": zona_idx},
                )
            )

        if zona.en_sequia:
            for x, y, celda in zona.celdas():
                celda.fertilidad = max(0.0, celda.fertilidad - self.penalizacion_fertilidad_sequia)
                if celda.profundidad_charco > 0.0:
                    celda.profundidad_charco = max(
                        0.0, celda.profundidad_charco - self.factor_secado_charco_sequia
                    )

    def _actualizar_inundacion(
        self, zona: Any, zona_idx: int, nombre_clima: str, reloj: Reloj, bus_eventos: BusEventos,
    ) -> None:
        if nombre_clima in self._CLIMAS_HUMEDOS:
            zona.dias_humedos_consecutivos += 1
        else:
            zona.dias_humedos_consecutivos = 0

        deberia_estar_en_inundacion = zona.dias_humedos_consecutivos >= self.dias_humedos_para_inundacion
        if deberia_estar_en_inundacion and not zona.en_inundacion:
            zona.en_inundacion = True
            # Desborde UNA SOLA VEZ al entrar (no cada dia que dure) --
            # evita crecimiento de charco sin limite. Cualquier celda
            # con agua real desborda hacia sus vecinas de tierra firme.
            nuevas_inundadas: set[tuple[int, int]] = set()
            for x, y, celda in zona.celdas():
                if hay_agua_potable(celda):
                    for nx, ny in vecinos(x, y, zona.ancho, zona.alto):
                        vecina = zona.obtener_celda(nx, ny)
                        if not hay_agua_potable(vecina):
                            vecina.profundidad_charco = min(
                                self.techo_charco,
                                vecina.profundidad_charco + self.incremento_charco_desborde,
                            )
                            nuevas_inundadas.add((nx, ny))
            zona.celdas_inundadas |= nuevas_inundadas
            bus_eventos.emitir(
                Evento(
                    tipo="InundacionIniciada", severidad=Severidad.NOTABLE, tick=reloj.tick_actual,
                    datos={"zona_idx": zona_idx, "celdas_desbordadas": len(nuevas_inundadas)},
                )
            )
        elif not deberia_estar_en_inundacion and zona.en_inundacion:
            zona.en_inundacion = False
            zona.celdas_inundadas.clear()
            bus_eventos.emitir(
                Evento(
                    tipo="InundacionTerminada", severidad=Severidad.NOTABLE, tick=reloj.tick_actual,
                    datos={"zona_idx": zona_idx},
                )
            )

    def procesar_fuego_tick(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        reloj: Reloj,
        bus_eventos: BusEventos,
    ) -> None:
        """
        Propaga llamas, extingue focos y aplica daño térmico a criaturas y flora.
        Debe ejecutarse a cadencia de tick en la Fase 2 del ciclo.

        Procesa TODAS las zonas del territorio -- ver el mismo criterio
        en ejecutar() de esta clase.
        """
        for zona_idx, zona in enumerate(mundo.territorio.zonas):
            self._procesar_fuego_tick_zona(gestor, zona, zona_idx, reloj, bus_eventos)

    def _procesar_fuego_tick_zona(
        self,
        gestor: GestorEntidades,
        zona: Any,
        zona_idx: int,
        reloj: Reloj,
        bus_eventos: BusEventos,
    ) -> None:
        # 2026-09-08: lee el registro de zona.celdas_en_llamas en vez de
        # escanear toda la cuadricula -- ver docstring de
        # ZonaBioma.celdas_en_llamas. sorted(...) es OBLIGATORIO, no
        # cosmetico: es un set, sin orden de iteracion garantizado, y el
        # orden en que se procesan los focos determina el orden en que
        # se consumen tiradas de rng.random() (extincion/propagacion) --
        # con un orden distinto al escaneo original (y, x) la secuencia
        # de aleatoriedad de TODO lo que venga despues en el tick se
        # desvia, mismo fenomeno ya documentado en este proyecto
        # (Sobrepoblacion..., CLAUDE.md). Se ordena igual que el escaneo
        # que sustituye: y ascendente, luego x ascendente.
        celdas_en_llamas: list[tuple[int, int]] = sorted(
            zona.celdas_en_llamas, key=lambda c: (c[1], c[0])
        )

        if not celdas_en_llamas:
            return

        nuevos_focos: list[tuple[int, int]] = []
        extinciones: list[tuple[int, int]] = []

        direcciones = [(0, 1), (0, -1), (1, 0), (-1, 0)]

        for fx, fy in celdas_en_llamas:
            if self.rng.random() < self.prob_extincion:
                extinciones.append((fx, fy))

            for dx, dy in direcciones:
                nx, ny = fx + dx, fy + dy
                if 0 <= nx < zona.ancho and 0 <= ny < zona.alto:
                    vecina = zona.obtener_celda(nx, ny)
                    if (
                        vecina.tipo_terreno == TipoTerreno.BOSQUE
                        and not vecina.en_llamas
                        and (nx, ny) not in nuevos_focos
                    ):
                        if self.rng.random() < self.prob_propagacion:
                            nuevos_focos.append((nx, ny))

        for ex, ey in extinciones:
            zona.obtener_celda(ex, ey).en_llamas = False
            zona.celdas_en_llamas.discard((ex, ey))

        for nx, ny in nuevos_focos:
            zona.obtener_celda(nx, ny).en_llamas = True
            zona.celdas_en_llamas.add((nx, ny))

        # 1. Flora en llamas -> Ceniza mineralizada. zona_idx se descarta
        # ANTES de indexar el grid de esta zona -- una entidad de otra
        # zona puede tener (x, y) fuera de los limites de esta (zonas de
        # distinto tamaño).
        plantas_a_purgar: list[int] = []
        for planta_id in sorted(gestor.entidades_con(Planta, Posicion)):
            pos_p = gestor.obtener_componente(planta_id, Posicion)
            if pos_p is not None and pos_p.zona_idx == zona_idx:
                celda_p = zona.obtener_celda(pos_p.x, pos_p.y)
                if celda_p.en_llamas:
                    celda_p.fertilidad = min(
                        self.techo_fertilidad,
                        celda_p.fertilidad + self.aporte_ceniza_planta,
                    )
                    plantas_a_purgar.append(planta_id)

        for pid in plantas_a_purgar:
            gestor.eliminar_entidad(pid)

        # 2. Criaturas vivas en llamas -> Necromasa calcinada
        criaturas = sorted(
            gestor.entidades_con(Posicion, PoolFisico, DimensionesFisicas, Identidad)
        )
        for cid in criaturas:
            pos_c = gestor.obtener_componente(cid, Posicion)
            pool_c = gestor.obtener_componente(cid, PoolFisico)
            dims_c = gestor.obtener_componente(cid, DimensionesFisicas)
            ident_c = gestor.obtener_componente(cid, Identidad)

            if pos_c is None or pool_c is None or dims_c is None or ident_c is None:
                continue
            if pos_c.zona_idx != zona_idx:
                continue

            celda_c = zona.obtener_celda(pos_c.x, pos_c.y)
            if celda_c.en_llamas:
                dano_neto = self.dano_por_tick_en_llamas * dims_c.vitalidad_maxima
                pool_c.vitalidad = max(0.0, pool_c.vitalidad - dano_neto)

                if pool_c.vitalidad <= 0.0:
                    masas, agua_tisular_restante = componer_necromasa(
                        dims_c.peso, self.fraccion_masa_seca_quemada, self.fraccion_hueso,
                        self.fraccion_agua_tisular_quemada,
                    )
                    crear_necromasa(
                        gestor=gestor,
                        pos_x=pos_c.x,
                        pos_y=pos_c.y,
                        masas=masas,
                        agua_tisular=agua_tisular_restante,
                        origen_especie=ident_c.especie.value,
                        tasa_putrefaccion=self.tasa_putrefaccion_calcinada,
                        zona_idx=zona_idx,
                    )

                    bus_eventos.emitir(
                        Evento(
                            tipo="Muerte",
                            severidad=Severidad.HISTORICO,
                            tick=reloj.tick_actual,
                            entidad_id=cid,
                            datos={
                                "causa": "incendio",
                                "especie": ident_c.especie.value,
                                "nombre": ident_c.nombre,
                            },
                        )
                    )
                    gestor.eliminar_entidad(cid)
                else:
                    bus_eventos.emitir(
                        Evento(
                            tipo="Herida",
                            severidad=Severidad.NOTABLE,
                            tick=reloj.tick_actual,
                            entidad_id=cid,
                            datos={
                                "causa": "fuego",
                                "vitalidad_restante": pool_c.vitalidad,
                            },
                        )
                    )

        # 3. Construcciones en llamas -> consumo de materiales por
        # combustibilidad (ver _cachear_configuracion).
        masa_minima_cache: dict[str, float] = {}
        for con_id in sorted(gestor.entidades_con(Construccion, Posicion)):
            pos_co = gestor.obtener_componente(con_id, Posicion)
            construccion = gestor.obtener_componente(con_id, Construccion)
            if pos_co is None or construccion is None or not construccion.materiales:
                continue
            if pos_co.zona_idx != zona_idx:
                continue
            celda_co = zona.obtener_celda(pos_co.x, pos_co.y)
            if not celda_co.en_llamas:
                continue

            ardio_algo = False
            for material, masa in list(construccion.materiales.items()):
                if masa <= 0.0:
                    continue
                combustibilidad = float(
                    self.catalogo_materiales.get(material, {}).get("combustibilidad", 0.0)
                )
                if combustibilidad <= 0.0:
                    continue
                delta = masa * combustibilidad * self.dano_por_tick_en_llamas
                construccion.materiales[material] = max(0.0, masa - delta)
                ardio_algo = True

            if not ardio_algo:
                continue  # sin ningún material combustible -- piedra no arde

            if construccion.tipo not in masa_minima_cache:
                masa_minima_cache[construccion.tipo] = masa_minima_para(
                    construccion.tipo, self.config_construccion
                )
            construccion.progreso = progreso_construccion(
                construccion.materiales, self.catalogo_materiales, masa_minima_cache[construccion.tipo]
            )

            if all(m <= self.umbral_purga_masa for m in construccion.materiales.values()):
                bus_eventos.emitir(
                    Evento(
                        tipo="ConstruccionColapsada",
                        severidad=Severidad.NOTABLE if construccion.tipo == "refugio" else Severidad.HISTORICO,
                        tick=reloj.tick_actual,
                        entidad_id=con_id,
                        datos={"x": pos_co.x, "y": pos_co.y, "tipo": construccion.tipo, "causa": "incendio"},
                    )
                )
                gestor.eliminar_entidad(con_id)

    def procesar_rayo_tick(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        reloj: Reloj,
        bus_eventos: BusEventos,
    ) -> None:
        """Rayo (2026-09-18, ver docs/superpowers/specs/
        2026-09-18-desastres-naturales-design.md): a cadencia de TICK,
        solo en zonas con Clima.TORMENTA activo. Celda al azar de la
        zona -- no restringido a bosque, a diferencia de la ignicion
        espontanea. Dano INSTANTANEO a quien este ahi (si hay alguien);
        si la celda es bosque, probabilidad adicional de iniciar un
        foco de incendio."""
        for zona_idx, zona in enumerate(mundo.territorio.zonas):
            if zona.clima_actual != Clima.TORMENTA:
                continue
            if self.rng.random() >= self.prob_impacto_rayo:
                continue

            x = self.rng.randrange(zona.ancho)
            y = self.rng.randrange(zona.alto)
            celda = zona.obtener_celda(x, y)

            bus_eventos.emitir(
                Evento(
                    tipo="RayoImpacto", severidad=Severidad.HISTORICO, tick=reloj.tick_actual,
                    datos={"x": x, "y": y, "zona_idx": zona_idx},
                )
            )

            for cid in sorted(
                gestor.entidades_con(Posicion, PoolFisico, DimensionesFisicas, Identidad)
            ):
                pos_c = gestor.obtener_componente(cid, Posicion)
                if pos_c is None or pos_c.zona_idx != zona_idx or pos_c.x != x or pos_c.y != y:
                    continue
                pool_c = gestor.obtener_componente(cid, PoolFisico)
                dims_c = gestor.obtener_componente(cid, DimensionesFisicas)
                ident_c = gestor.obtener_componente(cid, Identidad)
                dano = self.dano_rayo * dims_c.vitalidad_maxima
                pool_c.vitalidad = max(0.0, pool_c.vitalidad - dano)
                if pool_c.vitalidad <= 0.0:
                    procesar_deceso(
                        gestor=gestor, bus_eventos=bus_eventos, tick_actual=reloj.tick_actual,
                        entidad_id=cid, pos_x=x, pos_y=y, dims=dims_c, ident=ident_c,
                        causa="rayo", zona_idx=zona_idx,
                        fraccion_masa_seca=self.fraccion_masa_seca_normal,
                        fraccion_hueso=self.fraccion_hueso,
                        fraccion_agua_tisular=self.fraccion_agua_tisular_normal,
                    )
                else:
                    bus_eventos.emitir(
                        Evento(
                            tipo="Herida", severidad=Severidad.NOTABLE, tick=reloj.tick_actual,
                            entidad_id=cid,
                            datos={"causa": "rayo", "vitalidad_restante": pool_c.vitalidad},
                        )
                    )
                break  # una sola criatura por celda de impacto, no hace falta seguir buscando

            if (
                celda.tipo_terreno == TipoTerreno.BOSQUE
                and not celda.en_llamas
                and self.rng.random() < self.prob_rayo_inicia_incendio
            ):
                celda.en_llamas = True
                zona.celdas_en_llamas.add((x, y))
                bus_eventos.emitir(
                    Evento(
                        tipo="IncendioIniciado", severidad=Severidad.HISTORICO, tick=reloj.tick_actual,
                        datos={"x": x, "y": y, "zona_idx": zona_idx, "clima": "tormenta", "causa": "rayo"},
                    )
                )

    def procesar_inundacion_tick(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        reloj: Reloj,
        bus_eventos: BusEventos,
    ) -> None:
        """Inundacion (2026-09-18): dano a construcciones ORGANICAS en
        celdas desbordadas (zona.celdas_inundadas), mismo patron exacto
        que el dano por fuego a construcciones -- vulnerabilidad_agua en
        vez de combustibilidad."""
        for zona_idx, zona in enumerate(mundo.territorio.zonas):
            if not zona.celdas_inundadas:
                continue
            masa_minima_cache: dict[str, float] = {}
            for con_id in sorted(gestor.entidades_con(Construccion, Posicion)):
                pos_co = gestor.obtener_componente(con_id, Posicion)
                construccion = gestor.obtener_componente(con_id, Construccion)
                if pos_co is None or construccion is None or not construccion.materiales:
                    continue
                if pos_co.zona_idx != zona_idx:
                    continue
                if (pos_co.x, pos_co.y) not in zona.celdas_inundadas:
                    continue

                se_daño_algo = False
                for material, masa in list(construccion.materiales.items()):
                    if masa <= 0.0:
                        continue
                    vulnerabilidad = float(
                        self.catalogo_materiales.get(material, {}).get("vulnerabilidad_agua", 0.0)
                    )
                    if vulnerabilidad <= 0.0:
                        continue
                    delta = masa * vulnerabilidad * self.tasa_dano_inundacion
                    construccion.materiales[material] = max(0.0, masa - delta)
                    se_daño_algo = True

                if not se_daño_algo:
                    continue

                if construccion.tipo not in masa_minima_cache:
                    masa_minima_cache[construccion.tipo] = masa_minima_para(
                        construccion.tipo, self.config_construccion
                    )
                construccion.progreso = progreso_construccion(
                    construccion.materiales, self.catalogo_materiales, masa_minima_cache[construccion.tipo]
                )

                if all(m <= self.umbral_purga_masa for m in construccion.materiales.values()):
                    bus_eventos.emitir(
                        Evento(
                            tipo="ConstruccionColapsada",
                            severidad=Severidad.NOTABLE if construccion.tipo == "refugio" else Severidad.HISTORICO,
                            tick=reloj.tick_actual,
                            entidad_id=con_id,
                            datos={"x": pos_co.x, "y": pos_co.y, "tipo": construccion.tipo, "causa": "inundacion"},
                        )
                    )
                    gestor.eliminar_entidad(con_id)