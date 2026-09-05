# Parejas fundadoras en la siembra de población inicial

Fecha: 2026-09-06
Estado: aprobado por Diego en brainstorming, pendiente de encargo al pipeline.

## Contexto y motivación

Sesión de investigación de fragilidad de población (2026-09-05/06, ver
`CLAUDE.md`, secciones "Fragilidad de lobo" y las que le siguen) probó
exhaustivamente contra el motor real (decenas de corridas de 8000 ticks
sobre semillas nuevas) varias palancas tácticas para estabilizar la
población fundadora: reducir la muerte por hambre universal a la mitad,
subir la población fundadora x1.5, subir la tasa de concepción propia de
ardilla, y agrupar a los fundadores en grupos de 4 cerca entre sí.
**Ninguna funcionó de forma limpia** -- varias empeoraron otras especies
al aplicarlas (más presión de competencia sin compensación real).

Hallazgo real que explica por qué: medido directamente en la siembra
fundadora (sin ningún tick transcurrido), la distancia media al
conespecífico de sexo opuesto más cercano es de 5.4-9.9 celdas (gnomo),
11.5-18.8 celdas (lobo), 3.4-4.9 celdas (ardilla) -- casi cero contactos
inmediatos (misma celda, el requisito exacto que exige la concepción,
ver `sistemas/sistema_reproduccion.py:_macho_elegible_en_contacto`).
Toda la población fundadora depende enteramente del sesgo gregario de
deambular para cerrar esa distancia, mientras compite contra el riesgo
combinado (inanición, vejez, depredación) desde el segundo cero.

Diagnóstico compartido con Diego, confirmado en brainstorming: el
problema de fondo es una carrera entre "tiempo hasta el primer contacto
reproductivo viable" y "tiempo hasta que el riesgo acumulado mate al
fundador" -- ninguna palanca que solo toque la magnitud del riesgo o el
volumen de población cambia esa carrera si la distancia de partida sigue
siendo grande.

## Objetivo de este círculo

Reducir la distancia de partida a cero para una fracción de la población
fundadora, sembrándola como **parejas** (un macho y una hembra en la
misma celda desde el tick 0) en vez de individuos completamente
independientes. Deliberadamente el círculo más pequeño y barato de
verificar de los tres enfoques discutidos en brainstorming (los otros
dos -- ventana de resiliencia temprana en el modelo de mortalidad,
búsqueda activa de pareja más fuerte en movimiento -- quedan aparcados
como candidatos de un segundo círculo si este no basta).

Criterio de éxito acordado con Diego: ninguna de las 5 especies
fundadoras (gnomo, lobo, conejo, ardilla, caballo) debería extinguirse
en la mayoría de semillas nuevas -- hoy ardilla se extingue en el 100%
de las semillas probadas (84/84 en la sesión de investigación), y
gnomo/lobo/caballo entre el 58% y el 92% según la configuración.

## Diseño

### `nucleo/entidad.py:crear_criatura`

Gana un parámetro opcional nuevo, al final de la firma para no romper
ningún llamador existente:

```python
def crear_criatura(
    gestor: GestorEntidades,
    especie: Especie,
    pos_x: int,
    pos_y: int,
    config: dict[str, Any],
    rng: random.Random,
    tick_actual: int = 0,
    nombre: str | None = None,
    techo_fraccion_edad_inicial: float = 0.0,
    zona_idx: int = 0,
    sexo_forzado: Sexo | None = None,
) -> int:
```

Dentro de la función, la línea actual:

```python
sexo = rng.choice([Sexo.MACHO, Sexo.HEMBRA])
```

pasa a:

```python
sexo = sexo_forzado if sexo_forzado is not None else rng.choice([Sexo.MACHO, Sexo.HEMBRA])
```

Sin `sexo_forzado` (todo llamador existente: nacimientos reales durante
la partida vía `nacer_criatura`, y cualquier otro uso de `crear_criatura`
que no lo pase explícitamente), el comportamiento es idéntico al actual
-- bit a bit, sin ningún cambio de secuencia de `rng` para esos casos
(la propia línea de sorteo sigue ejecutándose igual, solo cambia el
resultado cuando el llamador fuerza un valor).

### `main.py:sembrar_poblacion_inicial`

El bucle actual, por cada especie:

```python
for _ in range(cantidad):
    pos_x, pos_y = rng_juego.choice(celdas_candidatas)
    eid = crear_criatura(gestor, especie, pos_x, pos_y, config, rng_juego, ...)
    ...
```

pasa a formar parejas explícitas. Por cada especie con `cantidad`
fundadores:

- `cantidad // 2` **parejas**: por cada una, sortear UNA celda con
  `rng_juego.choice(celdas_candidatas)` (mismo mecanismo de elección de
  celda que hoy, sin cambios), y llamar a `crear_criatura` DOS veces con
  esa misma `(pos_x, pos_y)` -- una con `sexo_forzado=Sexo.MACHO`, otra
  con `sexo_forzado=Sexo.HEMBRA`.
- Si `cantidad` es impar, el individuo sobrante se siembra exactamente
  como hoy: celda propia sorteada de forma independiente, sexo sin
  forzar (`sexo_forzado=None`) -- no hay con quién emparejarlo.

Cada llamada a `crear_criatura` sigue sorteando su propia edad inicial
por separado (`_sortear_edad_inicial_ticks`, sin cambios) -- los dos
miembros de una pareja pueden acabar con edades muy distintas entre sí,
variación real, no un caso a evitar.

El resto de la función (registro en `persistencia.registrar_entidad_nueva`,
manejo de `celdas_candidatas` vacías, etc.) no cambia.

### Alcance

Dos ficheros tocados (`nucleo/entidad.py`, `main.py`). Ningún otro
sistema del motor (reproducción, movimiento, decisión, necesidades) se
modifica -- el cambio es exclusivamente sobre CÓMO nace la población
fundadora en tick 0, no sobre ninguna regla que rija el resto de la
partida. Aplica por igual a las 5 especies (gnomo, lobo, conejo,
ardilla, caballo) -- ley general de cómo se funda cualquier población,
no una excepción para una especie concreta (principio de leyes
neutras).

## Qué NO cubre este círculo (aparcado, no descartado)

- Ventana de resiliencia temprana en el modelo de mortalidad (Enfoque B
  discutido en brainstorming).
- Búsqueda activa de pareja más fuerte, más allá del sesgo gregario
  genérico (Enfoque C).
- Cualquier ajuste de `techo_fraccion_edad_inicial_longevidad`,
  `factor_base_concepcion` u otras tasas ya investigadas hoy -- este
  círculo no toca ningún valor numérico, solo la disposición espacial
  de la siembra.
- Nacimientos posteriores a la siembra fundadora (`nacer_criatura`,
  `sistemas/sistema_reproduccion.py`) -- sin cambios, siguen naciendo en
  la posición de la madre en el momento del parto, como siempre.

## Riesgo conocido a vigilar en la verificación

El intento de agrupamiento probado hoy (grupos de 4 fundadores de la
misma especie cerca entre sí, sin garantizar sexo opuesto adyacente)
empeoró a gnomo y lobo -- hipótesis no confirmada del todo: concentrar
individuos de la misma especie concentra también la demanda de comida
local, acelerando el agotamiento del parche justo donde más se necesita.
Una pareja son solo 2 individuos compartiendo una celda (frente a 4 del
intento anterior) -- footprint mucho menor, pero la verificación contra
el motor real debe confirmar explícitamente que este riesgo no se
reproduce, no asumir que "menos" basta.

## Verificación

**Obligatoria, ligera** (respeta el ritmo de la sesión -- Diego pidió
explícitamente no lanzar baterías largas): `BOSQUE_AUTO_TICKS=3000` sin
intervención, sin ninguna excepción -- prueba de humo estándar del
proyecto. Además, una comparación dirigida y pequeña: 5 semillas NUEVAS
(nunca usadas en la investigación de hoy) × 4000 ticks, midiendo
población final y extinción por especie, contra la MISMA config sin el
cambio (mismo criterio metodológico del proyecto: comparar distribuciones
sobre semillas nuevas, no pares puntuales de la misma semilla antes/
después, porque este cambio desplaza la secuencia de `rng_juego` que
consume el resto del motor). No hace falta más resolución que esta para
confirmar la dirección del efecto -- si el resultado es prometedor pero
ambiguo, señalarlo como tal en vez de lanzar una batería mayor sin
consultarlo antes.

216/216 tests (cifra real a fecha de este spec) deben seguir en verde --
ningún test existente asume el orden ni el sexo de los fundadores
creados por `sembrar_poblacion_inicial`, pero conviene confirmarlo, no
darlo por hecho.

## Pendiente real, explícito

Este círculo puede no bastar por sí solo -- si la verificación dirigida
muestra una mejora real pero insuficiente (alguna especie sigue
extinguiéndose en la mayoría de semillas), los Enfoques B y C quedan
como candidatos directos del siguiente círculo, no como una señal de que
este círculo esté mal diseñado. Todas las tasas/umbrales tocados en la
investigación previa de hoy (saciedad de lobo, concepción de lobo,
`techo_fraccion_edad_inicial_longevidad`) siguen PROVISIONALES, sin
relación con este cambio.
