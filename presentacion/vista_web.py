"""
presentacion/vista_web.py

Servidor HTTP integrado para monitoreo visual en tiempo real del mundo en el navegador.
Serializa el estado completo en un payload JSON puro consumido por polling desde el canvas.

Codice Cartografico Procedural (propuesta de frontend, 2026-08-27):
sustituye el visor de bloques planos y emojis por un lienzo HTML5 Canvas con
textura de pergamino, lavado acuoso por bioma, hidrografia/relieve/vegetacion
vectorial, camara pan/zoom con runas Futhark y LOD, y un panel de inspeccion
ECS con ficha de criatura, seguimiento de camara y busqueda en la cronica
(pasos 1-4 de la propuesta, todos sobre este mismo archivo). El contrato JSON
de mas abajo solo expone campos que YA existen en el ECS (Principio 4:
honestidad sobre lo pendiente, nunca se inventa un dato que el motor no
calcula).
"""

from __future__ import annotations

import http.server
import json
import mimetypes
import re
import threading
from pathlib import Path
from typing import Any

from componentes.capacidad_mental import CapacidadMental
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Identidad
from componentes.intencion import Intencion
from componentes.necesidades import Necesidades
from componentes.necromasa import Necromasa
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

HTML_VISOR = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Un Mundo Vivo - Codice Cartografico</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@500;700&family=IM+Fell+English:ital@0;1&display=swap" rel="stylesheet">
  <style>
    :root {
      --madera: #2b1d12;
      --madera-oscura: #1a1109;
      --pergamino: #e6d8b8;
      --pergamino-oscuro: #cbb789;
      --tinta: #3a2b1a;
      --tinta-fuerte: #241a0f;
      --acento: #7a5230;
    }
    * { box-sizing: border-box; }
    body {
      background: var(--madera-oscura);
      background-image: radial-gradient(circle at 50% 0%, var(--madera), var(--madera-oscura) 70%);
      color: var(--pergamino);
      font-family: 'IM Fell English', Georgia, serif;
      margin: 0;
      padding: 18px;
      display: flex;
      flex-direction: column;
      align-items: center;
    }
    h1 {
      font-family: 'Cinzel', serif;
      font-weight: 700;
      letter-spacing: 2px;
      font-size: 20px;
      margin: 0 0 4px 0;
      text-align: center;
    }
    #subtitulo {
      font-style: italic;
      color: var(--pergamino-oscuro);
      margin-bottom: 14px;
      font-size: 13px;
    }
    #contenedor {
      display: flex;
      gap: 18px;
      max-width: 1280px;
      width: 100%;
    }
    #marco-mapa {
      padding: 10px;
      background: linear-gradient(135deg, #4a3320, #2b1d12);
      border: 1px solid #6b4a2c;
      border-radius: 3px;
      box-shadow: 0 0 22px rgba(0,0,0,0.55);
    }
    #canvas-mapa { display: block; background: var(--pergamino); cursor: grab; touch-action: none; }
    #canvas-mapa.arrastrando { cursor: grabbing; }
    #controles-mapa {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 8px;
      font-size: 11.5px;
      color: var(--pergamino-oscuro);
    }
    #btn-centrar {
      font-family: 'IM Fell English', Georgia, serif;
      font-size: 11.5px;
      background: linear-gradient(180deg, #efe2c0, #cbb789);
      color: var(--tinta-fuerte);
      border: 1px solid #6b4a2c;
      border-radius: 2px;
      padding: 3px 10px;
      cursor: pointer;
    }
    #btn-centrar:hover { background: #efe2c0; }
    #panel-lateral {
      flex: 1;
      min-width: 280px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .card {
      background: linear-gradient(180deg, #efe2c0, #e0cd9c);
      color: var(--tinta-fuerte);
      border: 1px solid #8a6a3e;
      padding: 10px 12px;
      border-radius: 2px;
      font-size: 12.5px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.4);
    }
    .card strong { font-family: 'Cinzel', serif; font-weight: 500; }
    #ficha-entidad h3 {
      font-family: 'Cinzel', serif;
      font-weight: 500;
      font-size: 13px;
      margin: 0 0 6px 0;
      border-bottom: 1px solid #8a6a3e;
      padding-bottom: 4px;
    }
    #ficha-entidad .fila-stat {
      display: flex;
      justify-content: space-between;
      font-size: 10.5px;
      margin-bottom: 1px;
    }
    #ficha-entidad .barra-contenedor {
      background: rgba(58,43,26,0.22);
      border-radius: 2px;
      height: 6px;
      overflow: hidden;
      margin: 1px 0 5px 0;
    }
    #ficha-entidad .barra-relleno { height: 100%; }
    #ficha-entidad .seccion-ficha { margin-top: 8px; }
    #ficha-entidad .seccion-ficha:first-of-type { margin-top: 0; }
    #ficha-entidad button.enlace-parentesco {
      background: none;
      border: none;
      color: #2c5c8a;
      text-decoration: underline;
      cursor: pointer;
      font-family: inherit;
      font-size: inherit;
      padding: 0;
    }
    #ficha-entidad .fila-botones { display: flex; gap: 6px; margin-top: 8px; }
    #ficha-entidad button.accion-ficha {
      font-family: 'IM Fell English', Georgia, serif;
      font-size: 11px;
      background: linear-gradient(180deg, #efe2c0, #cbb789);
      border: 1px solid #6b4a2c;
      border-radius: 2px;
      padding: 3px 8px;
      cursor: pointer;
      color: var(--tinta-fuerte);
    }
    #ficha-entidad button.accion-ficha.activo { background: #8a6a3e; color: #efe2c0; }
    #ficha-entidad .nota-ficha { font-style: italic; color: #6b5a3e; font-size: 10.5px; }
    #buscar-cronica {
      width: 100%;
      box-sizing: border-box;
      margin-bottom: 6px;
      font-family: inherit;
      font-size: 11.5px;
      padding: 3px 6px;
      border: 1px solid #8a6a3e;
      border-radius: 2px;
      background: #efe2c0;
      color: var(--tinta-fuerte);
    }
    #cronica {
      height: 300px;
      overflow-y: auto;
      display: flex;
      flex-direction: column-reverse;
      background: #ded0a8;
      padding: 8px;
      border: 1px solid #8a6a3e;
      font-size: 11.5px;
    }
    .linea-cronica {
      margin-bottom: 4px;
      line-height: 1.35;
      border-bottom: 1px solid #c9b789;
      padding-bottom: 3px;
    }
    .tag { font-weight: bold; }
    .tag-gnomo { color: #2c5c8a; }
    .tag-lobo { color: #8a2c2c; }
    .tag-conejo { color: #8a6a1c; }
    .tag-ardilla { color: #2c7a3a; }
    .tag-necromasa { color: #5a5148; }
    #footer-nota {
      font-size: 10.5px;
      color: var(--pergamino-oscuro);
      text-align: center;
      max-width: 1280px;
      margin-top: 10px;
      font-style: italic;
    }
  </style>
</head>
<body>
  <h1>Regio Septentrionalis: Vallis Runica</h1>
  <div id="subtitulo">Un Mundo Vivo &mdash; Codice de Simulacion (Paso 4: panel de inspeccion ECS y seguimiento)</div>
  <div id="contenedor">
    <div id="marco-mapa">
      <canvas id="canvas-mapa" width="700" height="700"></canvas>
      <div id="controles-mapa">
        <span id="lectura-zoom">Zoom: 1.00x</span>
        <button id="btn-centrar" type="button">Centrar mapa</button>
      </div>
    </div>
    <div id="panel-lateral">
      <div class="card" id="info-mundo">Cargando...</div>
      <div class="card" id="info-poblacion">Poblacion: -</div>
      <div class="card" id="ficha-entidad">
        <h3>Registro de Criatura</h3>
        <div class="nota-ficha">Toca una criatura o resto en el mapa para ver su ficha.</div>
      </div>
      <div class="card">
        <strong>Cronica en Vivo</strong>
        <input type="text" id="buscar-cronica" placeholder="Buscar en la cronica (tick, especie, causa...)">
        <div id="cronica"></div>
      </div>
    </div>
  </div>
  <div id="footer-nota">Rueda del raton: zoom (centrado en el cursor). Arrastrar: desplazar el mapa. Click sobre una criatura: ficha e inspeccion.</div>

  <script>
    const canvas = document.getElementById('canvas-mapa');
    const ctx = canvas.getContext('2d');

    // Colores de lavado por bioma -- aplicados sobre la base de pergamino
    // con alfa parcial (acuarela translucida), nunca opacos: el grano del
    // pergamino debe seguir visible a traves de cualquier bioma.
    const COLOR_BIOMA = {
      'bosque':   [46, 74, 42],
      'pradera':  [122, 138, 74],
      'montana':  [110, 104, 96],
      'desierto': [176, 150, 84],
      'tundra':   [163, 176, 178],
    };
    const COLOR_AGUA = [58, 92, 122];
    const COLOR_CHARCO = [90, 130, 160];
    const COLOR_FUEGO = [168, 58, 38];
    // Runas Futhark por especie (informe seccion 5 -- catalogo de identidad):
    // Gebo/gnomo, Laguz/lobo, Kaunan/conejo, Ansuz/ardilla. Necromasa no es
    // una criatura consciente ni figura en ese catalogo -- se queda con un
    // glifo neutro en vez de inventarle una runa que el informe no le da.
    const RUNAS = { 'gnomo': 'ᚷ', 'lobo': 'ᛚ', 'conejo': 'ᚲ', 'ardilla': 'ᚨ', 'necromasa': '🦴' };
    const COLOR_INK_ESPECIE = {
      'gnomo':   [44, 92, 138],
      'lobo':    [138, 44, 44],
      'conejo':  [138, 106, 28],
      'ardilla': [44, 122, 58],
      'necromasa': [90, 81, 72],
    };

    // Color por especie de planta (config/constantes.yaml, flora.especies --
    // exactamente estas cinco existen hoy en el catalogo, ninguna inventada).
    const COLOR_ESPECIE = {
      'manzano':          [61, 92, 46],
      'hierba_silvestre': [107, 138, 66],
      'cactus':           [92, 122, 72],
      'liquen':           [138, 148, 108],
      'musgo':            [58, 84, 56],
    };

    let pergaminoCache = null;   // canvas offscreen con grano, cacheado por semilla+tamano
    let pergaminoClave = null;

    // Biblioteca de assets externos (sellos cartograficos) -- ver
    // presentacion/assets/README.md. Este archivo nunca genera estas
    // imagenes, solo las detecta (si alguien las coloca ahi) y las usa.
    // Mientras catalogoAssets.flora[especie] este vacio para una especie
    // concreta (o catalogoAssets.relieve.montana este vacio), esa
    // categoria sigue con el dibujo vectorial de siempre -- ver el guard
    // en dibujarVegetacion() y en dibujarStampsRelieveYFlora() mas abajo.
    let catalogoAssets = {
      flora: {}, relieve: { montana: [] }, agua: { lago: [], rio: [] }, criaturas: {},
    };
    const imagenesCache = {};

    async function cargarBibliotecaAssets() {
      try {
        const resp = await fetch('/assets_manifest.json');
        if (!resp.ok) return;
        catalogoAssets = await resp.json();
        if (!catalogoAssets.agua) catalogoAssets.agua = { lago: [], rio: [] };
        if (!catalogoAssets.criaturas) catalogoAssets.criaturas = {};
      } catch (err) {
        console.error('No se pudo leer /assets_manifest.json:', err);
        return;
      }
      const rutas = [];
      for (const especie in catalogoAssets.flora) {
        for (const nombre of catalogoAssets.flora[especie]) rutas.push('flora/' + nombre);
      }
      for (const nombre of catalogoAssets.relieve.montana) rutas.push('relieve/' + nombre);
      for (const clave in catalogoAssets.agua) {
        for (const nombre of catalogoAssets.agua[clave]) rutas.push('agua/' + nombre);
      }
      for (const especie in catalogoAssets.criaturas) {
        for (const nombre of catalogoAssets.criaturas[especie]) rutas.push('criaturas/' + nombre);
      }

      await Promise.all(rutas.map((ruta) => new Promise((resolve) => {
        const img = new Image();
        img.onload = () => { imagenesCache[ruta] = img; resolve(); };
        img.onerror = () => resolve();   // asset roto/movido: se ignora, no rompe el visor
        img.src = '/assets/' + ruta;
      })));
    }
    cargarBibliotecaAssets();

    // Hash determinista [0,1) por celda -- mismo par (x,y,sal) da siempre
    // el mismo valor, para que la variante/jitter elegidos no cambien de
    // un frame a otro (nada de parpadeo por recalcular con Math.random()).
    function hash2(x, y, sal) {
      let h = (x * 374761393 + y * 668265263 + sal * 2147483647) | 0;
      h = (h ^ (h >>> 13)) * 1274126177;
      h = (h ^ (h >>> 16)) >>> 0;
      return h / 4294967296;
    }

    function elegirVariante(lista, x, y, sal) {
      if (!lista || lista.length === 0) return null;
      return lista[Math.floor(hash2(x, y, sal) * lista.length) % lista.length];
    }

    // Estampado con Y-sorting (informe: montañas y flora ordenadas de
    // norte a sur en un unico pase, para que el sur oculte al norte).
    // Devuelve true si dibujo con assets reales la categoria de relieve
    // (para que el llamador sepa si debe caer al dibujarRelieve() vectorial).
    function dibujarStampsRelieveYFlora(tam, data, frustum) {
      const montanaConAssets = (catalogoAssets.relieve.montana || []).length > 0;
      const elementos = [];

      for (let y = frustum.yMin; y < frustum.yMax; y++) {
        for (let x = frustum.xMin; x < frustum.xMax; x++) {
          const c = data.celdas[y][x];

          if (c.bioma === 'montana' && montanaConAssets) {
            const nombre = elegirVariante(catalogoAssets.relieve.montana, x, y, 91);
            const img = imagenesCache['relieve/' + nombre];
            if (img) {
              const baseY = (y + 1) * tam;
              elementos.push({
                img, ordenY: baseY,
                cx: x * tam + tam / 2 + (hash2(x, y, 92) - 0.5) * tam * 0.3,
                baseY,
                escala: 1.3 + c.elevacion * 0.7,
              });
            }
          }

          if (c.planta) {
            const variantes = catalogoAssets.flora[c.planta.especie] || [];
            const nombre = elegirVariante(variantes, x, y, 93);
            const img = nombre ? imagenesCache['flora/' + nombre] : null;
            if (img) {
              const baseY = y * tam + tam * 0.85 + (hash2(x, y, 95) - 0.5) * tam * 0.3;
              elementos.push({
                img, ordenY: baseY,
                cx: x * tam + tam / 2 + (hash2(x, y, 94) - 0.5) * tam * 0.5,
                baseY,
                escala: 0.4 + c.planta.etapa * 0.6,
              });
            }
          }
        }
      }

      elementos.sort((a, b) => a.ordenY - b.ordenY);
      for (const el of elementos) {
        const ancho = tam * 1.3 * el.escala;
        const alto = ancho * (el.img.naturalHeight / el.img.naturalWidth || 1);
        ctx.drawImage(el.img, el.cx - ancho / 2, el.baseY - alto, ancho, alto);
      }

      return montanaConAssets;
    }

    // Camara afin (informe seccion 4.1): tam0 es el tamano de celda de
    // referencia con zoom=1 (todo el grid cabe exacto en el canvas), fijado
    // la primera vez que se conoce data.ancho. offsetX/offsetY y zoom los
    // mueve la interaccion de raton -- ver mundoAPantalla()/pantallaAMundo()
    // mas abajo para la formula de transformacion.
    const ZOOM_MINIMO = 0.4, ZOOM_MAXIMO = 4.5;
    let tam0 = null;
    const camara = { zoom: 1, offsetX: 0, offsetY: 0 };

    function centrarCamara() {
      camara.zoom = 1;
      camara.offsetX = 0;
      camara.offsetY = 0;
    }

    function mundoAPantalla(x, y) {
      return { x: x * camara.zoom + camara.offsetX, y: y * camara.zoom + camara.offsetY };
    }

    // Frustum culling (informe seccion 4.1): rango de celdas realmente
    // visible en el canvas dado el zoom/offset actuales -- los bucles de
    // dibujo de terreno/vegetacion solo recorren este rango, no el grid
    // completo, aunque a 28x28 el ahorro real hoy sea modesto.
    function calcularFrustum(data) {
      const escala = tam0 * camara.zoom;
      const xMin = Math.max(0, Math.floor(-camara.offsetX / escala));
      const xMax = Math.min(data.ancho, Math.ceil((canvas.width - camara.offsetX) / escala));
      const yMin = Math.max(0, Math.floor(-camara.offsetY / escala));
      const yMax = Math.min(data.alto, Math.ceil((canvas.height - camara.offsetY) / escala));
      return { xMin, xMax, yMin, yMax };
    }

    // Paso 4: seleccion de entidad e inspeccion ECS ----------------------
    let entidadSeleccionadaId = null;
    let modoSeguimiento = false;
    let ultimoDataConocido = null;   // ultima instantanea recibida, para hit-test e informes por id

    // Hit-test contra la posicion en pantalla de cada entidad (misma
    // formula mundoAPantalla que usa el dibujado) -- selecciona la mas
    // cercana al click dentro de un radio razonable de acierto.
    function entidadEnPunto(data, px, py) {
      let mejor = null, distMejor = 16 * 16;   // radio de acierto ~16px
      for (const e of data.entidades) {
        const centro = mundoAPantalla((e.x + 0.5) * tam0, (e.y + 0.5) * tam0);
        const d = (centro.x - px) ** 2 + (centro.y - py) ** 2;
        if (d < distMejor) { distMejor = d; mejor = e; }
      }
      return mejor;
    }

    // --- Interaccion: arrastrar para desplazar, rueda para zoom, click para seleccionar ---
    let arrastrando = false;
    let ultimoPunteroX = 0, ultimoPunteroY = 0;
    let distanciaArrastre = 0;

    canvas.addEventListener('mousedown', (ev) => {
      arrastrando = true;
      distanciaArrastre = 0;
      canvas.classList.add('arrastrando');
      ultimoPunteroX = ev.clientX;
      ultimoPunteroY = ev.clientY;
    });
    window.addEventListener('mouseup', (ev) => {
      if (arrastrando && distanciaArrastre < 5 && ultimoDataConocido) {
        // Arrastre insignificante: se trata como un click de seleccion,
        // no como un pan -- evita que un pan largo dispare una seleccion
        // al soltar el boton lejos de donde se pulso.
        const rect = canvas.getBoundingClientRect();
        const px = (ev.clientX - rect.left) * (canvas.width / rect.width);
        const py = (ev.clientY - rect.top) * (canvas.height / rect.height);
        const encontrada = entidadEnPunto(ultimoDataConocido, px, py);
        entidadSeleccionadaId = encontrada ? encontrada.id : null;
        if (!encontrada) modoSeguimiento = false;
      }
      arrastrando = false;
      canvas.classList.remove('arrastrando');
    });
    window.addEventListener('mousemove', (ev) => {
      if (!arrastrando) return;
      const dx = ev.clientX - ultimoPunteroX, dy = ev.clientY - ultimoPunteroY;
      distanciaArrastre += Math.abs(dx) + Math.abs(dy);
      ultimoPunteroX = ev.clientX;
      ultimoPunteroY = ev.clientY;
      camara.offsetX += dx * (canvas.width / canvas.clientWidth);
      camara.offsetY += dy * (canvas.height / canvas.clientHeight);
    });
    canvas.addEventListener('wheel', (ev) => {
      ev.preventDefault();
      const rect = canvas.getBoundingClientRect();
      const px = (ev.clientX - rect.left) * (canvas.width / rect.width);
      const py = (ev.clientY - rect.top) * (canvas.height / rect.height);

      const zoomAnterior = camara.zoom;
      const factor = Math.exp(-ev.deltaY * 0.001);
      camara.zoom = Math.min(ZOOM_MAXIMO, Math.max(ZOOM_MINIMO, camara.zoom * factor));

      // Zoom centrado en el cursor: el punto del mundo bajo el raton debe
      // quedarse fijo en pantalla antes y despues de escalar.
      const razon = camara.zoom / zoomAnterior;
      camara.offsetX = px - (px - camara.offsetX) * razon;
      camara.offsetY = py - (py - camara.offsetY) * razon;
    }, { passive: false });

    document.getElementById('btn-centrar').addEventListener('click', centrarCamara);

    // PRNG determinista (mulberry32) sembrado por instantanea.semilla --
    // el grano del pergamino debe ser el MISMO en cada recarga del mismo
    // mundo, no ruido distinto cada frame (eso rompería la ilusion de un
    // mapa fisico real, no una textura decorativa aleatoria).
    function mulberry32(a) {
      return function () {
        a |= 0; a = (a + 0x6D2B79F5) | 0;
        let t = Math.imul(a ^ (a >>> 15), 1 | a);
        t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
      };
    }

    function construirPergamino(semilla, ancho, alto) {
      const off = document.createElement('canvas');
      off.width = canvas.width;
      off.height = canvas.height;
      const octx = off.getContext('2d');

      octx.fillStyle = '#e6d8b8';
      octx.fillRect(0, 0, off.width, off.height);

      const rng = mulberry32((semilla ?? 42) * 2654435761 % 4294967296);
      const manchas = Math.floor((off.width * off.height) / 900);
      for (let i = 0; i < manchas; i++) {
        const x = rng() * off.width;
        const y = rng() * off.height;
        const r = 1.5 + rng() * 5.5;
        const tono = rng() < 0.5 ? '60,45,25' : '210,190,140';
        octx.fillStyle = `rgba(${tono}, ${(0.02 + rng() * 0.05).toFixed(3)})`;
        octx.beginPath();
        octx.ellipse(x, y, r, r * (0.6 + rng() * 0.8), rng() * Math.PI, 0, Math.PI * 2);
        octx.fill();
      }

      const vinieta = octx.createRadialGradient(
        off.width / 2, off.height / 2, off.width * 0.35,
        off.width / 2, off.height / 2, off.width * 0.72
      );
      vinieta.addColorStop(0, 'rgba(0,0,0,0)');
      vinieta.addColorStop(1, 'rgba(40,26,12,0.35)');
      octx.fillStyle = vinieta;
      octx.fillRect(0, 0, off.width, off.height);

      return off;
    }

    function dibujarMarco(tam, ancho, alto) {
      // Diego pidio quitar la reticula (2026-08-27): el mapa no debe leerse
      // como celdas a nivel visual, aunque la simulacion siga siendo un
      // grid por dentro. Se queda solo el marco perimetral -- sin lineas
      // internas ni numeracion de coordenadas (esta ultima solo tenia
      // sentido como referencia de esa reticula que ya no esta).
      const compensa = 1 / camara.zoom;
      ctx.strokeStyle = 'rgba(36,26,15,0.85)';
      ctx.lineWidth = compensa * 3;
      ctx.strokeRect(0.75 * compensa, 0.75 * compensa, ancho * tam - 1.5 * compensa, alto * tam - 1.5 * compensa);
    }

    // Paso 2: relieve, hidrografia vectorial y vegetacion --------------

    function dibujarRelieve(tam, data, frustum) {
      // Silueta triangular con sombreado este por celda de bioma Montana
      // (LOD macro de la propuesta) -- sin isolineas de curva de nivel
      // todavia, eso queda para cuando el zoom micro le de sentido a un
      // trazo mas fino que una celda entera.
      for (let y = frustum.yMin; y < frustum.yMax; y++) {
        for (let x = frustum.xMin; x < frustum.xMax; x++) {
          const c = data.celdas[y][x];
          if (c.bioma !== 'montana') continue;
          const cx = x * tam + tam / 2;
          const base = y * tam + tam * 0.86;
          const apice = y * tam + tam * (0.22 - Math.min(0.14, c.elevacion * 0.14));
          const izq = x * tam + tam * 0.08;
          const der = x * tam + tam * 0.92;

          ctx.beginPath();
          ctx.moveTo(cx, apice); ctx.lineTo(izq, base); ctx.lineTo(cx, base);
          ctx.closePath();
          ctx.fillStyle = 'rgba(150,140,124,0.5)';
          ctx.fill();

          ctx.beginPath();
          ctx.moveTo(cx, apice); ctx.lineTo(der, base); ctx.lineTo(cx, base);
          ctx.closePath();
          ctx.fillStyle = 'rgba(94,84,70,0.5)';
          ctx.fill();

          ctx.strokeStyle = 'rgba(58,43,26,0.4)';
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(izq, base); ctx.lineTo(cx, apice); ctx.lineTo(der, base);
          ctx.stroke();
        }
      }
    }

    // Contorno real de un cluster de celdas (mismo algoritmo que ya se usa
    // para picos/lagos-sin-asset): recorre cada celda en sentido horario,
    // se queda solo con las aristas que dan a fuera del cluster, y las
    // encadena por sus puntos hasta formar el poligono de frontera exacto.
    function contornoDeCluster(cluster, tam) {
      const enCluster = new Set(cluster.map(c => c.x + ',' + c.y));
      const dentro = (x, y) => enCluster.has(x + ',' + y);
      const aristas = new Map();
      for (const { x, y } of cluster) {
        if (!dentro(x, y - 1)) aristas.set(`${x},${y}`, { x: x + 1, y: y });
        if (!dentro(x + 1, y)) aristas.set(`${x+1},${y}`, { x: x + 1, y: y + 1 });
        if (!dentro(x, y + 1)) aristas.set(`${x+1},${y+1}`, { x: x, y: y + 1 });
        if (!dentro(x - 1, y)) aristas.set(`${x},${y+1}`, { x: x, y: y });
      }
      const usados = new Set();
      let mejorBucle = [];
      for (const inicioClave of aristas.keys()) {
        if (usados.has(inicioClave)) continue;
        const bucle = [];
        let claveActual = inicioClave;
        while (!usados.has(claveActual) && aristas.has(claveActual)) {
          usados.add(claveActual);
          const [px, py] = claveActual.split(',').map(Number);
          bucle.push({ x: px, y: py });
          const fin = aristas.get(claveActual);
          claveActual = `${fin.x},${fin.y}`;
        }
        if (bucle.length > mejorBucle.length) mejorBucle = bucle;
      }
      return mejorBucle.map(p => ({ x: p.x * tam, y: p.y * tam }));
    }

    // Chaikin corner-cutting: redondea el contorno en bloques del grid
    // hacia una silueta organica -- sin esto, el borde entre dos biomas
    // vecinos es literalmente la arista recta de las celdas, que se nota
    // mucho mas ahora que no hay reticula encima disimulandolo.
    function suavizarChaikin(puntos, iteraciones) {
      let pts = puntos;
      for (let it = 0; it < iteraciones; it++) {
        const nuevos = [];
        for (let i = 0; i < pts.length; i++) {
          const p0 = pts[i], p1 = pts[(i + 1) % pts.length];
          nuevos.push({ x: p0.x * 0.75 + p1.x * 0.25, y: p0.y * 0.75 + p1.y * 0.25 });
          nuevos.push({ x: p0.x * 0.25 + p1.x * 0.75, y: p0.y * 0.25 + p1.y * 0.75 });
        }
        pts = nuevos;
      }
      return pts;
    }

    function trazarPoligono(puntos) {
      ctx.beginPath();
      ctx.moveTo(puntos[0].x, puntos[0].y);
      for (let i = 1; i <= puntos.length; i++) {
        const p = puntos[i % puntos.length];
        ctx.lineTo(p.x, p.y);
      }
    }

    // Componentes conexas (4-vecinos) por bioma -- mismo patron que
    // componentesAgua() de mas abajo, pero agrupando por Celda.bioma en
    // vez de tipo_agua.
    function componentesPorBioma(data) {
      const visitado = new Set();
      const resultado = [];
      for (let y = 0; y < data.alto; y++) {
        for (let x = 0; x < data.ancho; x++) {
          const clave = x + ',' + y;
          if (visitado.has(clave)) continue;
          const bioma = data.celdas[y][x].bioma;
          const pila = [[x, y]];
          visitado.add(clave);
          const cluster = [];
          while (pila.length) {
            const [cx, cy] = pila.pop();
            cluster.push({ x: cx, y: cy, c: data.celdas[cy][cx] });
            for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
              const nx = cx + dx, ny = cy + dy;
              if (nx < 0 || ny < 0 || nx >= data.ancho || ny >= data.alto) continue;
              const k = nx + ',' + ny;
              if (visitado.has(k)) continue;
              if (data.celdas[ny][nx].bioma === bioma) { visitado.add(k); pila.push([nx, ny]); }
            }
          }
          resultado.push({ bioma, cluster });
        }
      }
      return resultado;
    }

    // El contorno ya suavizado por Chaikin sigue leyendose "artificial"
    // (Diego, 2026-08-27): Chaikin solo redondea esquinas, el resultado es
    // una silueta demasiado uniforme -- una "burbuja" en vez de una costa
    // real. Esto añade una ondulacion de baja frecuencia (dos senos
    // superpuestos, como dos octavas de ruido) perpendicular al contorno,
    // con fase fija por region (hash de su primera celda + semilla del
    // mundo) para que no cambie de un frame a otro. No sustituye a
    // Chaikin, se aplica DESPUES: Chaikin quita las esquinas de celda,
    // esto rompe la regularidad que Chaikin por si solo deja perfecta.
    function ondularContorno(puntos, amplitud, fase) {
      let longitudAcum = 0;
      const salida = [];
      for (let i = 0; i < puntos.length; i++) {
        const p0 = puntos[i], p1 = puntos[(i + 1) % puntos.length];
        const dx = p1.x - p0.x, dy = p1.y - p0.y;
        const seg = Math.hypot(dx, dy) || 1;
        const nx = -dy / seg, ny = dx / seg;
        const onda1 = Math.sin(longitudAcum / 42 + fase) * amplitud;
        const onda2 = Math.sin(longitudAcum / 15 + fase * 2.3) * amplitud * 0.35;
        const bulto = onda1 + onda2;
        salida.push({ x: p0.x + nx * bulto, y: p0.y + ny * bulto });
        longitudAcum += seg;
      }
      return salida;
    }

    // Lavado de biomas como manchas organicas (una silueta suavizada por
    // region contigua) en vez de un fillRect por celda -- el borde entre
    // dos biomas vecinos ya no es la arista recta de la cuadricula.
    function dibujarBiomas(tam, data) {
      for (const { bioma, cluster } of componentesPorBioma(data)) {
        const base = COLOR_BIOMA[bioma] || [120, 110, 90];
        // Modulacion "acuarela": la lluvia media del cluster oscurece el
        // lavado -- mismo criterio que antes, ahora por region en vez de
        // por celda individual (una region contigua tiene lluvia parecida
        // de por si, al venir del mismo campo continuo).
        const lluviaMedia = cluster.reduce((s, c) => s + c.c.lluvia, 0) / cluster.length;
        const sombra = 1 - lluviaMedia * 0.22;
        const color = `${Math.round(base[0]*sombra)}, ${Math.round(base[1]*sombra)}, ${Math.round(base[2]*sombra)}`;

        // Capa base solida por celda (SIN Chaikin) primero: Chaikin encoge
        // cada region hacia dentro de forma independiente, asi que dos
        // regiones vecinas suavizadas por separado dejan un hueco sin
        // cubrir en su borde compartido -- ahi se veria el pergamino
        // crudo si esta capa no existiera. La silueta organica de encima
        // es la que de verdad se ve; esta capa solo evita el hueco.
        ctx.fillStyle = `rgba(${color}, 0.40)`;
        for (const cel of cluster) ctx.fillRect(cel.x * tam, cel.y * tam, tam, tam);

        let contorno = suavizarChaikin(contornoDeCluster(cluster, tam), 2);
        const fase = hash2(cluster[0].x, cluster[0].y, 211) * Math.PI * 2;
        contorno = ondularContorno(contorno, tam * 0.3, fase);
        trazarPoligono(contorno);
        ctx.fillStyle = `rgba(${color}, 0.40)`;
        ctx.fill();
      }
    }

    // Componentes conexas (4-vecinos) de celdas con el mismo tipo_agua --
    // el motor (nucleo/agua.py) SI agrupa celdas en cuerpos de agua al
    // generarlas, pero solo persiste tipo/profundidad por celda, no un id
    // de cuerpo. Reconstruirlo aqui via flood-fill sobre datos reales
    // (posicion + tipo_agua, ambos expuestos por construir_instantanea) no
    // inventa estado nuevo, solo agrupa visualmente lo que ya es contiguo.
    function componentesAgua(data, tipoObjetivo) {
      const visitado = new Set();
      const componentes = [];
      for (let y = 0; y < data.alto; y++) {
        for (let x = 0; x < data.ancho; x++) {
          if (data.celdas[y][x].tipo_agua !== tipoObjetivo) continue;
          const clave = x + ',' + y;
          if (visitado.has(clave)) continue;
          const pila = [[x, y]];
          visitado.add(clave);
          const comp = [];
          while (pila.length) {
            const [cx, cy] = pila.pop();
            const celda = data.celdas[cy][cx];
            comp.push({ x: cx, y: cy, elevacion: celda.elevacion, profundidad: celda.profundidad_agua });
            for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
              const nx = cx + dx, ny = cy + dy;
              if (nx < 0 || ny < 0 || nx >= data.ancho || ny >= data.alto) continue;
              const k = nx + ',' + ny;
              if (visitado.has(k)) continue;
              if (data.celdas[ny][nx].tipo_agua === tipoObjetivo) { visitado.add(k); pila.push([nx, ny]); }
            }
          }
          componentes.push(comp);
        }
      }
      return componentes;
    }

    // Reconstruccion visual de un camino continuo por una componente de
    // rio: nucleo/agua.py SI calcula un camino de descenso ordenado al
    // generar el mundo (_trazar_rio), pero no lo persiste por celda --
    // aqui se aproxima por vecino-mas-cercano partiendo de la celda de
    // mayor elevacion, sobre datos 100% reales (posicion + elevacion).
    // Para un cauce de un solo trazo (el caso normal) reproduce el camino
    // real; en una confluencia puede aproximar, nunca inventa una celda
    // que no exista.
    function ordenarCaminoRio(componente) {
      const restante = componente.slice().sort((a, b) => b.elevacion - a.elevacion);
      const camino = [restante.shift()];
      while (restante.length) {
        const actual = camino[camino.length - 1];
        let idxMejor = 0, distMejor = Infinity;
        for (let i = 0; i < restante.length; i++) {
          const dx = restante[i].x - actual.x, dy = restante[i].y - actual.y;
          const d = dx * dx + dy * dy;
          if (d < distMejor) { distMejor = d; idxMejor = i; }
        }
        camino.push(restante.splice(idxMejor, 1)[0]);
      }
      return camino;
    }

    // Spline Catmull-Rom simplificado (informe seccion 4.3): un
    // quadraticCurveTo por punto medio entre celdas consecutivas.
    function trazarSpline(puntos) {
      ctx.moveTo(puntos[0].x, puntos[0].y);
      for (let i = 1; i < puntos.length - 1; i++) {
        const xc = (puntos[i].x + puntos[i + 1].x) / 2;
        const yc = (puntos[i].y + puntos[i + 1].y) / 2;
        ctx.quadraticCurveTo(puntos[i].x, puntos[i].y, xc, yc);
      }
      const ultimo = puntos[puntos.length - 1];
      ctx.lineTo(ultimo.x, ultimo.y);
    }

    function dibujarCuenca(tam, comp) {
      // Lago/poza/rio de una sola celda: cuenca organica por solapamiento
      // de circulos, sin borde poligonal exacto (aproximacion deliberada,
      // suficiente para el nivel de detalle macro de este paso).
      for (const celda of comp) {
        const cx = celda.x * tam + tam / 2, cy = celda.y * tam + tam / 2;
        const profundidad = Math.min(1, celda.profundidad / 2.5);
        ctx.beginPath();
        ctx.arc(cx, cy, tam * 0.66, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(48, 82, 112, ${(0.5 + profundidad * 0.3).toFixed(3)})`;
        ctx.fill();
      }
      ctx.strokeStyle = 'rgba(28,40,51,0.5)';
      ctx.lineWidth = 1.2;
      for (const celda of comp) {
        const cx = celda.x * tam + tam / 2, cy = celda.y * tam + tam / 2;
        ctx.beginPath();
        ctx.arc(cx, cy, tam * 0.66, 0, Math.PI * 2);
        ctx.stroke();
      }
    }

    // Estampa una imagen ajustada al recuadro real (en pixeles de mundo)
    // de un cluster de celdas, con un margen para que la mancha organica
    // del sello sobresalga un poco de las celdas exactas (igual que la
    // silueta vectorial que sustituye nunca fue un rectangulo perfecto).
    function estamparEnRecuadro(img, cluster, tam, margen) {
      const minX = Math.min(...cluster.map(c => c.x)), maxX = Math.max(...cluster.map(c => c.x));
      const minY = Math.min(...cluster.map(c => c.y)), maxY = Math.max(...cluster.map(c => c.y));
      const anchoBase = (maxX - minX + 1) * tam, altoBase = (maxY - minY + 1) * tam;
      const w = anchoBase * margen, h = altoBase * margen;
      const cx = (minX + maxX + 1) / 2 * tam, cy = (minY + maxY + 1) / 2 * tam;
      ctx.drawImage(img, cx - w / 2, cy - h / 2, w, h);
    }

    function dibujarCuencaConAssets(tam, comp, variantesLago) {
      const nombre = elegirVariante(variantesLago, comp[0].x, comp[0].y, 96);
      const img = nombre ? imagenesCache['agua/' + nombre] : null;
      if (!img) { dibujarCuenca(tam, comp); return; }
      estamparEnRecuadro(img, comp, tam, 1.35);
    }

    // Un rio es un CAMINO, no una mancha -- un sello prediseñado no puede
    // calzar sus curvas exactas celda a celda (a diferencia de un lago o
    // una montaña, que son razonablemente compactos). Aproximacion
    // deliberada: se estampa UNA vez por curso de agua conectado, a su
    // proporcion original (sin deformar), escalado por la longitud real
    // del camino y con un giro de 90 grados si el curso es mas alto que
    // ancho -- no es un trazado exacto, es la pieza mas experimental del
    // sistema de sellos (ver presentacion/assets/README.md).
    function dibujarRioConAssets(tam, comp, variantesRio) {
      const camino = ordenarCaminoRio(comp);
      const nombre = elegirVariante(variantesRio, camino[0].x, camino[0].y, 97);
      const img = nombre ? imagenesCache['agua/' + nombre] : null;
      if (!img) { dibujarRioVectorial(tam, comp); return; }

      const minX = Math.min(...comp.map(c => c.x)), maxX = Math.max(...comp.map(c => c.x));
      const minY = Math.min(...comp.map(c => c.y)), maxY = Math.max(...comp.map(c => c.y));
      const cx = (minX + maxX + 1) / 2 * tam, cy = (minY + maxY + 1) / 2 * tam;
      const vertical = (maxY - minY) > (maxX - minX);

      const largo = tam * (comp.length * 0.62 + 1.5);
      const relacion = img.naturalHeight / img.naturalWidth || 0.3;
      let w = largo, h = largo * relacion;
      if (vertical) { const t = w; w = h; h = t; }

      ctx.save();
      ctx.translate(cx, cy);
      if (vertical) ctx.rotate(Math.PI / 2);
      ctx.drawImage(img, -largo / 2, -(largo * relacion) / 2, largo, largo * relacion);
      ctx.restore();
    }

    function dibujarRioVectorial(tam, comp) {
      if (comp.length < 2) { dibujarCuenca(tam, comp); return; }

      const camino = ordenarCaminoRio(comp).map(p => ({
        x: p.x * tam + tam / 2, y: p.y * tam + tam / 2, profundidad: p.profundidad,
      }));
      const profundidadMedia = camino.reduce((s, p) => s + p.profundidad, 0) / camino.length;
      const anchoBase = tam * (0.28 + Math.min(1, profundidadMedia / 1.5) * 0.4);

      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';

      // Halo translucido (el agua moja mas alla del cauce firme).
      ctx.beginPath();
      trazarSpline(camino);
      ctx.strokeStyle = 'rgba(58,92,122,0.35)';
      ctx.lineWidth = anchoBase * 1.8;
      ctx.stroke();

      // Cauce central, tinta de agua profunda.
      ctx.beginPath();
      trazarSpline(camino);
      ctx.strokeStyle = 'rgba(28,45,64,0.75)';
      ctx.lineWidth = anchoBase;
      ctx.stroke();
    }

    function dibujarHidrografia(tam, data) {
      const variantesLago = catalogoAssets.agua.lago || [];
      const variantesRio = catalogoAssets.agua.rio || [];

      componentesAgua(data, 'lago').forEach(comp => dibujarCuencaConAssets(tam, comp, variantesLago));
      componentesAgua(data, 'poza').forEach(comp => dibujarCuencaConAssets(tam, comp, variantesLago));

      for (const comp of componentesAgua(data, 'rio')) {
        if (comp.length < 2) { dibujarCuencaConAssets(tam, comp, variantesLago); continue; }
        if (variantesRio.length > 0) dibujarRioConAssets(tam, comp, variantesRio);
        else dibujarRioVectorial(tam, comp);
      }
    }

    function dibujarVegetacion(tam, data, frustum) {
      // Sin lista de entidades aparte: se recorre celdas[][] en el mismo
      // orden Y ascendente que el resto del lienzo -- el pintado de una
      // fila mas al sur pisa a la de mas al norte, mismo Y-sorting norte-
      // sur que pide la propuesta, gratis por el orden del bucle.
      //
      // LOD macro (informe seccion 4.2): con el mapa muy alejado, dibujar
      // una planta por celda individual es ruido visual sin ganar nada --
      // el lavado de bioma de la pasada anterior ya sugiere la vegetacion
      // como masa. Se omite esta capa entera por debajo de zoom 0.8, igual
      // que la tabla LOD de bosques pide "relleno plano" a esa escala.
      if (camara.zoom < 0.8) return;
      for (let y = frustum.yMin; y < frustum.yMax; y++) {
        for (let x = frustum.xMin; x < frustum.xMax; x++) {
          const c = data.celdas[y][x];
          if (!c.planta) continue;
          // Esta especie ya tiene assets reales cargados -- la dibuja
          // dibujarStampsRelieveYFlora() como sello, no como vectorial.
          if ((catalogoAssets.flora[c.planta.especie] || []).length > 0) continue;
          // Diego pidio quitar el tapiz vectorial de hierba silvestre por
          // ahora (2026-08-27) mientras no exista un asset real para ella
          // -- la celda se queda solo con el lavado de bioma de base, sin
          // relleno provisional. En cuanto haya flora/hierba_silvestre_*.png
          // el guard de arriba ya la desvia sola al sistema de sellos.
          if (c.planta.especie === 'hierba_silvestre') continue;
          const cx = x * tam + tam / 2, cy = y * tam + tam / 2;
          const escala = 0.32 + 0.68 * c.planta.etapa;
          const [r, g, b] = COLOR_ESPECIE[c.planta.especie] || [90, 110, 70];

          if (c.planta.especie === 'manzano') {
            ctx.strokeStyle = 'rgba(58,40,24,0.6)';
            ctx.lineWidth = Math.max(1, tam * 0.05);
            ctx.beginPath();
            ctx.moveTo(cx, cy + tam * 0.32);
            ctx.lineTo(cx, cy + tam * 0.08);
            ctx.stroke();

            ctx.beginPath();
            ctx.arc(cx, cy - tam * 0.05, tam * 0.34 * escala, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(${r},${g},${b},0.85)`;
            ctx.fill();

            if (c.planta.etapa >= 1.0) {
              ctx.fillStyle = 'rgba(150,40,32,0.8)';
              for (const [ox, oy] of [[-0.12, -0.08], [0.1, 0.02], [-0.02, 0.14]]) {
                ctx.beginPath();
                ctx.arc(cx + ox * tam, cy - tam * 0.05 + oy * tam, tam * 0.045, 0, Math.PI * 2);
                ctx.fill();
              }
            }
          } else if (c.planta.especie === 'hierba_silvestre') {
            ctx.strokeStyle = `rgba(${r},${g},${b},0.85)`;
            ctx.lineWidth = Math.max(1, tam * 0.06);
            for (const dx of [-0.18, 0, 0.18]) {
              ctx.beginPath();
              ctx.moveTo(cx + dx * tam, cy + tam * 0.3);
              ctx.quadraticCurveTo(cx + dx * tam * 1.4, cy, cx + dx * tam * 0.6, cy - tam * 0.28 * escala);
              ctx.stroke();
            }
          } else if (c.planta.especie === 'cactus') {
            const ancho = tam * 0.16 * escala, alto = tam * 0.42 * escala;
            ctx.fillStyle = `rgba(${r},${g},${b},0.85)`;
            ctx.beginPath();
            ctx.roundRect(cx - ancho / 2, cy + tam * 0.24 - alto, ancho, alto, ancho * 0.5);
            ctx.fill();
          } else {
            // liquen / musgo: mismo tratamiento (mancha baja e irregular
            // sin estructura vertical), solo cambia el color por especie.
            ctx.fillStyle = `rgba(${r},${g},${b},0.55)`;
            ctx.beginPath();
            ctx.ellipse(cx, cy + tam * 0.18, tam * 0.3 * escala, tam * 0.14 * escala, 0, 0, Math.PI * 2);
            ctx.fill();
          }
        }
      }
    }

    // Paso 4: ficha de criatura (panel de inspeccion ECS) ----------------

    function formatoPct(v) { return Math.round(Math.max(0, Math.min(1, v)) * 100) + '%'; }

    function colorBarra(valor) {
      if (valor > 0.55) return 'rgba(58,110,58,0.85)';
      if (valor > 0.25) return 'rgba(160,120,30,0.85)';
      return 'rgba(150,40,32,0.85)';
    }

    function filaBarra(etiqueta, valor) {
      const pct = Math.max(0, Math.min(1, valor)) * 100;
      return `<div class="fila-stat"><span>${etiqueta}</span><span>${formatoPct(valor)}</span></div>` +
             `<div class="barra-contenedor"><div class="barra-relleno" style="width:${pct}%;background:${colorBarra(valor)}"></div></div>`;
    }

    // Enlace a un progenitor SOLO si sigue presente en la instantanea
    // actual (vivo y dentro del ECS ahora mismo) -- si no, texto plano
    // honesto en vez de un enlace roto a algo que ya no se puede mostrar.
    function enlaceProgenitor(data, id, etiqueta) {
      if (id === null || id === undefined) {
        return `<span class="nota-ficha">${etiqueta}: fundador, sin registro</span>`;
      }
      const existe = data.entidades.some(en => en.id === id);
      if (!existe) return `<span class="nota-ficha">${etiqueta}: #${id} (no localizable ahora)</span>`;
      return `${etiqueta}: <button class="enlace-parentesco" data-id="${id}">#${id}</button>`;
    }

    function actualizarFicha(data) {
      const cont = document.getElementById('ficha-entidad');

      if (entidadSeleccionadaId === null) {
        cont.innerHTML = '<h3>Registro de Criatura</h3>' +
          '<div class="nota-ficha">Toca una criatura o resto en el mapa para ver su ficha.</div>';
        return;
      }

      const e = data.entidades.find(en => en.id === entidadSeleccionadaId);
      if (!e) {
        cont.innerHTML = '<h3>Registro de Criatura</h3>' +
          '<div class="nota-ficha">La entidad seleccionada ya no esta activa (murio, fue devorada o removida).</div>';
        entidadSeleccionadaId = null;
        modoSeguimiento = false;
        return;
      }

      if (e.tipo === 'necromasa') {
        cont.innerHTML = `<h3>🦴 Restos &middot; ${e.origen}</h3>` +
          `<div class="fila-stat"><span>Posicion</span><span>(${e.x}, ${e.y})</span></div>` +
          `<div class="fila-stat"><span>Masa organica</span><span>${e.masa} kg</span></div>` +
          `<div class="fila-botones"><button class="accion-ficha" id="btn-deseleccionar">Cerrar ficha</button></div>`;
        document.getElementById('btn-deseleccionar').addEventListener('click', () => {
          entidadSeleccionadaId = null; modoSeguimiento = false;
        });
        return;
      }

      const runa = RUNAS[e.tipo] || '?';
      let html = `<h3>${runa} ${e.tipo.toUpperCase()} #${e.id}${e.nombre ? ' &middot; "' + e.nombre + '"' : ''}</h3>`;
      html += `<div class="fila-stat"><span>Sexo</span><span>${e.sexo || '-'}</span></div>`;
      html += `<div class="fila-stat"><span>Edad</span><span>${e.edad_anios} anios</span></div>`;
      html += `<div class="fila-stat"><span>Accion actual</span><span>${e.accion || '-'}</span></div>`;
      html += `<div class="fila-stat"><span>Posicion</span><span>(${e.x}, ${e.y})</span></div>`;

      html += '<div class="seccion-ficha"><strong>Linaje</strong><br>' +
        enlaceProgenitor(data, e.id_madre, 'Madre') + '<br>' +
        enlaceProgenitor(data, e.id_padre, 'Padre') + '</div>';

      if (e.necesidades) {
        html += '<div class="seccion-ficha"><strong>Necesidades</strong>';
        for (const [k, v] of Object.entries(e.necesidades)) html += filaBarra(k, v);
        html += '</div>';
      }
      if (e.pool_fisico) {
        html += '<div class="seccion-ficha"><strong>Pools fisicos</strong>' +
          filaBarra('vitalidad', e.pool_fisico.vitalidad) +
          filaBarra('resistencia', e.pool_fisico.resistencia) + '</div>';
      }
      if (e.pool_mental) {
        html += '<div class="seccion-ficha"><strong>Pool mental</strong>' +
          filaBarra('estabilidad', e.pool_mental.estabilidad) + '</div>';
      }
      if (e.temperamento) {
        html += '<div class="seccion-ficha"><strong>Temperamento</strong>';
        for (const [k, v] of Object.entries(e.temperamento)) html += filaBarra(k, v);
        html += '</div>';
      }
      if (e.dimensiones) {
        // "peso" NO se muestra en kg: DimensionesFisicas.peso sigue siendo
        // una escala abstracta en el motor (ver componentes/dimensiones_
        // fisicas.py), fingir una unidad real aqui violaria el Principio 4.
        html += `<div class="seccion-ficha nota-ficha">Peso (escala relativa): ${e.dimensiones.peso} ` +
          `&middot; Altura: ${e.dimensiones.altura_m} m &middot; Fuerza: ${e.dimensiones.fuerza}</div>`;
      }

      html += `<div class="fila-botones">` +
        `<button class="accion-ficha${modoSeguimiento ? ' activo' : ''}" id="btn-seguir">` +
        `${modoSeguimiento ? 'Siguiendo...' : 'Seguir esta entidad'}</button>` +
        `<button class="accion-ficha" id="btn-deseleccionar">Cerrar ficha</button></div>`;

      cont.innerHTML = html;
      document.getElementById('btn-seguir').addEventListener('click', () => { modoSeguimiento = !modoSeguimiento; });
      document.getElementById('btn-deseleccionar').addEventListener('click', () => {
        entidadSeleccionadaId = null; modoSeguimiento = false;
      });
      cont.querySelectorAll('.enlace-parentesco').forEach((btn) => {
        btn.addEventListener('click', () => { entidadSeleccionadaId = parseInt(btn.dataset.id, 10); });
      });
    }

    let filtroCronica = '';
    document.getElementById('buscar-cronica').addEventListener('input', (ev) => {
      filtroCronica = ev.target.value.toLowerCase();
    });

    async function actualizar() {
      try {
        const resp = await fetch('/estado.json');
        if (!resp.ok) return;
        const data = await resp.json();
        if (!data.celdas) return;
        ultimoDataConocido = data;

        document.getElementById('info-mundo').innerHTML =
          `<strong>Semilla:</strong> ${data.semilla} &middot; <strong>Tick:</strong> ${data.tick} &middot; ` +
          `<strong>Dia:</strong> ${data.dia} &middot; <strong>Anio:</strong> ${data.anio}<br>` +
          `<strong>Estacion:</strong> ${data.estacion} &middot; <strong>Clima:</strong> ${data.clima}`;

        document.getElementById('info-poblacion').innerHTML =
          `<strong>Gnomos:</strong> ${data.censo.gnomo || 0} &middot; <strong>Lobos:</strong> ${data.censo.lobo || 0} &middot; ` +
          `<strong>Conejos:</strong> ${data.censo.conejo || 0} &middot; <strong>Ardillas:</strong> ${data.censo.ardilla || 0}<br>` +
          `<strong>Restos (Necromasa):</strong> ${data.censo.necromasa || 0}`;

        tam0 = canvas.width / data.ancho;
        const tam = tam0;

        // Modo seguimiento (informe seccion 6.1): la camara persigue a la
        // entidad seleccionada, con suavizado exponencial en vez de un
        // salto brusco cada tick -- solo mueve offsetX/offsetY, el zoom
        // actual del usuario se respeta.
        if (modoSeguimiento && entidadSeleccionadaId !== null) {
          const objetivo = data.entidades.find((en) => en.id === entidadSeleccionadaId);
          if (objetivo) {
            const deseadoX = canvas.width / 2 - (objetivo.x + 0.5) * tam * camara.zoom;
            const deseadoY = canvas.height / 2 - (objetivo.y + 0.5) * tam * camara.zoom;
            camara.offsetX += (deseadoX - camara.offsetX) * 0.15;
            camara.offsetY += (deseadoY - camara.offsetY) * 0.15;
          }
        }

        const claveActual = `${data.semilla}:${data.ancho}:${data.alto}`;
        if (pergaminoClave !== claveActual) {
          pergaminoCache = construirPergamino(data.semilla, data.ancho, data.alto);
          pergaminoClave = claveActual;
        }

        document.getElementById('lectura-zoom').textContent = `Zoom: ${camara.zoom.toFixed(2)}x`;

        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.save();
        ctx.translate(camara.offsetX, camara.offsetY);
        ctx.scale(camara.zoom, camara.zoom);

        const frustum = calcularFrustum(data);
        ctx.drawImage(pergaminoCache, 0, 0, data.ancho * tam, data.alto * tam);
        dibujarBiomas(tam, data);

        for (let y = frustum.yMin; y < frustum.yMax; y++) {
          for (let x = frustum.xMin; x < frustum.xMax; x++) {
            const c = data.celdas[y][x];
            const px = x * tam, py = y * tam;

            // Agua permanente (rio/lago/poza) ya no se pinta plana aqui --
            // dibujarHidrografia() la traza como forma vectorial despues de
            // esta pasada. El charco efimero SI se queda plano: es una
            // mancha de un tick, no un cuerpo geografico que merezca trazo.
            if (c.profundidad_charco > 0) {
              const intensidad = Math.min(1, c.profundidad_charco / 0.3);
              ctx.fillStyle = `rgba(${COLOR_CHARCO[0]}, ${COLOR_CHARCO[1]}, ${COLOR_CHARCO[2]}, ${0.15 + intensidad * 0.3})`;
              ctx.fillRect(px, py, tam, tam);
            }

            if (c.en_llamas) {
              ctx.fillStyle = `rgba(${COLOR_FUEGO[0]}, ${COLOR_FUEGO[1]}, ${COLOR_FUEGO[2]}, 0.55)`;
              ctx.fillRect(px, py, tam, tam);
            }
          }
        }

        const montanaUsoAssets = dibujarStampsRelieveYFlora(tam, data, frustum);
        if (!montanaUsoAssets) dibujarRelieve(tam, data, frustum);
        dibujarHidrografia(tam, data);
        dibujarVegetacion(tam, data, frustum);
        dibujarMarco(tam, data.ancho, data.alto);

        ctx.restore();

        // Entidades: LOD por nivel de zoom (informe seccion 4.2), dibujadas
        // en espacio de pantalla -- el tamano de runa/halo/etiqueta NO
        // escala junto al mapa, lo decide el nivel de detalle actual, igual
        // que un marcador de mapa real no cambia de tamano al hacer zoom.
        const nivel = camara.zoom < 0.8 ? 'macro' : (camara.zoom < 2.0 ? 'medio' : 'micro');
        data.entidades.forEach(e => {
          const centro = mundoAPantalla((e.x + 0.5) * tam, (e.y + 0.5) * tam);
          const margen = 24;
          if (centro.x < -margen || centro.x > canvas.width + margen ||
              centro.y < -margen || centro.y > canvas.height + margen) return;

          const [r, g, b] = COLOR_INK_ESPECIE[e.tipo] || [70, 60, 50];
          const runa = RUNAS[e.tipo] || '?';
          const seleccionada = e.id === entidadSeleccionadaId;

          if (nivel === 'macro') {
            ctx.beginPath();
            ctx.arc(centro.x, centro.y, 3, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(${r},${g},${b},0.9)`;
            ctx.fill();
            if (seleccionada) {
              ctx.beginPath();
              ctx.arc(centro.x, centro.y, 7, 0, Math.PI * 2);
              ctx.strokeStyle = 'rgba(212,172,13,0.9)';
              ctx.lineWidth = 1.5;
              ctx.stroke();
            }
            return;
          }

          // Retrato real (informe: sello por especie, no un icono generico)
          // si hay assets/criaturas/<especie>_N.png -- variante elegida por
          // hash del ID de la entidad (no de su posicion, que cambia cada
          // tick) para que el mismo individuo conserve siempre la misma
          // pose entre frames. Sin asset, cae al halo+runa de siempre.
          const variantesCriatura = catalogoAssets.criaturas[e.tipo] || [];
          const nombreCriatura = elegirVariante(variantesCriatura, e.id, 0, 199);
          const imgCriatura = nombreCriatura ? imagenesCache['criaturas/' + nombreCriatura] : null;

          let radioEfectivo;
          if (imgCriatura) {
            const alturaImg = nivel === 'micro' ? 34 : 22;
            const anchoImg = alturaImg * (imgCriatura.naturalWidth / imgCriatura.naturalHeight || 1);
            ctx.drawImage(imgCriatura, centro.x - anchoImg / 2, centro.y - alturaImg / 2, anchoImg, alturaImg);
            if (seleccionada) {
              ctx.beginPath();
              ctx.ellipse(centro.x, centro.y + alturaImg / 2 - 2, anchoImg * 0.42, 4, 0, 0, Math.PI * 2);
              ctx.strokeStyle = 'rgba(212,172,13,0.95)';
              ctx.lineWidth = 1.6;
              ctx.stroke();
            }
            radioEfectivo = alturaImg / 2;
          } else {
            const radioHalo = nivel === 'micro' ? 14 : 9;
            ctx.beginPath();
            ctx.arc(centro.x, centro.y, radioHalo, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(230,216,184,0.88)';
            ctx.fill();
            ctx.strokeStyle = seleccionada ? 'rgba(212,172,13,0.95)' : `rgba(${r},${g},${b},0.7)`;
            ctx.lineWidth = seleccionada ? 2.2 : 1.2;
            ctx.stroke();

            ctx.font = `${nivel === 'micro' ? 20 : 14}px 'Cinzel', Georgia, serif`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle = `rgba(${r},${g},${b},0.95)`;
            ctx.fillText(runa, centro.x, centro.y + 1);
            radioEfectivo = radioHalo;
          }

          if (nivel === 'micro') {
            ctx.font = '10px Georgia, serif';
            ctx.fillStyle = 'rgba(36,26,15,0.9)';
            const etiqueta = e.nombre || (e.tipo === 'necromasa' ? `Restos (${e.origen || '?'})` : e.tipo);
            ctx.textAlign = 'center';
            ctx.fillText(etiqueta, centro.x, centro.y + radioEfectivo + 9);

            if (e.pool_fisico) {
              const anchoBarra = 26, altoBarra = 3;
              const bx = centro.x - anchoBarra / 2, by = centro.y + radioEfectivo + 15;
              ctx.fillStyle = 'rgba(58,43,26,0.4)';
              ctx.fillRect(bx, by, anchoBarra, altoBarra);
              const vitalidad = Math.max(0, Math.min(1, e.pool_fisico.vitalidad));
              ctx.fillStyle = vitalidad > 0.35 ? 'rgba(58,110,58,0.85)' : 'rgba(150,40,32,0.85)';
              ctx.fillRect(bx, by, anchoBarra * vitalidad, altoBarra);
            }
          }
        });

        actualizarFicha(data);

        const divCronica = document.getElementById('cronica');
        const lineasFiltradas = filtroCronica
          ? data.cronica.filter((l) => l.toLowerCase().includes(filtroCronica))
          : data.cronica;
        divCronica.innerHTML = lineasFiltradas.map(l => `<div class="linea-cronica">${l}</div>`).join('');

      } catch (err) {
        console.error("Error al actualizar instantanea:", err);
      }
    }
    setInterval(actualizar, 250);
  </script>
</body>
</html>
"""


RUTA_ASSETS = Path(__file__).resolve().parent / "assets"
"""Biblioteca de imagenes externas (sellos cartograficos) que ALGUIEN
aporta -- este archivo NUNCA genera ni dibuja estas imagenes, solo las
detecta y las sirve. Ver presentacion/assets/README.md para la
convencion de nombres exacta. Mientras una categoria no tenga ningun
PNG todavia, el cliente cae de vuelta al dibujo vectorial de
dibujarVegetacion()/dibujarRelieve() -- ninguna categoria vacia rompe
el visor ni queda en blanco."""

_PATRON_ARCHIVO_CON_PREFIJO = re.compile(r"^([a-z_]+)_\d+\.png$")


def _agrupar_por_prefijo(carpeta: Path) -> dict[str, list[str]]:
    """flora/<clave>_<n>.png y agua/<clave>_<n>.png comparten la misma
    convencion -- el prefijo antes del ultimo "_N.png" agrupa variantes.
    No exige que el prefijo coincida con una clave real conocida (especie
    de flora, o 'lago'/'rio' en agua): si no coincide, simplemente nada
    lo selecciona nunca, inofensivo."""
    agrupado: dict[str, list[str]] = {}
    if carpeta.is_dir():
        for archivo in sorted(carpeta.iterdir()):
            m = _PATRON_ARCHIVO_CON_PREFIJO.match(archivo.name)
            if m and archivo.is_file():
                agrupado.setdefault(m.group(1), []).append(archivo.name)
    return agrupado


def construir_manifiesto_assets() -> dict[str, Any]:
    """Escanea RUTA_ASSETS en cada peticion (biblioteca pequeña, coste
    despreciable) y agrupa los archivos encontrados por categoria:
    flora.especie, agua.{lago,rio} y criaturas.especie por prefijo de
    nombre de archivo; relieve.montana con cualquier .png en esa carpeta
    (una unica variante de sello hoy, sin distincion de nombre)."""
    relieve_montana: list[str] = []
    carpeta_relieve = RUTA_ASSETS / "relieve"
    if carpeta_relieve.is_dir():
        relieve_montana = sorted(
            p.name for p in carpeta_relieve.iterdir() if p.is_file() and p.suffix.lower() == ".png"
        )

    return {
        "flora": _agrupar_por_prefijo(RUTA_ASSETS / "flora"),
        "relieve": {"montana": relieve_montana},
        "agua": _agrupar_por_prefijo(RUTA_ASSETS / "agua"),
        "criaturas": _agrupar_por_prefijo(RUTA_ASSETS / "criaturas"),
    }


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
        elif self.path == "/assets_manifest.json":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(construir_manifiesto_assets()).encode("utf-8"))
        elif self.path.startswith("/assets/"):
            self._servir_asset(self.path[len("/assets/") :])
        else:
            self.send_response(404)
            self.end_headers()

    def _servir_asset(self, ruta_relativa: str) -> None:
        """Sirve un archivo de RUTA_ASSETS/{flora,relieve}. Resuelve la ruta
        final y verifica que siga colgando de una de esas dos subcarpetas
        (no solo de RUTA_ASSETS en general) antes de leerla -- sin esto,
        un path.startswith("/assets/") con "../../" en la URL serviria
        cualquier archivo legible del sistema (path traversal), y sin la
        restriccion a flora/relieve especificamente, cualquier otro
        archivo suelto en RUTA_ASSETS (como el material fuente sin
        recortar) quedaria publicado por HTTP sin querer."""
        from urllib.parse import unquote

        destino = (RUTA_ASSETS / unquote(ruta_relativa)).resolve()
        carpetas_publicas = (
            RUTA_ASSETS / "flora", RUTA_ASSETS / "relieve", RUTA_ASSETS / "agua", RUTA_ASSETS / "criaturas",
        )
        if not any(destino.is_relative_to(c.resolve()) for c in carpetas_publicas):
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
    """Construye el DTO serializable para la interfaz web.

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
    plantas_por_celda: dict[tuple[int, int], dict[str, Any]] = {}
    for pid in sorted(gestor.entidades_con(Planta, Posicion)):
        planta = gestor.obtener_componente(pid, Planta)
        pos_p = gestor.obtener_componente(pid, Posicion)
        if planta and pos_p:
            plantas_por_celda[(pos_p.x, pos_p.y)] = {
                "especie": planta.especie,
                "etapa": round(planta.etapa, 3),
            }

    ticks_por_anio = Reloj.TICKS_POR_DIA * Reloj.DIAS_POR_ESTACION * Reloj.ESTACIONES_POR_ANIO

    # 1. Entidades Biologicas Vivas
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
                    "planta": plantas_por_celda.get((x, y)),
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
        "semilla": mundo.config.get("semilla_por_defecto"),
        "ancho": zona.ancho,
        "alto": zona.alto,
        "censo": censo,
        "entidades": lista_entidades,
        "celdas": celdas_data,
        "cronica": cronica,
    }
