# Orientación direccional de criaturas (componente `Orientacion`)

Fecha: 2026-09-19. Origen: la ronda de generación de assets vía PixelLab
(`docs/informe_generacion_assets_pixellab.md`) produjo, sin que se
pidiera explícitamente en el prompt, rigs de personaje con 4-8
direcciones por especie (`Idle/rotations/{norte,sur,este,oeste,...}.png`)
en vez de una única vista lateral fija. Diego decidió explícitamente
aprovechar esa direccionalidad de verdad en vez de descartarla y
quedarse con un solo frame — ver la conversación de diseño que motiva
esta spec. Esta pieza es **solo la mitad de motor**: un componente que
registra hacia dónde mira cada criatura, más la regla que lo mantiene
actualizado. La mitad de presentación (reorganizar los sprites,
seleccionar el frame en `terminal.html`, servir la nueva ruta) queda
fuera de esta spec a propósito — la implementa Claude directamente en
la sesión de diseño una vez esta pieza esté mergeada, por ser wiring de
presentación de un dato ya expuesto por el motor, no funcionalidad
nueva de simulación (ver CLAUDE.md, "Flujo de implementación").

## Diagnóstico / contexto técnico verificado

`sistemas/sistema_movimiento.py::_aplicar_movimiento` ya calcula un
vector `(dx, dy)` con `dx, dy ∈ {-1, 0, 1}` para cada desplazamiento, y
**ya permite movimiento diagonal real** (varios `_calcular_*` —
`_calcular_huida`, `_calcular_huida_erratica`, `_acercarse_a` — pueden
devolver `dx` y `dy` distintos de cero en el mismo tick). El motor ya
es, de hecho, una rejilla de 8 direcciones; simplemente no existe hoy
ningún componente que registre la orientación resultante.

Convención de ejes confirmada contra el renderizado real
(`presentacion/terminal_prototipo/terminal.html`, `cy = wy * tam`, y el
sprite lateral actual `sprites_criaturas/lobo.png`, que es un perfil
mirando hacia la derecha): `x` creciente = este, `y` creciente = sur
(igual que coordenadas de pantalla estándar, fila hacia abajo).

## Diseño

### Componente nuevo: `componentes/orientacion.py`

```python
@dataclass
class Orientacion:
    direccion: str = "este"
```

Dato puro, sin lógica, mismo patrón que `componentes/posicion.py`.
`"este"` por defecto: es la orientación que ya hornea el sprite lateral
estático de hoy, así que una criatura recién sembrada que aún no se ha
movido no cambia visualmente respecto al comportamiento actual.

Los 8 valores válidos: `"norte"`, `"sur"`, `"este"`, `"oeste"`,
`"noreste"`, `"noroeste"`, `"sureste"`, `"suroeste"`.

### Regla — no un script, aplica a cualquier entidad que se mueva

"Cuando una entidad se desplaza, su orientación pasa a la dirección
resultante de su vector de movimiento de ese tick; si no se desplaza
(`dx == 0 and dy == 0`), conserva la orientación que ya tenía." Universal
para toda entidad con `Intencion` + `Posicion` + `Orientacion`, sin
ningún caso particular por especie.

Mapeo total `(signo(dx), signo(dy)) -> direccion` (9 combinaciones,
`(0, 0)` no dispara actualización):

| dx | dy | dirección |
|---|---|---|
| +1 | 0 | este |
| -1 | 0 | oeste |
| 0 | +1 | sur |
| 0 | -1 | norte |
| +1 | +1 | sureste |
| +1 | -1 | noreste |
| -1 | +1 | suroeste |
| -1 | -1 | noroeste |

### Punto de enganche único

`sistemas/sistema_movimiento.py::_aplicar_movimiento`, en el paso 4
("Actualización atómica de coordenadas espaciales"), justo después de
`pos.x = nx; pos.y = ny`. Es el único lugar donde un desplazamiento se
confirma de verdad (antes de eso hay varios `return` tempranos por
restricciones de terreno/agua/pendiente que deben dejar la orientación
intacta si el movimiento no se llega a aplicar). Necesita recibir el
componente `Orientacion` de la entidad (o `None` si no lo tiene) igual
que ya recibe `pf: PoolFisico | None` — actualizarlo solo si no es
`None`.

### Alta al nacer

`Orientacion` se añade en `nucleo/entidad.py::crear_criatura` (mismo
sitio donde se añade `Posicion`, línea ~434), con el valor por defecto
`"este"` — no hace falta ningún sorteo ni parámetro adicional en la
llamada.

### Exposición en el DTO del visor

`presentacion/vista_web.py::construir_instantanea`, mismo patrón que el
resto de componentes opcionales del dict `dato`:

```python
orientacion = gestor.obtener_componente(eid, Orientacion)
if orientacion:
    dato["orientacion"] = orientacion.direccion
```

Insertar junto a los demás bloques `if componente: dato[...] = ...` de
esa función (después del bloque de `Intencion`/`accion` es un buen
sitio, antes de `Reproduccion`/`sexo`).

## Qué NO tocar en esta pieza

- Nada de `presentacion/terminal_prototipo/terminal.html` ni de las
  rutas HTTP de `presentacion/vista_web.py` (`ManejadorWeb`) — la
  reorganización de sprites y la selección de frame por dirección es
  presentación, se implementa aparte.
- No mover ni renombrar nada bajo `pixelLabAssetsCriaturas/` — ese
  directorio no es parte de esta pieza de motor.
- No añadir persistencia SQLite para `Orientacion` — es estado
  puramente derivado del último movimiento, se regenera solo con el
  primer paso tras cargar una partida (igual de válido que arrancar en
  `"este"` por defecto); no hace falta que sobreviva a un guardado/carga
  exacto.
- No tocar ninguna otra especie ni comportamiento existente — esta
  pieza es puramente aditiva, ningún `_calcular_*` cambia su valor de
  retorno.
- No inventar una novena dirección ni un estado "quieto" explícito — la
  ausencia de actualización (conservar la orientación anterior) ya
  cubre ese caso.

## Verificación esperada

- Tests dirigidos nuevos (`tests/test_orientacion.py` o similar):
  - Las 8 combinaciones de `(dx, dy)` mapean a la dirección correcta.
  - Una entidad con `dx=dy=0` conserva su orientación previa.
  - Un movimiento bloqueado por restricción de terreno/agua/pendiente
    (early `return` en `_aplicar_movimiento`) NO cambia la orientación.
  - Una criatura recién creada por `crear_criatura` tiene
    `Orientacion(direccion="este")`.
  - `construir_instantanea` incluye `"orientacion"` en el dict de una
    entidad que sí tiene el componente.
- Suite completa en verde, sin regresiones.
- Smoke test corto (`SIMULACION_AUTO_TICKS`, unos cientos de ticks):
  confirmar que `orientacion` en el DTO cambia de verdad para criaturas
  en movimiento activo (no se queda siempre en `"este"`).
