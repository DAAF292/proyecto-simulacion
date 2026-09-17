# Colonización espontánea: segunda oportunidad para especies en apuros

Fecha: 2026-09-17. Origen: el harness completo (15×10000 ticks) mostró
a zorro (93%) y águila (100% en la muestra) prácticamente extintos, con
funnels reproductivos sanos (168%/306% en su momento) truncados por un
colapso tardío sin ninguna vía de recuperación. Diego lo señaló de
forma más general: *"la población fundadora es la única oportunidad...
quizás deberíamos implantar una norma de cierta aleatoriedad que genere
de imprevisto una pareja de una raza"*.

## Diagnóstico

La población fundadora (`main.py::sembrar_poblacion_inicial`) es hoy
la ÚNICA vía de entrada de cualquier especie al mundo. Si un mal golpe
de suerte la extingue antes de establecerse (o mucho después, por
deriva estocástica), esa especie queda muerta para siempre en esa
partida -- sin inmigración, sin recolonización, sin ninguna segunda
oportunidad. En un ecosistema real esto no pasa: la dispersión/
inmigración es un proceso continuo, no un único evento fundacional.

## Diseño

### Ley general, no un guión

Cada día (mismo bloque de cadencia que clima/flora/desastres/
asentamiento/manada en `main.py`), para CUALQUIER especie cuya
población viva en el territorio caiga por debajo de un umbral crítico
(`umbral_poblacion_critica`, 2 -- sin pareja viable ya), se sortea una
probabilidad diaria muy baja de que aparezca una pareja nueva en una
celda de bioma compatible con esa especie.

**Deliberadamente restringido a especies en apuros**, no aplicado
indiscriminadamente a cualquier especie en cualquier momento -- se
consideró y se descartó la alternativa "cualquier especie, cualquier
momento" por ser un respawn disfrazado sin relación con el problema
real (especies que colapsan sin vía de recuperación), no una ley de
colonización de verdad. Condicionarlo a "está realmente en apuros"
mantiene la generalidad (no autorea qué especie ni cuándo) sin
convertirse en un parche universal.

### `sistemas/sistema_colonizacion.py::SistemaColonizacion`

- `BIOMAS_POR_ESPECIE`: conjunto (no cascada de fallback) de biomas
  compatibles por especie -- deliberadamente MÁS SIMPLE que el reparto
  con prioridad en cascada de `sembrar_poblacion_inicial` (bosque→
  pradera si no hay bosque, etc.): aquí solo hace falta encontrar UNA
  celda candidata, no repartir una población fundadora completa.
- `ejecutar(gestor, mundo, reloj, bus_eventos)`: cuenta población viva
  real por especie (`gestor.entidades_con(Identidad)`, mismo criterio
  que ya usa `herramientas/harness_calibracion.py::_contar_poblacion`);
  para cada especie bajo el umbral, sortea la probabilidad diaria: si
  sale, crea una pareja (`crear_criatura` × `tamano_pareja_colonizadora`)
  en una celda aleatoria de bioma compatible sin agua, y emite
  `Evento("ColonizacionEspontanea", Severidad.HISTORICO)`.

### Config nueva (`config/poblacion.yaml`, sección `colonizacion`, PROVISIONAL)

- `umbral_poblacion_critica: 2`
- `probabilidad_colonizacion_diaria: 0.005` (~1 vez cada 200 días de una
  especie en apuros, en promedio)
- `tamano_pareja_colonizadora: 2`

## Qué NO se toca

- `sembrar_poblacion_inicial` -- sigue siendo la única vía de entrada
  en el tick 0, sin cambios. Colonización espontánea es un mecanismo
  aparte, con su propio disparador y cadencia.
- `Sexo` (componente `Reproduccion`) -- sigue sin ningún consumidor que
  lo compruebe (confirmado antes de implementar); la pareja colonizadora
  no se fuerza a sexos opuestos porque nada en el motor lo necesitaría
  hoy.

## Deuda técnica declarada, no oculta

`BIOMAS_POR_ESPECIE` duplica conocimiento que ya vive (de otra forma,
con cascada de prioridad) dentro de `sembrar_poblacion_inicial` -- se
decidió NO unificar ambos en este círculo para no acoplar un mecanismo
nuevo a un refactor de la siembra inicial, que sería una segunda fuente
de complejidad en el mismo círculo. Si en el futuro esto genera
inconsistencias reales (una especie cuyo bioma cambia en un sitio y no
en el otro), unificar ambos mapeos es el primer candidato de limpieza.

## Riesgo real, comunicado sin maquillar

Si `probabilidad_colonizacion_diaria` se calibra demasiado alta, esto
puede convertirse en un parche que oculta problemas de calibración
reales (una especie mal ajustada que nunca prospera de verdad, solo
"revive" repetidamente) en vez de dar una segunda oportunidad legítima.
El harness ya tiene las métricas para detectarlo (diversidad sostenida
+ techo de extinción por especie, círculo anterior del mismo día) --
si una especie sigue apareciendo en el techo de extinción PESE a
colonización activa, es señal de que el problema es de calibración de
la especie, no de falta de oportunidades.

## Pendiente, no resuelto aquí

- Calibración de `probabilidad_colonizacion_diaria` contra el harness
  completo -- elegida por razonamiento ("muy rara"), no medida.
- Si debería depender de la proximidad a un asentamiento existente, o
  de otra señal además de población cruda -- no se consideró necesario
  para esta primera versión.
