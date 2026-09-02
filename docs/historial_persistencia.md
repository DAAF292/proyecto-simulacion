# Historial de diseño — `nucleo/persistencia.py`

Extraído de los comentarios en línea el 2026-09-02 (ver CLAUDE.md,
sección "Comentarios técnicos vs narrativa histórica"). Este módulo es
el más sensible del proyecto a un mal recorte -- SQL, orden de tuplas e
índices posicionales de columna (`fila[N]`) son la conexión real entre
guardar y cargar, así que aquí solo se movió texto narrativo puro; nada
del código, ni una coma de las explicaciones de índices, se tocó.

## `Persistencia` (clase) — versionado de esquema

`CREATE TABLE IF NOT EXISTS` nunca migra columnas: si el esquema
relacional cambia (una columna nueva, un tipo distinto), una base de
datos ya existente se queda con el esquema VIEJO para siempre, y
cualquier INSERT/SELECT nuevo revienta en tiempo de ejecución. Antes de
crear las tablas, se compara `VERSION_ESQUEMA` contra la guardada; si no
coincide, se hace DROP explícito de las siete tablas y se recrean desde
cero -- aceptable en esta fase del proyecto (todavía sin campañas reales
que conservar entre versiones de esquema). Verificado en su momento con
`PRAGMA table_info` contra un `datos/bosque.db` real que llevaba varios
días de desfase.

## `_serializar_snapshot_padre`

Esta función y su inversa (`_reconstruir_gestacion`) reemplazaron un
guardado/carga que leía/escribía `gest.padre_id` y `gest.padre_snapshot`
-- campos que `Gestacion` nunca tuvo en su forma actual (ver
`componentes/gestacion.py`: es `id_padre`, y en vez de un único snapshot
genérico tiene cuatro campos tipados más `tamano_camada`). Nunca se
detectó en producción porque `main.py` no invocaba
`guardar_snapshot`/`cargar_snapshot` -- se encontró auditando el código,
no por una excepción real.

## `marcar_entidad_muerta`

Fix aislado (2026-09-02, ver commit correspondiente): antes de este fix,
toda entidad quedaba marcada `viva=True` para siempre en la tabla
histórica una vez creada -- el snapshot en vivo (`componentes_estado`)
sí reflejaba correctamente quién seguía vivo, pero el registro histórico
permanente mentía.

## `guardar_snapshot` / `cargar_snapshot` — `semilla`

(2026-08-23) La semilla de generación de mundo nunca se persistía --
`cargar_snapshot` solo restauraba el estado DINÁMICO de celda
(fertilidad, charcos, fuego, recursos); el TERRENO en sí (tipo de bioma,
elevación) lo regenera `Mundo()` a partir de la semilla de config en
cada arranque. Si esa semilla cambiaba entre guardar y cargar, el
terreno regenerado no coincidía con el que produjo el estado dinámico
guardado, y eso pasaba en silencio. Guardar la semilla permite que
`cargar_snapshot` lo detecte y avise por stderr en vez de fallar en
silencio o bloquear la carga -- no hay overhead de UI de por medio
(`nucleo/` no importa nada de `presentacion/`) y un guardado antiguo
sigue siendo mejor que ninguno, incluso si el terreno ya no encaja.

## `cargar_snapshot` — `Reloj.tick_actual`

`Reloj.tick_actual` es un atributo de instancia plano fijado en
`__init__` (`nucleo/reloj.py`), NO una property respaldada por
`_tick_actual` -- escribir en `reloj._tick_actual` creaba un atributo
nuevo sin efecto real, dejando el reloj congelado en tick 0 tras cada
carga aunque `cargar_snapshot` devolviera `True`. Bug preexistente,
detectado al probar el roundtrip guardar/cargar por primera vez (nunca
se había ejecutado antes porque `main.py` no llamaba a
`cargar_snapshot`).

## `cargar_snapshot` — celdas, `deposito_mineral`/`masa_mineral_restante`

(2026-08-30, círculo 2 de profundidad) `deposito_mineral`/
`masa_mineral_restante` pasaron a ser estado mutable de la partida (una
veta agotada por `Accion.RECOLECTAR`), no puramente derivable de la
semilla -- se restauran igual que fertilidad/profundidad_charco.

## `cargar_snapshot` — celdas, `tiene_recurso`/`tipo_recurso`

(2026-08-23) `tiene_recurso`/`tipo_recurso` tienen su propio docstring
en `nucleo/celda.py` afirmando "sí se persiste" -- hasta ese momento no
había columnas para ellos y se perdían en cada carga, quedando siempre
en su valor por defecto (`False`/`""`), inconsistente con
`celda.recursos` ya restaurado. Sin consumidor real en ese momento
(ningún sistema los leía), así que no cambiaba el comportamiento
observable -- pero era la promesa documentada la que pasó a cumplirse.

## `cargar_snapshot` — entidades biológicas, índices de `fila`

`zona_idx` (2026-08-30, círculo 1 de profundidad) se añadió como última
columna de `componentes_estado` en su momento -- `fila[47]`. `agarre`
(2026-08-31, ver `componentes/agarre.py`) se añadió después de
`zona_idx`, como `fila[48]` -- desplazó en +1 los índices
`e.especie`..`e.id_padre` de más abajo (antes `fila[48]`..`fila[52]`,
ahora `fila[49]`..`fila[53]`), sin cambiar ninguno de los índices
anteriores (0..47, incluida la instantánea de gestación).
