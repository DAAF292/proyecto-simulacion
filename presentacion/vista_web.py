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
    .btn-modo {
      font-family: 'IM Fell English', Georgia, serif;
      font-size: 11.5px;
      background: linear-gradient(180deg, #efe2c0, #cbb789);
      color: var(--tinta-fuerte);
      border: 1px solid #6b4a2c;
      border-radius: 2px;
      padding: 3px 10px;
      cursor: pointer;
    }
    .btn-modo:hover { background: #efe2c0; }
    .btn-modo.activo { background: #8a6a3e; color: #efe2c0; }
    #grupo-modos { display: flex; gap: 4px; }
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
        <div id="grupo-modos">
          <button class="btn-modo activo" id="btn-modo-codice" type="button" title="Mapa de siempre: lavado de biomas, sellos y criaturas">Codice</button>
          <button class="btn-modo" id="btn-modo-relieve" type="button" title="Hipsometrico: alturas por tono sepia">Relieve</button>
          <button class="btn-modo" id="btn-modo-hidro" type="button" title="Hidrografia: tierra en pergamino, agua por profundidad">Hidro</button>
        </div>
        <button id="btn-centrar" type="button">Centrar mapa</button>
        <button id="btn-rotar" type="button" title="Rotar camara 90 grados (tecla R)">Rotar</button>
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

    // Circulo 2 generalizado (feedback de Diego: "que sea generalizado
    // para anadir nuevos biomas sin romper lo anterior"): cada bioma con
    // sellos de FORMACION a zoom macro declara aqui su pool. Anadir un
    // bioma nuevo = anadir sus assets + UNA entrada en esta tabla; la
    // funcion de estampado no cambia. Biomas sin entrada (pradera) se
    // quedan con sus sellos por celda (matas de hierba, etc.).
    // 'suprime' indica que categoria de sellos por celda sustituye la
    // formacion (montana -> relieve: los picos dentro de la cordillera
    // duplicarian; bosque -> flora: los arboles dentro de la masa
    // duplicarian; desierto/tundra suprimen NADA -- sus saguaros y pinos
    // son individuos que pisan sobre la region, como pide el objetivo).
    // (2026-08-29) Valores de respaldo puramente defensivos -- el DTO
    // real siempre trae bioma_umbrales (una sola fuente de verdad con
    // config/constantes.yaml), asi que esto solo se usa si el fetch aun
    // no ha llegado o en el arnes mock-DOM. Actualizados junto con la
    // recalibracion de config/constantes.yaml para no quedar
    // desactualizados frente al valor real.
    const UMBRALES_LAVADO_DEFECTO = {
      umbral_elevacion_montana: 0.6665,
      umbral_temperatura_tundra: 0.1346,
      umbral_lluvia_desierto: 0.3909,
      umbral_lluvia_bosque: 0.6041,
    };
    let umbralesLavado = null;   // se actualiza con el DTO cuando llega

    const PALETA_LAVADO = {
      pradera: [122, 138, 74],
      montana: [110, 104, 96],
      tundra: [188, 184, 170],
      desierto: [176, 150, 84],
      bosque: [46, 74, 42],
    };
    const BANDA_LAVADO = 0.2;    // anchura de la transicion alrededor de cada umbral


    function _mezclar(a, b, t) {
      return [
        Math.round(a[0] + (b[0] - a[0]) * t),
        Math.round(a[1] + (b[1] - a[1]) * t),
        Math.round(a[2] + (b[2] - a[2]) * t),
      ];
    }

    function _rampa(valor, umbral, banda) {
      // 0 antes del umbral-banda/2, 1 despues del umbral+banda/2, suave
      // dentro (smoothstep, mismo criterio que nucleo/campo_continuo.py).
      const t = Math.max(0, Math.min(1, (valor - (umbral - banda / 2)) / banda));
      return t * t * (3 - 2 * t);
    }

    const     FORMACIONES_POR_BIOMA = {
      // (2026-08-28) La entrada montana estuvo FUERA de la tabla parte del
      // dia: cfg=undefined -> la formacion no estampaba NADA ni marcaba
      // la supresion, y el por-celda estampaba las panoramicas celda a
      // celda (diagnostico del arnes: SONDA 'reading raiz'). Diego pide
      // explicitamente una formacion de imagen como la de bosques.
      montana:  { raiz: 'relieve', pool: 'cordillera', carpeta: 'relieve/', margen: 1.25, sal: 71, suprime: 'relieve' },
      bosque:   { raiz: 'flora', pool: 'masa_bosque', carpeta: 'flora/', margen: 1.2, sal: 73, suprime: 'flora' },
      desierto: { raiz: 'relieve', pool: 'masa_desierto', carpeta: 'relieve/', margen: 1.3, sal: 75, suprime: null },
      tundra:   { raiz: 'relieve', pool: 'masa_tundra', carpeta: 'relieve/', margen: 1.3, sal: 77, suprime: null },
    };
    const COLOR_AGUA = [58, 92, 122];
    const COLOR_CHARCO = [90, 130, 160];
    const COLOR_FUEGO = [168, 58, 38];
    // Runas Futhark por especie (informe seccion 5 -- catalogo de identidad):
    // Gebo/gnomo, Laguz/lobo, Kaunan/conejo, Ansuz/ardilla. Necromasa no es
    // una criatura consciente ni figura en ese catalogo -- se queda con un
    // glifo neutro en vez de inventarle una runa que el informe no le da.
    const RUNAS = { 'gnomo': 'áš·', 'lobo': 'á›š', 'conejo': 'áš²', 'ardilla': 'áš¨', 'necromasa': 'ðŸ¦´' };
    const COLOR_INK_ESPECIE = {
      'gnomo':   [44, 92, 138],
      'lobo':    [138, 44, 44],
      'conejo':  [138, 106, 28],
      'ardilla': [44, 122, 58],
      'necromasa': [90, 81, 72],
    };

    // (2026-08-27, correccion tras feedback de Diego: "el gnomo es mas
    // pequeño que el lobo en codigo, la representacion debe responder a
    // las medidas fisicas que tienen en el motor, no a una regla que tu
    // definas"). Version anterior (ESCALA_ESPECIE, retirada en ambas
    // sesiones que la escribieron -- esta rama la tenia igual que
    // master, misma tentacion de inventar una constante por especie): al
    // reves de lo que dice el propio motor, gnomo pesa [8,15], lobo
    // [60,90] (rangos_raciales) -- DimensionesFisicas.peso es
    // literalmente el sustituto declarado de la vieja "Categoria.
    // tamano" (ver docstring de componentes/dimensiones_fisicas.py), asi
    // que es el dato real a usar para el tamano visual, no una eleccion
    // mia.
    //
    // e.dimensiones.peso ya viene en el JSON (construir_instantanea, sin
    // cambios necesarios ahi) por INDIVIDUO, no por especie -- dos lobos
    // de la misma camada no tienen por que pesar igual (rango racial +
    // sorteo individual, el patron ya establecido en el proyecto). La
    // escala usa raiz cubica del peso (si el peso fuese proporcional a
    // un volumen, el tamano lineal escala con su raiz cubica -- una
    // relacion fisica real, no una curva elegida a ojo) normalizada
    // contra PESO_MAX_REFERENCIA, el maximo real de cualquier rango
    // racial hoy (lobo, 90 -- rangos_raciales.lobo.peso en
    // config/constantes.yaml). Si alguna vez se añade una especie con
    // peso mayor, esta constante quedaria desactualizada -- documentado
    // aqui a proposito para que sea facil de encontrar y corregir.
    //
    // necromasa es la unica excepcion real: son restos inertes, nunca
    // tuvieron DimensionesFisicas propio en el ECS (no son una criatura
    // viva), asi que no hay peso que leer -- ESCALA_NECROMASA conserva
    // el valor que master ya habia calibrado a ojo contra el visor real
    // ("un craneo a la altura de un gnomo seria un monstruo"), la unica
    // entrada de esta tabla que sigue siendo una eleccion visual en vez
    // de un dato del motor, porque el motor no modela un tamano para
    // restos que ya no son un organismo.
    const PESO_MAX_REFERENCIA = 90;
    const ESCALA_NECROMASA = 0.45;
    function escalaPorPeso(entidad) {
      if (entidad.tipo === 'necromasa') return ESCALA_NECROMASA;
      if (!entidad.dimensiones) return 1;
      return Math.cbrt(entidad.dimensiones.peso) / Math.cbrt(PESO_MAX_REFERENCIA);
    }

    // (2026-08-28) Factor de DENSIDAD por pose: no todas las poses de una
    // especie comparten proporciones -- el galope es largo y bajo, el
    // cadaver estirado, la posicion de pie alta y estrecha -- y forzar el
    // lado mayor de cualquiera al mismo valor aplanaba las anchas a
    // astillas (captura y medicion de Diego). La hoja fuente de cada
    // especie (nuevosAssetsDefinitivos/criaturas) dibuja TODAS sus poses a
    // la misma escala: el ancla es la altura de contenido de idle_e y el
    // factor de cada pose es lado_mayor_de_contenido / ancla, medido con
    // PIL recorte a recorte (idle_e no entra: su factor es 1 por
    // definicion). PROVISIONAL: valores de medicion automatica, pendientes
    // de validacion visual de Diego en el visor real -- una pose concreta
    // que se lea mal se recalibra aqui a mano, sin tocar el mecanismo.
    // RECALIBRADO (2026-09-03, feedback real de Diego sobre el visor en
    // marcha -- "un lobo que duerme no puede ser mas grande que ese
    // mismo lobo andando"). La tabla anterior usaba lado_mayor/
    // lado_mayor_de_idle_e: sensible a la orientacion del recorte, una
    // pose tumbada (dormir, muerto) es una tira horizontal larga y
    // estrecha, asi que su "lado mayor" salia desproporcionado aunque el
    // bulto visual real no lo fuera -- y ademas los sprites de lobo se
    // habian reemplazado desde el ultimo calculo sin recalibrar (gnomo
    // seguia coincidiendo con sus ficheros reales, lobo no). Recalculada
    // con raiz cuadrada del AREA de contenido real (bbox sin
    // transparencia, medido con PIL contra los ficheros actuales de
    // presentacion/assets/criaturas_poses/), una metrica que no depende
    // de la orientacion del recorte. andar_n/andar_s siguen siendo mas
    // pequenos que andar_e a proposito -- silueta de perfil frontal/
    // trasero, mas estrecha que de costado, diferencia anatomica real,
    // no un error de calibracion.
    const ESCALA_POSE = {
      'gnomo':   { 'andar_e': 1.169, 'andar_n': 1.167, 'andar_s': 1.177,
                   'durmiendo': 1.597, 'forrajeando': 1.696, 'herido': 1.818,
                   'idle_n': 1.135, 'idle_s': 1.185, 'muerto': 1.488 },
      'lobo':    { 'andar_e': 0.973, 'andar_n': 0.553, 'andar_s': 0.575,
                   'durmiendo': 0.831, 'forrajeando': 0.970, 'herido': 1.019,
                   'idle_n': 0.582, 'idle_s': 0.577, 'muerto': 0.919 },
      'conejo':  { 'andar_e': 1.117, 'durmiendo': 0.934, 'forrajeando': 1.016,
                   'herido': 1.107, 'idle_n': 0.742, 'muerto': 1.154 },
      'ardilla': { 'andar_e': 1.081, 'durmiendo': 0.805, 'forrajeando': 0.896,
                   'herido': 0.931, 'idle_n': 0.653, 'idle_s': 0.686,
                   'muerto': 0.899 },
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
      flora: {}, flora_color: {},
      relieve: { montana: [], cordillera: [], montana_color: [] },
      agua: { lago: [], lago_color: [], rio: [], piezas_rio: {} },
      criaturas: {},
      // (2026-08-28) Kit de poses: como el resto, llega por manifest, pero
      // imagenPose() lo lee en cada frame -- sin semilla aqui, un manifest
      // que tarde (o el arnes mock-DOM, donde el fetch siempre falla) deja
      // catalogoAssets.criaturas_poses undefined y el visor casca.
      criaturas_poses: {},
    };
    const imagenesCache = {};

    // Pivote LOD tinta/color (2026-08-27): a partir de este zoom el
    // terreno (flora/relieve/lagos) pasa de la biblioteca en tinta a su
    // gemela a color -- lejos parece un mapa, cerca "se dibuja un mundo
    // real" (peticion explicita de Diego). Umbral propio, no reutiliza los
    // 0.8/2.0 de LOD de entidades (gobiernan si una criatura muestra
    // retrato o punto, un eje distinto). Si la carpeta _color de una
    // categoria esta vacia, esa categoria sigue en tinta a cualquier zoom
    // -- ver elegirCatalogoTerreno().
    const     // (2026-08-28) 1.6 -> 1.0: el rango medio en tinta (0.8-1.6) leia las
    // cordilleras de plumilla como BLOQUES NEGROS sobre el lavado (capturas
    // de Diego: "pasa de macro a micro pero aun no se ha renderizado lo de
    // las montanas"). El color entra nada mas salir de macro; el pergamino
    // de plumilla queda solo para el mapa completo de un vistazo.
    ZOOM_ESTILO_COLOR = 1.0;

    // Alzado por elevacion (circulo 2026-09-03, spec en
    // docs/superpowers/specs/2026-09-03-motor-visual-elevacion-design.md):
    // terreno, sellos de relieve/flora y criaturas se dibujan mas arriba
    // en pantalla cuanto mayor es la elevacion REAL de su celda -- solo
    // en niveles medio/micro, macro se queda cenital puro. La camara
    // sigue aplicando pan/zoom con una unica transformacion global
    // (ctx.translate/scale en dibujarFrame): todo lo dibujado en espacio
    // de mundo (unidades de tam) hereda pan/zoom gratis, asi que basta
    // con restar este desplazamiento antes de multiplicar por tam.
    // PROVISIONAL: 0.6 elegido contra el rango real de elevacion medido
    // en 5 semillas (min~0.05, max~0.91, gradiente maximo entre celdas
    // vecinas ~0.17) -- un valor mayor produciria paredes verticales
    // dificiles de leer entre celdas contiguas.
    const ESCALA_VERTICAL_ELEVACION = 0.6;
    function alzadoY(elevacion, tam) {
      return (elevacion || 0) * tam * ESCALA_VERTICAL_ELEVACION;
    }

    // Mismo umbral que ya fijaba dibujarFrame inline -- extraido aqui
    // para que entidadEnPunto() (hit-test de click) pueda consultar el
    // nivel actual sin duplicar la formula.
    function nivelActual() {
      return camara.zoom < 0.8 ? 'macro' : (camara.zoom < 2.0 ? 'medio' : 'micro');
    }

    // Remapeo discreto de coordenadas para la rotacion de camara (circulo
    // 2026-09-03, spec en
    // docs/superpowers/specs/2026-09-03-caballera-rotacion-design.md):
    // NO es una rotacion continua -- es un intercambio/reflejo de ejes en
    // incrementos de 90 grados, aplicado ANTES de la proyeccion Caballera.
    // n es el lado del grid (el mundo es siempre cuadrado, ancho===alto,
    // verificado contra generar_zona_bioma -- un unico parametro, no dos).
    function rotarCoordenadas(wx, wy, n, rotacion) {
      switch (rotacion) {
        case 90:  return { px: wy, py: n - 1 - wx };
        case 180: return { px: n - 1 - wx, py: n - 1 - wy };
        case 270: return { px: n - 1 - wy, py: wx };
        default:  return { px: wx, py: wy };
      }
    }

    // Inversa de rotarCoordenadas -- la inversa de 90 es 270, la de 180 es
    // 180, la de 0 es 0 (propiedad del grupo de rotaciones discretas,
    // verificada por composicion antes de escribir esto). Usada por la
    // cara de risco para encontrar, dada una posicion de PANTALLA, que
    // celda del MUNDO es de verdad (para leer su elevacion real).
    function invertirRotacion(px, py, n, rotacion) {
      const inversa = { 0: 0, 90: 270, 180: 180, 270: 90 }[rotacion];
      const { px: wx, py: wy } = rotarCoordenadas(px, py, n, inversa);
      return { wx, wy };
    }

    // Proyeccion Caballera completa (circulo 2026-09-03): remapea las
    // coordenadas del mundo segun la rotacion de camara, y proyecta con
    // desplazamiento en X por profundidad + desplazamiento en Y por
    // elevacion real (alzadoY, ya construido, se reutiliza tal cual como
    // el termino vertical). PROVISIONAL: 45 grados / 0.5 son los valores
    // "estandar" citados en la propuesta original de Diego -- a validar
    // visualmente contra el visor real, no medidos contra el motor.
    const ALPHA_CABALLERA = 45 * Math.PI / 180;
    const K_CABALLERA = 0.5;
    function celdaAPantallaCompleta(wx, wy, elevacion, tam, n, rotacion) {
      const { px, py } = rotarCoordenadas(wx, wy, n, rotacion);
      const cx = (px + py * Math.cos(ALPHA_CABALLERA) * K_CABALLERA) * tam;
      const cy = (py * Math.sin(ALPHA_CABALLERA) * K_CABALLERA) * tam - alzadoY(elevacion, tam);
      return { cx, cy };
    }

    // Hachurado de relieve (circulo 2026-09-03, spec en
    // docs/superpowers/specs/2026-09-03-hachura-relieve-design.md):
    // constantes puramente de presentacion (mismo precedente que
    // ALPHA_CABALLERA/K_CABALLERA) -- estetica de renderizado, sin
    // ningun efecto sobre la simulacion, por eso viven aqui y no en
    // config/*.yaml. Todas PROVISIONAL, a calibrar contra un render
    // real, no contra el harness completo.
    const UMBRAL_PENDIENTE_VISIBLE = 0.02;
    const PENDIENTE_SATURACION = 0.12;
    const TRAZOS_MIN = 2;
    const TRAZOS_MAX = 6;
    const AZIMUT_LUZ_RELIEVE = 315 * Math.PI / 180;

    // Pendiente real por diferencias centrales de Celda.elevacion contra
    // los vecinos N/S/E/O en coordenadas de mundo. En el borde del grid
    // (sin vecino en un lado de un eje) se usa diferencia simple hacia
    // el unico vecino disponible -- sin vecino en NINGUN lado (grid de
    // longitud 1 en ese eje) da pendiente 0 en ese eje, caso degenerado
    // que no ocurre en la practica (el mundo es siempre 40x40) pero no
    // debe reventar si se prueba aislado.
    function calcularPendiente(data, x, y) {
      const n = data.ancho;
      const alto = data.alto;
      const elevEn = (xx, yy) => data.celdas[yy][xx].elevacion || 0;
      let dzdx;
      if (x > 0 && x < n - 1) dzdx = (elevEn(x + 1, y) - elevEn(x - 1, y)) / 2;
      else if (x < n - 1) dzdx = elevEn(x + 1, y) - elevEn(x, y);
      else if (x > 0) dzdx = elevEn(x, y) - elevEn(x - 1, y);
      else dzdx = 0;
      let dzdy;
      if (y > 0 && y < alto - 1) dzdy = (elevEn(x, y + 1) - elevEn(x, y - 1)) / 2;
      else if (y < alto - 1) dzdy = elevEn(x, y + 1) - elevEn(x, y);
      else if (y > 0) dzdy = elevEn(x, y) - elevEn(x, y - 1);
      else dzdy = 0;
      const magnitud = Math.sqrt(dzdx * dzdx + dzdy * dzdy);
      return { dzdx, dzdy, magnitud };
    }

    // Deriva la direccion de trazo EN PANTALLA proyectando el centro de
    // la celda y el centro desplazado un paso pequeno en la direccion
    // "cuesta abajo" de MUNDO, con la misma celdaAPantallaCompleta que
    // usa todo el resto del visor -- correcta bajo cualquier rotacion
    // de camara sin ninguna tabla de casos nueva (mismo principio que
    // ya aplica bordeDeCelda). El tamano del paso no importa: al
    // normalizar el resultado, cualquier paso pequeno da la misma
    // direccion (la proyeccion es afin en wx,wy a elevacion fija).
    function direccionTrazoPantalla(wx, wy, elevacion, tam, n, rotacion, dzdx, dzdy) {
      const mag = Math.sqrt(dzdx * dzdx + dzdy * dzdy);
      if (mag < 1e-9) return { dx: 1, dy: 0 };
      const wdx = -dzdx / mag;
      const wdy = -dzdy / mag;
      const PASO_MUNDO = 0.05;
      const centro = celdaAPantallaCompleta(wx + 0.5, wy + 0.5, elevacion, tam, n, rotacion);
      const paso = celdaAPantallaCompleta(
        wx + 0.5 + wdx * PASO_MUNDO, wy + 0.5 + wdy * PASO_MUNDO, elevacion, tam, n, rotacion,
      );
      const dx = paso.cx - centro.cx;
      const dy = paso.cy - centro.cy;
      const magPantalla = Math.sqrt(dx * dx + dy * dy);
      if (magPantalla < 1e-9) return { dx: 1, dy: 0 };
      return { dx: dx / magPantalla, dy: dy / magPantalla };
    }

    // Modula la intensidad de tinta del hachurado por orientacion de la
    // ladera respecto a una luz fija en el MUNDO (315/NW, decision ya
    // tomada por Diego para el circulo anterior de este mismo arco).
    // Producto escalar 2D del vector unitario cuesta-abajo con la
    // direccion de la luz -- sin componente de altitud, no hace falta
    // un vector 3D completo para esto. Ladera que mira hacia la luz
    // (producto escalar alto) -> trazo mas tenue (ALFA_LUZ_MIN); ladera
    // que da la espalda (producto escalar bajo) -> trazo mas marcado
    // (ALFA_LUZ_MAX). Acotado, nunca apaga ni satura del todo un trazo
    // por la luz sola -- la densidad sigue siendo la senal principal de
    // "cuanta pendiente hay".
    const ALFA_LUZ_MIN = 0.6;
    const ALFA_LUZ_MAX = 1.3;
    function alfaPorLuz(dzdx, dzdy) {
      const mag = Math.sqrt(dzdx * dzdx + dzdy * dzdy);
      if (mag < 1e-9) return 1.0;
      const wdx = -dzdx / mag;
      const wdy = -dzdy / mag;
      const lx = Math.cos(AZIMUT_LUZ_RELIEVE);
      const ly = Math.sin(AZIMUT_LUZ_RELIEVE);
      const dot = wdx * lx + wdy * ly; // [-1, 1]
      const t = (dot + 1) / 2; // [0, 1], 1 = mirando a la luz
      return ALFA_LUZ_MAX - t * (ALFA_LUZ_MAX - ALFA_LUZ_MIN);
    }

    async function cargarBibliotecaAssets() {
      try {
        const resp = await fetch('/assets_manifest.json');
        if (!resp.ok) return;
        catalogoAssets = await resp.json();
        if (!catalogoAssets.flora_color) catalogoAssets.flora_color = {};
        if (!catalogoAssets.relieve) catalogoAssets.relieve = { montana: [], montana_color: [] };
        if (!catalogoAssets.relieve.montana_color) catalogoAssets.relieve.montana_color = [];
        if (!catalogoAssets.agua) catalogoAssets.agua = { lago: [], lago_color: [], rio: [], piezas_rio: {} };
        if (!catalogoAssets.agua.lago_color) catalogoAssets.agua.lago_color = [];
        if (!catalogoAssets.agua.piezas_rio) catalogoAssets.agua.piezas_rio = {};
        if (!catalogoAssets.criaturas) catalogoAssets.criaturas = {};
        if (!catalogoAssets.criaturas_poses) catalogoAssets.criaturas_poses = {};
      } catch (err) {
        console.error('No se pudo leer /assets_manifest.json:', err);
        return;
      }
      const rutas = [];
      for (const especie in catalogoAssets.flora) {
        for (const nombre of catalogoAssets.flora[especie]) rutas.push(['flora/' + nombre, 'flora/' + nombre]);
      }
      for (const especie in catalogoAssets.flora_color) {
        for (const nombre of catalogoAssets.flora_color[especie]) rutas.push(['flora_color/' + nombre, 'flora_color/' + nombre]);
      }
      // (2026-08-29, fix de auditoria) Generico por prefijo, igual que
      // flora arriba: antes solo 'montana' y 'cordillera' se cargaban
      // (hardcodeados), asi que masa_desierto/masa_tundra -- declaradas
      // en FORMACIONES_POR_BIOMA y ya agrupadas por
      // construir_manifiesto_assets() via _agrupar_por_prefijo -- nunca
      // llegaban a precargarse: dibujarFormacionesMacro() encontraba
      // pool=[] para esos dos biomas y caia en silencio al estampado
      // por-celda de siempre. 'montana_color' es la unica clave especial
      // (viene de relieve_color/, no de relieve/) y se excluye aqui.
      for (const clave in catalogoAssets.relieve) {
        if (clave === 'montana_color') continue;
        for (const nombre of catalogoAssets.relieve[clave] || []) rutas.push(['relieve/' + nombre, 'relieve/' + nombre]);
      }
      for (const nombre of catalogoAssets.relieve.montana_color) rutas.push(['relieve_color/' + nombre, 'relieve_color/' + nombre]);
      for (const clave in catalogoAssets.agua) {
        if (clave === 'piezas_rio') continue;
        for (const nombre of catalogoAssets.agua[clave]) rutas.push(['agua/' + nombre, 'agua/' + nombre]);
      }
      for (const pieza in catalogoAssets.agua.piezas_rio) {
        const nombre = catalogoAssets.agua.piezas_rio[pieza];
        rutas.push(['agua/rio_piezas/' + nombre, 'agua/piezas_rio/' + pieza]);
      }
      for (const especie in catalogoAssets.criaturas) {
        for (const nombre of catalogoAssets.criaturas[especie]) rutas.push(['criaturas/' + nombre, 'criaturas/' + nombre]);
      }
      for (const especie in catalogoAssets.criaturas_poses) {
        for (const pose in catalogoAssets.criaturas_poses[especie]) {
          const nombre = catalogoAssets.criaturas_poses[especie][pose];
          rutas.push(['criaturas_poses/' + nombre, 'criaturas_poses/' + nombre]);
        }
      }

      await Promise.all(rutas.map(([ruta, clave]) => new Promise((resolve) => {
        const img = new Image();
        img.onload = () => { imagenesCache[clave] = img; resolve(); };
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

    function estiloColorActivo() {
      return camara.zoom >= ZOOM_ESTILO_COLOR;
    }

    // Elige entre la carpeta _color y su gemela en tinta segun el zoom
    // actual, cayendo siempre a tinta si la carpeta color esta vacia para
    // esa clave concreta (biblioteca parcial, no rompe nada -- mismo
    // criterio de "categoria vacia = vectorial/tinta" que ya regia antes
    // de este pivote, solo que ahora con un escalon intermedio).
    function poolTerreno(poolColor, prefijoColor, poolTinta, prefijoTinta) {
      if (estiloColorActivo() && poolColor && poolColor.length > 0) {
        return { lista: poolColor, prefijo: prefijoColor };
      }
      return { lista: poolTinta, prefijo: prefijoTinta };
    }

    // Pieza 2 (2026-08-27): construccion del elemento de cola Y-sorted de
    // una criatura en ESPACIO DE MUNDO (escala con el zoom y se oculta tras
    // los sellos de las celdas al sur, como un diorama). 2026-08-28: la
    // pose se resuelve por ESTADO DEL ECS (poses de criaturas_poses/,
    // kit por especie): herida (vitalidad), durmiendo/forrajeando (accion),
    // andar/idle por direccion de marcha (ultima direccion persiste en el
    // animador), y muerto para necromasa segun su especie de origen. El
    // anclaje es el PIE de SU celda -- misma convencion que los picos de
    // montana -- con un sesgo minimo que solo sirve para ganar empates
    // contra el sello de la propia celda; contra cualquier sello mas al
    // sur sigue perdiendo y queda oculto. Sin pose disponible, cae al
    // sprite generico de criaturas/ (variante por hash del id) y, sin
    // ningun asset, al halo+runa en la cola con el mismo anclaje.
    const ALTURA_CRIATURA_POR_CELDA = 0.55;
    // Calibracion provisional: lado mayor de una criatura de referencia
    // (escalaPorPeso 1, el lobo mas pesado de rangos_raciales) como
    // fraccion del alto de una celda. Eleccion de legibilidad a ojo
    // contra el visor real, no una medida del motor -- pero el factor
    // POR ESPECIE que multiplica a esta base si es dato real, ver
    // escalaPorPeso().
    // (2026-08-28) El lado ya no manda solo: se multiplica por el factor
    // de densidad de la pose resuelta (ESCALA_POSE) -- antes las poses
    // anchas (tumbadas, galope) colapsaban a astillas al forzar su lado
    // mayor al mismo valor que el de una pose de pie. Una pose tumbada
    // puede desbordar la celda en su eje largo: es la proporcion anatomi-
    // ca de la hoja fuente, no un desajuste.
    const EN_MARCHA_EPSILON = 0.02;
    // celdas de distancia entre posicion suavizada y objetivo ECS a partir
    // de las cuales la criatura cuenta como "en marcha" (pose de andar).
    const UMBRAL_HERIDO_POSE = 0.35;
    // Mismo umbral que pinta la barra de vitalidad en rojo: debajo, la
    // criatura muestra su pose herida. Calibracion provisional.
    const ACCIONES_FORRAJEANDO = new Set(['comer', 'cazar', 'beber']);
    // comer/cazar/beber comparten la pose de forrajeo (los sheets no traen
    // pose de bebida): aproximacion documentada, no un hallazgo perfecto.

    // Resuelve el fichero de pose con cadena de fallback: pose pedida ->
    // pose lateral E (especies sin piezas frontales/traseradas) -> null
    // (el llamador cae al sprite generico). El este (E) es la direccion
    // nativa de TODOS los recortes: oeste se resuelve espejando en el
    // canvas, nunca con piezas nativas izquierdas (evita dobles espejos).
    function imagenPose(especie, pose) {
      const kit = (catalogoAssets.criaturas_poses || {})[especie] || {};
      const intentos = {
        'forrajeando': ['forrajeando', 'idle_e'],
        'durmiendo': ['durmiendo', 'idle_e'],
        'herido': ['herido', 'idle_e'],
        'muerto': ['muerto'],
        'idle_s': ['idle_s', 'idle_e'],
        'idle_n': ['idle_n', 'idle_e'],
        'idle_e': ['idle_e'],
        'idle_o': ['idle_e'],
        'andar_s': ['andar_s', 'andar_e', 'idle_e'],
        'andar_n': ['andar_n', 'andar_e', 'idle_e'],
        'andar_e': ['andar_e'],
        'andar_o': ['andar_e'],
      }[pose] || [pose];
      for (const p of intentos) {
        const nombre = kit[p];
        if (nombre && imagenesCache['criaturas_poses/' + nombre]) {
          // Devuelve TAMBIEN la pose resuelta: el factor de escala
          // (ESCALA_POSE) es el de la pose cuyo fichero se dibuja, no el
          // de la pedida -- un fallback a idle_e debe medir como idle_e.
          return { img: imagenesCache['criaturas_poses/' + nombre], pose: p };
        }
      }
      return null;
    }

    // Estado del ECS -> nombre de pose. Las poses de suelo (forrajeando,
    // durmiendo, herido, muerto) llevan dir null: no se orientan por la
    // marcha, no se espejan nunca. Prioridad: muerto > herido > dormir >
    // forrajeo > marcha > idle.
    function resolverPose(e) {
      if (e.tipo === 'necromasa') return { pose: 'muerto', dir: null };
      const vitalidad = e.pool_fisico ? e.pool_fisico.vitalidad : 1;
      if (vitalidad < UMBRAL_HERIDO_POSE) return { pose: 'herido', dir: null };
      if (e.accion === 'dormir') return { pose: 'durmiendo', dir: null };
      if (ACCIONES_FORRAJEANDO.has(e.accion)) return { pose: 'forrajeando', dir: null };
      const dx = e.tx - e.x, dy = e.ty - e.y;
      const enMarcha = Math.abs(dx) + Math.abs(dy) > EN_MARCHA_EPSILON;
      // huir/huida_erratica/buscar_pareja/crisis_violenta caen aqui:
      // andan si se mueven, idle si no (aproximacion documentada);
      // catatonia/aliviarse quedan en idle con la ultima direccion.
      const dir = enMarcha
        ? (Math.abs(dx) >= Math.abs(dy) ? (dx > 0 ? 'e' : 'o') : (dy > 0 ? 's' : 'n'))
        : (e.ultimaDir || 's');
      return { pose: (enMarcha ? 'andar_' : 'idle_') + dir, dir };
    }

    function construirElementoCriatura(e, tam, elevacion = 0, n = 40, rotacion = 0) {
      const resuelta = resolverPose(e);
      let imgCriatura = null;
      let poseResuelta = null;
      if (e.tipo === 'necromasa') {
        const hallada = e.origen ? imagenPose(e.origen, 'muerto') : null;
        if (hallada) { imgCriatura = hallada.img; poseResuelta = hallada.pose; }
      } else {
        const hallada = imagenPose(e.tipo, resuelta.pose);
        if (hallada) { imgCriatura = hallada.img; poseResuelta = hallada.pose; }
      }
      if (!imgCriatura) {
        const variantesCriatura = catalogoAssets.criaturas[e.tipo] || [];
        const nombreCriatura = elegirVariante(variantesCriatura, e.id, 0, 199);
        imgCriatura = nombreCriatura ? imagenesCache['criaturas/' + nombreCriatura] : null;
      }
      // (2026-09-03, CORRECCION de la correccion anterior -- ver el
      // comentario de celdaComoQuad mas arriba) el "borde inferior de la
      // celda" no es "proyectar (e.x,e.y) y sumar tam plano" -- eso
      // asumia que una celda mide tam de alto en pantalla, y NO es asi
      // bajo Caballera (una fila del mundo solo desplaza sin(ALPHA)*K*tam,
      // no tam). El punto correcto es proyectar DIRECTAMENTE la posicion
      // fraccional real del mundo (e.x+0.5, e.y+1 -- centro en X, borde
      // sur en Y) a traves de la formula completa, exactamente como ya
      // hace el terreno con sus 4 esquinas reales. La correccion de hoy
      // (evitar pasar offsets DENTRO de celdaAPantallaCompleta) seguia
      // siendo el diagnostico correcto -- lo que estaba mal era el
      // remedio (sumar pixeles planos en vez de proyectar la posicion
      // real), no la deteccion del sintoma.
      const { cx, cy: baseY } = celdaAPantallaCompleta(e.x + 0.5, e.y + 1, elevacion, tam, n, rotacion);
      const { cy: baseYSuelo } = celdaAPantallaCompleta(e.x + 0.5, e.y + 1, 0, tam, n, rotacion);
      const ordenY = baseY + tam * 0.01;
      const [r, g, b] = COLOR_INK_ESPECIE[e.tipo] || [70, 60, 50];
      const runa = RUNAS[e.tipo] || '?';

      function dibujarSombra(radio) {
        ctx.beginPath();
        ctx.ellipse(cx, baseYSuelo, radio, radio * 0.35, 0, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(40,30,18,0.28)';
        ctx.fill();
      }

      if (imgCriatura) {
        const especiePose = e.tipo === 'necromasa' ? e.origen : e.tipo;
        const factorPose = (poseResuelta && ESCALA_POSE[especiePose] && ESCALA_POSE[especiePose][poseResuelta]) || 1;
        const lado = tam * ALTURA_CRIATURA_POR_CELDA * escalaPorPeso(e) * factorPose;
        const aspecto = imgCriatura.naturalWidth / imgCriatura.naturalHeight || 1;
        const alturaImg = aspecto >= 1 ? lado / aspecto : lado;
        const anchoImg = aspecto >= 1 ? lado : lado * aspecto;
        const espejar = resuelta.dir === 'o';
        return {
          ordenY,
          alturaVisual: alturaImg / 2,
          dibujar: () => {
            dibujarSombra(anchoImg * 0.35);
            if (espejar) {
              ctx.save();
              ctx.translate(cx, 0);
              ctx.scale(-1, 1);
              ctx.drawImage(imgCriatura, -anchoImg / 2, baseY - alturaImg, anchoImg, alturaImg);
              ctx.restore();
            } else {
              ctx.drawImage(imgCriatura, cx - anchoImg / 2, baseY - alturaImg, anchoImg, alturaImg);
            }
          },
        };
      }

      const radioHalo = tam * 0.3;
      return {
        ordenY,
        alturaVisual: radioHalo,
        dibujar: () => {
          dibujarSombra(radioHalo * 0.8);
          ctx.beginPath();
          ctx.arc(cx, baseY - radioHalo, radioHalo, 0, Math.PI * 2);
          ctx.fillStyle = 'rgba(230,216,184,0.88)';
          ctx.fill();
          ctx.strokeStyle = `rgba(${r},${g},${b},0.7)`;
          ctx.lineWidth = 1.2;
          ctx.stroke();
          ctx.font = `${Math.max(10, tam * 0.5)}px 'Cinzel', Georgia, serif`;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillStyle = `rgba(${r},${g},${b},0.95)`;
          ctx.fillText(runa, cx, baseY - radioHalo);
        },
      };
    }

    // Pieza 2: anotaciones de criatura en ESPACIO DE PANTALLA, dibujadas
    // DESPUES de la cola Y-sorted -- seleccion, nombre y barra de vitalidad
    // nunca quedan ocultos por un sello (convencion cartografica: las
    // etiquetas van sobre el mapa). alturaVisual es el semieje vertical del
    // cuerpo dibujado en la cola, para apoyar las anotaciones en sus pies.
    function dibujarAnotacionesEntidad(e, centro, alturaVisual, nivel, seleccionada) {
      if (seleccionada) {
        ctx.beginPath();
        ctx.ellipse(centro.x, centro.y + alturaVisual - 2, alturaVisual * 0.85, 4, 0, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(212,172,13,0.95)';
        ctx.lineWidth = 1.6;
        ctx.stroke();
      }
      if (nivel !== 'micro') return;

      ctx.font = '10px Georgia, serif';
      ctx.fillStyle = 'rgba(36,26,15,0.9)';
      const etiqueta = e.nombre || (e.tipo === 'necromasa' ? `Restos (${e.origen || '?'})` : e.tipo);
      ctx.textAlign = 'center';
      ctx.fillText(etiqueta, centro.x, centro.y + alturaVisual + 9);

      if (e.pool_fisico) {
        const anchoBarra = 26, altoBarra = 3;
        const bx = centro.x - anchoBarra / 2, by = centro.y + alturaVisual + 15;
        ctx.fillStyle = 'rgba(58,43,26,0.4)';
        ctx.fillRect(bx, by, anchoBarra, altoBarra);
        const vitalidad = Math.max(0, Math.min(1, e.pool_fisico.vitalidad));
        ctx.fillStyle = vitalidad > 0.35 ? 'rgba(58,110,58,0.85)' : 'rgba(150,40,32,0.85)';
        ctx.fillRect(bx, by, anchoBarra * vitalidad, altoBarra);
      }
    }

    // Estampado con Y-sorting (informe: montaÃ±as y flora ordenadas de
    // norte a sur en un unico pase, para que el sur oculte al norte).
    // Devuelve true si dibujo con assets reales la categoria de relieve
    // (para que el llamador sepa si debe caer al dibujarRelieve() vectorial).
    // elementosExtra (pieza 2): cola de criaturas ya construida en espacio
    // de mundo -- se mezcla en la misma ordenacion para oclusion real.
    function dibujarStampsRelieveYFlora(tam, data, frustum, elementosExtra = [], formaciones = null, nivel = null) {
      const poolMontana = poolTerreno(
        catalogoAssets.relieve.montana_color, 'relieve_color/',
        catalogoAssets.relieve.montana, 'relieve/',
      );
      const montanaConAssets = poolMontana.lista.length > 0;
      const elementos = [];

      for (let y = frustum.yMin; y < frustum.yMax; y++) {
        for (let x = frustum.xMin; x < frustum.xMax; x++) {
          const c = data.celdas[y][x];

          // Circulo 2: con formaciones activas, los sellos por celda de
          // montana no se dibujan (la cordillera del cluster los taparia
          // con un sello suyo). Sin formaciones (biblioteca vacia), el
          // por-celda de siempre queda intacto.
          // (2026-08-28) Guard de agua: ni pico ni planta en celdas con
          // agua permanente -- el sello desborda su celda y tapaba el
          // lago vecino (capturas de Diego); la capa de agua pinta esas
          // celdas y cualquier sello terrestre ahi es ruido.
          // (2026-08-28) Menos profusion, mas tamano (feedback de Diego
          // contra el visor real): solo ~la mitad de las celdas de
          // montana llevan sello (hash determinista) y la base sube a
          // 2.6 -- picos definidos en vez de muro continuo.
          // (2026-08-28) Los sellos de pico SOLO a color (sepia): en tinta la
          // ilustracion se funde en masa oscura y el relieve vectorial
          // dibuja la montana.
          if (c.bioma === 'montana' && !c.tipo_agua && montanaConAssets && estiloColorActivo()
              && !(formaciones && formaciones.relieve) && hash2(x, y, 99) < 0.5) {
            const nombre = elegirVariante(poolMontana.lista, x, y, 91);
            const img = imagenesCache[poolMontana.prefijo + nombre];
            if (img) {
              let cxBase, baseY;
              if (nivel === 'macro') {
                cxBase = x * tam + tam / 2;
                baseY = (y + 1) * tam;
              } else {
                // (2026-09-03, CORRECCION -- ver celdaComoQuad mas arriba)
                // proyectar directamente la posicion fraccional real del
                // mundo (x+0.5, y+1), no "proyectar (x,y) y sumar tam
                // plano" (una celda no mide tam de alto en pantalla bajo
                // Caballera).
                const proyeccion = celdaAPantallaCompleta(x + 0.5, y + 1, c.elevacion, tam, data.ancho, camara.rotacion);
                cxBase = proyeccion.cx;
                baseY = proyeccion.cy;
              }
              elementos.push({
                img, ordenY: baseY,
                cx: cxBase + (hash2(x, y, 92) - 0.5) * tam * 0.3,
                baseY,
                // (2026-08-28) Jerarquia de escala: la montana DOMINA el
                // paisaje -- base 2.6 (3.4-5.2 celdas de ancho en las
                // celdas estampadas) frente a la flora a base 1.0
                // (0.4-1.0). Antes compartian base 1.3 y las cordilleras
                // competian con las matas de hierba.
                escala: 2.0 + c.elevacion * 0.7, base: 2.6,
              });
            }
          }

          if (c.planta && !c.tipo_agua && !(formaciones && formaciones.flora && c.bioma === 'bosque')) {
            // Pieza nuevosAssetsDefinitivos (2026-08-27): el estado de la
            // planta elige el pool cuando existen sellos para el -- fruto
            // si la celda conserva recurso (manzanas / fruto_de_cactus) y
            // brote si la etapa es baja. Solo a zoom de color: los sellos
            // de estado existen solo en acuarela; a tinta (lejos) el genero
            // base manda, igual que los estados finos de criaturas no se
            // leen a zoom macro.
            let claveEspecie = c.planta.especie;
            if (estiloColorActivo()) {
              const recursos = c.recursos || {};
              if (c.planta.especie === 'manzano') {
                if ((recursos.manzanas || 0) > 0 && (catalogoAssets.flora_color.manzano_fruto || []).length > 0) {
                  claveEspecie = 'manzano_fruto';
                } else if (c.planta.etapa < 0.35 && (catalogoAssets.flora_color.manzano_brote || []).length > 0) {
                  claveEspecie = 'manzano_brote';
                }
              } else if (c.planta.especie === 'cactus') {
                if ((recursos.fruto_de_cactus || 0) > 0 && (catalogoAssets.flora_color.cactus_fruto || []).length > 0) {
                  claveEspecie = 'cactus_fruto';
                }
              }
            }
            const poolPlanta = poolTerreno(
              catalogoAssets.flora_color[claveEspecie], 'flora_color/',
              catalogoAssets.flora[claveEspecie], 'flora/',
            );
            const nombre = elegirVariante(poolPlanta.lista, x, y, 93);
            const img = nombre ? imagenesCache[poolPlanta.prefijo + nombre] : null;
            if (img) {
              let cxBase, baseYBase;
              if (nivel === 'macro') {
                cxBase = x * tam + tam / 2;
                baseYBase = y * tam + tam * 0.85;
              } else {
                // (2026-09-03, CORRECCION -- ver celdaComoQuad mas arriba)
                // proyectar directamente (x+0.5, y+0.85), no "proyectar
                // (x,y) y sumar 0.85*tam plano".
                const proyeccion = celdaAPantallaCompleta(x + 0.5, y + 0.85, c.elevacion, tam, data.ancho, camara.rotacion);
                cxBase = proyeccion.cx;
                baseYBase = proyeccion.cy;
              }
              const baseY = baseYBase + (hash2(x, y, 95) - 0.5) * tam * 0.3;
              elementos.push({
                img, ordenY: baseY,
                cx: cxBase + (hash2(x, y, 94) - 0.5) * tam * 0.5,
                baseY,
                // (2026-09-03) base 1.0 -> 1.4 -- feedback real de Diego:
                // un arbol maduro debe verse claramente mas grande que un
                // lobo (el mayor de los depredadores). Con base 1.0 un
                // arbol maduro ya salia ~1.9x un lobo en idle (1.0*tam
                // vs ~0.52*tam), pero un arbol JOVEN (etapa baja, escala
                // hasta 0.4) se quedaba mas pequeno que el propio lobo --
                // con base 1.4, un brote (escala 0.4) sale ~0.56*tam
                // (similar a un lobo adulto) y un arbol maduro (escala
                // 1.0) sale 1.4*tam (~2.7x un lobo) -- jerarquia
                // razonada, PROVISIONAL, sin calibrar contra el harness.
                escala: 0.4 + c.planta.etapa * 0.6, base: 1.4,
              });
            }
          }
        }
      }

      for (const extra of elementosExtra) elementos.push(extra);

      elementos.sort((a, b) => a.ordenY - b.ordenY);
      for (const el of elementos) {
        // Pieza 2: los elementos de criatura traen su propio closure de
        // dibujo (sprite o halo+runa en espacio de mundo); los de terreno
        // siguen siendo {img, cx, baseY, escala} de toda la vida.
        if (typeof el.dibujar === 'function') {
          el.dibujar();
          continue;
        }
        // base por categoria (2026-08-28): montana 2.0, flora 1.0 -- la
        // jerarquia de escala vive aqui, no en formulas sueltas.
        const ancho = tam * (el.base || 1.3) * el.escala;
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
    // (2026-09-03) ZOOM_MAXIMO subido de 4.5 a 8.0 -- feedback real de
    // Diego: a 4.5 las criaturas pequenas (conejo/ardilla, lado real
    // ~0.09-0.16*tam) quedaban demasiado pequenas para verlas/clicarlas
    // bien. PROVISIONAL, sin medir el efecto sobre rendimiento a esa
    // profundidad de zoom contra el motor real.
    const ZOOM_MINIMO = 0.4, ZOOM_MAXIMO = 8.0;
    let tam0 = null;
    const camara = { zoom: 1, offsetX: 0, offsetY: 0, rotacion: 0 };

    // (2026-09-03) Bounding box real de las 4 esquinas del mundo, ya
    // proyectadas con Caballera+rotacion (elevacion=0 -- la elevacion
    // real solo añade un desplazamiento vertical pequeño frente al
    // sesgo por profundidad, se ignora aqui por simplicidad). Como la
    // proyeccion es afin en (px,py) para cualquiera de las 4 rotaciones
    // discretas, el minimo/maximo de cx/cy del grid completo siempre
    // cae en una de las 4 esquinas -- no hace falta recorrer celda a
    // celda.
    function calcularBoundingBoxProyectado(n, rotacion) {
      const esquinas = [
        celdaAPantallaCompleta(0, 0, 0, tam0, n, rotacion),
        celdaAPantallaCompleta(n, 0, 0, tam0, n, rotacion),
        celdaAPantallaCompleta(0, n, 0, tam0, n, rotacion),
        celdaAPantallaCompleta(n, n, 0, tam0, n, rotacion),
      ];
      const xs = esquinas.map((e) => e.cx);
      const ys = esquinas.map((e) => e.cy);
      return { minX: Math.min(...xs), maxX: Math.max(...xs), minY: Math.min(...ys), maxY: Math.max(...ys) };
    }

    // (2026-09-03, CORREGIDO por segunda vez tras ver el visor real con
    // capturas) el primer intento centraba el BOUNDING BOX completo del
    // rombo -- pero ese rombo es bastante mas ancho que el canvas a
    // zoom 1 (el sesgo por profundidad expande el ancho real muy por
    // encima de lo que cabe), asi que centrar SU bounding box seguia
    // dejando la mitad del canvas vacio. Reencuadre: en niveles
    // medio/micro (Caballera) nunca se pretende ver el mundo ENTERO de
    // un vistazo -- para eso ya existe la vista macro cenital. Centrar
    // aqui significa centrar sobre el CENTRO LOGICO del mundo (la celda
    // del medio), no sobre el rombo completo -- mismo criterio que
    // cualquier vista de detalle de este tipo, nunca se ve el mapa
    // entero "de cerca".
    // (2026-09-03, TERCERA correccion de centrarCamara -- reportado por
    // Diego con capturas reales: seguia quedando mucho hueco vacio,
    // incluso centrando sobre el centro logico del mundo). Causa real,
    // medida contra el motor: el rombo Caballera es ESTRUCTURALMENTE
    // mucho mas ancho que alto con ALPHA=45/K=0.5 -- el eje X lleva la
    // anchura COMPLETA de una fila sin comprimir mas el desplazamiento
    // de profundidad, mientras el eje Y solo lleva la compresion. Con
    // un mundo 40x40 y canvas 900px: ancho del rombo ~1218px (ya se
    // desborda a zoom 1), alto ~318px (menos de la mitad del canvas).
    // Ningun centrado arregla esto -- subir el zoom para llenar la
    // altura desborda el ancho todavia mas de lo que ya se desborda.
    // Se acepta: en medio/micro NUNCA se pretende ver el ancho completo
    // del mundo sin hacer pan lateral (coherente con que tampoco se
    // pretende ver el mundo entero -- para eso esta la vista macro). El
    // zoom se ajusta para que la ALTURA del rombo llene el canvas (con
    // margen), no el ancho.
    const MARGEN_ENCUADRE_VERTICAL = 0.85;
    function centrarCamara() {
      if (!tam0 || !ultimoDataConocido) {
        camara.zoom = 1;
        camara.offsetX = 0;
        camara.offsetY = 0;
        return;
      }
      const n = ultimoDataConocido.ancho;
      const alto = ultimoDataConocido.alto;
      const bbox = calcularBoundingBoxProyectado(n, camara.rotacion);
      const alturaRombo = bbox.maxY - bbox.minY;
      camara.zoom = alturaRombo > 0
        ? Math.min(ZOOM_MAXIMO, Math.max(ZOOM_MINIMO, (canvas.height * MARGEN_ENCUADRE_VERTICAL) / alturaRombo))
        : 1;
      const centro = celdaAPantallaCompleta(n / 2, alto / 2, 0, tam0, n, camara.rotacion);
      camara.offsetX = canvas.width / 2 - centro.cx * camara.zoom;
      camara.offsetY = canvas.height / 2 - centro.cy * camara.zoom;
    }

    function rotarCamara() {
      camara.rotacion = (camara.rotacion + 90) % 360;
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

    // (2026-08-27, pieza 1 del plan visual aprobado por Diego) Las
    // entidades saltaban de celda en celda a cada instantanea de 250ms:
    // dibujarFrame leia data.entidades directamente. Este gestor mantiene
    // una posicion animada por entidad que persigue la posicion real del
    // ECS con el MISMO suavizado exponencial dependiente de dt que ya usa
    // el seguimiento de camara (tau = 0.15 s). Calibracion provisional:
    // es la constante de la camara reutilizada, no una medida del motor;
    // si el movimiento se ve lento o nervioso, es un numero a ajustar
    // contra el visor real. Una entidad recien vista (nacimiento) y un
    // mundo nuevo (semilla distinta al reiniciar el motor) aparecen
    // CLAVADOS en su celda, nunca deslizandose desde coordenadas viejas.
    // El hit-test de click (entidadEnPunto) y el objetivo del seguimiento
    // de camara siguen leyendo la posicion REAL de la instantanea: sobre
    // ellos no debe influir un retardo estetico de dibujo.
    class GestorAnimacionEntidades {
      constructor(tau = 0.15) {
        this.tau = tau;
        this.porId = new Map();
        this.semillaVista = null;
      }

      sincronizar(entidades, semilla) {
        if (semilla !== undefined && this.semillaVista !== null && semilla !== this.semillaVista) {
          this.porId.clear();
        }
        if (semilla !== undefined) this.semillaVista = semilla;

        const vivas = new Set();
        (entidades || []).forEach((ent) => {
          vivas.add(ent.id);
          const { x, y, ...resto } = ent;
          let animada = this.porId.get(ent.id);
          if (!animada) {
            animada = { ...resto, tx: x, ty: y, x, y };
            this.porId.set(ent.id, animada);
          } else {
            // El resto de campos (tipo, nombre, pool_fisico, origen...)
            // se copian tal cual: el bucle de dibujo no cambia.
            Object.assign(animada, resto);
            animada.tx = x;
            animada.ty = y;
          }
        });
        for (const id of this.porId.keys()) {
          if (!vivas.has(id)) this.porId.delete(id);
        }
      }

      avanzar(dtSegundos) {
        const alfa = 1 - Math.exp(-dtSegundos / this.tau);
        this.porId.forEach((e) => {
          // La ultima direccion de marcha persiste por individuo: cuando
          // la criatura para, conserva la pose idle orientada hacia donde
          // camino por ultima vez (la resolucion de pose la lee).
          const dx = e.tx - e.x, dy = e.ty - e.y;
          if (Math.abs(dx) + Math.abs(dy) > EN_MARCHA_EPSILON) {
            e.ultimaDir = Math.abs(dx) >= Math.abs(dy) ? (dx > 0 ? 'e' : 'o') : (dy > 0 ? 's' : 'n');
          }
          e.x += dx * alfa;
          e.y += dy * alfa;
        });
      }

      lista() {
        return Array.from(this.porId.values());
      }
    }
    const animadorEntidades = new GestorAnimacionEntidades();

    // Hit-test contra la posicion en pantalla de cada entidad (misma
    // formula mundoAPantalla que usa el dibujado) -- selecciona la mas
    // cercana al click dentro de un radio razonable de acierto.
    function entidadEnPunto(data, px, py) {
      let mejor = null, distMejor = 16 * 16;   // radio de acierto ~16px
      const nivel = nivelActual();
      for (const e of data.entidades) {
        let proyeccion;
        if (nivel === 'macro') {
          proyeccion = { cx: (e.x + 0.5) * tam0, cy: (e.y + 0.5) * tam0 };
        } else {
          const cxCelda = Math.max(0, Math.min(data.ancho - 1, Math.round(e.x)));
          const cyCelda = Math.max(0, Math.min(data.alto - 1, Math.round(e.y)));
          const elevacion = data.celdas[cyCelda][cxCelda].elevacion || 0;
          // (2026-09-03, CORRECCION -- ver celdaComoQuad mas arriba)
          // proyectar directamente el centro real (e.x+0.5, e.y+0.5), no
          // "proyectar (e.x,e.y) y sumar tam0/2 plano".
          proyeccion = celdaAPantallaCompleta(e.x + 0.5, e.y + 0.5, elevacion, tam0, data.ancho, camara.rotacion);
        }
        const centro = mundoAPantalla(proyeccion.cx, proyeccion.cy);
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
    document.getElementById('btn-rotar').addEventListener('click', rotarCamara);
    window.addEventListener('keydown', (ev) => {
      if (ev.key === 'r' || ev.key === 'R') rotarCamara();
    });

    // Pieza 3: botones de modo de mapa (codice / relieve / hidro)
    for (const m of ['codice', 'relieve', 'hidro']) {
      document.getElementById('btn-modo-' + m).addEventListener('click', () => setModoMapa(m));
    }

    // PRNG determinista (mulberry32) sembrado por instantanea.semilla --
    // el grano del pergamino debe ser el MISMO en cada recarga del mismo
    // mundo, no ruido distinto cada frame (eso romperÃ­a la ilusion de un
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

﻿    // Circulo 4 v2 (2026-08-27, feedback de Diego: numeros y reticula eran
    // invisibles a 0.43x porque todo escalaba con el mundo): el marco de
    // codice vive en ESPACIO DE PANTALLA -- trazo y tipografia de tamano
    // constante, anclados al rectangulo del mapa en pantalla. Se llama
    // DESPUES de restaurar la transformacion del mundo. Con celdas
    // pequenas en pantalla se numera cada k celdas para no amontonar.
    function dibujarMarcoCodice(ancho, alto, celdaPantalla, origenX, origenY) {
      const w = ancho * celdaPantalla, h = alto * celdaPantalla;

      ctx.strokeStyle = 'rgba(36,26,15,0.9)';
      ctx.lineWidth = 3;
      ctx.strokeRect(origenX + 1, origenY + 1, w - 2, h - 2);
      ctx.strokeStyle = 'rgba(36,26,15,0.55)';
      ctx.lineWidth = 1;
      const sep = 6;
      ctx.strokeRect(origenX + sep, origenY + sep, w - 2 * sep, h - 2 * sep);

      ctx.strokeStyle = 'rgba(36,26,15,0.18)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      for (let x = 1; x < ancho; x++) { ctx.moveTo(origenX + x * celdaPantalla, origenY + sep); ctx.lineTo(origenX + x * celdaPantalla, origenY + h - sep); }
      for (let y = 1; y < alto; y++) { ctx.moveTo(origenX + sep, origenY + y * celdaPantalla); ctx.lineTo(origenX + w - sep, origenY + y * celdaPantalla); }
      ctx.stroke();

      ctx.fillStyle = 'rgba(36,26,15,0.55)';
      ctx.font = '10px Georgia, serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      const cada = Math.max(1, Math.ceil(22 / celdaPantalla));
      for (let x = 0; x < ancho; x += cada) {
        const cx = origenX + x * celdaPantalla + celdaPantalla / 2;
        ctx.fillText(String(x + 1), cx, origenY + sep / 2);
        ctx.fillText(String(x + 1), cx, origenY + h - sep / 2);
      }
      for (let y = 0; y < alto; y += cada) {
        const cy = origenY + y * celdaPantalla + celdaPantalla / 2;
        ctx.fillText(String(y + 1), origenX + sep / 2, cy);
        ctx.fillText(String(y + 1), origenX + w - sep / 2, cy);
      }
    }

    // Paso 2: relieve, hidrografia vectorial y vegetacion --------------

    function dibujarRelieve(tam, data, frustum, esMacro) {
      // Silueta triangular con sombreado este por celda de bioma Montana
      // (LOD macro de la propuesta).
      // (2026-08-28, v3) Historial: v1 = triangulo identico por celda en
      // rejilla (papel pintado, feedback de Diego); v2 = hashes de
      // variacion sin damero, pero los picos apenas se solapaban y TODOS
      // se trazaban: enjambre de piramides sueltas (render de referencia).
      // La v3 lee como CORDILLERA: semiancho > media celda (los vecinos
      // se solapan), base en el borde de celda (las filas se funden, sin
      // terrazas), altura variable por hash + elevacion real, y TRAZO
      // SELECTIVO -- solo se traza el pico cuyo vecino sur no es montana
      // o es mas bajo: los picos ocultos detras quedan solo con relleno,
      // sus patas ya no cruzan el cuerpo del pico de delante (asi se
      // dibuja una cordillera de plumilla; trazarlo todo era lo que
      // producia las cruces de la v1).
      const alturaDe = (x, y) => {
        const c = data.celdas[y] && data.celdas[y][x];
        if (!c || c.bioma !== 'montana') return 0;
        const esc = 0.55 + 0.55 * hash2(x, y, 101);
        return tam * 0.95 * esc * (0.65 + 0.5 * Math.min(0.6, c.elevacion));
      };
      for (let y = frustum.yMin; y < frustum.yMax; y++) {
        for (let x = frustum.xMin; x < frustum.xMax; x++) {
          const c = data.celdas[y][x];
          if (c.bioma !== 'montana') continue;
          // (2026-09-03, CORRECCION -- ver celdaComoQuad mas arriba)
          // proyectar directamente (x+0.5, y+1), no "proyectar (x,y) y
          // sumar tam plano".
          let cxBase, base;
          if (esMacro) {
            cxBase = x * tam + tam / 2;
            base = (y + 1) * tam;
          } else {
            const proyeccion = celdaAPantallaCompleta(x + 0.5, y + 1, c.elevacion, tam, data.ancho, camara.rotacion);
            cxBase = proyeccion.cx;
            base = proyeccion.cy;
          }
          const cx = cxBase + (hash2(x, y, 102) - 0.5) * tam * 0.3;
          const apice = base - alturaDe(x, y);
          const semiancho = tam * (0.62 + 0.23 * hash2(x, y, 104));
          const izq = cx - semiancho, der = cx + semiancho;

          ctx.beginPath();
          ctx.moveTo(cx, apice); ctx.lineTo(izq, base); ctx.lineTo(cx, base);
          ctx.closePath();
          ctx.fillStyle = 'rgba(150,140,124,0.45)';
          ctx.fill();

          ctx.beginPath();
          ctx.moveTo(cx, apice); ctx.lineTo(der, base); ctx.lineTo(cx, base);
          ctx.closePath();
          ctx.fillStyle = 'rgba(94,84,70,0.45)';
          ctx.fill();

          if (alturaDe(x, y) >= alturaDe(x, y + 1)) {
            ctx.strokeStyle = 'rgba(58,43,26,0.55)';
            ctx.lineWidth = Math.max(0.8, tam * 0.03);
            ctx.beginPath();
            ctx.moveTo(izq, base); ctx.lineTo(cx, apice); ctx.lineTo(der, base);
            ctx.stroke();
          }
        }
      }
    }

    // Contorno real de un cluster de celdas (mismo algoritmo que ya se usa
    // para picos/lagos-sin-asset): recorre cada celda en sentido horario,
    // se queda solo con las aristas que dan a fuera del cluster, y las
    // encadena por sus puntos hasta formar el poligono de frontera exacto.
    function contornoDeCluster(cluster, tam, n, elevacion, esMacro) {
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
      // (2026-09-03, correccion real -- reportado por Diego: "hay lineas
      // por el mapa que no se entienden") esta silueta vivia en pixeles
      // planos (x*tam), ajena a la proyeccion Caballera que ya mueve
      // todo lo demas -- el agua quedaba desalineada de la orilla real.
      // A macro (cenital, sin Caballera) sigue igual que siempre.
      if (esMacro) {
        return mejorBucle.map(p => ({ x: p.x * tam, y: p.y * tam }));
      }
      return mejorBucle.map(p => {
        const { cx, cy } = celdaAPantallaCompleta(p.x, p.y, elevacion, tam, n, camara.rotacion);
        return { x: cx, y: cy };
      });
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
    // real. Esto aÃ±ade una ondulacion de baja frecuencia (dos senos
    // superpuestos, como dos octavas de ruido) perpendicular al contorno,
    // con fase fija por region (hash de su primera celda + semilla del
    // mundo) para que no cambie de un frame a otro. No sustituye a
    // Chaikin, se aplica DESPUES: Chaikin quita las esquinas de celda,
    // esto rompe la regularidad que Chaikin por si solo deja perfecta.
    // (2026-08-27, correccion): la primera version ondulaba hacia dentro Y
    // hacia fuera del borde real de celda por igual. Donde la onda tiraba
    // hacia dentro, se veia por debajo la capa de respaldo plana (fillRect
    // por celda, sin ondular, anadida antes para evitar huecos entre
    // regiones vecinas) -- ahi el borde seguia leyendose recto, que es
    // justo lo que Diego senalo en una region de tundra bastante
    // rectangular. Ahora la ondulacion SIEMPRE empuja hacia fuera (nunca
    // por debajo del borde real): "dilatacion" es un margen minimo
    // garantizado, la suma de ondas se anade encima sin poder bajar de
    // cero. Con esto la capa de respaldo deja de hacer falta -- ver
    // dibujarLavadoContinuo() mas abajo, ya no la dibuja.
    function ondularContorno(puntos, amplitud, fase) {
      const dilatacion = amplitud * 1.4;
      let longitudAcum = 0;
      const salida = [];
      for (let i = 0; i < puntos.length; i++) {
        const p0 = puntos[i], p1 = puntos[(i + 1) % puntos.length];
        const dx = p1.x - p0.x, dy = p1.y - p0.y;
        const seg = Math.hypot(dx, dy) || 1;
        const nx = -dy / seg, ny = dx / seg;
        const onda1 = Math.sin(longitudAcum / 42 + fase) * amplitud;
        const onda2 = Math.sin(longitudAcum / 15 + fase * 2.3) * amplitud * 0.35;
        const bulto = dilatacion + onda1 + onda2;
        salida.push({ x: p0.x + nx * bulto, y: p0.y + ny * bulto });
        longitudAcum += seg;
      }
      return salida;
    }

    // Lavado de biomas como manchas organicas (una silueta suavizada por
    // region contigua) en vez de un fillRect por celda -- el borde entre
    // dos biomas vecinos ya no es la arista recta de la cuadricula.
    // Pieza 3 (2026-08-27): modos de mapa (overlays de lectura). Solo cambia
    // la CAPA DE LAVADO del terreno: sellos, criaturas, agua trazada,
    // charcos, fuego y anotaciones son identicos en los tres modos -- es un
    // filtro de lectura del mismo mundo, no otro mundo.
    //   codice  -> lavado organico de biomas de siempre (dibujarLavadoContinuo)
    //   relieve -> hipsometrico: tono sepia por elevacion (0 = claro, 1 = oscuro)
    //   hidro   -> tierra sin lavado (pergamino) y agua azul por profundidad
    let modoMapa = 'codice';

    function modoMapaActual() {
      return modoMapa;
    }

    function setModoMapa(modo) {
      if (!['codice', 'relieve', 'hidro'].includes(modo)) return;
      modoMapa = modo;
      for (const m of ['codice', 'relieve', 'hidro']) {
        const btn = document.getElementById('btn-modo-' + m);
        if (btn) btn.classList.toggle('activo', m === modo);
      }
    }

    // Calibraciones provisionales (eleccion a ojo contra el visor real, no
    // medidas del motor): extremos de la rampa hipsometrica y de la rampa
    // de profundidad, y alfas de ambas aguadas.
    const HIPSOMETRICO_CLARO = [225, 210, 175];   // tierras bajas: pergamino calido
    const HIPSOMETRICO_OSCURO = [92, 74, 52];     // cumbres: tinta sepia
    const AGUA_SOMERA = [166, 196, 212];
    const AGUA_PROFUNDA = [38, 70, 92];
    const PROFUNDIDAD_MAXIMA_AGUA = 2;            // celdas mas hondas que esto saturan el tono

    function colorHipsometrico(elevacion) {
      const e = Math.max(0, Math.min(1, elevacion));
      return [0, 1, 2].map((i) =>
        Math.round(HIPSOMETRICO_CLARO[i] + (HIPSOMETRICO_OSCURO[i] - HIPSOMETRICO_CLARO[i]) * e)
      );
    }

    function colorAguaPorProfundidad(profundidad) {
      const f = Math.max(0, Math.min(1, profundidad / PROFUNDIDAD_MAXIMA_AGUA));
      return [0, 1, 2].map((i) =>
        Math.round(AGUA_SOMERA[i] + (AGUA_PROFUNDA[i] - AGUA_SOMERA[i]) * f)
      );
    }

    // Devuelve { relleno } para pintar la celda en los modos relieve/hidro,
    // o null si la celda no lleva lavado en el modo actual (en hidro, la
    // tierra deja ver el pergamino). En codice NUNCA se consulta: el lavado
    // organico de dibujarLavadoContinuo manda y esa ruta queda intacta.
    function lavadoDeCelda(celda) {
      if (modoMapa === 'relieve') {
        const [r, g, b] = colorHipsometrico(celda.elevacion || 0);
        return { relleno: `rgba(${r}, ${g}, ${b}, 0.5)`, r, g, b, alfa: '0.5' };
      }
      if (modoMapa === 'hidro') {
        if (!celda.tiene_agua) return null;
        const [r, g, b] = colorAguaPorProfundidad(celda.profundidad_agua || 0);
        return { relleno: `rgba(${r}, ${g}, ${b}, 0.6)`, r, g, b, alfa: '0.6' };
      }
      return null;
    }

    // Lavado por celda de los modos relieve/hidro (el codice no pasa por aqui).
    // Circulo 3 (2026-08-27): el lavado de biomas a medio/micro es un
    // CAMPO CONTINUO. Antes: clasificar cada celda y pintar rectangulos de
    // color plano -- transiciones duras entre bloques ("los colores y las
    // transiciones no son naturales", Diego). Ahora el color se MEZCLA
    // segun los campos continuos de la celda (lluvia/temperatura/
    // elevacion) con rampas suaves alrededor de los umbrales del motor
    // (que llegan por el DTO: una sola fuente de verdad). El orden de
    // mezcla replica el arbol de nucleo/bioma.py para que lavado y
    // clasificacion cuenten la misma historia.
    function colorLavadoContinuo(c) {
      const U = umbralesLavado || UMBRALES_LAVADO_DEFECTO;
      const P = PALETA_LAVADO;
      let color = P.pradera;
      const tDesierto = 1 - _rampa(c.lluvia || 0, U.umbral_lluvia_desierto, BANDA_LAVADO);
      color = _mezclar(color, P.desierto, tDesierto);
      color = _mezclar(color, P.bosque, _rampa(c.lluvia || 0, U.umbral_lluvia_bosque, BANDA_LAVADO));
      const tTundra = 1 - _rampa(c.temperatura || 0, U.umbral_temperatura_tundra, BANDA_LAVADO);
      color = _mezclar(color, P.tundra, tTundra);
      color = _mezclar(color, P.montana, _rampa(c.elevacion || 0, U.umbral_elevacion_montana, BANDA_LAVADO));
      return [color[0], color[1], color[2], 90];
    }

    // (2026-09-03, correccion real -- reportado por Diego con capturas:
    // borde "en escalera" entre el terreno y el fondo) HALLAZGO: una
    // celda no puede dibujarse como un cuadrado plano tam x tam en
    // pantalla. Bajo Caballera, un paso de una fila del mundo (wy -> wy+1)
    // solo desplaza cy en sin(ALPHA)*K*tam (~0.35*tam con los valores
    // actuales), no tam -- dibujar cuadrados de tam de alto los hace
    // solaparse mucho mas de lo que la proyeccion real produce, y el
    // canto recto de cada cuadrado es lo que se ve como escalera en el
    // borde del terreno. La celda es un PARALELOGRAMO: sus 4 esquinas
    // reales del mundo (wx,wy)-(wx+1,wy)-(wx+1,wy+1)-(wx,wy+1),
    // proyectadas con la MISMA elevacion de la celda (una celda es un
    // plano, no cuatro alturas distintas).
    function celdaComoQuad(wx, wy, elevacion, tam, n, rotacion) {
      return [
        celdaAPantallaCompleta(wx, wy, elevacion, tam, n, rotacion),
        celdaAPantallaCompleta(wx + 1, wy, elevacion, tam, n, rotacion),
        celdaAPantallaCompleta(wx + 1, wy + 1, elevacion, tam, n, rotacion),
        celdaAPantallaCompleta(wx, wy + 1, elevacion, tam, n, rotacion),
      ];
    }

    function trazarQuad(quad) {
      ctx.beginPath();
      ctx.moveTo(quad[0].cx, quad[0].cy);
      for (let i = 1; i < quad.length; i++) ctx.lineTo(quad[i].cx, quad[i].cy);
      ctx.closePath();
    }

    // De las 4 esquinas de la celda unidad (wx,wy)-(wx+1,wy+1), el borde
    // "mas profundo en pantalla" (mayor py tras rotarCoordenadas) no es
    // siempre el sur del mundo -- depende de la rotacion (a 90 grados es
    // el oeste, a 180 el norte, a 270 el este). Se deriva de forma
    // generica (comparando py real de las 4 esquinas) en vez de una
    // tabla escrita a mano, para no arriesgar un caso mal derivado.
    function bordeDeCelda(wx, wy, n, rotacion, masProfundo) {
      const esquinas = [
        { wx, wy }, { wx: wx + 1, wy }, { wx: wx + 1, wy: wy + 1 }, { wx, wy: wy + 1 },
      ].map((p) => ({ ...p, ...rotarCoordenadas(p.wx, p.wy, n, rotacion) }));
      const pyObjetivo = masProfundo
        ? Math.max(...esquinas.map((e) => e.py))
        : Math.min(...esquinas.map((e) => e.py));
      return esquinas.filter((e) => Math.abs(e.py - pyObjetivo) < 1e-9).map((e) => ({ wx: e.wx, wy: e.wy }));
    }

    // Cara de risco (generalizada, circulo 2026-09-03): rellena el hueco
    // entre el borde "mas profundo en pantalla" de la celda actual y el
    // borde "menos profundo" de su vecino de pantalla, cuando el vecino
    // es mas bajo. Ya no es un rectangulo plano -- es el cuadrilatero
    // real entre ambos bordes (que pueden estar sesgados por Caballera).
    function dibujarCaraDeRisco(tam, data, wx, wy, elevacion, r, g, b, alfaTexto) {
      const n = data.ancho;
      const { px, py } = rotarCoordenadas(wx, wy, n, camara.rotacion);
      const { wx: vx, wy: vy } = invertirRotacion(px, py + 1, n, camara.rotacion);
      if (vx < 0 || vy < 0 || vx >= data.ancho || vy >= data.alto) return;
      const vecino = data.celdas[vy][vx];
      const elevVecino = vecino.elevacion || 0;
      if (elevacion <= elevVecino) return;

      const miBorde = bordeDeCelda(wx, wy, n, camara.rotacion, true);
      const bordeVecino = bordeDeCelda(vx, vy, n, camara.rotacion, false);
      const p1 = celdaAPantallaCompleta(miBorde[0].wx, miBorde[0].wy, elevacion, tam, n, camara.rotacion);
      const p2 = celdaAPantallaCompleta(miBorde[1].wx, miBorde[1].wy, elevacion, tam, n, camara.rotacion);
      const p3 = celdaAPantallaCompleta(bordeVecino[1].wx, bordeVecino[1].wy, elevVecino, tam, n, camara.rotacion);
      const p4 = celdaAPantallaCompleta(bordeVecino[0].wx, bordeVecino[0].wy, elevVecino, tam, n, camara.rotacion);

      ctx.fillStyle = `rgba(${Math.round(r * 0.7)}, ${Math.round(g * 0.7)}, ${Math.round(b * 0.7)}, ${alfaTexto})`;
      ctx.beginPath();
      ctx.moveTo(p1.cx, p1.cy);
      ctx.lineTo(p2.cx, p2.cy);
      ctx.lineTo(p3.cx, p3.cy);
      ctx.lineTo(p4.cx, p4.cy);
      ctx.closePath();
      ctx.fill();
    }

    function dibujarLavadoContinuo(tam, data, frustum) {
      for (let y = frustum.yMin; y < frustum.yMax; y++) {
        for (let x = frustum.xMin; x < frustum.xMax; x++) {
          const c = data.celdas[y][x];
          const [r, g, b, a] = colorLavadoContinuo(c);
          const alfaTexto = (a / 255).toFixed(3);
          ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${alfaTexto})`;
          trazarQuad(celdaComoQuad(x, y, c.elevacion, tam, data.ancho, camara.rotacion));
          ctx.fill();
          dibujarCaraDeRisco(tam, data, x, y, c.elevacion, r, g, b, alfaTexto);
        }
      }
    }

    function dibujarLavadoModo(tam, data, frustum) {
      for (let y = frustum.yMin; y < frustum.yMax; y++) {
        for (let x = frustum.xMin; x < frustum.xMax; x++) {
          const c = data.celdas[y][x];
          const lavado = lavadoDeCelda(c);
          if (!lavado) continue;
          ctx.fillStyle = lavado.relleno;
          trazarQuad(celdaComoQuad(x, y, c.elevacion, tam, data.ancho, camara.rotacion));
          ctx.fill();
          dibujarCaraDeRisco(tam, data, x, y, c.elevacion, lavado.r, lavado.g, lavado.b, lavado.alfa);
        }
      }
    }

    // (2026-08-29, fix de auditoria) dibujarBiomas() -- v2 del lavado de
    // bioma, manchas organicas por region con la tabla plana COLOR_BIOMA
    // -- se eliminó de aqui junto con COLOR_BIOMA (huerfana sin su unico
    // consumidor): ningun camino de ejecucion las llamaba desde que
    // dibujarLavadoContinuo()/PALETA_LAVADO (campo continuo, v3, mas
    // arriba) las sustituyo el 2026-08-27. Codigo muerto confirmado por
    // grep antes de borrar (ninguna llamada real, solo comentarios que
    // las mencionaban -- ya corregidos para apuntar a
    // dibujarLavadoContinuo).

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
      // Contain (2026-08-28): el sello ENCAJA en el recuadro ampliado sin
      // deformarse. Estirar ancho y alto por separado deformaba las
      // orillas de los lagos y achataba/estiraba cordilleras y bosques
      // (capturas de Diego: el bosque gigante a un tercio del mapa). El
      // sobrante del recuadro queda de lavado/pergamino, no como hueco
      // del sello: mejor cobertura insuficiente que silueta falsa.
      const esc = Math.min(w / img.naturalWidth, h / img.naturalHeight);
      const dw = img.naturalWidth * esc, dh = img.naturalHeight * esc;
      ctx.drawImage(img, cx - dw / 2, cy - dh / 2, dw, dh);
    }

    // Sello de agua cuyo encuadre natural encaja con la FORMA del cuerpo:
    // elegir por hash podia caer a un sello cuadrado para una laguna
    // alargada y el contain lo encogeria dejando pergamino a los lados.
    // Desempate determinista: a delta igual decide el hash de siempre.
    function selloPorAspecto(variantes, comp, tam, sal) {
      if (!variantes || variantes.length === 0) return null;
      const minX = Math.min(...comp.map(c => c.x)), maxX = Math.max(...comp.map(c => c.x));
      const minY = Math.min(...comp.map(c => c.y)), maxY = Math.max(...comp.map(c => c.y));
      const anchoBase = (maxX - minX + 1) * tam, altoBase = (maxY - minY + 1) * tam;
      const aspectoCluster = anchoBase / altoBase;
      let mejor = null, mejorDelta = Infinity;
      for (const nombre of variantes) {
        const img = imagenesCache['agua/' + nombre];
        if (!img) continue;
        const delta = Math.abs(img.naturalWidth / img.naturalHeight - aspectoCluster);
        if (delta < mejorDelta - 1e-6 || (Math.abs(delta - mejorDelta) <= 1e-6 && hash2(comp[0].x, comp[0].y, sal) < 0.5)) {
          mejorDelta = delta;
          mejor = img;
        }
      }
      return mejor;
    }

    // (2026-08-28, decision de Diego: FUERA los sellos de imagen de
    // cuerpos de agua -- lago/poza pintados) El agua se PINTA: silueta
    // organica del cuerpo (contorno + Chaikin + ondulacion, el pipeline
    // de silueta de los biomas) con relleno DINAMICO por profundidad
    // real de celda -- orilla clara, banda media, nucleo profundo --
    // nunca un azul monocromo. A zoom de tinta (estiloColorActivo()
    // falso) el agua es una AGUADA apagada integrada en el pergamino:
    // un solo lavado translucido + contorno de tinta, sin bandas (el
    // detalle de profundidad no se lee de lejos y el color solido
    // quedaba superpuesto sobre un mapa en tinta -- capturas de Diego).
    // Los PNG de agua quedan en disco sin referenciar, como el resto de
    // bibliotecas retiradas.
    const AGUA_COLOR = {
      orilla: [168, 196, 210], medio: [108, 148, 172], profundo: [56, 88, 118],
      contorno: [28, 40, 51],
    };
    const AGUA_TINTA = {
      relleno: [104, 120, 130], contorno: [36, 26, 15],
    };

    function contraerPoligono(poly, delta) {
      // (2026-08-28) Offset del contorno hacia DENTRO por la bisectriz de
      // las normales de las aristas adyacentes, con delta constante. El
      // sentido interno (horario/antihorario) se detecta con el area
      // firmada; en coordenadas de pantalla (y hacia abajo) un area
      // positiva es un poligono visualmente horario y la rotacion
      // (dy,-dx) apunta hacia FUERA, de ahi el signo negativo -- sin
      // esto, el contorno se expandiria en vez de contraerse. A diferencia
      // de escalar hacia el centroide, funciona en cuerpos concavos y da
      // bandas de grosor constante.
      if (delta <= 0 || poly.length < 3) return poly;
      let area2 = 0;
      for (let i = 0; i < poly.length; i++) {
        const a = poly[i], b = poly[(i + 1) % poly.length];
        area2 += a.x * b.y - b.x * a.y;
      }
      const s = area2 > 0 ? -1 : 1;
      return poly.map((p, i) => {
        const a = poly[(i - 1 + poly.length) % poly.length];
        const b = poly[(i + 1) % poly.length];
        let nx = (b.y - a.y) * s, ny = (a.x - b.x) * s;
        const len = Math.hypot(nx, ny) || 1;
        return { x: p.x + (nx / len) * delta, y: p.y + (ny / len) * delta };
      });
    }

    function pintarCuerpoAgua(comp, tam, sal, n, esMacro) {
      // (2026-08-28, v4) HACHURADO horizontal clasico de los mapas de
      // plumilla: relleno de agua + trazos ondulados paralelos recortados
      // por la silueta (clip). Historial: v2 bandas contraidas (bordes
      // duros), v3 manchas por celda (burbujas, feedback de Diego) --
      // ambas retiradas. El hachurado es UNA textura uniforme, no
      // acumulaciones ni bandas.
      if (comp.length === 0) return;
      const tinta = !estiloColorActivo();
      // (2026-09-03) Elevacion representativa del cuerpo de agua -- media
      // de sus celdas reales (ya la trae componentesAgua). El agua no
      // "flota": se ancla a la misma altura que el terreno que la rodea,
      // igual que el resto de elementos ya migrados a Caballera.
      const elevacionAgua = comp.reduce((s, c) => s + (c.elevacion || 0), 0) / comp.length;
      let silueta = suavizarChaikin(contornoDeCluster(comp, tam, n, elevacionAgua, esMacro), 2);
      const fase = hash2(comp[0].x, comp[0].y, sal) * Math.PI * 2;

      trazarPoligono(silueta);
      if (tinta) {
        ctx.fillStyle = `rgba(${AGUA_TINTA.relleno.join(',')}, 0.28)`;
        ctx.fill();
      } else {
        ctx.fillStyle = `rgba(${AGUA_COLOR.orilla.join(',')}, 0.95)`;
        ctx.fill();
      }

      // Trazos ondulados horizontales dentro de la silueta (clip).
      // (2026-09-03, correccion real -- "lineas que no se entienden") el
      // bounding box del muestreo salia de comp (coordenadas de mundo
      // planas, x*tam), ajeno a donde la silueta YA proyectada por
      // Caballera cae de verdad -- las lineas se dibujaban fuera de
      // fase con el propio contorno que las recorta. Se deriva de la
      // silueta YA proyectada, no de comp.
      ctx.save();
      trazarPoligono(silueta);
      ctx.clip();
      let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
      for (const p of silueta) {
        if (p.x < minX) minX = p.x;
        if (p.x > maxX) maxX = p.x;
        if (p.y < minY) minY = p.y;
        if (p.y > maxY) maxY = p.y;
      }
      const colorTrazo = tinta ? AGUA_TINTA.contorno : AGUA_COLOR.profundo;
      const alfaTrazo = tinta ? 0.30 : 0.32;
      ctx.strokeStyle = `rgba(${colorTrazo.join(',')}, ${alfaTrazo})`;
      ctx.lineWidth = Math.max(0.7, tam * 0.055);
      const paso = tam * 0.38;
      let ypx = minY;
      let fila = 0;
      while (ypx <= maxY + tam) {
        ctx.beginPath();
        let px = minX - tam * 0.5;
        let primero = true;
        while (px <= maxX + tam * 1.5) {
          const py = ypx + Math.sin(px / (tam * 0.9) + fase + fila * 0.7) * tam * 0.09;
          if (primero) { ctx.moveTo(px, py); primero = false; }
          else ctx.lineTo(px, py);
          px += tam * 0.22;
        }
        ctx.stroke();
        ypx += paso;
        fila++;
      }
      ctx.restore();

      // Contorno de orilla.
      trazarPoligono(silueta);
      ctx.strokeStyle = tinta
        ? `rgba(${AGUA_TINTA.contorno.join(',')}, 0.55)`
        : `rgba(${AGUA_COLOR.contorno.join(',')}, 0.6)`;
      ctx.lineWidth = tinta ? 1.1 : 1.0;
      ctx.stroke();
    }

    function dibujarCuencaConAssets(tam, comp, variantesLago, n, esMacro) {
      // (2026-08-28) Ya no estampa sellos de imagen: el agua se pinta
      // (pintarCuerpoAgua, decision de Diego). La firma conserva el
      // nombre y el argumento de variantes para no reescribir el
      // llamador; el argumento queda sin uso, y los PNG de agua siguen
      // en disco sin referenciar.
      pintarCuerpoAgua(comp, tam, 96, n, esMacro);
    }

    // Circulo 2 (2026-08-27): a zoom macro el mapa es PERGAMINO PURO con
    // sellos de FORMACION -- la generalizacion cartografica propuesta por
    // Diego en el README: cada cluster de un bioma con formacion declarada
    // en FORMACIONES_POR_BIOMA se estampa como UN sello de formacion, en
    // vez de un sello por celda que a esta escala era ruido. La funcion es
    // generica: el conocimiento de que sello usa cada bioma vive en la
    // tabla. Devuelve un objeto con true por cada bioma formado mas las
    // categorias 'suprime' activadas -- el llamador suprime entonces los
    // sellos por celda de esas categorias. Sin biblioteca, el objeto sale
    // vacio y el estampado por celda de siempre queda intacto.
    function dibujarFormacionesMacro(tam, data, frustum, soloBiomas = null) {
      const resultado = {};
      for (const comp of componentesPorBioma(data)) {
        const cfg = FORMACIONES_POR_BIOMA[comp.bioma];
        if (!cfg) continue;
        if (soloBiomas && !soloBiomas.includes(comp.bioma)) continue;
        // (2026-08-28) Las celdas del cluster con agua permanente quedan
        // FUERA del sello de formacion: el recuadro de un cluster de
        // montana/bosque que linda con un lago abarcaba el agua y el
        // sello estampado encima la tapaba (capturas de Diego: picos
        // sobre el lago). Esas celdas las pinta la capa de agua.
        const cluster = comp.cluster.filter(c => !c.c.tipo_agua);
        if (cluster.length === 0) continue;
        const pool = (catalogoAssets[cfg.raiz] || {})[cfg.pool] || [];
        if (pool.length === 0) continue;
        const nombre = elegirVariante(pool, cluster[0].x, cluster[0].y, cfg.sal);
        const img = nombre ? imagenesCache[cfg.carpeta + nombre] : null;
        if (!img) continue;
        estamparEnRecuadro(img, cluster, tam, cfg.margen);
        resultado[comp.bioma] = true;
        if (cfg.suprime) resultado[cfg.suprime] = true;
      }
      return resultado;
    }

    // (2026-08-29, fix de auditoria) dibujarRioConAssets() -- estampar un
    // sello de imagen unico por curso de rio, la pieza "mas experimental
    // del sistema de sellos" segun su propio comentario -- se eliminó de
    // aqui: codigo muerto confirmado por grep (cero llamadas reales). Los
    // rios son spline vectorial siempre desde el commit eea8104 (ver la
    // nota de dibujarRioPiezas mas arriba, mismo hallazgo). Los PNG de
    // agua.rio quedan en disco sin referenciar.
    function dibujarRioVectorial(tam, comp, n, esMacro) {
      // (2026-08-28) El rio es un cuerpo de agua alargado y se pinta con
      // el MISMO pipeline que lagos y pozas (banda organica del contorno
      // de su cauce+orillas, bandas de profundidad). Historial: la
      // spline por centros rebotaba cauce-orilla en dientes de sierra
      // (la orilla NO es superficial: 0.001-0.03 unidades x escala 100
      // = hasta 3 m, indistinguible del cauce por profundidad).
      pintarCuerpoAgua(comp, tam, 213, n, esMacro);
    }

    // (2026-08-29, fix de auditoria) Kit de piezas de rio por celda
    // (direccionCardinalMasCercana, dibujarPiezaRotada, dibujarRioPiezas,
    // y dibujarCuenca -- su unico otro llamador) se eliminó de aqui:
    // codigo muerto confirmado por grep (cero llamadas reales) desde que
    // el autotile de piezas se retiro del camino de ejecucion en favor
    // del spline vectorial siempre (dibujarRioVectorial, arriba --
    // reconfirmado por el commit eea8104, que abandona el autotile "en
    // pruebas posteriores contra mas formas reales del motor"). Los PNG
    // de agua/rio_piezas/ siguen en disco sin referenciar, mismo criterio
    // de "no borrar assets" que el resto del proyecto -- ver
    // presentacion/assets/README.md.

    function dibujarHidrografia(tam, data, rioFino = false) {
      // (2026-08-27, feedback de Diego: "me parece horrible como quedan
      // los lagos o cuerpos de agua cuando el zoom se aleja, deberiamos
      // seguir usando las imagenes... no los trazados esos matematicos")
      // Intento intermedio (retirado el 2026-08-28, misma sesion que
      // añadio el kit de piezas): activar agua.rio_piezas a cualquier
      // zoom en vez de solo en el escenario a color. Se volvio a romper
      // contra caminos reales del motor (serpientes de "gancho"
      // repetido) en cuanto se probo con mas formas de rio -- el mismo
      // tipo de fallo que ya obligo a dos rondas de parches sobre el
      // autotile por celda (ver historial de este archivo). Diego pedia
      // imagenes en vez de trazo matematico para "los lagos o cuerpos de
      // agua" -- el lago/poza YA los cumple con un sello real a
      // cualquier zoom; el rio en concreto es un CAMINO, no una mancha,
      // y un kit de piezas fijas nunca calzo con la variedad real de
      // giros que traza el motor. Vuelve a spline vectorial siempre
      // (dibujarRioVectorial mas abajo) -- las piezas y sus funciones
      // quedan en el archivo sin usar, mismo criterio que el resto de
      // material retirado (no se borra, se documenta).
      const colorActivo = estiloColorActivo();
      const poolLago = colorActivo && (catalogoAssets.agua.lago_color || []).length > 0
        ? catalogoAssets.agua.lago_color : (catalogoAssets.agua.lago || []);
      // Cuerpo pequeno -> sello de poza (redondo, con su orilla de piedra);
      // un lago estirado hasta el recuadro de 1-2 celdas ahogaba la orilla,
      // y una poza estirada a una laguna grande se leia como mancha.
      const poolPoza = colorActivo && (catalogoAssets.agua.poza_color || []).length > 0
        ? catalogoAssets.agua.poza_color : (catalogoAssets.agua.poza || []);
      // Umbral provisional: cuerpos de hasta 4 celdas usan poza. Calibracion
      // a ojo contra el visor real (los sellos de poza son redondos; a partir
      // de ~2x2 el sello de lago reparto su orilla mejor).
      const poolDeCuerpo = (comp) => (comp.length <= 4 && poolPoza.length > 0) ? poolPoza : poolLago;

      // (2026-08-28) El RIO se traza PRIMERO: al desembocar, el sello del
      // lago (con su orilla) tapa la boca del rio -- antes se pintaba el
      // meandro azul ENCIMA del agua del lago (capturas de Diego). Y el
      // rio es SIEMPRE spline vectorial: el autotile de piezas
      // (dibujarRioPiezas) produce serpientes de gancho repetido contra
      // caminos reales del motor -- mismo tipo de fallo que su historial
      // ya documenta -- y se retira del camino (el material queda en
      // disco sin uso, como el resto de bibliotecas retiradas).
      // (2026-09-03) rioFino coincide con esMacro en el unico llamador
      // real (dibujarFrame pasa esMacro aqui) -- se reutiliza para
      // decidir si el agua se proyecta con Caballera o se queda cenital.
      const esMacro = rioFino;
      for (const comp of componentesAgua(data, 'rio')) {
        dibujarRioVectorial(tam, comp, data.ancho, esMacro);
      }
      componentesAgua(data, 'lago').forEach(comp => dibujarCuencaConAssets(tam, comp, poolDeCuerpo(comp), data.ancho, esMacro));
      componentesAgua(data, 'poza').forEach(comp => dibujarCuencaConAssets(tam, comp, poolDeCuerpo(comp), data.ancho, esMacro));
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
          // (2026-08-29, fix de auditoria) Antes solo miraba
          // catalogoAssets.flora (tinta): liquen y musgo solo tienen
          // assets en flora_color/, sin gemela en tinta, asi que este
          // guard nunca se disparaba para ellos a zoom de color -- se
          // dibujaba el sello real (via poolTerreno() en
          // dibujarStampsRelieveYFlora) Y ADEMAS la elipse vectorial
          // semitransparente encima, doble capa visible en cualquier
          // celda de montana con liquen o de tundra con musgo. Mismo
          // poolTerreno() que usa el estampado real, para que este guard
          // decida exactamente lo mismo que decide si habra un sello.
          const poolExistente = poolTerreno(
            catalogoAssets.flora_color[c.planta.especie], 'flora_color/',
            catalogoAssets.flora[c.planta.especie], 'flora/',
          );
          if ((poolExistente.lista || []).length > 0) continue;
          // Diego pidio quitar el tapiz vectorial de hierba silvestre por
          // ahora (2026-08-27) mientras no exista un asset real para ella
          // -- la celda se queda solo con el lavado de bioma de base, sin
          // relleno provisional. En cuanto haya flora/hierba_silvestre_*.png
          // el guard de arriba ya la desvia sola al sistema de sellos.
          if (c.planta.especie === 'hierba_silvestre') continue;
          // (2026-09-03, CORRECCION -- ver celdaComoQuad mas arriba) esta
          // funcion solo corre a camara.zoom>=0.8 (el guard de arriba),
          // siempre en medio/micro. Proyecta directamente el CENTRO real
          // de la celda (x+0.5, y+0.5), no "proyectar (x,y) y sumar
          // tam/2 plano".
          const proyeccionPlanta = celdaAPantallaCompleta(x + 0.5, y + 0.5, c.elevacion, tam, data.ancho, camara.rotacion);
          const cx = proyeccionPlanta.cx, cy = proyeccionPlanta.cy;
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
        cont.innerHTML = `<h3>ðŸ¦´ Restos &middot; ${e.origen}</h3>` +
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

    // (2026-08-27, corrigiendo feedback de Diego contra el visor real --
    // "el zoom no es fluido, las criaturas saltan como con lag") Antes,
    // TODO el dibujo del canvas vivia dentro de actualizar(), disparado por
    // un solo setInterval(actualizar, 250) -- es decir, el mapa entero solo
    // se REPINTABA 4 veces por segundo, encadenado a cuando llegaba un
    // fetch nuevo. Arrastrar/hacer zoom con el raton SI actualizaba
    // camara.zoom/offsetX/Y al instante, pero la pantalla no reflejaba ese
    // cambio hasta el siguiente tick del intervalo -- de ahi el zoom a
    // trompicones y las criaturas "saltando" de una posicion a la
    // siguiente sin ningun paso intermedio. Esto ya era asi antes del
    // pivote a color de hoy, pero se ha notado mas porque cada repintado
    // ahora hace mas trabajo (composicion de sellos a color, autotile de
    // rio), alargando el tiempo entre fotogramas visibles.
    //
    // Separado en dos bucles independientes: obtenerDatos() seguisiendo
    // por polling a 250ms (frecuencia del propio motor, no tiene sentido
    // pedir mas rapido), solo actualiza el ESTADO (ultimoDataConocido) y
    // los paneles de texto/cronica -- nunca toca el canvas directamente.
    // dibujarFrame() corre en requestAnimationFrame (el ritmo del
    // navegador, tipicamente 60Hz) y SOLO dibuja, leyendo siempre el
    // ultimo estado conocido -- el pan/zoom del raton se refleja en el
    // fotogramas siguiente, no en el proximo tick de red.
    async function obtenerDatos() {
      try {
        const resp = await fetch('/estado.json');
        if (!resp.ok) return;
        const data = await resp.json();
        if (!data.celdas) return;
        ultimoDataConocido = data;
        animadorEntidades.sincronizar(data.entidades, data.semilla);
        if (data.bioma_umbrales) umbralesLavado = data.bioma_umbrales;

        document.getElementById('info-mundo').innerHTML =
          `<strong>Semilla:</strong> ${data.semilla} &middot; <strong>Tick:</strong> ${data.tick} &middot; ` +
          `<strong>Dia:</strong> ${data.dia} &middot; <strong>Anio:</strong> ${data.anio}<br>` +
          `<strong>Estacion:</strong> ${data.estacion} &middot; <strong>Clima:</strong> ${data.clima}`;

        document.getElementById('info-poblacion').innerHTML =
          `<strong>Gnomos:</strong> ${data.censo.gnomo || 0} &middot; <strong>Lobos:</strong> ${data.censo.lobo || 0} &middot; ` +
          `<strong>Conejos:</strong> ${data.censo.conejo || 0} &middot; <strong>Ardillas:</strong> ${data.censo.ardilla || 0}<br>` +
          `<strong>Restos (Necromasa):</strong> ${data.censo.necromasa || 0}`;

        const claveActual = `${data.semilla}:${data.ancho}:${data.alto}`;
        if (pergaminoClave !== claveActual) {
          pergaminoCache = construirPergamino(data.semilla, data.ancho, data.alto);
          pergaminoClave = claveActual;
        }

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
    setInterval(obtenerDatos, 250);
    obtenerDatos();

    let ultimoTiempoFrame = null;

    function dibujarFrame(tiempoAhora) {
      requestAnimationFrame(dibujarFrame);
      const data = ultimoDataConocido;
      if (!data || !pergaminoCache) return;

      // Delta de tiempo real entre fotogramas (no un contador de ticks),
      // para que el suavizado de camara.seguimiento converja al mismo
      // ritmo real independientemente de a cuantos Hz dibuje el navegador.
      const dt = ultimoTiempoFrame === null ? 1 / 60 : Math.min(0.1, (tiempoAhora - ultimoTiempoFrame) / 1000);
      ultimoTiempoFrame = tiempoAhora;

      // Pieza 1: avanza las posiciones animadas de las entidades hacia la
      // posicion real de la ultima instantanea, con el mismo dt de la camara.
      animadorEntidades.avanzar(dt);

      tam0 = canvas.width / data.ancho;
      const tam = tam0;

      // Modo seguimiento (informe seccion 6.1): la camara persigue a la
      // entidad seleccionada con suavizado exponencial dependiente de dt
      // (antes era un salto de 0.15 fijo por cada tick de red de 250ms --
      // mismo suavizado en el tiempo, pero ahora interpolado en cada
      // fotograma en vez de en escalones de 250ms).
      if (modoSeguimiento && entidadSeleccionadaId !== null) {
        const objetivo = data.entidades.find((en) => en.id === entidadSeleccionadaId);
        if (objetivo) {
          const deseadoX = canvas.width / 2 - (objetivo.x + 0.5) * tam * camara.zoom;
          const deseadoY = canvas.height / 2 - (objetivo.y + 0.5) * tam * camara.zoom;
          const alfa = 1 - Math.exp(-dt / 0.15);
          camara.offsetX += (deseadoX - camara.offsetX) * alfa;
          camara.offsetY += (deseadoY - camara.offsetY) * alfa;
        }
      }

      document.getElementById('lectura-zoom').textContent = `Zoom: ${camara.zoom.toFixed(2)}x`;

      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.save();
      ctx.translate(camara.offsetX, camara.offsetY);
      ctx.scale(camara.zoom, camara.zoom);

      // El nivel de zoom decide TODO el camino de render (lavado, sellos,
      // formaciones, criaturas) -- se calcula antes que nada. Reutiliza
      // nivelActual() (antes duplicaba la formula inline) para que solo
      // haya una fuente de verdad del umbral 0.8/2.0.
      const nivel = nivelActual();
      // (2026-09-03) Con la proyeccion Caballera activa (medio/micro),
      // calcularFrustum ya no es valido: asume x*escala+offsetX sin
      // sesgo, y el termino de profundidad de Caballera acopla X a la
      // fila (wy) incluso sin rotar -- un rango estrecho de wy puede
      // desplazar wx fuera de lo que calcularFrustum calcularia. El
      // mundo es pequeno (40x40, 1600 celdas) y el propio calculo
      // estrecho ya se documentaba como "ahorro modesto" a esta escala
      // -- se itera la cuadricula completa en medio/micro. Macro sigue
      // usando el calculo estrecho, sin cambios (cenital, sin sesgo).
      const frustum = nivel === 'macro'
        ? calcularFrustum(data)
        : { xMin: 0, xMax: data.ancho, yMin: 0, yMax: data.alto };
      ctx.drawImage(pergaminoCache, 0, 0, data.ancho * tam, data.alto * tam);
      // Circulo 2: a zoom macro el mapa es PERGAMINO PURO -- sin lavado
      // de color de biomas en modo codice (los sellos de formacion
      // definen montanas y bosques; las zonas se leen por el sello, no
      // por una aguada de reticula). Los modos relieve/hidro SI lavan
      // aunque sea macro: son filtros de lectura que el usuario pide
      // explicitamente. Medio/micro conservan el lavado organico.
      // Circulo 3: a medio/micro el modo codice pinta el CAMPO CONTINUO de
      // biomas (mezcla suave por lluvia/temperatura/elevacion). A macro,
      // pergamino puro como en el circulo 2.
      const esMacro = nivel === 'macro';
      if (!esMacro) {
        if (modoMapa === 'codice') dibujarLavadoContinuo(tam, data, frustum);
        else dibujarLavadoModo(tam, data, frustum);
      }

      for (let y = frustum.yMin; y < frustum.yMax; y++) {
        for (let x = frustum.xMin; x < frustum.xMax; x++) {
          const c = data.celdas[y][x];
          // (2026-09-03, CORRECCION -- ver celdaComoQuad mas arriba) el
          // charco/fuego cubren la celda entera, igual que el terreno --
          // se dibujan como el mismo paralelogramo, no un fillRect plano.
          // Agua permanente (rio/lago/poza) ya no se pinta plana aqui --
          // dibujarHidrografia() la traza como forma vectorial despues de
          // esta pasada. El charco efimero SI se queda plano: es una
          // mancha de un tick, no un cuerpo geografico que merezca trazo.
          // El charco efimero SI se queda plano (a macro ni eso: a esa
          // escala una mancha de un tick es ruido), no un cuerpo
          // geografico que merezca trazo.
          if (!esMacro && c.profundidad_charco > 0) {
            const intensidad = Math.min(1, c.profundidad_charco / 0.3);
            ctx.fillStyle = `rgba(${COLOR_CHARCO[0]}, ${COLOR_CHARCO[1]}, ${COLOR_CHARCO[2]}, ${0.15 + intensidad * 0.3})`;
            trazarQuad(celdaComoQuad(x, y, c.elevacion, tam, data.ancho, camara.rotacion));
            ctx.fill();
          }

          if (c.en_llamas) {
            ctx.fillStyle = `rgba(${COLOR_FUEGO[0]}, ${COLOR_FUEGO[1]}, ${COLOR_FUEGO[2]}, 0.55)`;
            if (esMacro) {
              ctx.fillRect(x * tam, y * tam, tam, tam);
            } else {
              trazarQuad(celdaComoQuad(x, y, c.elevacion, tam, data.ancho, camara.rotacion));
              ctx.fill();
            }
          }
        }
      }

      // Entidades: LOD por nivel de zoom (informe seccion 4.2) + pieza 2
      // (2026-08-27, diseño cerrado con Diego): a zoom medio/micro las
      // criaturas dejan de ser marcadores de pantalla y entran en la MISMA
      // cola Y-sorted que montanas y flora -- un gnomo tras un pico al sur
      // queda oculto tras el. A zoom macro (< 0.8) siguen siendo puntos de
      // tinta en pantalla: de lejos el mapa sigue siendo un mapa, un
      // marcador no participa en oclusiones. (La declaracion de `nivel` y
      // `entidadesAnimadas` subio al principio de dibujarFrame con el
      // circulo 2: el camino de lavado la consulta antes.)
      // Posiciones INTERPOLADAS (pieza 1): el bucle de dibujo lee del
      // gestor de animacion, no de la instantanea cruda -- mismos campos,
      // pero x/y avanzan suavemente entre instantaneas.
      const entidadesAnimadas = animadorEntidades.lista();

      // Cola de criaturas en espacio de mundo (solo medio/micro). El mapa
      // id->alturaVisual alimenta la capa de anotaciones posterior. Margen
      // de 2 celdas alrededor del frustum para no construir elementos que
      // nunca entrarian en pantalla.
      const visualesPorId = new Map();
      let elementosCriaturas = [];
      if (nivel !== 'macro') {
        const margenCeldas = 2;
        elementosCriaturas = entidadesAnimadas
          .filter((e) => e.x > frustum.xMin - margenCeldas && e.x < frustum.xMax + margenCeldas &&
                         e.y > frustum.yMin - margenCeldas && e.y < frustum.yMax + margenCeldas)
          .map((e) => {
            const cxCelda = Math.max(0, Math.min(data.ancho - 1, Math.round(e.x)));
            const cyCelda = Math.max(0, Math.min(data.alto - 1, Math.round(e.y)));
            const elevacionEntidad = data.celdas[cyCelda][cxCelda].elevacion || 0;
            const el = construirElementoCriatura(e, tam, elevacionEntidad, data.ancho, camara.rotacion);
            visualesPorId.set(e.id, el.alturaVisual);
            return el;
          });
      }

      // Pieza 2: el agua (lagos/rios) va ANTES de la cola Y-sorted -- es
      // terreno plano, no un objeto con altura. Estampandola despues, la
      // orilla del sello de lago (que desborda su recuadro sobre las
      // celdas de tierra vecinas por diseÃ±o) tapaba por completo a las
      // criaturas que pisaban esas celdas -- regresion detectada contra el
      // visor real: un conejo desaparecia bajo la orilla. Con el agua
      // debajo, la orilla queda DETRAS de criaturas/arboles/picos, como
      // pide un diorama. (El orden agua-despues era el de antes de la
      // pieza 2; el cambio de capa es visible y pendiente de tu visto.)
      // Circulo 2: a macro, rios de plumilla fina y sellos de formacion
      // (cordilleras/masas); los sellos por celda cubiertos por una
      // formacion se suprimen dentro de dibujarStampsRelieveYFlora.
      // (2026-08-28) El ORDEN de capa cambia: formaciones PRIMERO, agua
      // despues. Antes el agua iba antes que las formaciones y la masa de
      // bosque estampada encima tapaba el rio que la cruzaba (capturas de
      // Diego, render de referencia macro). Geograficamente el rio/lago
      // esta EN el bosque, no debajo: agua tras formaciones, y antes que
      // los sellos por celda para que la orilla siga quedando DETRAS de
      // criaturas/arboles/picos (regresion del conejo, pieza 2).
      // (2026-08-28, reparto de la montana por rangos, con la formacion de
      // imagen RESTAURADA (fue el bug: sin entrada en la tabla no
      // estampaba nada):
      //   macro: TODAS las formaciones de imagen, montana incluida --
      //     una cordillera por masa, como la de bosques (pide Diego).
      //   medio-tinta (0.8-1.0): solo la de montana (por celda no: las
      //     panoramicas solapadas a tinta se funden en masa).
      //   color (>=1.0): sin formaciones -> sellos por celda sepia.
      const formaciones = nivel === 'macro'
        ? dibujarFormacionesMacro(tam, data, frustum, null)
        : (nivel === 'medio' && !estiloColorActivo())
          ? dibujarFormacionesMacro(tam, data, frustum, ['montana'])
          : null;
      dibujarHidrografia(tam, data, esMacro);
      const montanaUsoAssets = dibujarStampsRelieveYFlora(tam, data, frustum, elementosCriaturas, formaciones, nivel);
      // (2026-08-28) El vectorial vuelve a ser SOLO el fallback sin
      // biblioteca (Diego: "no un conjunto de triangulos" cuando hay
      // formaciones de imagen): con formaciones activas formaciones.
      // relieve lo suprime, con por-celda de color lo cubre montanaUsoAssets.
      if (!montanaUsoAssets && !(formaciones && formaciones.relieve)) dibujarRelieve(tam, data, frustum, esMacro);
      dibujarVegetacion(tam, data, frustum);
      // Circulo 4: a macro el marco es el de codice (reticula de atlas con
      // coordenadas); a medio/micro, el perimetral clasico sin rejilla.
      // Circulo 4 v2: a medio/micro, perimetral clasico (espacio de mundo).
      // A macro, el marco de codice se dibuja DESPUES de restaurar la
      // transformacion, en espacio de pantalla: trazo y numeros de tamano
      // constante a cualquier zoom.
      if (!esMacro) dibujarMarco(tam, data.ancho, data.alto);

      ctx.restore();

      // Circulo 4 v2: el marco de codice en ESPACIO DE PANTALLA, sobre el
      // rectangulo del mapa ya proyectado (trazo y numeros constantes).
      if (esMacro) dibujarMarcoCodice(data.ancho, data.alto, tam * camara.zoom, camara.offsetX, camara.offsetY);

      // A zoom macro: puntos de tinta en espacio de pantalla, como siempre
      // (marcador de mapa, sin oclusiones -- decisión de diseño pieza 2).
      // Adición de Diego (2026-08-27): de lejos solo se marcan las
      // CRIATURAS CONSCIENTES con la runa de su especie -- el conejo que
      // no mira, el lobo que acecha: eso es detalle de cerca. El filtro
      // lee del DTO (estabilidad_mental_maxima existe solo para quienes
      // tienen CapacidadMental), no hardcodea especies.
      if (nivel === 'macro') {
        entidadesAnimadas.filter(e => e.consciente === true).forEach(e => {
          const centro = mundoAPantalla((e.x + 0.5) * tam, (e.y + 0.5) * tam);
          const margen = 24;
          if (centro.x < -margen || centro.x > canvas.width + margen ||
              centro.y < -margen || centro.y > canvas.height + margen) return;

          const [r, g, b] = COLOR_INK_ESPECIE[e.tipo] || [70, 60, 50];
          const seleccionada = e.id === entidadSeleccionadaId;
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
        });
        return;
      }

      // A zoom medio/micro el cuerpo de la criatura ya se dibujo DENTRO de
      // la cola Y-sorted (espacio de mundo, con oclusion real). Aqui solo
      // queda la capa de anotaciones en pantalla: seleccion siempre, y
      // nombre + barra de vitalidad a nivel micro.
      entidadesAnimadas.forEach(e => {
          // (2026-09-03) Corrige un cabo suelto del circulo del alzado
          // vertical: esta posicion nunca seguia el alzado (ni ahora el
          // sesgo de Caballera) del cuerpo ya dibujado en la cola
          // Y-sorted -- solo se llega aqui con nivel!=='macro' (el
          // branch macro ya retorno arriba), asi que siempre usa la
          // proyeccion completa.
          const cxCelda = Math.max(0, Math.min(data.ancho - 1, Math.round(e.x)));
          const cyCelda = Math.max(0, Math.min(data.alto - 1, Math.round(e.y)));
          const elevacionEntidad = data.celdas[cyCelda][cxCelda].elevacion || 0;
          // (2026-09-03, CORRECCION -- ver celdaComoQuad mas arriba)
          // proyectar directamente el centro real (e.x+0.5, e.y+0.5).
          const baseAnotacion = celdaAPantallaCompleta(e.x + 0.5, e.y + 0.5, elevacionEntidad, tam, data.ancho, camara.rotacion);
          const centro = mundoAPantalla(baseAnotacion.cx, baseAnotacion.cy);
          const margen = 24;
          if (centro.x < -margen || centro.x > canvas.width + margen ||
              centro.y < -margen || centro.y > canvas.height + margen) return;
          dibujarAnotacionesEntidad(e, centro, visualesPorId.get(e.id) ?? tam * 0.3, nivel, e.id === entidadSeleccionadaId);
        });
    }
    requestAnimationFrame(dibujarFrame);
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


def _listar_pngs(carpeta: Path) -> list[str]:
    """Cualquier .png de la carpeta cuenta como variante intercambiable,
    sin convencion de prefijo -- mismo criterio que relieve/montana."""
    if not carpeta.is_dir():
        return []
    return sorted(p.name for p in carpeta.iterdir() if p.is_file() and p.suffix.lower() == ".png")


def _agrupar_poses(carpeta: Path) -> dict[str, dict[str, str]]:
    """criaturas_poses/{especie}_{pose}.png expone un KIT de poses por
    especie (idle_s/idle_n/idle_e, andar_s/n/e, forrajeando, durmiendo,
    herido, muerto) -- igual que agua.piezas_rio, piezas con significado
    funcional propio, NO variantes esteticas intercambiables. La especie
    es el primer token del nombre; la pose, todo lo que va detras. Un
    kit incompleto para una especie no rompe nada: el cliente resuelve
    cadena de fallback hasta el sprite generico de criaturas/."""
    agrupado: dict[str, dict[str, str]] = {}
    if carpeta.is_dir():
        for archivo in sorted(carpeta.iterdir()):
            if not archivo.is_file() or archivo.suffix.lower() != ".png":
                continue
            especie, _, pose = archivo.stem.partition("_")
            if especie and pose:
                agrupado.setdefault(especie, {})[pose] = archivo.name
    return agrupado


def _listar_pngs_por_nombre(carpeta: Path) -> dict[str, str]:
    """Como _listar_pngs, pero expone cada pieza por su nombre de archivo
    (sin extension) en vez de agruparlas como variantes -- para un kit de
    piezas con significado funcional propio (recto/curva/cruce/te/gancho
    de agua/rio_piezas/), no variantes esteticas intercambiables."""
    if not carpeta.is_dir():
        return {}
    return {p.stem: p.name for p in sorted(carpeta.iterdir()) if p.is_file() and p.suffix.lower() == ".png"}


def construir_manifiesto_assets() -> dict[str, Any]:
    """    Escanea RUTA_ASSETS en cada peticion (biblioteca pequeÃ±a, coste
    despreciable) y agrupa los archivos encontrados por categoria:
    flora.especie, agua.{lago,rio} y criaturas.especie por prefijo de
    nombre de archivo; criaturas_poses.especie como kit de piezas con
    significado funcional (una pose por estado del ECS); relieve.montana
    con cualquier .png en esa carpeta (sin distincion de nombre).

    2026-08-27 (pivote LOD tinta/color): cada categoria de terreno gana un
    segundo escenario -- flora_color/ y relieve_color/ (mismo convenio que
    sus gemelas en tinta) y agua.lago_color -- que el visor solo usa a
    partir de cierto nivel de zoom (ZOOM_ESTILO_COLOR en el cliente); si
    una de estas carpetas esta vacia, el cliente simplemente sigue usando
    la variante en tinta a cualquier zoom, no rompe nada. agua.piezas_rio
    es un kit de piezas (no variantes) para el autotile de rio por celda,
    ver dibujarRioPiezas() en el cliente."""
    return {
        "flora": _agrupar_por_prefijo(RUTA_ASSETS / "flora"),
        "flora_color": _agrupar_por_prefijo(RUTA_ASSETS / "flora_color"),
        "relieve": {
            # (2026-08-28) montana/cordillera separados por prefijo: las
            # cordilleras son KIT de formacion macro (FORMACIONES_POR_BIOMA
            # lee 'cordillera'), nunca variantes por celda -- mezcladas en
            # la misma lista, el por-celda podia comprimir una cordillera
            # entera a 3 celdas y a zoom lejano su trama se fundia en un
            # bloque de tinta (capturas de Diego). Con el pool separado, la
            # formacion de montana vuelve a funcionar en el navegador.
            #
            # (2026-08-29, fix de auditoria) Generalizado a
            # _agrupar_por_prefijo(), igual que flora/agua/criaturas: la
            # version anterior solo reconocia 'montana_' y 'cordillera_'
            # a mano, asi que 'masa_desierto_*.png' y 'masa_tundra_*.png'
            # -- ya en disco, ya declarados en FORMACIONES_POR_BIOMA --
            # nunca aparecian en el manifiesto. dibujarFormacionesMacro()
            # encontraba siempre pool=[] para esos dos biomas y caia en
            # silencio al estampado por-celda, sin ningun error visible
            # (un test que simulaba los datos en memoria en vez de pasar
            # por este manifiesto real daba falso verde). El regex de
            # _agrupar_por_prefijo ya separa correctamente cada prefijo
            # (montana/cordillera/masa_desierto/masa_tundra) en su propia
            # clave -- no hace falta filtrar a mano.
            **_agrupar_por_prefijo(RUTA_ASSETS / "relieve"),
            "montana_color": _listar_pngs(RUTA_ASSETS / "relieve_color"),
        },
        "agua": _agrupar_por_prefijo(RUTA_ASSETS / "agua") | {
            "piezas_rio": _listar_pngs_por_nombre(RUTA_ASSETS / "agua" / "rio_piezas"),
        },
        "criaturas": _agrupar_por_prefijo(RUTA_ASSETS / "criaturas"),
        "criaturas_poses": _agrupar_poses(RUTA_ASSETS / "criaturas_poses"),
    }


class ManejadorWeb(http.server.BaseHTTPRequestHandler):
    """Manejador HTTP simple sin librerÃ­as externas."""

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
            RUTA_ASSETS / "flora", RUTA_ASSETS / "flora_color",
            RUTA_ASSETS / "relieve", RUTA_ASSETS / "relieve_color",
            RUTA_ASSETS / "agua", RUTA_ASSETS / "criaturas",
            RUTA_ASSETS / "criaturas_poses",
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
    plantas_por_celda: dict[tuple[int, int], dict[str, Any]] = {}
    for pid in sorted(gestor.entidades_con(Planta, Posicion)):
        planta = gestor.obtener_componente(pid, Planta)
        pos_p = gestor.obtener_componente(pid, Posicion)
        if planta and pos_p and pos_p.zona_idx == 0:
            plantas_por_celda[(pos_p.x, pos_p.y)] = {
                "especie": planta.especie,
                "etapa": round(planta.etapa, 3),
            }

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
        "celdas": celdas_data,
        "cronica": cronica,
    }



