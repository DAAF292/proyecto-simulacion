"""
presentacion/vista_web.py

Servidor HTTP integrado para monitoreo visual en tiempo real del mundo en el navegador.
Serializa el estado completo en un payload JSON puro consumido por polling desde el canvas.
"""

from __future__ import annotations

import http.server
import json
import threading
from typing import Any

from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Identidad
from componentes.intencion import Intencion
from componentes.necesidades import Necesidades
from componentes.necromasa import Necromasa
from componentes.pool_fisico import PoolFisico
from componentes.pool_mental import PoolMental
from componentes.posicion import Posicion
from nucleo.entidad import GestorEntidades
from nucleo.mundo import Mundo
from nucleo.reloj import Reloj

HTML_VISOR = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Un Mundo Vivo - Vista Web</title>
  <style>
    body { background: #1a1a1a; color: #e0e0e0; font-family: monospace; margin: 0; padding: 15px; display: flex; flex-direction: column; align-items: center; }
    #contenedor { display: flex; gap: 20px; max-width: 1200px; width: 100%; }
    #canvas-mapa { border: 2px solid #333; background: #000; }
    #panel-lateral { flex: 1; display: flex; flex-direction: column; gap: 10px; }
    .card { background: #242424; border: 1px solid #3a3a3a; padding: 10px; border-radius: 4px; font-size: 12px; }
    #cronica { height: 280px; overflow-y: auto; display: flex; flex-direction: column-reverse; background: #181818; padding: 8px; border: 1px solid #333; font-size: 11px; }
    .linea-cronica { margin-bottom: 4px; line-height: 1.3; border-bottom: 1px solid #222; padding-bottom: 2px; }
    .tag { font-weight: bold; padding: 2px 4px; border-radius: 2px; }
    .tag-gnomo { color: #5dade2; }
    .tag-lobo { color: #e74c3c; }
    .tag-conejo { color: #f39c12; }
    .tag-ardilla { color: #2ecc71; }
    .tag-necromasa { color: #95a5a6; }
  </style>
</head>
<body>
  <h2>🌲 Un Mundo Vivo — Panel de Simulación</h2>
  <div id="contenedor">
    <canvas id="canvas-mapa" width="560" height="560"></canvas>
    <div id="panel-lateral">
      <div class="card" id="info-mundo">Cargando...</div>
      <div class="card" id="info-poblacion">Población: -</div>
      <div class="card">
        <strong>📜 Crónica en Vivo:</strong>
        <div id="cronica"></div>
      </div>
    </div>
  </div>

  <script>
    const canvas = document.getElementById('canvas-mapa');
    const ctx = canvas.getContext('2d');
    const COLORES_TERRENO = {
      'bosque': '#1e4d2b', 'pradera': '#4a7c29', 'montana': '#7f8c8d',
      'desierto': '#d4ac0d', 'tundra': '#aeb6bf', 'agua': '#2980b9'
    };
    const GLIFOS = { 'gnomo': '🧙', 'lobo': '🐺', 'conejo': '🐇', 'ardilla': '🐿️', 'necromasa': '🦴' };

    async function actualizar() {
      try {
        const resp = await fetch('/estado.json');
        if (!resp.ok) return;
        const data = await resp.json();

        document.getElementById('info-mundo').innerHTML = 
          `<strong>Tick:</strong> ${data.tick} | <strong>Día:</strong> ${data.dia} | <strong>Estación:</strong> ${data.estacion}<br>` +
          `<strong>Clima:</strong> ${data.clima}`;

        document.getElementById('info-poblacion').innerHTML = 
          `<strong>Vivos:</strong> Gnomos: ${data.censo.gnomo || 0} | Lobos: ${data.censo.lobo || 0} | ` +
          `Conejos: ${data.censo.conejo || 0} | Ardillas: ${data.censo.ardilla || 0} | ` +
          `<strong>Restos (Necromasa):</strong> ${data.censo.necromasa || 0}`;

        const celdas = data.grid;
        const tam = canvas.width / data.ancho;

        for (let y = 0; y < data.alto; y++) {
          for (let x = 0; x < data.ancho; x++) {
            const c = celdas[y][x];
            ctx.fillStyle = c.en_llamas ? '#c0392b' : (c.tiene_agua ? COLORES_TERRENO['agua'] : (COLORES_TERRENO[c.terreno] || '#111'));
            ctx.fillRect(x * tam, y * tam, tam, tam);

            if (c.profundidad_charco > 0 && !c.tiene_agua) {
              ctx.fillStyle = 'rgba(52, 152, 219, 0.4)';
              ctx.fillRect(x * tam, y * tam, tam, tam);
            }
          }
        }

        ctx.font = `${tam * 0.7}px sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';

        data.entidades.forEach(e => {
          const glifo = GLIFOS[e.tipo] || '❓';
          ctx.fillText(glifo, e.x * tam + tam / 2, e.y * tam + tam / 2);
        });

        const divCronica = document.getElementById('cronica');
        divCronica.innerHTML = data.cronica.map(l => `<div class="linea-cronica">${l}</div>`).join('');

      } catch (err) {
        console.error("Error al actualizar instantánea:", err);
      }
    }
    setInterval(actualizar, 250);
  </script>
</body>
</html>
"""


class ManejadorWeb(http.server.BaseHTTPRequestHandler):
    """Manejador HTTP simple sin librerías externas."""

    servidor_ref: ServidorWeb | None = None

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_VISOR.encode("utf-8"))
        elif self.path == "/estado.json":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            payload = self.servidor_ref.instantanea_json if self.servidor_ref else "{}"
            self.wfile.write(payload.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        pass


class ServidorWeb:
    """Servidor multihilo desacoplado en background."""

    def __init__(self, puerto: int = 8765) -> None:
        self.puerto = puerto
        self.instantanea_json: str = "{}"
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
) -> dict[str, Any]:
    """Construye el DTO serializable para la interfaz web."""
    zona = mundo.territorio.zonas[0]
    censo: dict[str, int] = {}

    lista_entidades: list[dict[str, Any]] = []

    # 1. Entidades Biológicas Vivas
    for eid in sorted(gestor.entidades_con(Identidad, Posicion)):
        ident = gestor.obtener_componente(eid, Identidad)
        pos = gestor.obtener_componente(eid, Posicion)
        if ident and pos:
            esp = ident.especie.value
            censo[esp] = censo.get(esp, 0) + 1
            lista_entidades.append(
                {
                    "id": eid,
                    "tipo": esp,
                    "x": pos.x,
                    "y": pos.y,
                    "nombre": ident.nombre,
                }
            )

    # 2. Entidades Inertes (Necromasa)
    for nid in sorted(gestor.entidades_con(Necromasa, Posicion)):
        nec = gestor.obtener_componente(nid, Necromasa)
        pos_n = gestor.obtener_componente(nid, Posicion)
        if nec and pos_n:
            censo["necromasa"] = censo.get("necromasa", 0) + 1
            lista_entidades.append(
                {
                    "id": nid,
                    "tipo": "necromasa",
                    "x": pos_n.x,
                    "y": pos_n.y,
                    "masa": round(nec.masa_organica, 2),
                    "origen": nec.origen_especie,
                }
            )

    grid_data: list[list[dict[str, Any]]] = []
    for y in range(zona.alto):
        fila: list[dict[str, Any]] = []
        for x in range(zona.ancho):
            c = zona.obtener_celda(x, y)
            fila.append(
                {
                    "terreno": c.tipo_terreno.value,
                    "tiene_agua": c.tiene_agua,
                    "profundidad_charco": round(c.profundidad_charco, 3),
                    "en_llamas": c.en_llamas,
                    "fertilidad": round(c.fertilidad, 2),
                }
            )
        grid_data.append(fila)

    clima_actual = getattr(zona, "clima_actual", None)

    return {
        "tick": reloj.tick_actual,
        "dia": reloj.dia,
        "estacion": reloj.estacion.value,
        "clima": clima_actual.value if clima_actual else "despejado",
        "ancho": zona.ancho,
        "alto": zona.alto,
        "censo": censo,
        "entidades": lista_entidades,
        "grid": grid_data,
        "cronica": cronica,
    }