"""
sistemas/sistema_asentamiento.py

Detección diaria de asentamientos (clúster de refugios individuales
terminados) y cálculo de liderazgo (ver nucleo/asentamiento.py). Cadencia
diaria, mismo corte que clima/descomposición/flora/ciclo_vital/desastres
(main.py:ejecutar_tick).

Recalcula mundo.asentamientos ÍNTEGRO cada día, pero el ID de cada
asentamiento SÍ es estable entre días (2026-09-15, ver
nucleo/asentamiento.py:resolver_identidades_persistentes y
docs/superpowers/specs/2026-09-15-identidad-persistente-asentamiento-design.md)
-- continuidad por solape de miembros, no por coincidencia exacta, así
que perder o ganar un miembro no "refunda" el pueblo. El evento
"AsentamientoFundado" se emite solo cuando el id resuelto es
genuinamente nuevo (no existía ayer).
"""

from __future__ import annotations

import random
from typing import Any

from componentes.capacidad_mental import CapacidadMental
from componentes.construccion import Construccion
from componentes.identidad import Identidad
from componentes.memoria_espacial import MemoriaEspacial
from componentes.posicion import Posicion
from componentes.relaciones import Relaciones
from componentes.temperamento import Temperamento
from nucleo.asentamiento import (
    Asentamiento,
    agrupar_por_proximidad,
    calcular_centro,
    calcular_liderazgo,
    distancia_caracter,
    generar_nombre,
    rasgo_geografico_notable,
    resolver_identidades_persistentes,
)
from nucleo.conocimiento import erosionar
from nucleo.entidad import GestorEntidades
from nucleo.parentesco import es_familia_directa
from nucleo.eventos import BusEventos, Evento, Severidad
from nucleo.indice_espacial import construir_indice_espacial
from nucleo.memoria import capacidad_memoria, registrar_recuerdo
from nucleo.relaciones import ajustar_afinidad, capacidad_vinculos
from nucleo.mundo import Mundo
from nucleo.reloj import Reloj


class SistemaAsentamiento:
    def __init__(self, config: dict[str, Any], rng: random.Random) -> None:
        self.config = config
        self.rng = rng
        self.config_asentamiento: dict[str, Any] = self.config.get("asentamiento", {})
        self.poblacion_minima: int = int(
            self.config_asentamiento.get("poblacion_minima_asentamiento", 3)
        )
        self.radio_cluster: int = int(self.config_asentamiento.get("radio_cluster_celdas", 6))
        self.umbral_consciencia_agencia: float = float(
            self.config.get("decision", {}).get("umbral_consciencia_agencia", 0.3)
        )
        self.umbral_continuidad_identidad: float = float(
            self.config_asentamiento.get("umbral_continuidad_identidad", 0.5)
        )
        self.tasa_erosion_conocimiento: float = float(
            self.config_asentamiento.get("tasa_erosion_conocimiento_dia", 0.005)
        )
        # Nombre propio (2026-09-15, ver nucleo/asentamiento.py:
        # generar_nombre y config/nombres.yaml:nombres_asentamiento).
        self.catalogo_nombres_asentamiento: dict[str, Any] = self.config.get(
            "nombres_asentamiento", {}
        )
        # Mix geográfico (2026-09-15, corrección tras feedback de Diego):
        # probabilidad de usar el catálogo temático (agua/montaña) en
        # vez del genérico cuando la celda de fundación tiene un rasgo
        # notable. PROVISIONAL.
        self.probabilidad_nombre_tematico: float = float(
            self.config_asentamiento.get("probabilidad_nombre_tematico", 0.6)
        )
        self._indice_actual = None
        # Observación para SIMULACION_AUTO_TICKS (2026-09-06, círculo 5b -- ver
        # docs/superpowers/specs/2026-09-06-lealtad-liderazgo-design.md):
        # cuántas aplicaciones reales de lealtad diaria miembro->líder se
        # escribieron durante la tanda. Solo observación, no cambia la
        # simulación.
        self._stats_lealtad_aplicada: int = 0

    def ejecutar(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        reloj: Reloj,
        bus_eventos: BusEventos,
    ) -> None:
        # Cadencia diaria (2026-09-08, nucleo/indice_espacial.py):
        # construye su propio indice local -- llamada de baja frecuencia,
        # mismo criterio que sistema_manada.py.
        self._indice_actual = construir_indice_espacial(gestor)
        # 1. Refugios que llegaron a estar TERMINADOS alguna vez, por
        # propietario -- pertenencia usa completado_alguna_vez, no
        # progreso: uno a medio construir por PRIMERA vez
        # (completado_alguna_vez=False) todavía no es un lugar donde
        # vivir y no cuenta; uno ya habitado que decayó un poco sigue
        # contando -- necesita reparación, no deja de ser parte del
        # pueblo mientras tanto.
        refugios: dict[int, tuple[int, int]] = {}
        zona_por_refugio: dict[int, int] = {}
        for cid in gestor.entidades_con(Construccion, Posicion):
            construccion = gestor.obtener_componente(cid, Construccion)
            if construccion.tipo != "refugio" or not construccion.completado_alguna_vez:
                continue
            if construccion.propietario_id is None:
                continue
            pos = gestor.obtener_componente(cid, Posicion)
            refugios[construccion.propietario_id] = (pos.x, pos.y)
            zona_por_refugio[construccion.propietario_id] = pos.zona_idx

        if not refugios:
            mundo.asentamientos = {}
            mundo.asentamiento_registro_identidad = {}
            mundo.asentamiento_tick_fundacion = {}
            self._erosionar_conocimiento_diario(mundo)
            return

        # Un asentamiento no puede tener miembros que no comparten
        # espacio real (con varias cuevas compartiendo rangos de
        # coordenadas pequeños, dos refugios en zonas DISTINTAS podrían
        # agruparse por pura coincidencia numérica) -- se agrupa por zona
        # primero, y agrupar_por_proximidad (genérica, sin noción de
        # zona) se llama una vez por zona, nunca mezclando refugios de
        # zonas distintas.
        grupos: list[set[int]] = []
        for zona_idx_actual in sorted(set(zona_por_refugio.values())):
            refugios_de_zona = {
                rid: pos for rid, pos in refugios.items() if zona_por_refugio[rid] == zona_idx_actual
            }
            grupos.extend(agrupar_por_proximidad(refugios_de_zona, self.radio_cluster))

        grupos_validos = [
            frozenset(grupo) for grupo in grupos if len(grupo) >= self.poblacion_minima
        ]

        # Identidad persistente (2026-09-15, ver docs/superpowers/specs/
        # 2026-09-15-identidad-persistente-asentamiento-design.md):
        # reutiliza el id de ayer por solape en vez de reasignar 1..N
        # desde cero -- así un asentamiento que pierde o gana un miembro
        # sigue siendo "el mismo" de un día para otro.
        registro_anterior = mundo.asentamiento_registro_identidad
        miembros_por_id = resolver_identidades_persistentes(
            grupos_validos, registro_anterior, self.umbral_continuidad_identidad,
        )

        nuevos: dict[int, Asentamiento] = {}
        tick_fundacion_hoy: dict[int, int] = {}
        for id_resuelto, grupo in miembros_por_id.items():
            es_nuevo = id_resuelto not in registro_anterior
            tick_fundacion = reloj.tick_actual if es_nuevo else mundo.asentamiento_tick_fundacion.get(
                id_resuelto, reloj.tick_actual
            )
            tick_fundacion_hoy[id_resuelto] = tick_fundacion

            zona_asentamiento = zona_por_refugio[next(iter(grupo))]
            centro = calcular_centro(refugios, grupo)
            lideres = calcular_liderazgo(gestor, grupo, self.config_asentamiento)
            asentamiento = Asentamiento(
                id=id_resuelto,
                centro=centro,
                miembros=grupo,
                lideres=frozenset(lideres),
                zona_idx=zona_asentamiento,
                tick_fundacion=tick_fundacion,
            )
            nuevos[id_resuelto] = asentamiento

            # Memoria comunitaria: cada miembro registra la posición del
            # asentamiento -- mismo mecanismo genérico que refugio, tipo
            # "asentamiento", sin tocar nucleo/memoria.py.
            for mid in grupo:
                mem = gestor.obtener_componente(mid, MemoriaEspacial)
                cap_mental = gestor.obtener_componente(mid, CapacidadMental)
                if mem is not None and cap_mental is not None:
                    capacidad = capacidad_memoria(cap_mental, self.config)
                    registrar_recuerdo(mem, "asentamiento", centro[0], centro[1], capacidad)

            if es_nuevo:
                # Nombre propio (2026-09-15): sorteado UNA sola vez,
                # exactamente aquí -- nunca se vuelve a tocar mientras
                # este id persista (ver Mundo.asentamiento_nombre).
                # Mix geográfico: rasgo real de la celda de fundación
                # (agua/montaña/None), ver nucleo/asentamiento.py:
                # rasgo_geografico_notable.
                celda_centro = mundo.territorio.zonas[zona_asentamiento].obtener_celda(
                    centro[0], centro[1]
                )
                rasgo = rasgo_geografico_notable(celda_centro)
                nombre_asentamiento = generar_nombre(
                    self.rng, self.catalogo_nombres_asentamiento,
                    rasgo, self.probabilidad_nombre_tematico,
                )
                if nombre_asentamiento is not None:
                    mundo.asentamiento_nombre[id_resuelto] = nombre_asentamiento
                datos_evento: dict[str, Any] = {
                    "x": centro[0],
                    "y": centro[1],
                    "poblacion": len(grupo),
                    "lideres": sorted(lideres),
                    "asentamiento_id": id_resuelto,
                }
                if nombre_asentamiento is not None:
                    datos_evento["nombre_asentamiento"] = nombre_asentamiento
                nombres_lideres = []
                for lid in lideres:
                    ident = gestor.obtener_componente(lid, Identidad)
                    if ident is not None and ident.nombre:
                        nombres_lideres.append(ident.nombre)
                if nombres_lideres:
                    datos_evento["nombres_lideres"] = nombres_lideres
                bus_eventos.emitir(
                    Evento(
                        tipo="AsentamientoFundado",
                        severidad=Severidad.HISTORICO,
                        tick=reloj.tick_actual,
                        datos=datos_evento,
                    )
                )

        mundo.asentamientos = nuevos
        mundo.asentamiento_registro_identidad = miembros_por_id
        mundo.asentamiento_tick_fundacion = tick_fundacion_hoy

        # Acreción diaria de amistad por convivencia (2026-09-04,
        # nucleo/relaciones.py): justo después de recalcular
        # mundo.asentamientos, cada par de miembros CONSCIENTES del
        # mismo asentamiento gana afinidad positiva. Efecto colateral
        # de vivir juntos, sin ninguna acción de la Utility AI.
        self._acrecion_amistad_convivencia(gestor, mundo, reloj)
        # Acreción diaria de lealtad de seguidor hacia líder (2026-09-06,
        # círculo 5b -- ver docs/superpowers/specs/2026-09-06-lealtad-liderazgo-design.md):
        # misma cadencia que la amistad por convivencia, pero dirigida
        # específicamente miembro->líder: los seguidores admiran al líder,
        # no necesariamente al revés (no se autora reciprocidad).
        self._acrecion_lealtad_liderazgo(gestor, mundo, reloj)
        self._erosionar_conocimiento_diario(mundo)

    def _erosionar_conocimiento_diario(self, mundo: Mundo) -> None:
        """Decaimiento diario de conocimiento colectivo (2026-09-15, ver
        nucleo/conocimiento.py) -- se aplica con independencia de si hoy
        existe algún asentamiento vivo (entradas de un id ya retirado
        del registro simplemente siguen ahí, inertes, sin que nada las
        lea de nuevo -- no se purgan por id muerto, mismo criterio de
        laissez-faire que Relaciones.vinculos apuntando a un id ya
        muerto)."""
        for conocimiento_asen in mundo.asentamiento_conocimiento.values():
            erosionar(conocimiento_asen, self.tasa_erosion_conocimiento)

    def _acrecion_amistad_convivencia(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        reloj: Reloj,
    ) -> None:
        """(2026-09-04, nucleo/relaciones.py) Acreci\u00f3n diaria de amistad.

        Afinidad POSITIVA emergente de convivencia real en el mismo
        asentamiento, sin ninguna acci\u00f3n nueva de la Utility AI \u2014 efecto
        colateral de vivir juntos, no una decisi\u00f3n consciente de
        "hacerse amigos". Solamente ESCRIBE afinidad, nunca la lee para
        cambiar comportamiento.

        Mismo patr\u00f3n que el rencor (sistema_movimiento.py
        :_ajustar_afinidad_rencor): un individuo NO consciente no
        escribe ni recibe nada; cada parte usa su propia
        capacidad_vinculos.

        Bono de parentesco (2026-09-17, ver docs/superpowers/specs/
        2026-09-17-convivencia-familiar-design.md, Circulo A del arco
        "vida familiar"): un par que es_familia_directa() (hermanos, o
        padre/madre-hijo) gana afinidad diaria multiplicada por
        factor_amistad_convivencia_familia -- los lazos de sangre hacen
        mas estrecha la convivencia, no solo pertenecer al mismo
        asentamiento por igual que un vecino cualquiera. Reutiliza
        nucleo.parentesco.es_familia_directa (Identidad.id_madre/id_padre
        en vivo) sin ningun componente nuevo.
        """
        delta = float(
            self.config.get("relaciones", {}).get("delta_amistad_convivencia_dia", 0.05)
        )
        if delta <= 0.0:
            return
        factor_familia = float(
            self.config.get("relaciones", {}).get(
                "factor_amistad_convivencia_familia", 2.0
            )
        )
        for asentamiento in mundo.asentamientos.values():
            conscientes: list[int] = []
            for mid in asentamiento.miembros:
                cap_mental = gestor.obtener_componente(mid, CapacidadMental)
                if (
                    cap_mental is not None
                    and cap_mental.consciencia >= self.umbral_consciencia_agencia
                ):
                    conscientes.append(mid)
            # Cada PAR distinto, una sola vez; ambas direcciones.
            for i in range(len(conscientes)):
                for j in range(i + 1, len(conscientes)):
                    delta_par = delta
                    if es_familia_directa(conscientes[i], conscientes[j], gestor):
                        delta_par = delta * factor_familia
                    self._ajustar_amistad(
                        gestor, conscientes[i], conscientes[j], delta_par, reloj.tick_actual
                    )
                    self._ajustar_amistad(
                        gestor, conscientes[j], conscientes[i], delta_par, reloj.tick_actual
                    )

    def _acrecion_lealtad_liderazgo(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        reloj: Reloj,
    ) -> None:
        """Lealtad diaria de seguidor hacia lider (2026-09-06, circulo 5b --
        ver docs/superpowers/specs/2026-09-06-lealtad-liderazgo-design.md):
        mismo patron que _acrecion_amistad_convivencia, dirigido
        especificamente miembro->lider. Es literalmente como se construyen
        "seguidores" -- sin contador de dias en el poder, la propia
        Relaciones acumulada hace ese papel.

        Disonancia de caracter (2026-09-17, ver docs/superpowers/specs/
        2026-09-17-liderazgo-influencia-design.md): el delta diario ya
        NO es incondicionalmente positivo -- si la distancia de caracter
        (nucleo.asentamiento.distancia_caracter) entre miembro y lider
        supera umbral_disonancia_liderazgo, el dia ERODE lealtad en vez
        de sumarla, proporcional al exceso sobre el umbral. Sostenido en
        el tiempo, esto es la "rebelion": la reputacion cae bajo
        umbral_reputacion_descalificante y el lider queda descalificado
        en el proximo calcular_liderazgo -- mecanismo YA EXISTENTE, sin
        cambios, solo alimentado por una señal nueva."""
        delta_base = float(self.config.get("relaciones", {}).get("delta_lealtad_liderazgo", 0.0))
        if delta_base <= 0.0:
            return
        umbral_disonancia = float(
            self.config_asentamiento.get("umbral_disonancia_liderazgo", 0.5)
        )
        delta_erosion_base = float(
            self.config.get("relaciones", {}).get(
                "delta_erosion_lealtad_liderazgo", delta_base
            )
        )
        for asentamiento in mundo.asentamientos.values():
            if not asentamiento.lideres:
                continue
            for miembro_id in asentamiento.miembros:
                if miembro_id in asentamiento.lideres:
                    continue
                temperamento_miembro = gestor.obtener_componente(miembro_id, Temperamento)
                for lider_id in asentamiento.lideres:
                    delta = delta_base
                    temperamento_lider = gestor.obtener_componente(lider_id, Temperamento)
                    if (
                        temperamento_miembro is not None
                        and temperamento_lider is not None
                        and umbral_disonancia > 0.0
                    ):
                        dist = distancia_caracter(temperamento_miembro, temperamento_lider)
                        if dist >= umbral_disonancia:
                            exceso = (
                                (dist - umbral_disonancia) / (1.0 - umbral_disonancia)
                                if umbral_disonancia < 1.0 else 0.0
                            )
                            delta = -delta_erosion_base * exceso
                    if self._ajustar_amistad(
                        gestor, miembro_id, lider_id, delta, reloj.tick_actual,
                    ):
                        self._stats_lealtad_aplicada += 1

    def _ajustar_amistad(
        self,
        gestor: GestorEntidades,
        autor_id: int,
        otro_id: int,
        delta: float,
        tick_actual: int,
    ) -> bool:
        """Escribe afinidad POSITIVA de `autor_id` hacia `otro_id`.

        Devuelve True si la afinidad se escribió de verdad (el autor es
        consciente y tiene Relaciones), False si el gate de consciencia u
        otro motivo impidió la escritura -- solo se usa para los stats de
        observación de SIMULACION_AUTO_TICKS; los llamadores de convivencia
        ignoran el retorno."""
        cap_mental = gestor.obtener_componente(autor_id, CapacidadMental)
        if (
            cap_mental is None
            or cap_mental.consciencia < self.umbral_consciencia_agencia
        ):
            return False
        relaciones = gestor.obtener_componente(autor_id, Relaciones)
        if relaciones is None:
            return False
        capacidad = capacidad_vinculos(cap_mental, self.config)
        ajustar_afinidad(
            relaciones,
            otro_id,
            delta,
            tick_actual,
            capacidad,
        )
        return True
