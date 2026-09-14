# Minería real -- diseño (2026-09-12)

## Contexto y motivación

Diego, al plantear cómo desarrollar el arco de asentamientos/profesiones,
corrigió una afirmación mía: "minería ya existe" era falso en el sentido
que importa. Lo que existe desde el arco de profundidad geológica
(2026-08-30) es la parte GEOLÓGICA (vetas finitas, `masa_mineral_restante`,
generación real) -- pero la ACCIÓN de extraerlas es literalmente la misma
`RECOLECTAR` genérica que agarra una rama caída del suelo, sin ningún
requisito de herramienta. Verificado contra el código
(`sistema_recursos.py:780`, antes de este círculo): el gate era `if
celda.deposito_mineral and celda.masa_mineral_restante > 0.0:`, sin
ninguna comprobación de herramienta.

Diego: "para minar realmente hacen falta herramientas, picos por ejemplo
y así. [...] con una rama y una piedra podemos hacer un martillo, pero
para hacer un edificio necesitamos tablas de madera, losas de piedra".
Distinción real: recoger lo que ya está suelto (rama, piedra_suelta) no
exige herramienta; producir de verdad (extraer una veta) sí.

Círculo 1 de una secuencia de tres acordada con Diego: minería real
(este) → tala real (destruye una `Planta`, círculo aparte, mayor alcance)
→ agricultura/ganadería (arco propio, grande, aparcado).

## Diseño

**Un pico fabricado gatea la extracción de veta.** Reutiliza el 100% de
la infraestructura ya construida en "fabricación de herramientas"
(2026-09-11): `Accion.FABRICAR`, el resolutor `candidatos_fabricar`
(`sistema_decision.py`), `mejor_receta_completable`/`tiene_herramienta`
(`nucleo/armas.py`/`nucleo/herramientas.py`), `_via_material_crudo`
(gathering de madera/piedra crudos). Cero mecanismo nuevo -- solo una
tercera categoría FABRICAR ("mineria") y un gate nuevo en la extracción.

**Catálogo de recetas SEPARADO** (`config/herramientas.yaml:
recetas_mineria`, distinto de `recetas`): `pico` reutiliza los mismos
materiales crudos que `hacha_primitiva` (madera+piedra) -- pero al vivir
en un catálogo distinto, `mejor_receta_completable` nunca tiene que
elegir entre pico y hacha_primitiva con el mismo inventario (cada
categoría FABRICAR resuelve solo contra su propio catálogo). Alternativa
descartada: diferenciar materiales para evitar la ambigüedad -- no
funciona, `mejor_receta_completable` usa `set(objetos)` (sin conteo), así
que "2x piedra" no se puede exigir con el mecanismo actual.

**Motivo causal de FABRICAR-mineria**: mismo patrón exacto que
"herramienta" (utilidad = `necesidad_trabajo` = `max(utilidad_recolectar,
utilidad_construir)`, SIN descuento -- un descuento deja a la categoría
incapaz de ganarle nunca a la necesidad que la origina, mismo error ya
evitado con "arma"/"herramienta"), pero con un disparador MÁS ESPECÍFICO:
solo se activa si la celda actual tiene de verdad una veta sin explotar
(`celda.deposito_mineral` con masa restante) -- no "necesito trabajar" en
abstracto. Un individuo que nunca ha estado junto a una veta sin pico
nunca desarrolla interés en fabricar uno (principio 5, leyes neutras).

**RECOLECTAR hereda el motivo de mineria** para juntar madera/piedra
crudos, mismo eslabón que ya usan arma/herramienta -- nuevo flag
`Intencion.recolectar_motivo_mineria`, extendiendo el resolutor de
precedencia ya corregido ayer ("prioridad consciente") a CUATRO
eslabones: fuego > arma > herramienta > mineria (empate exacto resuelto
por el primero comprobado, mismo criterio ya usado). Vía 4 en
`_resolver_recolectar`, comparte `_via_material_crudo` con Vía 2/3.

**Gate de extracción**: `celda.deposito_mineral` con masa restante ahora
exige `tiene_herramienta(objetos_totales, recetas_mineria)`. Sin pico, la
extracción de veta se SALTA (no se interrumpe la resolución) y cae al
siguiente nivel de prioridad ya existente (material de flora, luego
`tipo_sustrato`) -- un consciente sin pico junto a una veta sigue
recolectando lo que sí puede, no se queda parado.

**Deliberadamente fuera de este círculo**: el pico NO se suma al bono
genérico de velocidad de recolección/construcción
(`factor_bono_tasa_recolectar_con_herramienta`) que ya da
`hacha_primitiva` -- su único efecto es destrabar la extracción de veta,
sin inventar un segundo efecto no pedido. `tipo_sustrato` (piedra/arcilla/
tierra a granel) sigue sin gate, igual que antes -- la distinción de
Diego es sobre vetas de mineral real, no sobre el terreno base.

## Verificación planeada

- Tests de ley: gate de extracción sin pico salta a sustrato; con pico
  extrae; FABRICAR-mineria produce `pico` real; motivo de mineria no
  intercepta madera/piedra motivados por arma/herramienta (regresión del
  mismo bug corregido ayer, aplicado al cuarto eslabón); precedencia
  correcta en empate.
- `BOSQUE_AUTO_TICKS` con la semilla por defecto: contadores nuevos
  (`_stats_picos_fabricados`, `_stats_veta_bloqueada_sin_pico`) para
  confirmar que el mecanismo se ejerce en juego libre, no solo en tests
  dirigidos.
- Roundtrip de persistencia sin excepciones (aunque `recetas_mineria` no
  añade estado nuevo persistido -- `pico` viaja en `Inventario.objetos`,
  mismo campo JSON ya existente).
