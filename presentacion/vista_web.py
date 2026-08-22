"""Vista web: primera capa de presentacion mas alla de la terminal
(discutida y confirmada con Diego -- ver tambien config/constantes.yaml,
seccion 'visual'). Mapa en tiempo real en el navegador, coloreado por
bioma+elevacion+agua+fuego+recurso, con las criaturas encima como emoji
por especie -- mismo espiritu que _simbolo_celda/_estilo_celda de
main.py (funciones puras que leen Celda y deciden como mostrarla), solo
que aqui el resultado es JSON para que lo pinte el navegador, no texto
para una terminal.

Arquitectura, deliberadamente minima (coherente con "sin frameworks
pesados"): SOLO libreria estandar. Un ThreadingHTTPServer sirve dos
cosas -- la pagina HTML/CSS/JS (estatica, incrustada aqui mismo, sin
build step) en "/", y la ultima instantanea del mundo como JSON en
"/estado". La pagina hace fetch() a "/estado" cada pocos milisegundos y
repinta un <canvas> -- polling simple, no WebSockets: esta simulacion no
corre a fotogramas por segundo, un tick nuevo cada X decimas de segundo
(ver 'visual.segundos_por_tick') es sobradamente lento para que preguntar
en vez de que nos avisen sea indistinguible en la practica.

Quien avanza el tiempo real NO es este modulo -- eso vive en main.py (un
tercer modo de ejecucion, 'modo visual', distinto de interactivo/
headless: avanza solo, a una cadencia fija de reloj, en vez de esperar
Enter o correr a maxima velocidad). Este modulo solo construye
instantaneas (funcion pura, sin tocar gestor/zona) y las sirve; nunca
llama a gestor.entidades_con(...) para escribir nada, ni conoce ningun
sistema del motor -- mismo desacople que ya tenia presentacion/narrador.py
respecto a como se muestra el texto que genera.

Simbolo por especie (tabla EMOJI_POR_ESPECIE): deliberadamente una tabla,
no un if/else -- anadir una especie nueva (la proxima criatura que se
diseñe) es una linea aqui, no logica nueva. Nivel de detalle visual
elegido con Diego para esta primera pasada: emoji via canvas fillText, ni
formas geometricas (mas pobre visualmente) ni sprites de verdad (asset
grafico real, fuera de alcance ahora) -- intencion declarada de Diego a
largo plazo: mundo en pixel art con animaciones. Esta arquitectura no
compromete esa evolucion futura: el separador entre "que hay en el mundo"
(instantanea JSON) y "como se dibuja" (la funcion JS de pintado) es
exactamente el punto donde algun dia se enchufarian sprites en vez de
emoji, sin tocar el resto.
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from componentes.identidad import Identidad
from componentes.posicion import Posicion

EMOJI_POR_ESPECIE = {
    "gnomo": "\U0001F9D1",  # 🧑
    "lobo": "\U0001F43A",   # 🐺
    "conejo": "\U0001F430",  # 🐰 (2026-08-20, introduccion de conejo/ardilla)
    "ardilla": "\U0001F43F",  # 🐿️
}


def construir_instantanea(gestor, zona, reloj, config, cronica=()) -> dict:
    """Funcion pura: lee gestor/zona/reloj, no los muta. Mismo criterio
    que presentacion/narrador.py -- decide QUE se representa, no como se
    pinta (eso es la pagina HTML/JS de abajo).

    cronica (correccion posterior, a peticion de Diego: "que en la
    interfaz haya un apartado donde el narrador vaya contando que pasa"):
    lista de frases YA narradas (presentacion/narrador.py:narrar) que
    main.py acumula tick a tick -- este modulo no las genera ni las
    guarda, solo las traslada al JSON tal cual se le pasan. La
    acumulacion/limite de tamano vive en main.py (deque acotado), no
    aqui, para que esta funcion siga siendo pura y sin estado propio."""
    from nucleo.clima import estacion_actual

    celdas = []
    for x, y, celda in zona.celdas():
        celdas.append({
            "x": x, "y": y,
            "bioma": celda.tipo_terreno.value,
            "elevacion": round(celda.elevacion, 3),
            "tipo_agua": celda.tipo_agua,
            "tiene_recurso": celda.tiene_recurso,
            "en_llamas": celda.en_llamas,
        })

    entidades = []
    for id_e in gestor.entidades_con(Posicion, Identidad):
        pos = gestor.obtener_componente(id_e, Posicion)
        identidad = gestor.obtener_componente(id_e, Identidad)
        entidades.append({"id": id_e, "x": pos.x, "y": pos.y, "especie": identidad.especie.value})

    return {
        "ancho": zona.ancho, "alto": zona.alto,
        "tick": reloj.tick_actual, "dia": reloj.dia, "anio": reloj.anio,
        "estacion": estacion_actual(reloj.estacion).value,
        "clima": zona.clima_actual.value,
        "celdas": celdas,
        "entidades": entidades,
        "cronica": list(cronica),
    }


class _EstadoCompartido:
    """Unico punto de mutacion concurrente de este modulo: main.py escribe
    una instantanea nueva cada tick (hilo principal), el servidor HTTP la
    lee cada vez que el navegador hace fetch() (hilo del servidor) -- un
    Lock basta, la frecuencia de ambos lados es baja (ticks cada decimas
    de segundo, polling cada pocos cientos de milisegundos)."""

    def __init__(self):
        self._lock = threading.Lock()
        self._instantanea: dict | None = None

    def actualizar(self, instantanea: dict) -> None:
        with self._lock:
            self._instantanea = instantanea

    def leer(self) -> dict | None:
        with self._lock:
            return self._instantanea


class _ManejadorVista(BaseHTTPRequestHandler):
    estado: _EstadoCompartido = None  # inyectado por iniciar_servidor() via subclase dinamica

    def log_message(self, formato, *args):
        pass  # silencia el log por defecto (una linea por peticion) -- no aporta nada aqui, es puro ruido

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._responder(200, "text/html; charset=utf-8", _PAGINA_HTML.encode("utf-8"))
        elif self.path == "/estado":
            instantanea = self.estado.leer()
            cuerpo = json.dumps(instantanea if instantanea is not None else {}).encode("utf-8")
            self._responder(200, "application/json; charset=utf-8", cuerpo)
        else:
            self._responder(404, "text/plain; charset=utf-8", b"no encontrado")

    def _responder(self, codigo: int, tipo_contenido: str, cuerpo: bytes) -> None:
        self.send_response(codigo)
        self.send_header("Content-Type", tipo_contenido)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)


class ServidorVista:
    """Envoltorio fino sobre ThreadingHTTPServer -- expone solo lo que
    main.py necesita (actualizar la instantanea, conocer la URL), oculta
    el resto (hilo, socket, manejador)."""

    def __init__(self, servidor_http: ThreadingHTTPServer, estado: _EstadoCompartido, puerto: int):
        self._servidor_http = servidor_http
        self._estado = estado
        self.url = f"http://localhost:{puerto}"

    def actualizar(self, instantanea: dict) -> None:
        self._estado.actualizar(instantanea)


def iniciar_servidor(puerto: int) -> ServidorVista:
    """Arranca el servidor en un hilo daemon (muere solo al salir el
    proceso principal, sin necesidad de un apagado explicito -- coherente
    con que main.py no tiene hoy ningun otro recurso que cerrar
    ordenadamente al terminar, ver el finally de main())."""
    estado = _EstadoCompartido()
    manejador = type("_ManejadorVistaConEstado", (_ManejadorVista,), {"estado": estado})
    servidor_http = ThreadingHTTPServer(("localhost", puerto), manejador)
    hilo = threading.Thread(target=servidor_http.serve_forever, daemon=True)
    hilo.start()
    return ServidorVista(servidor_http, estado, puerto)


# Colores por bioma en RGB base (paleta real, no la de 16 colores ANSI de
# la terminal) -- JS los oscurece/aclara segun la elevacion de cada celda
# (ver _sombrear en el JS de abajo) para dar sensacion de relieve sin
# necesitar ningun dato nuevo, solo el campo de elevacion que ya existe.
_PAGINA_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Un mundo vivo</title>
<style>
  body { background: #111; color: #ddd; font-family: monospace; padding: 16px; }
  #fila-superior { display: flex; gap: 24px; }
  canvas { image-rendering: pixelated; border: 1px solid #444; }
  #hud div { margin-bottom: 4px; }
  #hud h2 { font-size: 14px; margin: 12px 0 4px; color: #9c9; }
  #cronica-wrap { margin-top: 16px; max-width: 900px; }
  #cronica-wrap h2 { font-size: 14px; margin: 0 0 4px; color: #9c9; }
  #cronica {
    height: 180px; overflow-y: auto; background: #1a1a1a; border: 1px solid #444;
    padding: 8px; font-size: 13px; line-height: 1.5;
  }
  #cronica div { color: #bbb; }
  #cronica div:last-child { color: #eee; }
</style>
</head>
<body>
  <div id="fila-superior">
    <canvas id="mapa"></canvas>
    <div id="hud">
      <h2>Estado</h2>
      <div id="tick">tick=-</div>
      <div id="fecha">dia=- anio=-</div>
      <div id="clima">estacion=- clima=-</div>
      <h2>Poblacion</h2>
      <div id="poblacion"></div>
    </div>
  </div>
  <div id="cronica-wrap">
    <h2>Cronica</h2>
    <div id="cronica"></div>
  </div>
<script>
const TAM_CELDA = 22;
const COLOR_BIOMA = {
  pradera: [163, 177, 82],
  bosque: [45, 106, 79],
  desierto: [214, 189, 118],
  montana: [120, 120, 128],
  tundra: [226, 232, 235],
};
const COLOR_AGUA = {
  rio: "rgba(66, 135, 245, 0.8)",
  lago: "rgba(30, 80, 160, 0.8)",
  poza: "rgba(100, 180, 200, 0.85)",
};
const EMOJI_POR_ESPECIE = { gnomo: "\\u{1F9D1}", lobo: "\\u{1F43A}", conejo: "\\u{1F430}", ardilla: "\\u{1F43F}" };

const lienzo = document.getElementById("mapa");
const ctx = lienzo.getContext("2d");
let dimensionado = false;

function sombrear([r, g, b], elevacion) {
  // aclara/oscurece el color base de bioma segun la elevacion [0,1] --
  // da sensacion de relieve reutilizando un dato que ya existe, sin
  // inventar ninguna textura ni sprite.
  const factor = 0.65 + 0.55 * elevacion;
  return `rgb(${Math.min(255, r * factor) | 0}, ${Math.min(255, g * factor) | 0}, ${Math.min(255, b * factor) | 0})`;
}

function dibujar(estado) {
  if (!estado.celdas) return;
  if (!dimensionado) {
    lienzo.width = estado.ancho * TAM_CELDA;
    lienzo.height = estado.alto * TAM_CELDA;
    dimensionado = true;
  }

  const ahora = Date.now();
  const pulso = 0.6 + 0.4 * Math.abs(Math.sin(ahora / 220));  // parpadeo del fuego

  for (const celda of estado.celdas) {
    const px = celda.x * TAM_CELDA;
    const py = celda.y * TAM_CELDA;

    ctx.fillStyle = sombrear(COLOR_BIOMA[celda.bioma] || [80, 80, 80], celda.elevacion);
    ctx.fillRect(px, py, TAM_CELDA, TAM_CELDA);

    if (celda.tiene_recurso) {
      ctx.fillStyle = "rgba(255, 255, 255, 0.55)";
      ctx.beginPath();
      ctx.arc(px + TAM_CELDA - 5, py + TAM_CELDA - 5, 2.5, 0, Math.PI * 2);
      ctx.fill();
    }

    if (celda.tipo_agua) {
      ctx.fillStyle = COLOR_AGUA[celda.tipo_agua] || "rgba(66,135,245,0.8)";
      ctx.fillRect(px, py, TAM_CELDA, TAM_CELDA);
    }

    if (celda.en_llamas) {
      ctx.fillStyle = `rgba(230, 80, 20, ${pulso})`;
      ctx.fillRect(px, py, TAM_CELDA, TAM_CELDA);
    }
  }

  ctx.font = `${TAM_CELDA - 4}px sans-serif`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  const poblacion = {};
  for (const e of (estado.entidades || [])) {
    const emoji = EMOJI_POR_ESPECIE[e.especie] || "?";
    ctx.fillText(emoji, e.x * TAM_CELDA + TAM_CELDA / 2, e.y * TAM_CELDA + TAM_CELDA / 2);
    poblacion[e.especie] = (poblacion[e.especie] || 0) + 1;
  }

  document.getElementById("tick").textContent = `tick=${estado.tick}`;
  document.getElementById("fecha").textContent = `dia=${estado.dia} anio=${estado.anio}`;
  document.getElementById("clima").textContent = `estacion=${estado.estacion} clima=${estado.clima}`;
  document.getElementById("poblacion").innerHTML = Object.entries(poblacion)
    .map(([especie, n]) => `${EMOJI_POR_ESPECIE[especie] || "?"} ${especie}: ${n}`)
    .join("<br>");
}

function escaparHtml(texto) {
  const d = document.createElement("div");
  d.textContent = texto;
  return d.innerHTML;
}

function actualizarCronica(estado) {
  // Solo se llama cuando llega una instantanea NUEVA del servidor (dentro
  // de actualizar(), no del redibujado a 100ms) -- si se re-renderizara
  // a ese ritmo se perderia la posicion de scroll cada vez que alguien
  // intenta leer hacia atras. cercaDelFondo: solo auto-scrollea si el
  // usuario ya estaba viendo lo mas reciente, para no arrastrarlo hacia
  // abajo mientras revisa la cronica pasada.
  const contenedor = document.getElementById("cronica");
  const cercaDelFondo = contenedor.scrollHeight - contenedor.scrollTop - contenedor.clientHeight < 40;
  contenedor.innerHTML = (estado.cronica || []).map(f => `<div>${escaparHtml(f)}</div>`).join("");
  if (cercaDelFondo) {
    contenedor.scrollTop = contenedor.scrollHeight;
  }
}

let ultimaInstantanea = null;

async function actualizar() {
  try {
    const resp = await fetch("/estado");
    ultimaInstantanea = await resp.json();
    actualizarCronica(ultimaInstantanea);
  } catch (e) {
    // servidor no listo todavia o main.py aun no ha producido la primera
    // instantanea -- se reintenta solo en el siguiente intervalo, sin
    // ruido en consola por cada fallo transitorio del primer segundo.
  }
}

// dos ritmos distintos a proposito: 'actualizar' pregunta al servidor
// solo cada 250ms (no hace falta mas, un tick nuevo tarda bastante mas
// que eso); 'dibujar' repinta a 100ms usando la ULTIMA instantanea
// conocida, para que el parpadeo del fuego (que depende del reloj del
// navegador, no de si llego un tick nuevo) se vea fluido sin machacar la
// red con peticiones innecesarias.
setInterval(actualizar, 250);
setInterval(() => { if (ultimaInstantanea) dibujar(ultimaInstantanea); }, 100);
actualizar();
</script>
</body>
</html>
"""
