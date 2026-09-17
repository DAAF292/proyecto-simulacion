# Influencia de liderazgo: arrastre de carácter + rebelión por disonancia

Fecha: 2026-09-17. Tercer círculo de la sesión, tema "líder — cómo
plantear la influencia del líder o consejo en una población" de la lista
original. Diseñado en conversación con Diego.

## Motivación

El liderazgo ya construido (`calcular_liderazgo`, `nucleo/asentamiento.py`)
es una ETIQUETA: decide quién lidera por composición de temperamento,
alimenta lealtad y rumor, pero nunca gobierna nada de verdad -- el
temperamento del líder no tiene ningún efecto sobre el comportamiento del
resto del pueblo. Diego: quiere que el temperamento del líder mueva al
pueblo (ejemplo: un poblado pacífico con un líder agresivo y dominante
que lo incite hacia el conflicto), pero de forma NO determinante -- si la
disonancia entre el líder y el carácter del pueblo es demasiado alta,
este debe poder "revelarse" en la medida de lo posible.

## Decisión de diseño: sin agregado de "pueblo", todo por individuo

Se descartó explícitamente comparar el líder contra un "temperamento
medio del pueblo" calculado de forma centralizada -- cada seguidor
calcula su propia distancia de carácter frente al líder, y arrastre/
resistencia se resuelven individuo a individuo. El patrón agregado
("pueblo pacífico resiste a líder agresivo") emerge de la suma de
reacciones individuales, sin necesitar ningún promedio impuesto desde
arriba -- más fiel al principio de leyes neutras que un cálculo
centralizado.

## Límite real reconocido, no resuelto aquí

El ejemplo de partida de Diego ("incite a conquistar y luchar") no tiene
destino mecánico hoy: no existe ninguna interacción entre asentamientos
distintos en el motor (verificado en el primer círculo de esta sesión,
sigue siendo cierto). El arrastre de este círculo se aplica solo a los
ejes que SÍ tienen consumidor real hoy: `disposicion_a_aportar` y el
`sesgo_prosocial` de la elección mejora-propia-vs-comunal. "Incitar a la
guerra" queda pendiente de que exista interacción entre pueblos (mismo
tipo de dependencia que ya bloqueaba "explorar" en el círculo de
satisfacción de vivienda).

## Diseño

### `distancia_caracter(t_a, t_b)` (`nucleo/asentamiento.py`)

Distancia euclídea normalizada a [0,1] sobre los tres ejes de carácter
cívico que ya deciden gobierno (`empatía`, `lealtad`, `agresividad` --
mismos que `disposicion_a_aportar`; `dominancia` queda fuera, por el
mismo motivo que ya la excluye esa función: decide quién lidera, no
cuánto se comparte).

### `temperamento_efectivo_por_liderazgo(...)` (`nucleo/asentamiento.py`)

Dado un seguidor y el `Asentamiento` al que pertenece, devuelve una
COPIA de su `Temperamento` con `empatía/lealtad/agresividad`
interpolados hacia el (promedio de, si hay consejo) líder(es) -- NO
sustituye el rasgo real en ningún otro sitio del motor (crisis mental,
depredación, `SOCIALIZAR` siguen leyendo `Temperamento` sin modular).

```
dist = distancia_caracter(seguidor, lider_promedio)
factor = 0                                                    si dist >= umbral_disonancia_liderazgo
factor = peso_max_arrastre * (1 - dist/umbral) * lealtad_hacia_lider   si no
rasgo_efectivo = rasgo_propio + factor * (rasgo_lider - rasgo_propio)
```

`lealtad_hacia_lider`: afinidad ya acumulada en `Relaciones.vinculos`
hacia el/los líder(es), 0.0 sin vínculo (mismo criterio que la
reputación neutra de `calcular_liderazgo`). Un líder nunca se arrastra
a sí mismo (`id_seguidor in asen.lideres` devuelve el temperamento sin
modular).

Consumido en `sistema_decision.py` (3 puntos, temperamento_prosocial
calculado una vez por individuo por tick, reutilizado): los gates de
`almacen`/`cocina` (`disposicion_a_aportar`), `sesgo_prosocial` (solo
vía empatía -- sociabilidad, el otro término de esa fórmula, no se
contagia), y `_compromiso_construir_mantiene` (misma re-verificación
diaria de disposición).

### Erosión de lealtad por disonancia (`_acrecion_lealtad_liderazgo`,
`sistema_asentamiento.py`)

Hasta hoy el delta diario de lealtad miembro→líder era incondicionalmente
positivo. Ahora:

```
si dist(miembro, líder) < umbral_disonancia_liderazgo: delta = delta_base (sin cambios)
si no: delta = -delta_erosion_lealtad_liderazgo * (dist - umbral) / (1 - umbral)
```

Esta es la "rebelión": ningún mecanismo nuevo, solo una señal nueva
alimentando dos piezas YA EXISTENTES -- la lealtad puede caer en vez de
solo subir, y si cae lo bastante bajo `umbral_reputacion_descalificante`
(`calcular_liderazgo`, sin tocar), el líder queda descalificado en el
próximo recálculo diario. El techo de la rebelión en este círculo es
"pierde el puesto" -- fractura del asentamiento o éxodo de miembros
queda deliberadamente fuera (decisión de Diego).

## Config nueva (todas PROVISIONALES)

- `config/comportamiento.yaml`, sección `asentamiento`:
  `umbral_disonancia_liderazgo: 0.5`, `peso_max_arrastre_liderazgo: 0.5`.
- `config/relaciones.yaml`, sección `relaciones`:
  `delta_erosion_lealtad_liderazgo: 0.03` (mismo valor que
  `delta_lealtad_liderazgo` por defecto, simetría como hipótesis de
  partida).
