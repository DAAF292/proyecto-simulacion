"""
presentacion/vista_web.py

Servidor HTTP integrado para monitoreo visual en tiempo real del mundo en el navegador.
Serializa el estado completo en un payload JSON puro consumido por polling desde el canvas.

(2026-08-23) Capa visual ampliada siguiendo el informe de arquitectura visual de Diego
(pixel art hibrido Dwarf Fortress / WorldBox), en su version "sin artes": todo el
pipeline (autotiling por bitmask, sombreado de relieve, bandas de profundidad de agua,
doble bufer, camara con pan/zoom, ensamblaje de criaturas por capas) se implementa
completo, sustituyendo unicamente el CONSUMO de sprites/tileset dibujados a mano por
formas geometricas y los glifos emoji que este visor ya usaba. El algoritmo es identico
al que usaria con arte real -- el swap final (sprites de verdad en vez de figuras) no
tocaria nada de la logica de aqui, solo la funcion de dibujo de cada capa.

No se separa el payload en estatico/dinamico (idea evaluada y aparcada explicitamente,
ver conversacion con Diego 2026-08-23): con el tamano de mapa actual y servidor/cliente
en local, el coste de reenviar el grid completo cada poll no esta medido como un
problema real -- perfilar primero, no anticipar.
"""

from __future__ import annotations

import http.server
import json
import mimetypes
import threading
from pathlib import Path
from typing import Any

from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.gestacion import Gestacion
from componentes.identidad import Identidad
from componentes.intencion import Intencion
from componentes.necesidades import Necesidades
from componentes.necromasa import Necromasa
from componentes.pool_fisico import PoolFisico
from componentes.pool_mental import PoolMental
from componentes.posicion import Posicion
from componentes.reproduccion import Reproduccion
from nucleo.ciclo_vital import TICKS_POR_ANIO, edad_ticks
from nucleo.clima import estacion_actual
from nucleo.entidad import GestorEntidades
from nucleo.mundo import Mundo
from nucleo.reloj import Reloj

# (2026-08-24) Reintroduccion parcial y deliberada de arte real, tras el
# revert completo de la sesion anterior (ver CLAUDE.md, seccion "Limites
# conocidos y pendientes"). A diferencia de aquel intento -- que sustituia
# TODO de golpe (14 variantes de gnomo + fauna + flora) y hubo que revertir
# entero -- esta vez es una sola pieza: solo la textura de terreno (biomas +
# agua), decidida con Diego pieza a pieza (criaturas e iconos de accion
# quedan para despues, cada uno validado por separado antes de sumar el
# siguiente). Fuente: paquete "Tilesets" de PyxelSpace (nuevosAssets/Tilesets),
# licencia comercial con atribucion obligatoria (nombre+email del comprador
# en los creditos del proyecto) -- pendiente de anotar en el informe cuando
# se cierre esta pieza.
RUTA_ASSETS = Path(__file__).resolve().parent / "assets"

HTML_VISOR = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Un Mundo Vivo - Vista Web</title>
  <style>
    body { background: #1a1a1a; color: #e0e0e0; font-family: monospace; margin: 0; padding: 15px; display: flex; flex-direction: column; align-items: center; }
    #contenedor { display: flex; gap: 20px; max-width: 1300px; width: 100%; }
    #canvas-mapa { border: 2px solid #333; background: #000; image-rendering: pixelated; image-rendering: crisp-edges; cursor: grab; }
    #canvas-mapa:active { cursor: grabbing; }
    #panel-lateral { flex: 1; display: flex; flex-direction: column; gap: 10px; min-width: 260px; }
    .card { background: #242424; border: 1px solid #3a3a3a; padding: 10px; border-radius: 4px; font-size: 12px; }
    #cronica { height: 280px; overflow-y: auto; display: flex; flex-direction: column-reverse; background: #181818; padding: 8px; border: 1px solid #333; font-size: 11px; }
    .linea-cronica { margin-bottom: 4px; line-height: 1.3; border-bottom: 1px solid #222; padding-bottom: 2px; }
    #ayuda-camara { font-size: 10px; color: #888; }
  </style>
</head>
<body>
  <h2>🌲 Un Mundo Vivo — Panel de Simulación</h2>
  <div id="contenedor">
    <div>
      <canvas id="canvas-mapa" width="640" height="640"></canvas>
      <div id="ayuda-camara">Arrastra para mover la cámara · rueda del ratón para zoom</div>
    </div>
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
    // ------------------------------------------------------------------
    // Capa visual (2026-08-23) -- version "sin artes": autotiling
    // procedimental, sombreado de relieve, agua por profundidad, doble
    // bufer, camara con pan/zoom, ensamblaje de criaturas por capas con
    // formas geometricas + glifos en vez de sprites dibujados a mano.
    // ------------------------------------------------------------------

    const TILE_NATIVO = 16;      // px por celda en el buffer de terreno (resolucion nativa)
    const INTERVALO_POLL_MS = 250;

    const canvas = document.getElementById('canvas-mapa');
    const ctx = canvas.getContext('2d');
    ctx.imageSmoothingEnabled = false;

    const bufferTerreno = document.createElement('canvas');
    const bufferCtx = bufferTerreno.getContext('2d');
    bufferCtx.imageSmoothingEnabled = false;

    // (2026-08-23) Paleta reajustada -- la version anterior salia demasiado
    // palida/grisacea en pantalla (bosque y pradera casi indistinguibles,
    // tonos frios). Mas saturacion y mas contraste entre biomas, sin tocar
    // el algoritmo de autotiling/sombreado que consume estos colores.
    const COLORES_TERRENO = {
      'bosque': [21, 74, 42], 'pradera': [107, 158, 60], 'montana': [112, 104, 96],
      'desierto': [224, 178, 96], 'tundra': [205, 214, 219]
    };
    const COLORES_SEXO = { 'macho': '#5dade2', 'hembra': '#e874c9' };
    const GLIFOS_ESPECIE = { 'gnomo': '🧙', 'lobo': '🐺', 'conejo': '🐇', 'ardilla': '🐿️' };
    const ICONOS_ACCION = {
      'comer': '🍎', 'beber': '💧', 'huir': '💨', 'cazar': '⚔️',
      'buscar_pareja': '❤️', 'dormir': '💤'
    };

    // (2026-08-24/25) Texturas reales de terreno -- historial resumido (ver
    // CLAUDE.md y informe_implementacion_bosque.docx 7.53-7.57 para el
    // detalle completo): version original con PyxelSpace "Tilesets";
    // pivote a Urizen (Vurmux) el 24-08 a peticion de Diego buscando una
    // estetica mas oscura/rogue, con recorte dedicado por bioma (grid
    // nativo real de Urizen: 13x13px, confirmado midiendo pixeles, no a
    // ojo); desierto revertido a PyxelSpace el 25-08 porque Urizen no tiene
    // ningun tile que lea como arena; y el resto de biomas revertidos
    // tambien a PyxelSpace el mismo dia porque los suelos de Urizen son
    // literalmente suelos DE MAZMORRA (piedra con juntas, tablon con
    // remaches) y leen "demasiado geometricos" para terreno natural
    // continuo -- Urizen se reserva para decoracion/criaturas (pieza 2), no
    // para el relleno de suelo. El tinte sigue viniendo de COLORES_TERRENO
    // via 'multiply' en todos los casos -- mismo mecanismo, solo cambia el
    // origen del asset. El mecanismo de las 8 variantes anti-repetición es
    // independiente de qué PNG se cargue, así que no cambia con estos swaps.
    const RUTA_TEXTURAS = {
      'grass': 'assets/terreno/grass.png',
      'sand': 'assets/terreno/sand.png',
      'stone': 'assets/terreno/stone.png',
      'water': 'assets/terreno/water.png',
    };
    const TEXTURA_POR_BIOMA = {
      'bosque': 'grass', 'pradera': 'grass', 'montana': 'stone',
      'desierto': 'sand', 'tundra': 'stone'
    };
    const TEXTURAS = {};
    const texturaLista = {};
    for (const [clave, ruta] of Object.entries(RUTA_TEXTURAS)) {
      const img = new Image();
      img.onload = () => { texturaLista[clave] = true; };
      img.src = ruta;
      TEXTURAS[clave] = img;
    }

    // (2026-08-25) Pieza 2: sprites de criaturas, mismo patron de carga que
    // la textura de terreno (flag de listo, fallback si aun no cargo). Los
    // 4 recortes salen de Urizen (Vurmux), nativos de 13x13 -- ver CLAUDE.md
    // e informe_implementacion_bosque.docx para de donde sale cada uno
    // dentro del sheet. Nota importante sobre conejo/ardilla: Urizen NO
    // tiene ningun sprite con silueta de ardilla (orejas cortas + cola
    // tupida son los rasgos que la distinguen de un conejo, y ninguna pieza
    // revisada del sheet -- ni la fila de fauna de seccion 1 ni el bloque
    // humanoide/cuadrupedo de seccion 5 -- los tiene). Decision explicita de
    // Diego (25-08) tras planteársela: en vez de mantener dos tamanos de
    // conejo (cria/adulto), usar un unico conejo (el "grande") como especie
    // conejo, y reutilizar el sprite del conejo "pequeño" retinido hacia un
    // tono mas propio de ardilla como especie ardilla. Es una aproximacion
    // deliberada y transparente, no una forma de ardilla real -- la silueta
    // sigue siendo de conejo. Si aparece un sprite con silueta de ardilla de
    // verdad en el futuro, esto se sustituye sin tocar el resto del mecanismo.
    const RUTA_SPRITES_CRIATURA = {
      'gnomo': 'assets/sprites_criaturas/urizen_gnomo.png',
      'lobo': 'assets/sprites_criaturas/urizen_lobo.png',
      'conejo': 'assets/sprites_criaturas/urizen_conejo.png',
      'ardilla': 'assets/sprites_criaturas/urizen_ardilla.png',
    };
    // Tinte multiply aplicado solo donde el sprite base necesita cambiar de
    // tono para acercarse a lo que representa (mismo mecanismo del tinte de
    // bioma en el terreno, precalculado una vez al cargar en vez de por
    // frame). Provisional: tono elegido a ojo, sin calibrar contra el motor
    // en marcha -- si no convence es un solo valor que cambiar.
    const TINTE_CRIATURA = {
      'ardilla': [176, 100, 56],
    };

    function crearSpriteTenido(imgBase, tinte) {
      // Tintar preservando la silueta transparente: multiply sobre todo el
      // lienzo tambien pintaria fuera del sprite (un rect opaco, porque
      // multiply con alfa de fondo 0 no se queda transparente) -- por eso
      // el paso final en 'destination-in' recorta el resultado de vuelta a
      // la alfa original del sprite. Se hace una sola vez al cargar, no en
      // cada frame.
      const c = document.createElement('canvas');
      c.width = imgBase.width;
      c.height = imgBase.height;
      const cctx = c.getContext('2d');
      cctx.drawImage(imgBase, 0, 0);
      cctx.globalCompositeOperation = 'multiply';
      cctx.fillStyle = `rgb(${tinte[0]},${tinte[1]},${tinte[2]})`;
      cctx.fillRect(0, 0, c.width, c.height);
      cctx.globalCompositeOperation = 'destination-in';
      cctx.drawImage(imgBase, 0, 0);
      return c;
    }

    const SPRITES_CRIATURA = {};
    const spriteCriaturaListo = {};
    for (const [clave, ruta] of Object.entries(RUTA_SPRITES_CRIATURA)) {
      const img = new Image();
      img.onload = () => {
        SPRITES_CRIATURA[clave] = TINTE_CRIATURA[clave] ? crearSpriteTenido(img, TINTE_CRIATURA[clave]) : img;
        spriteCriaturaListo[clave] = true;
      };
      img.src = ruta;
    }

    // (2026-08-24) Feedback directo de Diego sobre la primera version de esta
    // pieza: con un unico crop de 32x32 estampado igual en cada celda, a
    // zoom normal se ve claramente el patron que se repite (efecto "papel
    // pintado" -- ojo humano detectando periodicidad regular). Primer intento
    // (flip por paridad de x/y, 4 variantes, periodo 2x2) mejoraba pero
    // seguia siendo visible, sobre todo en piedra/arena por su estructura
    // interna muy geometrica -- confirmado con un render de referencia en
    // Python antes de conformarme con esa version. Version actual: las 8
    // simetrias del cuadrado (4 rotaciones de 90 grados x espejado opcional,
    // grupo diedrico D4) elegidas por un hash simple y determinista de (x,y)
    // -- no la paridad directa, para que el propio patron de seleccion de
    // variante no cree su propia periodicidad visible. Sigue sin añadir
    // ningun asset nuevo ni ningun rng en el cliente (misma celda siempre
    // produce la misma variante, estable entre polls).
    //
    // Leccion adicional al elegir los tiles de Urizen (misma pieza, segunda
    // iteracion): las 8 variantes NO ayudan si el propio tile es casi
    // simetrico bajo rotacion/espejado -- un motivo de "marco cuadrado
    // centrado" se ve igual (a ojo, aunque no sea identico pixel a pixel)
    // en las 8 orientaciones, así que el patron de repeticion vuelve a
    // notarse por mas que el hash este bien distribuido. No es un bug del
    // hash (verificado sin periodicidad ni diagonales constantes) sino una
    // eleccion de asset: se prefirio el tile de roca agrietada de Urizen
    // (asimetrico) frente al de bloque de piedra con marco (simetrico) para
    // montana precisamente por esto -- confirmado en el render de
    // referencia en Python antes de fijar la eleccion final.
    function dibujarTexturaVariada(img, x, y, px, py, size) {
      // (2026-08-24) Primera version de este hash (x*A + y*B mod 8, con A y B
      // primos grandes cualquiera) resulto tener A y B congruentes con 1 y -1
      // modulo 8 -- el hash colapsaba a (x-y) mod 8, es decir: la MISMA
      // variante se repetia en toda una diagonal completa del mapa (franjas
      // a 45 grados en vez de ruido). Detectado con el arnes de mock-DOM
      // comprobando explicitamente celdas con x-y constante, no solo pares
      // (dx,0)/(0,dy) -- esa prueba mas simple no lo habria visto. Con mezcla
      // de bits estilo MurmurHash3 (xor + multiplicaciones + shifts) no hay
      // formula lineal que colapse asi.
      let h = (Math.imul(x, 0x27d4eb2f) ^ Math.imul(y, 0x165667b1)) | 0;
      h = Math.imul(h ^ (h >>> 15), 0x85ebca6b);
      h = Math.imul(h ^ (h >>> 13), 0xc2b2ae35);
      h = ((h ^ (h >>> 16)) >>> 0) % 8;
      const rot = (h % 4) * (Math.PI / 2);
      const flip = h >= 4;
      bufferCtx.save();
      bufferCtx.translate(px + size / 2, py + size / 2);
      bufferCtx.rotate(rot);
      bufferCtx.scale(flip ? -1 : 1, 1);
      bufferCtx.drawImage(img, -size / 2, -size / 2, size, size);
      bufferCtx.restore();
    }

    let referencias = {};
    let estadoAnterior = null;   // { porId, t } del poll previo, para interpolar
    let estadoActual = null;     // { data, porId, t } del ultimo poll recibido
    let tPollActual = performance.now();

    const camara = { x: null, y: null, zoom: 1 };
    let arrastrando = false;
    let ultimoRaton = { x: 0, y: 0 };

    // --- Terreno: dibujado una vez por poll en el buffer offscreen, no cada frame ---
    function dibujarTerreno(data) {
      const ancho = data.ancho, alto = data.alto;
      bufferTerreno.width = ancho * TILE_NATIVO;
      bufferTerreno.height = alto * TILE_NATIVO;
      bufferCtx.imageSmoothingEnabled = false;
      const grid = data.grid;

      for (let y = 0; y < alto; y++) {
        for (let x = 0; x < ancho; x++) {
          const c = grid[y][x];
          const px = x * TILE_NATIVO, py = y * TILE_NATIVO;
          const colorBase = COLORES_TERRENO[c.terreno] || [20, 20, 20];

          // 1. Relleno base del bioma: textura real tenida con el color de
          // bioma (ver bloque TEXTURAS arriba). Si la textura aun no cargo
          // (primer poll, o fallo de red), cae al relleno de color plano de
          // antes -- nunca deja una celda en blanco.
          const claveTex = TEXTURA_POR_BIOMA[c.terreno];
          if (claveTex && texturaLista[claveTex]) {
            dibujarTexturaVariada(TEXTURAS[claveTex], x, y, px, py, TILE_NATIVO);
            bufferCtx.globalCompositeOperation = 'multiply';
            bufferCtx.fillStyle = `rgb(${colorBase[0]},${colorBase[1]},${colorBase[2]})`;
            bufferCtx.fillRect(px, py, TILE_NATIVO, TILE_NATIVO);
            bufferCtx.globalCompositeOperation = 'source-over';
          } else {
            bufferCtx.fillStyle = `rgb(${colorBase[0]},${colorBase[1]},${colorBase[2]})`;
            bufferCtx.fillRect(px, py, TILE_NATIVO, TILE_NATIVO);
          }

          // 2. Autotiling procedimental (equivalente al bitmask de 4 bits del
          // informe, sin tileset: en vez de mapear a una subtextura, se
          // mezcla el color hacia el vecino distinto con un degradado en el
          // borde correspondiente -- mismo calculo de vecinos, distinto
          // consumo visual).
          const vecinos4 = [[0, -1, 'N'], [1, 0, 'E'], [0, 1, 'S'], [-1, 0, 'O']];
          for (const [dx, dy, dir] of vecinos4) {
            const nx = x + dx, ny = y + dy;
            if (nx < 0 || ny < 0 || nx >= ancho || ny >= alto) continue;
            const vecino = grid[ny][nx];
            if (vecino.terreno === c.terreno) continue;
            const cv = COLORES_TERRENO[vecino.terreno] || colorBase;
            let grad;
            const franja = TILE_NATIVO * 0.4;
            if (dir === 'N') grad = bufferCtx.createLinearGradient(px, py, px, py + franja);
            else if (dir === 'S') grad = bufferCtx.createLinearGradient(px, py + TILE_NATIVO, px, py + TILE_NATIVO - franja);
            else if (dir === 'O') grad = bufferCtx.createLinearGradient(px, py, px + franja, py);
            else grad = bufferCtx.createLinearGradient(px + TILE_NATIVO, py, px + TILE_NATIVO - franja, py);
            grad.addColorStop(0, `rgba(${cv[0]},${cv[1]},${cv[2]},0.35)`);
            grad.addColorStop(1, `rgba(${cv[0]},${cv[1]},${cv[2]},0)`);
            bufferCtx.fillStyle = grad;
            bufferCtx.fillRect(px, py, TILE_NATIVO, TILE_NATIVO);
          }

          // 3. Sombreado de relieve: diferencia de elevacion con el vecino diagonal
          if (x > 0 && y > 0) {
            const dz = c.elevacion - grid[y - 1][x - 1].elevacion;
            if (dz > 0.001) {
              bufferCtx.fillStyle = `rgba(255,255,255,${Math.min(0.35, dz * 1.5)})`;
              bufferCtx.fillRect(px, py, TILE_NATIVO, TILE_NATIVO);
            } else if (dz < -0.001) {
              bufferCtx.fillStyle = `rgba(0,0,0,${Math.min(0.3, -dz * 1.5)})`;
              bufferCtx.fillRect(px, py, TILE_NATIVO, TILE_NATIVO);
            }
          }

          // 4. Marcador sutil de recurso (util para observar el motor, no estetico)
          if (c.tiene_recurso) {
            bufferCtx.fillStyle = 'rgba(120,220,120,0.55)';
            bufferCtx.beginPath();
            bufferCtx.arc(px + TILE_NATIVO / 2, py + TILE_NATIVO / 2, TILE_NATIVO * 0.12, 0, Math.PI * 2);
            bufferCtx.fill();
          }

          // 5. Agua permanente: textura real de base + bandas de profundidad
          // (semi-transparentes, tal cual antes) + espuma procedimental en el borde
          if (c.tiene_agua) {
            if (texturaLista['water']) {
              dibujarTexturaVariada(TEXTURAS['water'], x, y, px, py, TILE_NATIVO);
            }
            let colorAgua, alfa;
            if (c.profundidad_agua <= 0.3) { colorAgua = '135,206,235'; alfa = 0.55; }
            else if (c.profundidad_agua <= 1.0) { colorAgua = '52,120,190'; alfa = 0.75; }
            else { colorAgua = '15,50,100'; alfa = 0.92; }
            bufferCtx.fillStyle = `rgba(${colorAgua},${alfa})`;
            bufferCtx.fillRect(px, py, TILE_NATIVO, TILE_NATIVO);

            const grosor = TILE_NATIVO * 0.15;
            for (const [dx, dy] of [[0, -1], [1, 0], [0, 1], [-1, 0]]) {
              const nx = x + dx, ny = y + dy;
              if (nx < 0 || ny < 0 || nx >= ancho || ny >= alto || !grid[ny][nx].tiene_agua) {
                bufferCtx.fillStyle = 'rgba(255,255,255,0.4)';
                if (dx === 0 && dy === -1) bufferCtx.fillRect(px, py, TILE_NATIVO, grosor);
                if (dx === 0 && dy === 1) bufferCtx.fillRect(px, py + TILE_NATIVO - grosor, TILE_NATIVO, grosor);
                if (dx === -1 && dy === 0) bufferCtx.fillRect(px, py, grosor, TILE_NATIVO);
                if (dx === 1 && dy === 0) bufferCtx.fillRect(px + TILE_NATIVO - grosor, py, grosor, TILE_NATIVO);
              }
            }
          } else if (c.profundidad_charco > 0) {
            // (2026-08-24) Antes era una opacidad fija de 0.5 -- con lluvia
            // extendida eso tine el mapa ENTERO de azul (confirmado en vivo:
            // a maxima profundidad de charco, 0.5 produce un lavado ciano
            // que hace ilegible la paleta de biomas). Ahora escala con la
            // profundidad real / techo configurado (mismo patron que las
            // bandas de agua permanente de arriba), con un techo de opacidad
            // mucho mas bajo. ALPHA_MAX_CHARCO=0.2 es una eleccion estetica
            // mia, comparada en vivo contra el motor real a varios valores
            // (0.5 original, 0.2, 0.12) -- 0.12 ya resultaba casi invisible
            // (perdia el valor informativo de "aqui hay agua efimera"), 0.5
            // lavaba el mapa; 0.2 fue el punto donde el tinte se nota sin
            // tapar el color de bioma. Sigue siendo gusto, no una medicion
            // objetiva -- si no convence, es un solo numero que cambiar.
            const ratioCharco = Math.min(1, c.profundidad_charco / (data.techo_profundidad_charco || 0.03));
            const ALPHA_MAX_CHARCO = 0.2;
            bufferCtx.fillStyle = `rgba(100,170,220,${ratioCharco * ALPHA_MAX_CHARCO})`;
            bufferCtx.fillRect(px, py, TILE_NATIVO, TILE_NATIVO);
          }

          // 6. Fuego
          if (c.en_llamas) {
            bufferCtx.fillStyle = 'rgba(192,57,43,0.75)';
            bufferCtx.fillRect(px, py, TILE_NATIVO, TILE_NATIVO);
          }
        }
      }
    }

    // --- Camara: transformacion afin (traslacion + zoom), aplicada antes de dibujar ---
    function aplicarTransformCamara() {
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.imageSmoothingEnabled = false;
      ctx.translate(canvas.width / 2, canvas.height / 2);
      ctx.scale(camara.zoom, camara.zoom);
      ctx.translate(-camara.x, -camara.y);
    }

    // --- Ensamblaje de criaturas por capas (paperdoll geometrico, sin sprites) ---
    function dibujarEntidad(e, alpha) {
      let x = e.x, y = e.y;
      const anterior = estadoAnterior ? estadoAnterior.porId[e.id] : null;
      if (anterior) {
        x = anterior.x + (e.x - anterior.x) * alpha;
        y = anterior.y + (e.y - anterior.y) * alpha;
      }
      const cx = x * TILE_NATIVO + TILE_NATIVO / 2;
      let cy = y * TILE_NATIVO + TILE_NATIVO / 2;
      const enMovimiento = !!anterior && (anterior.x !== e.x || anterior.y !== e.y);

      // 2. Marcha organica (bobbing): desplazamiento vertical en seno mientras se mueve
      if (enMovimiento) cy -= Math.abs(Math.sin(alpha * Math.PI)) * 3;

      if (e.tipo === 'necromasa') {
        ctx.save();
        ctx.globalAlpha = 0.8;
        ctx.font = `${TILE_NATIVO * 0.9}px sans-serif`;
        ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        ctx.fillText('🦴', cx, cy);
        ctx.restore();
        return;
      }

      const ref = referencias[e.tipo] || { peso_medio: 1, altura_media: 1 };
      let escala = ((e.peso / ref.peso_medio) + (e.altura / ref.altura_media)) / 2;
      if (!isFinite(escala) || escala <= 0) escala = 1;
      escala = Math.max(0.5, Math.min(1.6, escala));

      ctx.save();
      ctx.translate(cx, cy);

      // 3. Orientacion: inversion horizontal si se mueve hacia -X
      if (enMovimiento && (e.x - anterior.x) < 0) ctx.scale(-1, 1);

      // Capa 0: sombra proyectada
      ctx.globalAlpha = 0.35;
      ctx.fillStyle = '#000';
      ctx.beginPath();
      ctx.ellipse(0, TILE_NATIVO * 0.35 * escala, TILE_NATIVO * 0.35 * escala, TILE_NATIVO * 0.12 * escala, 0, 0, Math.PI * 2);
      ctx.fill();

      // Capa 1: cuerpo base -- tinte por sexo, opacidad por madurez/canicie
      const edadRatio = Math.min(1, e.edad_ratio || 0);
      ctx.globalAlpha = e.edad_ratio > 1 ? 0.6 : (0.55 + 0.45 * edadRatio);
      ctx.fillStyle = COLORES_SEXO[e.sexo] || '#bbbbbb';
      ctx.beginPath();
      ctx.ellipse(0, 0, TILE_NATIVO * 0.4 * escala, TILE_NATIVO * 0.5 * escala, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.globalAlpha = 1;

      // Capas 2-3 (rasgos/atuendo): sprite real de Urizen si ya cargo: si no
      // (primer poll, especie sin sprite, o fallo de red) cae al glifo emoji
      // -- mismo patron de robustez que la textura de terreno, nunca deja la
      // entidad en blanco mientras carga.
      if (spriteCriaturaListo[e.tipo]) {
        const tam = TILE_NATIVO * 1.1 * escala;
        ctx.drawImage(SPRITES_CRIATURA[e.tipo], -tam / 2, -tam / 2, tam, tam);
      } else {
        ctx.font = `${TILE_NATIVO * 0.9 * escala}px sans-serif`;
        ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        ctx.fillText(GLIFOS_ESPECIE[e.tipo] || '❓', 0, 0);
      }

      // Capa 4: overlays de estado -- herida y gestacion
      if (e.vitalidad !== undefined && e.vitalidad < 0.5) {
        ctx.globalAlpha = 0.25 + (0.5 - e.vitalidad);
        ctx.fillStyle = 'red';
        ctx.beginPath();
        ctx.arc(0, 0, TILE_NATIVO * 0.55 * escala, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = 1;
      }
      if (e.gestando) {
        ctx.fillStyle = 'rgba(255,200,220,0.65)';
        ctx.beginPath();
        ctx.arc(TILE_NATIVO * 0.15 * escala, TILE_NATIVO * 0.15 * escala, TILE_NATIVO * 0.18 * escala, 0, Math.PI * 2);
        ctx.fill();
      }

      ctx.restore();

      // Capa 5: icono flotante de intencion -- fuera del scale invertido, siempre legible
      if (e.accion && ICONOS_ACCION[e.accion]) {
        ctx.save();
        ctx.font = `${TILE_NATIVO * 0.5}px sans-serif`;
        ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        ctx.fillText(ICONOS_ACCION[e.accion], cx, cy - TILE_NATIVO * 0.75);
        ctx.restore();
      }
    }

    function actualizarPaneles(data) {
      document.getElementById('info-mundo').innerHTML =
        `<strong>Tick:</strong> ${data.tick} | <strong>Día:</strong> ${data.dia} | <strong>Estación:</strong> ${data.estacion}<br>` +
        `<strong>Clima:</strong> ${data.clima}`;

      document.getElementById('info-poblacion').innerHTML =
        `<strong>Vivos:</strong> Gnomos: ${data.censo.gnomo || 0} | Lobos: ${data.censo.lobo || 0} | ` +
        `Conejos: ${data.censo.conejo || 0} | Ardillas: ${data.censo.ardilla || 0} | ` +
        `<strong>Restos (Necromasa):</strong> ${data.censo.necromasa || 0}`;

      const divCronica = document.getElementById('cronica');
      divCronica.innerHTML = data.cronica.map(l => `<div class="linea-cronica">${l}</div>`).join('');
    }

    // --- Bucle de red (cadencia de poll) ---
    async function poll() {
      try {
        const resp = await fetch('/estado.json');
        if (!resp.ok) return;
        const data = await resp.json();
        referencias = data.referencias || {};

        const porId = {};
        data.entidades.forEach(e => { porId[e.id] = e; });

        estadoAnterior = estadoActual ? { porId: estadoActual.porId } : null;
        estadoActual = { data, porId };
        tPollActual = performance.now();

        if (camara.x === null) {
          camara.x = (data.ancho * TILE_NATIVO) / 2;
          camara.y = (data.alto * TILE_NATIVO) / 2;
        }

        dibujarTerreno(data);
        actualizarPaneles(data);
      } catch (err) {
        console.error("Error al actualizar instantánea:", err);
      }
    }

    // --- Bucle de render (60 FPS, independiente de la cadencia de poll) ---
    function animar() {
      if (estadoActual) {
        const alpha = Math.min(1, (performance.now() - tPollActual) / INTERVALO_POLL_MS);
        aplicarTransformCamara();
        ctx.drawImage(bufferTerreno, 0, 0);

        // 4. Ordenamiento de profundidad (Y-sorting) antes del pase de dibujo
        const entidadesOrdenadas = estadoActual.data.entidades.slice().sort((a, b) => a.y - b.y);
        entidadesOrdenadas.forEach(e => dibujarEntidad(e, alpha));
      }
      requestAnimationFrame(animar);
    }

    // --- Camara: pan con arrastre, zoom con rueda ---
    canvas.addEventListener('mousedown', e => {
      arrastrando = true;
      ultimoRaton = { x: e.clientX, y: e.clientY };
    });
    window.addEventListener('mouseup', () => { arrastrando = false; });
    window.addEventListener('mousemove', e => {
      if (!arrastrando || camara.x === null) return;
      camara.x -= (e.clientX - ultimoRaton.x) / camara.zoom;
      camara.y -= (e.clientY - ultimoRaton.y) / camara.zoom;
      ultimoRaton = { x: e.clientX, y: e.clientY };
    });
    canvas.addEventListener('wheel', e => {
      e.preventDefault();
      const factor = e.deltaY < 0 ? 1.1 : 0.9;
      camara.zoom = Math.max(0.3, Math.min(4, camara.zoom * factor));
    }, { passive: false });

    setInterval(poll, INTERVALO_POLL_MS);
    poll();
    requestAnimationFrame(animar);
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
        elif self.path.startswith("/assets/"):
            self._servir_asset()
        else:
            self.send_response(404)
            self.end_headers()

    def _servir_asset(self) -> None:
        """Sirve estaticos solo desde presentacion/assets/ (2026-08-24, pieza
        de terreno con arte real -- ver RUTA_ASSETS arriba). Resuelve la ruta
        y verifica que siga dentro de RUTA_ASSETS antes de leerla, para que
        un "../" en la URL no pueda escapar del directorio de assets."""
        rel = self.path[len("/assets/"):].split("?")[0]
        try:
            ruta = (RUTA_ASSETS / rel).resolve()
            ruta.relative_to(RUTA_ASSETS)
        except (ValueError, RuntimeError):
            self.send_response(404)
            self.end_headers()
            return
        if not ruta.is_file():
            self.send_response(404)
            self.end_headers()
            return
        tipo, _ = mimetypes.guess_type(str(ruta))
        self.send_response(200)
        self.send_header("Content-Type", tipo or "application/octet-stream")
        self.end_headers()
        self.wfile.write(ruta.read_bytes())

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
    config: dict[str, Any],
) -> dict[str, Any]:
    """
    Construye el DTO serializable para la interfaz web.

    (2026-08-23) Ampliado con los campos que la capa visual necesita para el
    ensamblaje de criaturas por capas y el renderizado de terreno continuo
    (informe de arquitectura visual de Diego, version "sin artes"): peso,
    altura, sexo, edad_ratio, vitalidad, gestacion e intencion por entidad;
    elevacion, tipo_agua, profundidad_agua, tiene_recurso y tipo_recurso por
    celda; y una tabla de referencias (peso_medio/altura_media por especie,
    derivada de rangos_raciales) para que el cliente pueda escalar cada
    individuo sin duplicar esos numeros en JS -- el servidor sigue siendo la
    unica fuente de verdad, el cliente solo proyecta.
    """
    zona = mundo.territorio.zonas[0]
    censo: dict[str, int] = {}
    rangos_raciales = config.get("rangos_raciales", {})

    lista_entidades: list[dict[str, Any]] = []

    # 1. Entidades Biológicas Vivas
    for eid in sorted(gestor.entidades_con(Identidad, Posicion)):
        ident = gestor.obtener_componente(eid, Identidad)
        pos = gestor.obtener_componente(eid, Posicion)
        if not (ident and pos):
            continue

        esp = ident.especie.value
        censo[esp] = censo.get(esp, 0) + 1

        dato: dict[str, Any] = {
            "id": eid,
            "tipo": esp,
            "x": pos.x,
            "y": pos.y,
            "nombre": ident.nombre,
        }

        dims = gestor.obtener_componente(eid, DimensionesFisicas)
        if dims is not None:
            dato["peso"] = round(dims.peso, 2)
            dato["altura"] = round(dims.altura, 2)
            longevidad_ticks = dims.longevidad * TICKS_POR_ANIO
            if longevidad_ticks > 0:
                ratio = edad_ticks(ident.tick_nacimiento, reloj.tick_actual) / longevidad_ticks
                dato["edad_ratio"] = round(max(0.0, min(1.5, ratio)), 3)

        repro = gestor.obtener_componente(eid, Reproduccion)
        if repro is not None:
            dato["sexo"] = repro.sexo.value

        pool_fisico = gestor.obtener_componente(eid, PoolFisico)
        if pool_fisico is not None:
            dato["vitalidad"] = round(pool_fisico.vitalidad, 3)

        dato["gestando"] = gestor.obtener_componente(eid, Gestacion) is not None

        intencion = gestor.obtener_componente(eid, Intencion)
        if intencion is not None:
            dato["accion"] = intencion.accion.value

        lista_entidades.append(dato)

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
                    "elevacion": round(c.elevacion, 3),
                    "tiene_agua": c.tiene_agua,
                    "tipo_agua": c.tipo_agua,
                    "profundidad_agua": round(c.profundidad_agua, 3),
                    "profundidad_charco": round(c.profundidad_charco, 3),
                    "en_llamas": c.en_llamas,
                    "fertilidad": round(c.fertilidad, 2),
                    "tiene_recurso": c.tiene_recurso,
                    "tipo_recurso": c.tipo_recurso,
                }
            )
        grid_data.append(fila)

    referencias: dict[str, Any] = {}
    for especie_key, cfg_raza in rangos_raciales.items():
        peso_r = cfg_raza.get("peso")
        altura_r = cfg_raza.get("altura")
        if peso_r and altura_r:
            referencias[especie_key] = {
                "peso_medio": round((peso_r[0] + peso_r[1]) / 2, 2),
                "altura_media": round((altura_r[0] + altura_r[1]) / 2, 2),
            }

    clima_actual = getattr(zona, "clima_actual", None)

    # (2026-08-24) Necesario para que el cliente escale la opacidad del
    # charco por profundidad real en vez de un techo adivinado -- unica
    # fuente de verdad config/constantes.yaml, el cliente solo proyecta.
    techo_profundidad_charco = config.get("charcos", {}).get("techo_profundidad_charco", 0.03)

    return {
        "tick": reloj.tick_actual,
        "techo_profundidad_charco": techo_profundidad_charco,
        "dia": reloj.dia,
        # (2026-08-23) mismo bug que en sistema_necesidades.py/sistema_flora.py:
        # Reloj.estacion es un int creciente, no el Enum Estacion.
        "estacion": estacion_actual(reloj.estacion).value,
        "clima": clima_actual.value if clima_actual else "despejado",
        "ancho": zona.ancho,
        "alto": zona.alto,
        "censo": censo,
        "entidades": lista_entidades,
        "grid": grid_data,
        "referencias": referencias,
        "cronica": cronica,
    }
