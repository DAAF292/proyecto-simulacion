# Tipos de propagación de flora — viento, caída, zoocoria (pieza 2 de 4)

Fecha: 2026-09-01
Estado: aprobado por Diego (2026-09-01), pendiente de implementación

## Contexto y alcance

Segunda pieza de la cola de "poblar más el mundo" acordada en brainstorming
(1. distribución causal de flora, ya especificada en
`docs/superpowers/specs/2026-09-01-distribucion-causal-flora-design.md` y
troceada en 5 planes; **2. este documento**; 3. cupo de espacio compartido
por celda; 4. catálogo ampliado).

Hoy `sistemas/sistema_flora.py:SistemaFlora._intentar_propagacion` es un
único mecanismo ciego para las 5 especies existentes: cada día, con
probabilidad `prob_propagacion_por_dia`, una planta madura intenta
colonizar UNA celda vecina contigua elegida al azar, validada solo por
"¿el bioma es compatible y no hay agua?". Ninguna relación con cómo se
dispersa realmente una semilla -- un diente de león y una bellota se
propagan exactamente igual.

Este círculo introduce tres vectores reales -- viento, caída (gravedad,
esencialmente el mecanismo de hoy, refinado) y zoocoria (un animal come el
fruto y dispersa la semilla lejos) -- y conecta la validación del destino
a `idoneidad_colonizacion`, ya construida en la pieza 1, en vez del chequeo
tosco actual.

## Decisiones de diseño cerradas con Diego

1. **Un único vector dominante por especie**, no varios a la vez --
   declarado en `config/flora.yaml` como `tipo_propagacion: viento | caida
   | zoocoria`, catálogo cerrado de tres valores. Mismo criterio que
   `biomas` (atributo de catálogo por especie, no un rango sorteado).
2. **Asignación por especie** (PROVISIONAL, razonada, sin calibrar):
   `hierba_silvestre`, `liquen`, `musgo` -> `viento` (semilla ligera /
   reproducción por esporas); `manzano` -> `zoocoria` (fruto comestible);
   `cactus` -> `caida` (fruto pesado, cae cerca de la base).
3. **Viento reutiliza la dirección global ya existente**
   (`viento_dx`/`viento_dy`, sorteada una vez por mundo en generación,
   confirmado en la pieza 1 que se queda como constante -- viento
   dinámico/realista queda en la cola como pieza futura sin plan
   concreto). Ninguna generación de campo de viento nueva.
4. **Zoocoria reutiliza `Accion.ALIVIARSE`**, ya existente y ya sube la
   fertilidad de la celda donde se usa -- un individuo que ha comido fruto
   de una especie zoocora lleva la semilla consigo; la siguiente vez que
   hace `ALIVIARSE` (evento real, disperso en tiempo y espacio según el
   comportamiento del propio individuo, no un parámetro de alcance que
   nosotros fijemos), hay una probabilidad de que la semilla se plante
   ahí. Desacoplado del ciclo diario de `SistemaFlora` -- lo dispara el
   comportamiento del animal (COMER, luego ALIVIARSE en otro momento y
   lugar), no la planta.
5. **La validación del destino, en las tres vías, es la misma**:
   `idoneidad_colonizacion(especie_cfg, celda_destino, capacidad_retencion)
   >= umbral_minimo_idoneidad_colonizacion` (pieza 1, mismo umbral ya
   configurado) -- una semilla que llega a una celda solo prende si el
   suelo real la sostiene, sustituye el chequeo actual de "bioma
   compatible + sin agua".
6. **Corrección de paso, encontrada al diseñar esta pieza, no señalada
   antes**: `_intentar_propagacion` nunca actualizaba
   `Celda.tiene_recurso`/`Celda.tipo_recurso` al colonizar una celda en
   tiempo real (la generación inicial del mundo sí los fija; la
   colonización durante la partida, no) -- inofensivo hoy porque el
   chequeo real de "¿celda ya colonizada?" usa las entidades `Planta`
   existentes, no ese campo, pero deja el dato incoherente (relevante para
   el visor, por ejemplo). Diego confirmó corregirlo de paso, ya que las
   tres vías nuevas comparten el mismo punto de colonización.

## Diseño técnico

### 1. Catálogo -- `config/flora.yaml`

Nuevo campo `tipo_propagacion` por especie:

```yaml
hierba_silvestre: {tipo_propagacion: viento, alcance_viento_celdas: [2, 6]}
manzano:          {tipo_propagacion: zoocoria}
cactus:           {tipo_propagacion: caida}
liquen:           {tipo_propagacion: viento, alcance_viento_celdas: [1, 3]}
musgo:            {tipo_propagacion: viento, alcance_viento_celdas: [1, 3]}
```

(Notación resumida arriba solo para mostrar los pares -- en el fichero
real cada campo es una línea más dentro del bloque YAML ya existente de
cada especie.) `alcance_viento_celdas` solo se declara en especies
`viento` -- PROVISIONAL, hierba silvestre alcanza más lejos que liquen o
musgo (semilla ligera de pradera abierta frente a esporas de superficies
más resguardadas).

Nueva sección, sibling de `especies:` dentro de `flora:`:

```yaml
  probabilidad_recogida_semilla_zoocoria: 0.3
  probabilidad_plantar_semilla_en_aliviarse: 0.5
```

Ambas PROVISIONALES. La primera: probabilidad de que comer el fruto de
una especie zoocora deje una semilla "recogida". La segunda: probabilidad
de que un `ALIVIARSE` con una semilla ya recogida sea el evento que la
deposita (no cada `ALIVIARSE` disemina necesariamente la semilla concreta
que se está transportando -- mismo estilo de modelado por probabilidad
que ya usa `probabilidad_encender_fuego`, sin simular tránsito digestivo
real).

### 2. Helper compartido de colonización -- `nucleo/flora.py`

Nueva función, reutilizada por las tres vías (sustituye la lógica de
validación+creación que hoy vive solo dentro de
`sistemas/sistema_flora.py:SistemaFlora._intentar_propagacion`):

```python
def intentar_colonizar_celda(
    gestor: GestorEntidades,
    celda_dest: Celda,
    capacidad_retencion: float,
    especie: str,
    especie_cfg: dict[str, Any],
    umbral_minimo: float,
    nx: int,
    ny: int,
    zona_idx: int,
) -> bool:
```

A diferencia de `idoneidad_colonizacion` en la generación inicial (pieza
1, donde había que construir una `Celda` parcial porque el grid todavía no
existía), aquí la `Celda` real del destino ya existe con todos sus campos
reales -- se le pasa directamente, sin construir nada temporal. Devuelve
`False` sin tocar nada si `celda_dest.tiene_recurso` ya es `True` (celda
ocupada) o si la idoneidad no llega al umbral; si coloniza, además de
crear la entidad `Planta` dejará `celda_dest.tiene_recurso = True` y
`celda_dest.tipo_recurso = especie` (la corrección de la Decisión 6),
inicializando `celda_dest.recursos` igual que hace hoy
`_intentar_propagacion`. Import diferido de `crear_planta` desde
`nucleo.entidad` (confirmado sin ciclo de imports: `nucleo/entidad.py` no
importa `nucleo/flora.py`).

### 3. Caída -- ajuste de `_intentar_propagacion`

**Corrección de ubicación (autorrevisión de este documento, 2026-09-01):
`_intentar_propagacion` NO vive en `nucleo/zona_bioma.py` -- es un método
de la clase `SistemaFlora`, definido en `sistemas/sistema_flora.py`. Ese
módulo (`nucleo/zona_bioma.py`) solo contiene `_generar_manchas` (el
algoritmo de manchas, hoy usado solo para vetas de mineral tras la pieza
1) y el helper `vecinos()` -- funciones distintas, sin relación con la
propagación de flora en tiempo real.**

`sistemas/sistema_flora.py:SistemaFlora._intentar_propagacion` conserva
su algoritmo de selección de celda (vecino contiguo al azar, sin cambios)
pero sustituye su validación actual (`celda_dest.tipo_terreno in
biomas_compatibles and not celda_dest.tiene_agua`) por una llamada a
`nucleo.flora.intentar_colonizar_celda` (importada en
`sistemas/sistema_flora.py`, junto a `crear_planta`/`recursos_alimento`,
ya importadas de `nucleo.entidad`/`nucleo.flora` respectivamente en ese
fichero). Es la única vía de propagación en tiempo real para especies
`caida` -- la generación inicial del mundo (pieza 1) no la usa en
absoluto, usa `colonizar_por_idoneidad` directamente.

### 4. Viento -- nuevo método `_propagar_viento`

Nuevo método de `SistemaFlora`, en `sistemas/sistema_flora.py`, junto a
`_intentar_propagacion` (mismo fichero, misma clase -- comparten
`self.rng` y el resto de estado de la instancia). Firma análoga a
`_intentar_propagacion`, con `viento_dx`/`viento_dy`/`alcance_min`/
`alcance_max` como argumentos adicionales:

- Sortea una distancia `d` en `[alcance_min, alcance_max]`.
- Candidata única: `(origen_x + viento_dx * d, origen_y + viento_dy * d)`,
  descartada si cae fuera del grid.
- Si la candidata es válida (biomas compatibles -- mismo filtro grueso
  previo que ya usa caída) y `intentar_colonizar_celda` prospera, listo;
  si no, no se reintenta ese día (mismo criterio de "un intento por
  planta por día" que ya rige `_intentar_propagacion`).

### 5. Dispatch por `tipo_propagacion` -- `sistema_flora.py`

`_ejecutar_zona`, en el bloque de propagación (tras el chequeo de
`prob_propagacion_por_dia`), pasa de llamar siempre a
`_intentar_propagacion` a leer `cfg_esp["tipo_propagacion"]`:

- `caida` -> `_intentar_propagacion` (sin cambios de firma).
- `viento` -> `_propagar_viento`, con `viento_dx`/`viento_dy` leídos de
  `zona.viento_dx`/`zona.viento_dy` (nuevos atributos de `ZonaBioma`,
  confirmado que hoy son variables puramente locales dentro de
  `generar_zona_bioma` -- se pierden al terminar la generación, ningún
  sitio los guarda). `ZonaBioma.__init__` gana `viento_dx: int = 0,
  viento_dy: int = 0`, junto a `clima_actual` (mismo objeto que ya lleva
  el otro estado de la zona); `generar_zona_bioma` los pasa al construir
  el `ZonaBioma` final en vez de dejarlos caer. Por construcción, cada
  zona sortea su PROPIO viento hoy (`sortear_viento_dominante` se llama
  una vez por invocación de `generar_zona_bioma`, y `nucleo/cueva.py`
  no genera ninguno -- las cuevas no tienen clima propio, ver spec de la
  pieza 1) -- correcto para este círculo, ya que la única zona con flora
  hoy es la superficie.
- `zoocoria` -> no se intenta nada aquí, `continue` -- su propagación no
  está gobernada por el ciclo diario de la planta.

### 6. Zoocoria -- componente `Semillas` + hooks

`componentes/semillas.py` (nuevo): `Semillas.especie_transportada: str =
""`. Añadido a las CUATRO especies por igual en `crear_criatura` Y
`nacer_criatura` (mismo patrón -- y misma advertencia -- que `Agarre`:
dos fábricas ECS separadas, hay que tocar ambas).

`sistemas/sistema_recursos.py:_resolver_comer`, tras la transferencia
nutricional exitosa del bloque de forrajeo vegetal (2. Evaluación de
Forrajeo Vegetal): si `celda.tipo_recurso` tiene
`tipo_propagacion == "zoocoria"` en el catálogo, el individuo no lleva ya
una semilla (`semillas.especie_transportada == ""`), y supera
`probabilidad_recogida_semilla_zoocoria`, fija
`semillas.especie_transportada = celda.tipo_recurso`.

`sistemas/sistema_recursos.py:_resolver_aliviarse`, extendida (gana
`gestor`, `entidad_id`, `pos_x`, `pos_y`, `zona_idx` como parámetros, para
poder consultar `Semillas` y crear una `Planta`): tras el bono de
fertilidad ya existente, si `semillas.especie_transportada` no está vacío
y supera `probabilidad_plantar_semilla_en_aliviarse`, intenta
`intentar_colonizar_celda` en la celda actual con esa especie; se limpia
`semillas.especie_transportada = ""` en cualquier caso (éxito o fallo de
idoneidad) -- la semilla se deposita igual, prenda o no.

### 7. Persistencia

`Semillas.especie_transportada` se persiste (columna `semillas` en
`componentes_estado`, mismo criterio que `Agarre.objetos` -- perderla al
recargar sería una regresión silenciosa, no un campo transitorio
inofensivo). `VERSION_ESQUEMA` sube de `"0.30-fase0"` a `"0.31-fase0"`
(DROP-and-recreate, mismo criterio ya establecido en todo el proyecto).

## Fuera de alcance (explícito)

- Viento dinámico/realista (afectado por relieve o vegetación local) --
  confirmado en la pieza 1 como pieza futura sin plan concreto, sigue
  igual aquí.
- Cupo de espacio compartido por celda (pieza 3 de la cola) y catálogo
  ampliado (pieza 4) -- ninguno tocado aquí.
- Varios vectores a la vez por especie.
- Propagación de flora en cuevas -- `nucleo/cueva.py` sigue sin flora,
  límite conocido preexistente, no tocado.
- Calibrar `alcance_viento_celdas`,
  `probabilidad_recogida_semilla_zoocoria`,
  `probabilidad_plantar_semilla_en_aliviarse` contra el harness completo.

## Verificación planeada

1. Arnés dirigido: `intentar_colonizar_celda` (celda ya ocupada -> False
   sin tocar nada; idoneidad insuficiente -> False; éxito -> Planta
   creada + `tiene_recurso`/`tipo_recurso` coherentes); `_propagar_viento`
   (distancia dentro del rango configurado, dirección correcta, fuera de
   grid -> sin efecto); dispatch por `tipo_propagacion` (una especie
   `zoocoria` nunca dispara `_intentar_propagacion`/`_propagar_viento`
   desde el ciclo diario); zoocoria completa (COMER fruto zoocora ->
   `Semillas` se llena; `ALIVIARSE` con semilla -> intento de
   colonización en la celda actual, `Semillas` se vacía después).
2. Roundtrip de persistencia de `Semillas.especie_transportada`.
3. Varias semillas de generación + `BOSQUE_AUTO_TICKS` sin intervención,
   confirmando en juego real: manzanos dispersados por zoocoria de
   verdad (no solo en el arnés), hierba/liquen/musgo con manchas que
   siguen la dirección del viento del mundo, cactus con propagación de
   corto alcance como antes.
4. Suite de tests existente (22 + los añadidos por la pieza 1) en verde.

## Pendiente explícito tras este círculo

- Las tres constantes numéricas nuevas y `umbrales`/`alcances`
  PROVISIONALES, sin calibrar.
- Piezas 3 (cupo de espacio) y 4 (catálogo ampliado) de la cola, sin
  empezar.
