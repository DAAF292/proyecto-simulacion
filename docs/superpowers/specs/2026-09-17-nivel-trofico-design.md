# Nivel trófico: filtro ecológico general para depredación entre pares

Fecha: 2026-09-17. Origen: el harness completo (15×10000 ticks) mostró
a zorro (93%) y águila (100% en esta muestra) prácticamente extintos.
El círculo de "evasión por vuelo" (mismo día, anterior a este) resolvió
la parte física del problema de águila (un lobo no puede perseguir algo
que vuela), pero dejó sin resolver la pregunta que Diego hizo a
continuación: **¿es de verdad realista que lobo trate a zorro (que no
vuela) como presa garantizada?**

## Diagnóstico

Verificado contra el motor real: `magnitud_disposicion_por_peso` (la
única señal que decide si algo es presa válida) satura rápido para
diferencias de peso grandes -- lobo-vs-zorro (0.65-0.74), lobo-vs-conejo
(0.75-0.80) y lobo-vs-ardilla (0.82-0.85) quedan todos agrupados en un
rango parecido, muy por encima del umbral (0.5). La fórmula no
distingue "esto es alimento real" de "esto es un par ecológico que
rara vez se cazaría entre sí" -- ambos casos superan el umbral con
holgura.

## Por qué esto no viola el principio de leyes neutras

El proyecto no prohíbe rasgos específicos de una especie -- ya existen
varios declarados como categorías raciales (`medio_alimentacion`,
`vuela`, `tipo_refugio_fauna`), no como sucesos narrados. Lo que
prohíbe es autorear un HECHO CONCRETO ("lobo no caza zorro"). Una
categoría física declarada por especie, que alimenta una ley GENERAL
aplicable a cualquier par, es el mismo patrón exacto que `vuela` --
esta pieza sigue esa convención, no la rompe.

## Diseño

### `nivel_trofico`: nuevo rasgo racial (entero fijo, mismo patrón que `vuela`)

Con el catálogo actual, dos niveles reales:

- **0 (herbívoro)**: gnomo, conejo, ardilla, caballo, venado,
  cabra_montesa -- implícito, sin declarar (mismo criterio que
  `vuela: False` por defecto).
- **1 (depredador)**: lobo, zorro, águila -- hoy son ecológicamente
  PARES, no una jerarquía entre ellos: los tres cazan herbívoros,
  ninguno tiene un rol narrativo de cazarse mutuamente. Explícitamente
  NO se modela "lobo es ápice sobre zorro/águila" -- esa jerarquía no
  existe hoy en el catálogo, solo existiría si se diseñara a propósito.

Deja sitio explícito a fauna futura de nivel 2+ (ejemplo de Diego: un
monstruo cuyo rol narrativo SÍ sea cazar a los depredadores actuales) --
sin tocar nada de lo de arriba cuando llegue ese momento.

### La ley general -- tres casos, no uno

1. **Presa de nivel trófico ESTRICTAMENTE MENOR** que el cazador → caza
   normal, sin cambios (cualquier depredador actual cazando cualquier
   herbívoro).
2. **Presa del MISMO nivel trófico** → penalización real a la
   probabilidad de éxito (`_resolver_ataque`) -- NO un suelo absoluto:
   la competencia/caza intragremial entre pares ecológicos ocurre en la
   naturaleza (lobos sí matan zorros alguna vez, por competencia
   territorial, no como fuente de alimento habitual), solo con mucha
   menos frecuencia que la caza trófica real. Distinto criterio,
   deliberado, frente a la evasión por vuelo (ese caso SÍ fuerza el
   suelo total porque el obstáculo es físico -- perseguir algo que
   vuela -- no de comportamiento).
3. **Presa de nivel trófico MAYOR** → nunca presa válida, gateado en
   `_es_presa_valida` (el cazador ni siquiera lo intenta con éxito, con
   independencia del peso) -- prepara el terreno para el monstruo
   futuro sin tener hoy ningún efecto observable (nada tiene nivel 2
   todavía).

### Interacción con la evasión por vuelo (mismo día, círculo anterior)

Lobo-vs-águila queda cubierto DOS VECES: mismo nivel trófico (esta
pieza, penalización parcial) Y águila vuela (pieza anterior, suelo
total). No hay conflicto -- el más restrictivo domina en la práctica,
que es exactamente el resultado correcto (un ave es difícil de cazar
tanto por volar como por ser un par ecológico). Lobo-vs-zorro (ninguno
vuela) queda cubierto SOLO por esta pieza -- es la que realmente
faltaba.

### Implementación

- `SistemaDepredacion._nivel_trofico(especie: str) -> int` -- mismo
  patrón de lectura de `rangos_raciales` que `_vuela`.
- `_es_presa_valida`: nuevo gate, `nivel_trofico(presa) >
  nivel_trofico(cazador)` → `return False`, antes que el resto de
  chequeos de peso.
- `_resolver_ataque`: si `nivel_trofico(presa) == nivel_trofico(cazador)`,
  `prob_exito -= penalizacion_disposicion_mismo_nivel_trofico`, situado
  DESPUÉS de todos los bonos (arma, manada, agresividad) y ANTES del
  forzado de suelo por vuelo -- ningún bono acumulado debería poder
  compensarlo tampoco, mismo criterio que vuelo.

### Config nueva (`config/combate.yaml`, sección `depredacion`, PROVISIONAL)

- `penalizacion_disposicion_mismo_nivel_trofico: 0.35` -- elegido para
  que lobo (peor caso de disposición ~0.65-0.69 contra zorro/águila)
  quede cerca del suelo de captura sin forzarlo del todo, a diferencia
  de vuelo. Sin calibrar contra el harness completo.

## Qué NO se toca

- Ningún depredador actual cazando un herbívoro -- cae siempre en el
  caso 1, sin cambio de comportamiento.
- La evasión por vuelo (círculo anterior, mismo día) -- sigue
  aplicando sin cambios, esta pieza es ortogonal.
- `medio_alimentacion` -- se consideró reutilizarlo directamente
  (opción descartada, ver conversación) porque no distinguiría un
  futuro depredador de nivel 2 de uno de nivel 1 (ambos "cazan"); un
  entero ordinal sí lo permite sin inventar un segundo campo más
  adelante.

## Pendiente, no resuelto aquí

- Calibración del valor exacto de la penalización contra el harness
  completo -- elegido por razonamiento sobre los números de disposición
  reales, no medido en juego.
- Si algún día existe más de un nivel de "depredador de herbívoros"
  (p.ej. una distinción real entre mesodepredador y ápice dentro del
  catálogo actual), este esquema ya lo soporta sin cambios -- pero no
  se fuerza esa distinción hoy sin una razón narrativa real que la
  motive.
