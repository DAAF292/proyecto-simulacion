# Biblioteca de assets cartográficos

Regenerada el 2026-09-04 desde `presentacion/nuevosAssetsDefinitivos/` (10
hojas, pares `<bioma>Macro` en tinta / `<bioma>Micro` en color, más 4 hojas
sueltas de `montañas/` y 4 hojas de pose por criatura). La carpeta anterior
(`presentacion/assets/`, fuente `nuevosAssets/`) se borró por completo en el
commit `20999a4` — esta es una reconstrucción desde cero, no una migración.

Esta carpeta la llena una persona o un script de extracción (nunca el motor
ni el visor en tiempo real). `presentacion/vista_web.py` solo detecta y sirve
lo que encuentre aquí (`construir_manifiesto_assets()`); si una categoría
está vacía, el visor cae automáticamente al dibujo vectorial que ya existe,
nunca se rompe ni queda en blanco.

**Script de extracción**: `presentacion/arnes/extraer_sprites_definitivos.py`
— detección por componentes conexas (distancia al fondo estimado de las
esquinas + dilatación morfológica para fusionar el hachurado disperso de la
tinta en un único blob por sprite), alfa con zona muerta + rampa (mismo
criterio que ya documentaba esta carpeta en su versión anterior, evita el
halo rectangular que costó un bug real la primera vez). El mapeo
índice-de-detección → nombre de archivo es una tabla escrita a mano revisando
cada hoja imagen por imagen, no es automático — si se regenera una hoja
fuente, hay que revisar la tabla de nuevo, no solo re-correr el script.

## Convención de nombres (sin cambios respecto a la versión anterior)

- `flora/<especie>_<n>.png` + `flora_color/<especie>_<n>.png` — variantes
  intercambiables por especie real de `config/flora.yaml` (`flora.especies`).
- `flora_color/manzano_fruto_<n>.png`, `flora_color/cactus_fruto_<n>.png` —
  sellos de estado (recurso todavía presente en la celda), leídos
  directamente por el cliente (`vista_web.py`, líneas ~1071-1078). Sin
  `manzano_brote_<n>.png` esta vez (pendiente, ver abajo).
- `relieve/pico_<n>.png` + `relieve_color/pico_<n>.png` — variantes de pico
  suelto, sin distinción de nombre (cualquier `.png` cuenta).
- `relieve/cordillera_<n>.png`, `relieve/masa_desierto_<n>.png`,
  `relieve/masa_tundra_<n>.png`, `flora/masa_bosque_<n>.png` — pools de
  **formación macro** que `FORMACIONES_POR_BIOMA` (vista_web.py:330-339) ya
  lee activamente para estampar un cluster completo de celdas contiguas como
  una sola silueta panorámica en vez de sello por sello. Estaban vacíos tras
  el borrado — sin ellos, montaña/desierto/tundra caían al estampado
  por-celda y bosque no dibujaba nada de formación (montaña llegó a estar
  además desconectada de la tabla en su día, ver el comentario del propio
  código). Con esta extracción los cuatro tienen contenido real.
- `agua/lago_<n>.png`, `agua/poza_<n>.png` + `_color` — igual que antes.
- `criaturas_poses/<especie>_<pose>.png` — kit de poses por especie
  (`idle_e/idle_n/idle_s`, `andar_e/andar_n/andar_s`, `durmiendo`,
  `forrajeando`, `herido`, `muerto`). `idle_e` es el ancla de escala
  (`ESCALA_POSE`, factor 1.0 por definición); un kit incompleto no rompe
  nada — el cliente resuelve una cadena de fallback.
  `<especie>_andar_<dir>_f2/f3/f4.png` — frames adicionales del ciclo de
  paso presentes en las hojas fuente, extraídos porque la extracción es
  gratuita en este punto, **sin consumidor todavía** (el visor solo dibuja
  un sprite estático por pose, sin animación) — listos si algún día se
  añade animación por pose.
- `relieve/formacion_<n>.png` + `relieve_color/formacion_<n>.png` —
  formaciones rocosas nuevas de las hojas fuente (arcos, mesas, cairns,
  acantilados, dunas de roca) **sin categoría en el visor actual** todavía
  (`vista_web.py` no las lee bajo ningún nombre). Decisión explícita de
  Diego (2026-09-04): extraerlas igualmente para uso futuro en vez de
  descartarlas, sin cablear nada del lado del cliente en este círculo.

## Aproximaciones provisionales — sin sprite fuente real, decisión explícita

- **`flora_color/arbusto_montano_<n>.png`**: ninguna hoja trae un arbusto de
  montaña genérico. Se reutiliza el mismo arbusto de `pradera` (mismo
  archivo que `arbusto_espinoso`). Aprobado por Diego como aproximación
  provisional — sustituir en cuanto exista un sprite propio.
- **`flora_color/hierba_artica_<n>.png`**: ninguna hoja de tundra trae una
  cobertura de hierba (solo árboles/líquenes/arbustos/nieve/roca). Se
  reutiliza la hierba de `pradera`. Misma decisión, mismo criterio.
- **`criaturas_poses/lobo_andar_s.png`**: la hoja de lobo trae ciclos de
  paso reales para E (lateral) y N (espalda), pero ningún ciclo hacia
  cámara. Se usa un único frame de la pose de carrera frontal como
  aproximación — no es un ciclo de 4 frames como `andar_e`/`andar_n`.
- **`criaturas_poses/{lobo,conejo,ardilla}_herido.png`**: no hay pose de
  "herido" explícita en ninguna hoja de criatura (solo en gnomo, sentado y
  llorando). Se usa la pose de gruñido/huida sobresaltada más cercana como
  analogía — gnomo es la única especie con un sprite de herido "real".

## Huecos conocidos, no resueltos

- `flora_color/manzano_brote_<n>.png` — el cliente lo busca
  (`planta.etapa < 0.35`) pero ninguna hoja trae un manzano joven/brote
  distinguible del árbol maduro sin fruto. Sin sprite, cae al pool base
  `manzano`.
- `zorro.jpeg` / `caballo.jpeg` (en `nuevosAssetsDefinitivos/criaturas/`) —
  sin especie real en `componentes/identidad.py`, no se procesan (mismo
  criterio que la biblioteca anterior).
- `helecho` sigue con sprite aproximado (brotes genéricos de la hoja de
  bosque, no una forma de helecho real) — mismo hueco que la biblioteca
  anterior señalaba como "ningún sheet fuente tenía una forma de helecho de
  verdad", todavía cierto en esta hoja nueva.
- Ninguna de las variantes/huellas es fruto de calibración — son las
  agrupaciones que ya traían las hojas fuente, sin ajuste de cuántas
  variantes "hacen falta" por especie.
