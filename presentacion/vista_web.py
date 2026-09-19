"""
presentacion/vista_web.py

Servidor HTTP integrado para monitoreo visual en tiempo real del mundo en el navegador.
Serializa el estado completo en un payload JSON puro consumido por polling desde el
visor terminal (presentacion/terminal_prototipo/).

RETIRADA DEL "CODICE CARTOGRAFICO" (2026-09-16): este archivo llegó a contener,
ademas de lo de abajo, un frontend HTML+Canvas completo ("Codice Cartografico",
pergamino/acuarela con proyeccion Caballera, hachurado vectorial de relieve,
poses de criatura por estado del ECS, etc.) servido en "/". Diego decidio
retirarlo por completo -- varias sesiones sin encontrar un estilo de arte
definitivo estaban restando foco al desarrollo del motor de simulacion -- y
quedarse en exclusiva con el visor terminal (estetica CRT ambar, mapa 100%
glifos/ASCII, sin ningun asset de imagen). El Codice esta documentado por
completo, mecanismo a mecanismo, en docs/informe_codice_cartografico.md, y su
codigo fuente exacto es recuperable en cualquier momento con
`git show 51c03e894da188f8dfc68bff4e513a7392a45175:presentacion/vista_web.py`
-- no se perdio nada, solo se saco de este archivo. El contrato JSON de mas
abajo (construir_instantanea) no formaba parte del Codice y no se ha tocado:
es la misma fuente de datos que ya consumia el visor terminal desde que se
conecto en vivo (2026-09-13).
"""

from __future__ import annotations

import http.server
import json
import mimetypes
import threading
from pathlib import Path
from typing import Any

from componentes.capacidad_mental import CapacidadMental
from componentes.construccion import Construccion
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.fogata import Fogata
from componentes.identidad import Identidad
from componentes.intencion import Intencion
from componentes.necesidades import Necesidades
from componentes.necromasa import Necromasa
from componentes.orientacion import Orientacion
from componentes.planta import Planta
from componentes.pool_fisico import PoolFisico
from componentes.pool_mental import PoolMental
from componentes.posicion import Posicion
from componentes.reproduccion import Reproduccion
from componentes.temperamento import Temperamento
from nucleo.clima import estacion_actual
from nucleo.entidad import GestorEntidades
from nucleo.mundo import Mundo
from nucleo.reloj import Reloj

RUTA_TERMINAL = Path(__file__).resolve().parent / "terminal_prototipo"
"""Unico frontend visual del proyecto desde 2026-09-16 (antes coexistia con
el Codice Cartografico retirado, ver docstring del modulo). Servido por
ESTE servidor -- mismo puerto, mismo /estado.json en vivo -- para no
duplicar el bucle de simulacion. terminal.html, datos.js y datos.json se
leen del disco en cada peticion (no se cachean en memoria): sigue siendo
un prototipo que Diego edita a mano."""


class ManejadorWeb(http.server.BaseHTTPRequestHandler):
    """Manejador HTTP simple sin librerías externas."""

    servidor_ref: ServidorWeb | None = None

    _ARCHIVOS_TERMINAL = {
        "/": "terminal.html",
        "/index.html": "terminal.html",
        "/terminal.html": "terminal.html",
        "/datos.js": "datos.js",
        "/datos.json": "datos.json",
    }

    # Rutas de control de partida (2026-09-16, ver
    # docs/superpowers/specs/2026-09-16-servidor-control-remoto-design.md):
    # cuales esperan un `factor`/`semilla` opcional en el body y cuales no
    # esperan body en absoluto -- una sola lista para no duplicar el set
    # de rutas válidas entre el despachador y la validación de método.
    _RUTAS_PARTIDA = {"/partida/nueva", "/partida/pausar", "/partida/reanudar", "/partida/velocidad", "/partida/finalizar"}

    def do_GET(self) -> None:
        if self.path in self._ARCHIVOS_TERMINAL:
            self._servir_terminal(self._ARCHIVOS_TERMINAL[self.path])
        elif self.path == "/estado.json":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            payload = self.servidor_ref.instantanea_json if self.servidor_ref else "{}"
            self.wfile.write(payload.encode("utf-8"))
        elif self.path.startswith("/sprites_criaturas/"):
            self._servir_sprite("sprites_criaturas", self.path[len("/sprites_criaturas/"):])
        elif self.path.startswith("/sprites_construcciones/"):
            self._servir_sprite("sprites_construcciones", self.path[len("/sprites_construcciones/"):])
        elif self.path.startswith("/sprites_flora/"):
            self._servir_sprite("sprites_flora", self.path[len("/sprites_flora/"):])
        elif self.path.startswith("/sprites_terreno/"):
            self._servir_sprite("sprites_terreno", self.path[len("/sprites_terreno/"):])
        elif self.path.startswith("/sprites_elementos/"):
            self._servir_sprite("sprites_elementos", self.path[len("/sprites_elementos/"):])
        else:
            self.send_response(404)
            self.end_headers()

    def _servir_terminal(self, nombre_archivo: str) -> None:
        destino = RUTA_TERMINAL / nombre_archivo
        if not destino.is_file():
            self.send_response(404)
            self.end_headers()
            return
        tipo, _ = mimetypes.guess_type(str(destino))
        self.send_response(200)
        self.send_header("Content-Type", tipo or "application/octet-stream")
        self.end_headers()
        self.wfile.write(destino.read_bytes())

    def _servir_sprite(self, subcarpeta: str, ruta_relativa: str) -> None:
        """Sprites reales de fauna, construcciones, flora (arbol/arbusto) y
        terreno (2026-09-16 fauna/construcciones/flora, 2026-09-19 terreno,
        ver presentacion/terminal_prototipo/sprites_criaturas/,
        sprites_construcciones/, sprites_flora/ y sprites_terreno/) --
        excepcion deliberada al
        "mapa 100% glifos" original del mismo dia: decision de Diego de usar
        un estilo hibrido ASCII+sprite, introduciendo assets solo donde se
        vayan encontrando los adecuados (ver CLAUDE.md, "Estado actual").
        Mismo guardia anti path-traversal que el resto de rutas de disco de
        este archivo."""
        from urllib.parse import unquote

        carpeta_sprites = (RUTA_TERMINAL / subcarpeta).resolve()
        destino = (carpeta_sprites / unquote(ruta_relativa)).resolve()
        if not destino.is_relative_to(carpeta_sprites):
            self.send_response(403)
            self.end_headers()
            return
        if not destino.is_file():
            self.send_response(404)
            self.end_headers()
            return
        tipo, _ = mimetypes.guess_type(str(destino))
        self.send_response(200)
        self.send_header("Content-Type", tipo or "application/octet-stream")
        self.end_headers()
        self.wfile.write(destino.read_bytes())

    def do_POST(self) -> None:
        """Control de partida (2026-09-16, ver spec del servidor de
        control remoto): nueva/pausar/reanudar/velocidad/finalizar. Si el
        servidor lo arrancó main.py en modo SIMULACION_MODO_VISUAL=1 (el
        camino CLI de siempre, sin GestorPartidas inyectado), estas rutas
        responden 501 -- ese modo sigue sin saber nada de control remoto,
        exactamente igual que antes de este círculo."""
        gestor_partidas = self.servidor_ref.gestor_partidas if self.servidor_ref else None
        if gestor_partidas is None:
            self.send_response(501)
            self.end_headers()
            return
        if self.path not in self._RUTAS_PARTIDA:
            self.send_response(404)
            self.end_headers()
            return

        longitud = int(self.headers.get("Content-Length", 0) or 0)
        cuerpo: dict[str, Any] = {}
        if longitud > 0:
            crudo = self.rfile.read(longitud)
            try:
                cuerpo = json.loads(crudo) if crudo else {}
            except json.JSONDecodeError:
                self._responder_json(400, {"ok": False, "error": "body JSON invalido"})
                return

        if self.path == "/partida/nueva":
            semilla = cuerpo.get("semilla")
            semilla_real = gestor_partidas.nueva(int(semilla) if semilla is not None else None)
            self._responder_json(200, {"ok": True, "semilla": semilla_real})
        elif self.path == "/partida/pausar":
            ok = gestor_partidas.pausar()
            self._responder_json(200 if ok else 409, {"ok": ok})
        elif self.path == "/partida/reanudar":
            ok = gestor_partidas.reanudar()
            self._responder_json(200 if ok else 409, {"ok": ok})
        elif self.path == "/partida/velocidad":
            factor = cuerpo.get("factor")
            if factor is None:
                self._responder_json(400, {"ok": False, "error": "falta 'factor'"})
                return
            nueva_velocidad = gestor_partidas.velocidad(float(factor))
            if nueva_velocidad is None:
                self._responder_json(409, {"ok": False, "error": "sin partida activa"})
            else:
                self._responder_json(200, {"ok": True, "velocidad": nueva_velocidad})
        else:  # /partida/finalizar -- idempotente, sin partida activa tambien responde ok
            gestor_partidas.finalizar()
            self._responder_json(200, {"ok": True})

    def _responder_json(self, codigo: int, payload: dict[str, Any]) -> None:
        cuerpo = json.dumps(payload).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def log_message(self, format: str, *args: Any) -> None:
        pass


class ServidorWeb:
    """Servidor multihilo desacoplado en background."""

    def __init__(self, puerto: int = 8765) -> None:
        self.puerto = puerto
        self.instantanea_json: str = "{}"
        # Sin tipo concreto (evita import circular: gestor_partidas.py ya
        # importa ServidorWeb de aqui) -- None mientras nadie lo inyecte,
        # que es exactamente el caso del modo CLI de main.py (ver
        # ManejadorWeb.do_POST, responde 501 cuando esto es None).
        self.gestor_partidas: Any | None = None
        ManejadorWeb.servidor_ref = self
        self._httpd = http.server.ThreadingHTTPServer(("0.0.0.0", self.puerto), ManejadorWeb)
        self._hilo: threading.Thread | None = None

    def iniciar(self) -> None:
        self._hilo = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._hilo.start()

    def detener(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()

    def actualizar_instantanea(self, payload: dict[str, Any]) -> None:
        self.instantanea_json = json.dumps(payload)


def construir_instantanea(
    mundo: Mundo,
    gestor: GestorEntidades,
    reloj: Reloj,
    cronica: list[str],
    semilla: int,
) -> dict[str, Any]:
    """Construye el DTO serializable para la interfaz web.

    `semilla` explicita desde 2026-09-16 (antes se leia de
    mundo.config.get("semilla_por_defecto"), que funcionaba solo porque
    la semilla nunca cambiaba en caliente -- ver
    docs/superpowers/specs/2026-09-16-servidor-control-remoto-design.md):
    una partida lanzada desde el servidor de control web puede tener una
    semilla aleatoria distinta de la del config, y este DTO no tiene
    ninguna otra forma de saberla.

    Contrato honesto (Principio 4): cada campo expuesto aqui lee un
    componente o propiedad que YA existe en el ECS -- ningun dato se
    inventa o se aproxima para rellenar el esquema de la propuesta visual.
    Ejemplos de omision deliberada: DimensionesFisicas.peso NO se expone
    como "peso_kg" (su docstring dice explicitamente que la escala sigue
    siendo abstracta, sin kilogramos reales todavia); Celda.elevacion/
    lluvia/temperatura/tipo_agua se exponen tal cual, sin redondeos que
    inventen precision que no existe.
    """
    zona = mundo.territorio.zonas[0]
    censo: dict[str, int] = {}
    lista_entidades: list[dict[str, Any]] = []

    # Plantas maduras/en crecimiento por celda (entidades ECS con
    # Posicion, ver componentes/planta.py) -- se adjuntan a su celda en
    # vez de mezclarse en la lista de "entidades" biologicas: para el
    # renderizado del mapa son una propiedad del terreno, no un agente.
    #
    # CORRECCION (2026-08-31, hallazgo real tras el Circulo 3 de
    # profundidad -- ver CLAUDE.md): este DTO solo dibuja zonas[0]
    # (superficie), pero las tres consultas de entidades de aqui abajo no
    # filtraban por zona_idx -- una entidad en una cueva con las MISMAS
    # coordenadas numericas que una de superficie se mezclaba sin
    # distincion (dos criaturas en (5,5) de zonas distintas llegaban
    # como dos filas identicas, sin ningun campo que las diferenciara;
    # una planta de cueva podia incluso PISAR la entrada del dict de una
    # planta de superficie, misma clave (x,y)). No es "todavia no hay
    # arte de cueva" (omision aceptada) -- es corromper la vista de
    # superficie en cuanto algo cruza a una cueva por deambulacion
    # normal (el portal no exige ninguna decision consciente, ver
    # sistema_movimiento.py). Filtrar por zona_idx==0 aqui no es una
    # capacidad nueva, es la correccion minima para que la vista que YA
    # existe (solo superficie) deje de mentir cuando hay contenido bajo
    # tierra -- un selector de zona real sigue siendo trabajo de
    # presentacion aparte, no resuelto aqui.
    # LISTA por celda, no un unico dict: desde "cupo de espacio compartido
    # por celda" (2026-09-03) una especie de cobertura (hierba_silvestre,
    # flor_silvestre, liquen, musgo...) puede cohabitar la misma celda con
    # una especie competidora (arbol/arbusto) -- con una clave (x,y) que
    # sobrescribia en vez de acumular, la cobertura quedaba silenciosamente
    # tapada por la ultima planta insertada. Bug real, no solo de esta
    # vista: confirmado contra el motor (semilla 42) que 101 celdas tenian
    # una especie de cobertura oculta de esta forma.
    plantas_por_celda: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for pid in sorted(gestor.entidades_con(Planta, Posicion)):
        planta = gestor.obtener_componente(pid, Planta)
        pos_p = gestor.obtener_componente(pid, Posicion)
        if planta and pos_p and pos_p.zona_idx == 0:
            plantas_por_celda.setdefault((pos_p.x, pos_p.y), []).append({
                "especie": planta.especie,
                "etapa": round(planta.etapa, 3),
            })

    ticks_por_anio = Reloj.TICKS_POR_DIA * Reloj.DIAS_POR_ESTACION * Reloj.ESTACIONES_POR_ANIO

    # 1. Entidades Biologicas Vivas
    for eid in sorted(gestor.entidades_con(Identidad, Posicion)):
        ident = gestor.obtener_componente(eid, Identidad)
        pos = gestor.obtener_componente(eid, Posicion)
        if not (ident and pos) or pos.zona_idx != 0:
            continue

        esp = ident.especie.value
        censo[esp] = censo.get(esp, 0) + 1

        dato: dict[str, Any] = {
            "id": eid,
            "tipo": esp,
            "nombre": ident.nombre,
            "x": pos.x,
            "y": pos.y,
            "edad_anios": round((reloj.tick_actual - ident.tick_nacimiento) / ticks_por_anio, 2),
            "id_madre": ident.id_madre,
            "id_padre": ident.id_padre,
        }

        intencion = gestor.obtener_componente(eid, Intencion)
        if intencion:
            dato["accion"] = intencion.accion.value

        orientacion = gestor.obtener_componente(eid, Orientacion)
        if orientacion:
            dato["orientacion"] = orientacion.direccion

        reproduccion = gestor.obtener_componente(eid, Reproduccion)
        if reproduccion:
            dato["sexo"] = reproduccion.sexo.value

        necesidades = gestor.obtener_componente(eid, Necesidades)
        if necesidades:
            dato["necesidades"] = {
                "saciedad": round(necesidades.saciedad, 3),
                "energia": round(necesidades.energia, 3),
                "seguridad": round(necesidades.seguridad, 3),
                "hidratacion": round(necesidades.hidratacion, 3),
                "aliviado": round(necesidades.aliviado, 3),
                "oxigenacion": round(necesidades.oxigenacion, 3),
                "confort_termico": round(necesidades.confort_termico, 3),
                "impulso_reproductivo": round(necesidades.impulso_reproductivo, 3),
            }

        pool_fisico = gestor.obtener_componente(eid, PoolFisico)
        if pool_fisico:
            dato["pool_fisico"] = {
                "vitalidad": round(pool_fisico.vitalidad, 3),
                "resistencia": round(pool_fisico.resistencia, 3),
            }

        dimensiones = gestor.obtener_componente(eid, DimensionesFisicas)
        if dimensiones:
            dato["dimensiones"] = {
                "peso": round(dimensiones.peso, 3),
                "altura_m": round(dimensiones.altura, 3),
                "fuerza": round(dimensiones.fuerza, 3),
                "agilidad": round(dimensiones.agilidad, 3),
                "vitalidad_maxima": round(dimensiones.vitalidad_maxima, 3),
                "resistencia_maxima": round(dimensiones.resistencia_maxima, 3),
            }

        pool_mental = gestor.obtener_componente(eid, PoolMental)
        if pool_mental:
            dato["pool_mental"] = {"estabilidad": round(pool_mental.estabilidad, 3)}

        capacidad_mental = gestor.obtener_componente(eid, CapacidadMental)
        if capacidad_mental:
            dato["estabilidad_mental_maxima"] = round(capacidad_mental.estabilidad_mental_maxima, 3)
            # Circulo 1 (2026-08-27): quien es "consciente" lo decide el
            # motor con el mismo umbral de agencia que usa el sistema de
            # decision (config/constantes.yaml, decision
            # .umbral_consciencia_agencia) -- una sola fuente de verdad; el
            # visor solo renderiza el flag (a zoom macro solo se marcan
            # las conscientes, decision de Diego).
            umbral = (
                mundo.config.get("decision", {}).get("umbral_consciencia_agencia", 0.3)
            )
            dato["consciencia"] = round(capacidad_mental.consciencia, 3)
            dato["consciente"] = capacidad_mental.consciencia >= umbral

        temperamento = gestor.obtener_componente(eid, Temperamento)
        if temperamento:
            dato["temperamento"] = {
                "valentia": round(temperamento.valentia, 3),
                "sociabilidad": round(temperamento.sociabilidad, 3),
                "agresividad": round(temperamento.agresividad, 3),
            }

        lista_entidades.append(dato)

    # 2. Entidades Inertes (Necromasa)
    for nid in sorted(gestor.entidades_con(Necromasa, Posicion)):
        nec = gestor.obtener_componente(nid, Necromasa)
        pos_n = gestor.obtener_componente(nid, Posicion)
        if nec and pos_n and pos_n.zona_idx == 0:
            censo["necromasa"] = censo.get("necromasa", 0) + 1
            lista_entidades.append(
                {
                    "id": nid,
                    "tipo": "necromasa",
                    "x": pos_n.x,
                    "y": pos_n.y,
                    # CÍRCULO 2 de materiales físicos (2026-08-30): "masa"
                    # se queda como total (compatibilidad del DTO), "masas"
                    # añade el desglose por material para el panel de
                    # inspección (tejido_blando vs. hueso persistente).
                    "masa": round(sum(nec.masas.values()), 2),
                    "masas": {k: round(v, 2) for k, v in nec.masas.items()},
                    "origen": nec.origen_especie,
                }
            )

    # 2.5 Construcciones (refugio/almacen/salon_comun/cocina) -- entidad
    # física real desde 2026-08-30 (componentes/construccion.py), nunca
    # expuesta hasta ahora en este DTO: el visor antiguo (Códice
    # Cartográfico) no llegó a dibujar ninguna construcción en ningún
    # momento de su historia (verificado, cero referencias a "refugio"/
    # "almacen" en este fichero antes de esta línea). "completado_alguna_vez"
    # es lo que decide si ya existe una estructura reconocible que dibujar
    # (mismo criterio que SistemaAsentamiento usa para pertenencia, ver
    # CLAUDE.md "Corrección de diseño... completado_alguna_vez") -- una
    # construcción a medio empezar (progreso<1.0, nunca completada) no
    # tiene nada que mostrar todavía.
    construcciones_data: list[dict[str, Any]] = []
    for cid in sorted(gestor.entidades_con(Construccion, Posicion)):
        constr = gestor.obtener_componente(cid, Construccion)
        pos_c = gestor.obtener_componente(cid, Posicion)
        if constr and pos_c and pos_c.zona_idx == 0 and constr.completado_alguna_vez:
            construcciones_data.append(
                {
                    "id": cid,
                    "tipo": constr.tipo,
                    "x": pos_c.x,
                    "y": pos_c.y,
                    "progreso": round(constr.progreso, 3),
                }
            )

    # 2.6 Fogatas (componentes/fogata.py, 2026-09-19) -- fuego controlado
    # y beneficioso (sube el objetivo de confort térmico de quien esté en
    # su celda, ver sistema_necesidades.py), entidad real desde antes de
    # esta sesión pero NUNCA expuesta hasta ahora en este DTO (verificado:
    # cero referencias a "Fogata"/"fogata" en este fichero antes de esta
    # línea) -- el visor no tenía forma de saber que existían. Sin
    # "completado_alguna_vez" ni progreso: una Fogata existe entera desde
    # que se enciende (ver nucleo/entidad.py::crear_fogata) o no existe.
    fogatas_data: list[dict[str, Any]] = []
    for fid in sorted(gestor.entidades_con(Fogata, Posicion)):
        fog = gestor.obtener_componente(fid, Fogata)
        pos_f = gestor.obtener_componente(fid, Posicion)
        if fog and pos_f and pos_f.zona_idx == 0:
            fogatas_data.append(
                {
                    "id": fid,
                    "x": pos_f.x,
                    "y": pos_f.y,
                    "combustible_restante": round(fog.combustible_restante, 2),
                }
            )

    # 3. Grid de celdas -- solo campos que ya existen en nucleo/celda.py.
    celdas_data: list[list[dict[str, Any]]] = []
    for y in range(zona.alto):
        fila: list[dict[str, Any]] = []
        for x in range(zona.ancho):
            c = zona.obtener_celda(x, y)
            fila.append(
                {
                    "x": x,
                    "y": y,
                    "bioma": c.tipo_terreno.value,
                    "elevacion": round(c.elevacion, 3),
                    "lluvia": round(c.lluvia, 3),
                    "temperatura": round(c.temperatura, 3),
                    "tiene_agua": c.tiene_agua,
                    "tipo_agua": c.tipo_agua,
                    "profundidad_agua": round(c.profundidad_agua, 3),
                    "profundidad_charco": round(c.profundidad_charco, 3),
                    "en_llamas": c.en_llamas,
                    "fertilidad": round(c.fertilidad, 3),
                    "recursos": {k: round(v, 2) for k, v in c.recursos.items()},
                    "plantas": plantas_por_celda.get((x, y), []),
                }
            )
        celdas_data.append(fila)

    clima_actual = getattr(zona, "clima_actual", None)

    return {
        "tick": reloj.tick_actual,
        "dia": reloj.dia,
        "anio": reloj.anio,
        # (2026-08-23) mismo bug que en sistema_necesidades.py/sistema_flora.py:
        # Reloj.estacion es un int creciente, no el Enum Estacion.
        "estacion": estacion_actual(reloj.estacion).value,
        "clima": clima_actual.value if clima_actual else "despejado",
        "semilla": semilla,
        # Circulo 3: umbrales del clasificador para el lavado continuo del
        # visor -- una sola fuente de verdad (config bioma).
        # (2026-08-29, fix de auditoria) Esta clave estaba literalmente
        # duplicada dos veces seguidas, idéntica -- un dict-literal de
        # Python descarta en silencio la primera aparición, así que no
        # rompía nada, pero era codigo sobrante (probablemente de un
        # merge o una edicion repetida) sin ningun proposito.
        "bioma_umbrales": {
            "umbral_elevacion_montana": mundo.config.get("bioma", {}).get("umbral_elevacion_montana", 0.6665),
            "umbral_temperatura_tundra": mundo.config.get("bioma", {}).get("umbral_temperatura_tundra", 0.1346),
            "umbral_lluvia_desierto": mundo.config.get("bioma", {}).get("umbral_lluvia_desierto", 0.3909),
            "umbral_lluvia_bosque": mundo.config.get("bioma", {}).get("umbral_lluvia_bosque", 0.6041),
        },
        "ancho": zona.ancho,
        "alto": zona.alto,
        "censo": censo,
        "entidades": lista_entidades,
        "construcciones": construcciones_data,
        "fogatas": fogatas_data,
        "celdas": celdas_data,
        "cronica": cronica,
    }
