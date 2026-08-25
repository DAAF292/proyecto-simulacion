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

    // (2026-08-25) TILE_NATIVO baja de 16 a 8 -- Diego abrio el Overworld.png
    // de Mini Medieval en Tiled (con grid configurable, en vez de mis scripts
    // de PIL con cuadricula roja dibujada encima) y confirmo visualmente que
    // el grid nativo real de TODO el pack (suelo, agua, orillas) es 8x8, no
    // 16x16. Las piezas de agua/orilla ya se extrajeron a 8x8 desde el
    // principio y verificaron correctamente contra ese grid; las cuatro
    // texturas de suelo (grass/sand/rock/tundra) se habian extraido como
    // bloques de 16x16 -- un acierto casual de tileo, no una pieza atomica
    // real, exactamente el mismo tipo de error de fondo que las orillas v1
    // (confundir una composicion de varias celdas del grid con una unica
    // pieza), solo que sin sintoma visible esta vez. Bajar TILE_NATIVO a 8
    // hace que TODO el tileset se dibuje a resolucion nativa 1:1 (antes el
    // agua/orillas de 8x8 se reescalaban x2 sin distorsion pero con grano
    // visualmente mas grueso que el suelo de 16x16 sin escalar -- ver
    // CLAUDE.md). Las cuatro texturas de suelo se reextrajeron como bancos
    // de 4 variantes reales de 8x8 cada una (ver RUTA_TEXTURAS) en vez de
    // depender solo de la rotacion D4 sobre una unica imagen.
    const TILE_NATIVO = 8;       // px por celda en el buffer de terreno (resolucion nativa)
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

    // (2026-08-25) Texturas reales de terreno -- tercer pivote de fuente,
    // historial completo en CLAUDE.md e informe_implementacion_bosque.docx
    // (7.53-7.61): PyxelSpace "Tilesets" -> Urizen (Vurmux) -> vuelta a
    // PyxelSpace -> ahora "Mini Medieval" (VEXED/v3x3d, itch.io, CC BY 4.0),
    // a peticion de Diego tras no quedar conforme con el resultado de Urizen
    // en pantalla. Mini Medieval resuelve el problema de fondo que arrastraban
    // las dos fuentes anteriores: tiene suelo continuo real (no losas de
    // mazmorra como Urizen) Y variedad genuina por bioma (a diferencia de
    // PyxelSpace, que solo cubria 3 texturas para 5 biomas). Recortes: un
    // tile solido de 16x16 por bioma, extraido de la seccion "GROUND EDGES"
    // de cada Overworld.png (el tile de relleno limpio, sin las decoraciones
    // sueltas de flores/setas que trae la seccion "GROUND" de al lado -- esas
    // se dejan fuera de esta pieza a proposito, ver nota de alcance en
    // CLAUDE.md). montana no tiene expansion de Mini Medieval dedicada (no
    // existe un "Mini Medieval - Mountain" en el pack comprado): se usa el
    // patron de piedra/adoquín gris de la seccion PATH del pack base como
    // aproximacion, aceptado y documentado como tal.
    //
    // A diferencia de Urizen y PyxelSpace, estos tiles YA vienen con el
    // color de bioma correcto (no son grises neutros pensados para tintar) --
    // aplicar el mismo 'multiply' de antes a toda opacidad los oscureceria
    // sin necesidad. Por eso el tinte se reserva solo para bosque/pradera
    // (que comparten el mismo tile de hierba y si necesitan diferenciarse
    // entre si) y se aplica en 'source-over' a alfa baja en vez de 'multiply'
    // a alfa completa -- un nudge de color, no un tinte que pueda aplastar
    // el brillo (la leccion de la pieza de Urizen de ayer). montana/desierto/
    // tundra/agua se dibujan tal cual, sin ningun tinte encima.
    const RUTA_TEXTURAS = {
      // (2026-08-25) grass/sand/rock/tundra pasan de una sola imagen de
      // 16x16 a un banco de 4 variantes reales de 8x8 -- el grid nativo real
      // confirmado en Tiled (ver nota junto a TILE_NATIVO). No son un
      // recorte generico: cada variante es una celda distinta y genuina de
      // la seccion GROUND del pack correspondiente (sin decoraciones sueltas
      // de flores/cactus/setas), elegidas evitando las celdas que resultaron
      // ser lisas de un solo color al comprobar con getcolors() -- grass
      // col0/sand col0,5,6 (base/desert) y tundra col0fila1 (arctic) eran
      // planas y se descartaron a favor de otras celdas con textura real de
      // la misma franja. rock mantiene las mismas 4 celdas que ya se usaban
      // (bloque de grava de PATH), ahora citadas como banco explicito en vez
      // de una unica imagen de 16x16.
      'grass': [
        'assets/terreno/mm_grass_a.png', 'assets/terreno/mm_grass_b.png',
        'assets/terreno/mm_grass_c.png', 'assets/terreno/mm_grass_d.png'
      ],
      'sand': [
        'assets/terreno/mm_sand_a.png', 'assets/terreno/mm_sand_b.png',
        'assets/terreno/mm_sand_c.png', 'assets/terreno/mm_sand_d.png'
      ],
      'rock': [
        'assets/terreno/mm_rock_a.png', 'assets/terreno/mm_rock_b.png',
        'assets/terreno/mm_rock_c.png', 'assets/terreno/mm_rock_d.png'
      ],
      'tundra': [
        'assets/terreno/mm_tundra_a.png', 'assets/terreno/mm_tundra_b.png',
        'assets/terreno/mm_tundra_c.png', 'assets/terreno/mm_tundra_d.png'
      ],
      'water': 'assets/terreno/mm_water.png',
      // (2026-08-25) SUPERSEDIDO el mismo dia -- ver nota larga junto a
      // dibujarAnilloOrilla() mas abajo (renombrada en v4 -- antes se llamaba
      // dibujarBordesAgua). Estas 12 piezas sustituyen al primer
      // 'orilla' de una sola textura rotada (que producia un festoneado
      // artificial, ver CLAUDE.md): 4 esquinas convexas + 4 tramos rectos,
      // con 3 variantes de textura cada uno en O/E para evitar repeticion
      // visible en tramos largos, extraidas pieza a pieza (no como bloque ya
      // montado) de Mini-Medieval-Ocean-v2.1.
      'orilla_esquina_no': 'assets/terreno/mm_orilla_esquina_no.png',
      'orilla_esquina_ne': 'assets/terreno/mm_orilla_esquina_ne.png',
      'orilla_esquina_so': 'assets/terreno/mm_orilla_esquina_so.png',
      'orilla_esquina_se': 'assets/terreno/mm_orilla_esquina_se.png',
      'orilla_borde_n': 'assets/terreno/mm_orilla_borde_n.png',
      'orilla_borde_s': 'assets/terreno/mm_orilla_borde_s.png',
      'orilla_borde_o_a': 'assets/terreno/mm_orilla_borde_o_a.png',
      'orilla_borde_o_b': 'assets/terreno/mm_orilla_borde_o_b.png',
      'orilla_borde_o_c': 'assets/terreno/mm_orilla_borde_o_c.png',
      'orilla_borde_e_a': 'assets/terreno/mm_orilla_borde_e_a.png',
      'orilla_borde_e_b': 'assets/terreno/mm_orilla_borde_e_b.png',
      'orilla_borde_e_c': 'assets/terreno/mm_orilla_borde_e_c.png',
      // (2026-08-25) SUPERSEDIDO el mismo dia, segunda vuelta: Diego probo el
      // render de referencia y señalo dos fallos reales sobre las 12 piezas
      // de arriba -- (1) estaban invertidas (el acento de agua tocaba la
      // hierba en vez del agua: las piezas se extrajeron bien pero se
      // colocaron sin voltearlas -- en la hoja original el lado con acento
      // de agua mira hacia FUERA del anillo, no hacia el agujero interior,
      // porque el asset esta pensado como un atolon en mar abierto, no como
      // una playa contra tierra firme) y (2) "estas usando las orillas de
      // desierto o oceano, cada bioma tendra que tener orillas respectivas".
      // Las 12 piezas de arriba se corrigieron in-place (ver dibujarBordesAgua)
      // y se reservan para desierto/tundra/montana; estas 8 son el juego
      // equivalente para bosque/pradera, extraidas de la seccion "BASIC
      // WATER" del pack BASE (no Ocean) -- mismo problema de orientacion
      // encontrado y corregido de la misma manera. Sin variantes de textura
      // en O/E (el pack solo trae una, a diferencia de Ocean con 3).
      // Limitacion aceptada por Diego: cada pieza trae un poste/estaca de
      // madera decorativo que sobresale un poco hacia fuera en cada celda de
      // borde (no hay variante "sin poste" para alternar) -- se ve mas
      // recargado que las capturas de referencia, pero Diego acepto usarlo
      // "de momento", con la expectativa de que mejore cuando el suelo tenga
      // su propia textura/decoracion (pieza aparte, no resuelta hoy).
      'orilla_verde_esquina_no': 'assets/terreno/mm_orilla_verde_esquina_no.png',
      'orilla_verde_esquina_ne': 'assets/terreno/mm_orilla_verde_esquina_ne.png',
      'orilla_verde_esquina_so': 'assets/terreno/mm_orilla_verde_esquina_so.png',
      'orilla_verde_esquina_se': 'assets/terreno/mm_orilla_verde_esquina_se.png',
      'orilla_verde_borde_n': 'assets/terreno/mm_orilla_verde_borde_n.png',
      'orilla_verde_borde_s': 'assets/terreno/mm_orilla_verde_borde_s.png',
      'orilla_verde_borde_o': 'assets/terreno/mm_orilla_verde_borde_o.png',
      'orilla_verde_borde_e': 'assets/terreno/mm_orilla_verde_borde_e.png',
    };
    // Biomas que usan el juego de orilla "verde" (musgo/tierra del pack base)
    // en vez del juego "arena" (Ocean) por defecto -- ver nota arriba.
    const BIOMAS_ORILLA_VERDE = new Set(['bosque', 'pradera']);
    const TEXTURA_POR_BIOMA = {
      'bosque': 'grass', 'pradera': 'grass', 'montana': 'rock',
      'desierto': 'sand', 'tundra': 'tundra'
    };
    // Subconjunto de COLORES_TERRENO que recibe el nudge de color descrito
    // arriba -- deliberadamente NO incluye montana/desierto/tundra.
    const TINTE_SUAVE_TERRENO = { 'bosque': COLORES_TERRENO['bosque'], 'pradera': COLORES_TERRENO['pradera'] };
    // (2026-08-25) Soporta tanto una ruta unica (string) como un banco de
    // variantes (array de rutas) -- lo segundo se usa para grass/sand/rock/
    // tundra desde el cambio a 8x8 nativo. texturaLista[clave] solo pasa a
    // true cuando TODAS las variantes del banco han cargado, para que
    // dibujarTexturaVariada nunca intente dibujar con un array a medio
    // rellenar.
    const TEXTURAS = {};
    const texturaLista = {};
    for (const [clave, ruta] of Object.entries(RUTA_TEXTURAS)) {
      if (Array.isArray(ruta)) {
        const imgs = ruta.map(r => {
          const img = new Image();
          img.src = r;
          return img;
        });
        let cargadas = 0;
        imgs.forEach(img => {
          img.onload = () => { cargadas++; if (cargadas === imgs.length) texturaLista[clave] = true; };
        });
        TEXTURAS[clave] = imgs;
      } else {
        const img = new Image();
        img.onload = () => { texturaLista[clave] = true; };
        img.src = ruta;
        TEXTURAS[clave] = img;
      }
    }

    // (2026-08-25) Sprites de criaturas -- pivote de Urizen a Mini Medieval
    // el mismo dia que el terreno (ver nota de arriba). Cambio de fondo, no
    // solo de fuente: Mini Medieval SI tiene las cuatro especies como
    // animales reales y reconocibles (Animals.png, con cria/adulto y
    // animaciones IDLE/SIT/WALK/ACTION/HIT/DEAD por especie) -- en concreto
    // trae una ardilla de verdad (SQUIRREL KIT/SQUIRREL), asi que ya NO hace
    // falta la aproximacion de Urizen (conejo pequeño retenido) documentada
    // ayer en la pieza 2. Por ahora se usa solo el frame IDLE (una pose fija
    // por especie, igual que con Urizen) para las cuatro; el resto de
    // animaciones del pack (ciclo de paso al caminar, HIT al recibir daño,
    // DEAD para necromasa por especie de origen, poses de ACTION para
    // comer/cazar donde el pack las tenga) quedan catalogadas en el informe
    // de analisis pero deliberadamente fuera de esta pieza -- son una fuente
    // de complejidad aparte (seleccion de frame por estado + temporizado de
    // animacion), no algo que sumar en el mismo incremento que el cambio de
    // fuente de arte.
    //
    // gnomo no tiene una fila de "raza pequeña" dedicada en Units.png (es un
    // sheet de soldados humanos recoloreados, sin gnomos/enanos segun la
    // propia descripcion del autor en itch.io) -- se eligio la unidad mas
    // sencilla y pequeña disponible en la primera fila como aproximacion,
    // sabiendo que no tiene barba blanca ni gorro rojo como pedia Diego.
    // Aproximacion documentada, no un hallazgo forzado a pasar por bueno.
    const RUTA_SPRITES_CRIATURA = {
      'gnomo': 'assets/sprites_criaturas/mm_gnomo.png',
      'lobo': 'assets/sprites_criaturas/mm_lobo.png',
      'conejo': 'assets/sprites_criaturas/mm_conejo.png',
      'ardilla': 'assets/sprites_criaturas/mm_ardilla.png',
    };
    const SPRITES_CRIATURA = {};
    const spriteCriaturaListo = {};
    for (const [clave, ruta] of Object.entries(RUTA_SPRITES_CRIATURA)) {
      const img = new Image();
      img.onload = () => { spriteCriaturaListo[clave] = true; };
      img.src = ruta;
      SPRITES_CRIATURA[clave] = img;
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
    // (2026-08-25) Extraido de dibujarTexturaVariada para reutilizarlo tambien
    // en la seleccion de variante de los tramos rectos de orilla (ver
    // dibujarBordesAgua mas abajo) -- mismo mezclado de bits, mismo criterio
    // de "reutiliza antes de inventar" que el resto del proyecto. Comportamiento
    // identico al de antes del refactor (mismo input -> mismo entero de salida).
    function hash32Celda(x, y) {
      let h = (Math.imul(x, 0x27d4eb2f) ^ Math.imul(y, 0x165667b1)) | 0;
      h = Math.imul(h ^ (h >>> 15), 0x85ebca6b);
      h = Math.imul(h ^ (h >>> 13), 0xc2b2ae35);
      return (h ^ (h >>> 16)) >>> 0;
    }

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
      // (2026-08-25) Acepta tanto una imagen unica (water, orillas) como un
      // banco de variantes reales (grass/sand/rock/tundra desde el cambio a
      // 8x8 nativo). La orientacion D4 se deriva de los 3 bits bajos del
      // hash (h % 8, igual que antes); el indice de variante se deriva de
      // los bits restantes (h / 8, sin solapar ningun bit con la
      // orientacion) para que ambas elecciones sean independientes entre si
      // -- evita a proposito el tipo de correlacion lineal que ya causo el
      // bug de las franjas diagonales documentado mas abajo, aunque aqui el
      // riesgo es menor por no ser una formula lineal en (x,y).
      const arr = Array.isArray(img) ? img : [img];
      const h = hash32Celda(x, y);
      const orientCode = h % 8;
      const rot = (orientCode % 4) * (Math.PI / 2);
      const flip = orientCode >= 4;
      const idxVariante = arr.length > 1 ? Math.floor(h / 8) % arr.length : 0;
      bufferCtx.save();
      bufferCtx.translate(px + size / 2, py + size / 2);
      bufferCtx.rotate(rot);
      bufferCtx.scale(flip ? -1 : 1, 1);
      bufferCtx.drawImage(arr[idxVariante], -size / 2, -size / 2, size, size);
      bufferCtx.restore();
    }

    // (2026-08-25) SUPERSEDIDO el mismo dia: primera version de "orillas"
    // (dibujarOrillaDireccional) tomaba un recorte de 24x10 que en realidad
    // era una composicion YA MONTADA (esquina+centro+esquina de un estanque
    // circular del pack), y la rotaba/repetia en cada celda de borde como si
    // fuera una unica pieza reutilizable. Diego vio el resultado en un render
    // de referencia y con razon no lo acepto: cada celda ponia su propia
    // "esquina" redundante, produciendo una costa festoneada (cadena de
    // medias lunas pinzadas en las uniones) en vez de una linea continua --
    // visualmente peor que el estado anterior (espuma blanca lisa).
    //
    // Diego pidio explicitamente NO abandonar el asset del pack y resolverlo
    // "de la forma mas profesional" usando el tileset. Investigacion mas a
    // fondo (diseccion tile a tile de 8x8, no por bloques ya montados, ver
    // CLAUDE.md para las coordenadas nativas completas) encontro que el pack
    // SI separa pieza de esquina y pieza de tramo recto -- mi primer intento
    // fallo por la unidad de recorte elegida, no porque el pack careciera de
    // piezas componibles. Esta es la version corregida: un autotile minimo de
    // 4 esquinas convexas + 4 tramos rectos (sin pieza cóncava dedicada -- el
    // pack tampoco la trae; en una entrante de costa los dos tramos rectos
    // simplemente se encuentran sin adorno extra, una simplificacion estandar
    // en sistemas de autotile minimos y aceptable aqui). Los tramos rectos
    // O/E tienen 3 variantes de textura (extraidas del propio pack, no
    // inventadas) elegidas con el mismo hash32Celda que ya usa
    // dibujarTexturaVariada, para que un tramo de costa largo no muestre la
    // misma piedra repetida en cada celda.
    // (2026-08-25) v4, misma tarde: rediseño de fondo tras discutirlo con
    // Diego usando capas separadas en Tiled (agua en una capa, suelo en
    // otra, anillo de orilla en una tercera por encima). Su ejemplo con
    // capas dejo claro algo que las versiones v2/v3 hacian mal: el anillo de
    // orilla debe superponerse sobre las celdas de TIERRA que rodean el
    // agua, nunca sobre la celda de agua misma -- "si tienes dos celdas de
    // agua eso solo tiene textura agua, las celdas circundantes seran del
    // bioma que corresponda, en una segunda capa pintamos la orilla
    // alrededor... y se superpone al bioma que haya debajo". v2/v3 hacian
    // justo lo contrario: pintaban el anillo (opaco, sin transparencia,
    // verificado con getcolors) DENTRO de la celda de agua. Medido con PIL:
    // cada pieza es ~88% color de tierra y solo ~12% agua, asi que toda
    // celda de agua en el borde se pintaba casi entera como tierra --
    // cualquier cuerpo de agua se veia mas pequeño de lo que decia el
    // modelo, y un canal de 1 celda de ancho (100% celdas de borde) se veia
    // casi sin nada de agua real, pareciendo una estructura en vez de un
    // canal (el hallazgo de "torre" de ayer). Girar el sistema a celdas de
    // tierra resuelve esto de raiz sin tocar ningun PNG: el agua queda
    // siempre intacta (paso de agua de dibujarCapaTerrenoAgua ya no dibuja
    // ningun anillo), y la celda de tierra vecina -- que YA es
    // mayoritariamente ese color -- recibe el anillo con naturalidad.
    //
    // Segundo cambio de fondo, geometrico: con el anillo en la celda de
    // agua, una esquina convexa (p.ej. "esquina_no") se disparaba cuando esa
    // celda de AGUA tenia tierra en dos lados cardinales adyacentes -- el
    // caso comun en cualquier laguna rectangular (las 4 esquinas de la
    // propia agua). Trasladado tal cual a la celda de tierra (usar la misma
    // condicion pero con agua/tierra invertidos) NO es el equivalente
    // correcto: para una laguna rectangular solida, la celda de tierra en la
    // esquina diagonal de la laguna nunca tiene agua en dos lados
    // cardinales a la vez (el agua le toca en diagonal, no en cruz) -- con
    // la condicion ingenua invertida las esquinas dejarian de dispararse
    // nunca para formas convexas normales, solo en muescas concavas, justo
    // al reves de lo que hace falta. La regla correcta (la misma que usan
    // los sistemas de autotile de 8 direcciones estandar en RPG Maker/Tiled
    // Wang tiles para la esquina convexa exterior): una celda de tierra
    // recibe la pieza de esquina cuando su vecino DIAGONAL en esa direccion
    // es agua Y sus dos vecinos CARDINALES en esa misma esquina son ambos
    // tierra (si alguno de los dos cardinales ya fuera agua, esa direccion
    // se resuelve como tramo recto, no como esquina). Sin pieza concava
    // dedicada (el pack no la trae, misma limitacion aceptada que en v2):
    // una muesca de tierra rodeada de agua en dos lados cardinales
    // adyacentes se resuelve con los dos tramos rectos independientes
    // encontrandose sin adorno extra.
    //
    // Bug de opacidad (documentado, no resuelto en esta version): las 20
    // piezas son 100% opacas (alfa 255 verificado con PIL) -- si una celda
    // de tierra necesita mas de una pieza en lados NO adyacentes (p.ej. un
    // istmo de tierra de 1 celda entre dos cuerpos de agua, con agua al
    // norte Y al sur), el segundo drawImage borra el primero sin dejar
    // rastro. Es el mismo bug que en v2/v3, ahora del lado de tierra en vez
    // de agua -- afecta a istmos/penínsulas estrechas, un caso mas raro que
    // los canales estrechos de antes pero real. No resuelto aqui: exigiria
    // recortar el alfa de las piezas o componer con mascaras, un cambio
    // mayor que Diego no ha pedido todavia.
    function juegoOrillaPara(bioma) {
      return BIOMAS_ORILLA_VERDE.has(bioma) ? 'orilla_verde_' : 'orilla_';
    }

    // Dibuja el anillo de orilla sobre una celda de TIERRA (x,y) que tenga
    // algun vecino de agua, cardinal o diagonal. No hace nada si la celda es
    // agua o si no toca agua por ningun lado.
    function dibujarAnilloOrilla(grid, ancho, alto, x, y, px, py, size) {
      const c = grid[y][x];
      if (c.tiene_agua) return;
      const esAgua = (nx, ny) => nx >= 0 && ny >= 0 && nx < ancho && ny < alto && grid[ny][nx].tiene_agua;
      const n = esAgua(x, y - 1), s = esAgua(x, y + 1), o = esAgua(x - 1, y), e = esAgua(x + 1, y);
      // Esquina convexa: diagonal es agua Y ambos cardinales de esa esquina
      // son tierra (si alguno fuera agua, ese lado ya se resuelve como
      // tramo recto -- ver nota larga arriba).
      const no = !n && !o && esAgua(x - 1, y - 1);
      const ne = !n && !e && esAgua(x + 1, y - 1);
      const so = !s && !o && esAgua(x - 1, y + 1);
      const se = !s && !e && esAgua(x + 1, y + 1);
      if (!n && !s && !o && !e && !no && !ne && !so && !se) return;
      const j = juegoOrillaPara(c.terreno);
      let dibujadoN = false, dibujadoS = false, dibujadoO = false, dibujadoE = false;
      if (no) { bufferCtx.drawImage(TEXTURAS[j + 'esquina_no'], px, py, size, size); dibujadoN = dibujadoO = true; }
      if (ne) { bufferCtx.drawImage(TEXTURAS[j + 'esquina_ne'], px, py, size, size); dibujadoN = dibujadoE = true; }
      if (so) { bufferCtx.drawImage(TEXTURAS[j + 'esquina_so'], px, py, size, size); dibujadoS = dibujadoO = true; }
      if (se) { bufferCtx.drawImage(TEXTURAS[j + 'esquina_se'], px, py, size, size); dibujadoS = dibujadoE = true; }
      if (n && !dibujadoN) {
        bufferCtx.drawImage(TEXTURAS[j + 'borde_n'], px, py, size, size);
      }
      if (s && !dibujadoS) {
        bufferCtx.drawImage(TEXTURAS[j + 'borde_s'], px, py, size, size);
      }
      if (o && !dibujadoO) {
        if (j === 'orilla_') {
          const variantes = ['orilla_borde_o_a', 'orilla_borde_o_b', 'orilla_borde_o_c'];
          bufferCtx.drawImage(TEXTURAS[variantes[hash32Celda(x, y) % 3]], px, py, size, size);
        } else {
          bufferCtx.drawImage(TEXTURAS[j + 'borde_o'], px, py, size, size);
        }
      }
      if (e && !dibujadoE) {
        if (j === 'orilla_') {
          const variantes = ['orilla_borde_e_a', 'orilla_borde_e_b', 'orilla_borde_e_c'];
          bufferCtx.drawImage(TEXTURAS[variantes[hash32Celda(x, y) % 3]], px, py, size, size);
        } else {
          bufferCtx.drawImage(TEXTURAS[j + 'borde_e'], px, py, size, size);
        }
      }
    }

    function orillaCargada() {
      return texturaLista['orilla_esquina_no'] && texturaLista['orilla_borde_n'] &&
        texturaLista['orilla_borde_o_a'] && texturaLista['orilla_borde_e_a'] &&
        texturaLista['orilla_verde_esquina_no'] && texturaLista['orilla_verde_borde_n'] &&
        texturaLista['orilla_verde_borde_o'] && texturaLista['orilla_verde_borde_e'];
    }

    let referencias = {};
    let estadoAnterior = null;   // { porId, t } del poll previo, para interpolar
    let estadoActual = null;     // { data, porId, t } del ultimo poll recibido
    let tPollActual = performance.now();

    // (2026-08-25) zoom inicial sube de 1 a 2 al bajar TILE_NATIVO de 16 a 8:
    // sin este ajuste el mundo se veria de golpe a la mitad de tamaño en
    // pantalla (mismo numero de celdas, la mitad de px nativos cada una) --
    // zoom=2 compensa exactamente el cambio y deja el tamaño en pantalla
    // igual que antes por defecto. Limites de la rueda tambien x2 (0.3-4 ->
    // 0.6-8) por el mismo motivo, para no perder rango de detalle disponible.
    const camara = { x: null, y: null, zoom: 2 };
    let arrastrando = false;
    let ultimoRaton = { x: 0, y: 0 };

    // (2026-08-25) Reordenado en tres pasadas explicitas sobre el grid, cada
    // una en su propia funcion, a peticion de Diego tras proponer pensar el
    // mapa "por capas" (terreno/agua, accidentes geograficos, flora, objetos,
    // criaturas). Aclaracion importante que quedo documentada en la
    // conversacion y se repite aqui porque es facil perderla de vista
    // leyendo solo el codigo: esto reordena la CAPA DE DIBUJO en el visor,
    // no el modelo de datos del motor -- el DTO de celda ya separaba
    // terreno/agua/elevacion/recurso como campos independientes antes de
    // este cambio; lo que faltaba era que el dibujo los tratara como pasos
    // independientes en vez de mezclarlos en un unico bucle. Flora y objetos
    // como capas de datos reales (no solo el marcador de recurso actual, que
    // es un flag binario) siguen sin existir y son piezas aparte, no
    // resueltas por este cambio.
    //
    // Beneficio concreto, no solo estetico: separar el sombreado de relieve
    // (antes paso 3, mezclado con el resto) en dibujarCapaRelieve() propia
    // permite confirmar o descartar de forma directa el hallazgo pendiente
    // de la mancha diagonal que Diego senalo como "filtro de clima" --
    // comentar la llamada a esta funcion y comparar el render basta para
    // verificarlo, en vez de tener que leerlo entre otros ocho efectos en el
    // mismo bucle.

    // --- Capa 1: terreno + agua (incluye orillas y charco, que son agua) ---
    function dibujarCapaTerrenoAgua(data) {
      const { ancho, alto, grid } = data;
      for (let y = 0; y < alto; y++) {
        for (let x = 0; x < ancho; x++) {
          const c = grid[y][x];
          const px = x * TILE_NATIVO, py = y * TILE_NATIVO;
          const colorBase = COLORES_TERRENO[c.terreno] || [20, 20, 20];

          // Relleno base del bioma: textura real de Mini Medieval, ya con el
          // color de bioma correcto de fabrica (a diferencia de Urizen/
          // PyxelSpace no hace falta tintarla para que lea bien). Solo
          // bosque/pradera reciben un nudge de color suave en 'source-over'
          // a alfa baja (no 'multiply' a alfa completa -- eso aplastaria el
          // brillo, la leccion de ayer) porque comparten el mismo tile base
          // y si necesitan diferenciarse entre si. Si la textura aun no
          // cargo (primer poll, o fallo de red), cae al relleno de color
          // plano de siempre -- nunca deja una celda en blanco.
          const claveTex = TEXTURA_POR_BIOMA[c.terreno];
          if (claveTex && texturaLista[claveTex]) {
            dibujarTexturaVariada(TEXTURAS[claveTex], x, y, px, py, TILE_NATIVO);
            const tinteSuave = TINTE_SUAVE_TERRENO[c.terreno];
            if (tinteSuave) {
              bufferCtx.fillStyle = `rgba(${tinteSuave[0]},${tinteSuave[1]},${tinteSuave[2]},0.18)`;
              bufferCtx.fillRect(px, py, TILE_NATIVO, TILE_NATIVO);
            }
          } else {
            bufferCtx.fillStyle = `rgb(${colorBase[0]},${colorBase[1]},${colorBase[2]})`;
            bufferCtx.fillRect(px, py, TILE_NATIVO, TILE_NATIVO);
          }

          // Autotiling procedimental (equivalente al bitmask de 4 bits del
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

          // Agua permanente: textura real de base + bandas de profundidad
          // (semi-transparentes) + orilla procedimental en el borde.
          //
          // (2026-08-25) mm_water.png dejo de ser un color plano: ahora es un
          // tile de olas real de 8x8 de la seccion WAVES del pack Ocean,
          // confirmado sin costura visible al teselarlo 6x6 antes de usarlo
          // (dibujarTexturaVariada de sobra reutilizado, cero codigo nuevo
          // para esto). A peticion expresa de Diego ("quiero meter la
          // textura del agua tambien... para que el mapa quede como los
          // mockups"). Las alfas de las bandas de profundidad de abajo
          // (0.55/0.75/0.92) son ANTERIORES a este cambio, pensadas para un
          // color plano debajo -- con la textura real, 0.92 en la banda
          // profunda la aplastaba casi del todo (confirmado en un render de
          // referencia comparando ambos). Bajadas a 0.30/0.45/0.60,
          // comparadas en el mismo render de referencia -- sigue habiendo
          // gradiente de profundidad claramente visible, pero la ola se nota
          // en las tres bandas. Es una eleccion de gusto, no una medicion
          // objetiva (mismo tipo de ajuste que el de ALPHA_MAX_CHARCO) --
          // si no convence, son tres numeros que cambiar.
          // (2026-08-25) v4: el agua YA NO dibuja ningun anillo de orilla
          // sobre si misma -- ver la nota larga junto a dibujarAnilloOrilla()
          // mas abajo sobre por que eso hacia que el agua se viera mas
          // pequeña de lo real. La celda de agua se pinta siempre pura:
          // textura de olas + banda de profundidad, nada mas. El anillo se
          // dibuja aparte, en dibujarCapaOrillas(), sobre las celdas de
          // TIERRA vecinas.
          if (c.tiene_agua) {
            if (texturaLista['water']) {
              dibujarTexturaVariada(TEXTURAS['water'], x, y, px, py, TILE_NATIVO);
            }
            let colorAgua, alfa;
            if (c.profundidad_agua <= 0.3) { colorAgua = '135,206,235'; alfa = 0.30; }
            else if (c.profundidad_agua <= 1.0) { colorAgua = '52,120,190'; alfa = 0.45; }
            else { colorAgua = '15,50,100'; alfa = 0.60; }
            bufferCtx.fillStyle = `rgba(${colorAgua},${alfa})`;
            bufferCtx.fillRect(px, py, TILE_NATIVO, TILE_NATIVO);
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
        }
      }
    }

    // --- Capa 2: anillo de orilla sobre las celdas de tierra que tocan agua ---
    // Se dibuja DESPUES de la capa de terreno/agua (para superponerse al
    // bioma que ya esta pintado debajo, tal como lo describio Diego) y ANTES
    // del relieve (para que el sombreado de elevacion siga aplicandose por
    // encima del anillo igual que sobre cualquier otra celda de tierra).
    function dibujarCapaOrillas(data) {
      const { ancho, alto, grid } = data;
      if (!orillaCargada()) return;
      for (let y = 0; y < alto; y++) {
        for (let x = 0; x < ancho; x++) {
          const px = x * TILE_NATIVO, py = y * TILE_NATIVO;
          dibujarAnilloOrilla(grid, ancho, alto, x, y, px, py, TILE_NATIVO);
        }
      }
    }

    // --- Capa 3: accidentes geograficos (relieve) ---
    // Sombreado de relieve: diferencia de elevacion con el vecino diagonal.
    // Separado en su propia pasada (antes vivia dentro del mismo bucle que
    // el resto) precisamente para poder aislarlo al diagnosticar la mancha
    // diagonal que Diego senalo -- ver nota larga arriba de dibujarTerreno().
    function dibujarCapaRelieve(data) {
      const { ancho, alto, grid } = data;
      for (let y = 1; y < alto; y++) {
        for (let x = 1; x < ancho; x++) {
          const c = grid[y][x];
          const px = x * TILE_NATIVO, py = y * TILE_NATIVO;
          const dz = c.elevacion - grid[y - 1][x - 1].elevacion;
          if (dz > 0.001) {
            bufferCtx.fillStyle = `rgba(255,255,255,${Math.min(0.35, dz * 1.5)})`;
            bufferCtx.fillRect(px, py, TILE_NATIVO, TILE_NATIVO);
          } else if (dz < -0.001) {
            bufferCtx.fillStyle = `rgba(0,0,0,${Math.min(0.3, -dz * 1.5)})`;
            bufferCtx.fillRect(px, py, TILE_NATIVO, TILE_NATIVO);
          }
        }
      }
    }

    // --- Capa 4: decoracion/eventos (marcador de recurso, fuego) ---
    // Marcador de recurso es hoy un proxy tosco de "flora" (un punto verde,
    // no una textura ni una densidad real) -- se deja en esta capa a
    // proposito para que el dia que flora exista como concepto real del
    // motor, sustituirlo aqui no obligue a reordenar nada mas.
    function dibujarCapaDecoracion(data) {
      const { ancho, alto, grid } = data;
      for (let y = 0; y < alto; y++) {
        for (let x = 0; x < ancho; x++) {
          const c = grid[y][x];
          const px = x * TILE_NATIVO, py = y * TILE_NATIVO;
          if (c.tiene_recurso) {
            bufferCtx.fillStyle = 'rgba(120,220,120,0.55)';
            bufferCtx.beginPath();
            bufferCtx.arc(px + TILE_NATIVO / 2, py + TILE_NATIVO / 2, TILE_NATIVO * 0.12, 0, Math.PI * 2);
            bufferCtx.fill();
          }
          if (c.en_llamas) {
            bufferCtx.fillStyle = 'rgba(192,57,43,0.75)';
            bufferCtx.fillRect(px, py, TILE_NATIVO, TILE_NATIVO);
          }
        }
      }
    }

    // --- Terreno: dibujado una vez por poll en el buffer offscreen, no cada frame ---
    function dibujarTerreno(data) {
      const ancho = data.ancho, alto = data.alto;
      bufferTerreno.width = ancho * TILE_NATIVO;
      bufferTerreno.height = alto * TILE_NATIVO;
      bufferCtx.imageSmoothingEnabled = false;
      dibujarCapaTerrenoAgua(data);
      dibujarCapaOrillas(data);
      dibujarCapaRelieve(data);
      dibujarCapaDecoracion(data);
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
      camara.zoom = Math.max(0.6, Math.min(8, camara.zoom * factor));
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
