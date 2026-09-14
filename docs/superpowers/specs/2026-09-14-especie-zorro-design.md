# Especie zorro — mesodepredador de presas pequeñas (2026-09-14)

## Motivación

Diego pidió una criatura nueva que actúe como depredador intermedio de
conejo/ardilla y ayude a controlar su crecimiento. Lobo (60-90kg) ya
existe como único depredador del catálogo, pero está mal ajustado a
presas pequeñas: `aporte_maximo = (peso_presa/peso_cazador) *
eficiencia_biomasa_saciedad` hace que una captura de conejo o ardilla
apenas alimente a un animal de su tamaño (hallazgo ya documentado en
CLAUDE.md, "Por qué lobo se muere de hambre pese a cazar más que
nadie", 2026-09-04/05). Zorro llena ese hueco: un cazador de tamaño
mucho más cercano al de su presa, para el que conejo/ardilla sí son
nutricionalmente significativas.

## Decisiones cerradas con Diego antes de diseñar los números

1. **Peso: fidelidad real (5-9kg) sobre control garantizado.** La
   disposición de caza (`nucleo/disposicion.py`,
   `combate.umbral_disposicion_caza=0.5`) es logarítmica y exige un
   ratio de peso `>= e≈2.72` entre cazador y presa. Con zorro en
   [5,9]kg:
   - Contra ardilla [0.3,0.6]kg: ratio mínimo 8.3 — **caza garantizada
     en el 100% de los individuos**.
   - Contra conejo [1.5,3.0]kg: ratio va de 1.67 (zorro ligero/conejo
     pesado, no cazable) a 6.0 (zorro pesado/conejo ligero, sí
     cazable) — **control real pero PARCIAL**, depende del individuo.
   Diego eligió esto explícitamente en vez de subir el peso mínimo a
   ~8.2kg (que habría garantizado caza de cualquier conejo al precio
   de alejarse del zorro real, rozando tamaño de coyote). Mismo patrón
   ya aceptado en el proyecto con lobo/cabra_montesa: parte del espacio
   de sorteo sí, parte no — no es un fallo, es la ley aplicada con
   honestidad.
2. **Bioma: bosque y pradera a la vez (generalista).** Bosque y
   pradera ya son contiguos en el motor (frontera confirmada,
   `sistema_movimiento.py` no filtra por bioma en la persecución de
   caza — ver CLAUDE.md, "Lobo caza en montaña"), así que un zorro
   nacido en cualquiera de los dos ya podría perseguir presa del otro
   cruzando la frontera. Pero para que la POBLACIÓN FUNDADORA arranque
   con territorio propio en ambos (no solo cruzando por persecución
   incidental), se siembra sobre un pool combinado bosque+pradera, sin
   forzar reparto 50/50 — el sorteo decide, mismo criterio que ya usa
   `candidatas_bosque` en el resto de `sembrar_poblacion_inicial`.

## Resto del catálogo — calibración razonada, PROVISIONAL

Reutiliza el 100% del mecanismo ya existente (fábricas ECS genéricas
`crear_criatura`/`nacer_criatura` parametrizadas por `especie.value`
sobre `rangos_raciales`, sin ningún código nuevo de depredación —
`_es_presa_valida`/`_resolver_ataque` ya son agnósticos a especie).

| Atributo | Valor | Razonamiento |
|---|---|---|
| `medio_alimentacion` | `cazar` | Segundo depredador del catálogo (junto a lobo) |
| `peso` | [5, 9] kg | Acordado arriba |
| `altura` | [0.35, 0.55] | Entre conejo (0.15-0.25) y lobo (0.6-0.9) |
| `longevidad` | [4, 8] años | Corta a propósito — evita el error ya cometido con gnomo (gestación/vida desproporcionada) |
| `duracion_gestacion_dias` | [45, 60] | Corta (zorro real ~52d), perfil sostenible ya validado con lobo/venado, no el error original de gnomo |
| `camada` | [2, 4] | Su población la limita la disponibilidad de presa, no hace falta camada única como gnomo |
| `factor_base_concepcion` | 0.015 | Mismo valor ya validado como sostenible en lobo/venado/caballo combinado con gestación corta |
| `puntos_agarre` | 1 (boca) | Mismo criterio que lobo — sin manos prensiles |
| `fuerza` | [0.25, 0.45] | Menor que lobo, coherente con su tamaño |
| `agilidad`/`velocidad` | [0.5, 0.85] | Cazador ágil pero no el más rápido del catálogo |
| `resistencia_enfermedad` | [0.3, 0.6] | Rango intermedio, sin consumidor que lo distinga hoy |
| `agudeza_sensorial` | [0.6, 0.9] | Más alta que lobo — oído/olfato es el rasgo distintivo real del zorro |
| `vitalidad_maxima`/`resistencia_maxima` | [0.35, 0.6] | Menor que lobo, coherente con tamaño |
| `valentia` | [0.3, 0.6] | Menor que lobo — cazador sigiloso/oportunista, prefiere evitar el conflicto directo |
| `sociabilidad` | [0.2, 0.45] | Zorro real es territorial/solitario, no de manada — bajo pero no nulo (no bloquea la concepción, que ya se multiplica por esto) |
| `agresividad` | [0.2, 0.5] | Menor que lobo |
| `dominancia` | [0.15, 0.4] | Similar a otras presas/mesodepredadores |
| `empatia`/`lealtad`/`curiosidad`/`inteligencia`/`memoria`/`voluntad`/`resiliencia`/`estabilidad_mental_maxima`/`fe` | rangos intermedios entre lobo y ardilla | Sin ningún consumidor específico que los distinga hoy |
| `consciencia` | [0.0, 0.15] | Fauna, no consciente — mismo criterio que el resto |
| `zorros_iniciales` | 8 | Comparable a `lobos_iniciales` (6) — depredador, no necesita población grande |
| `necesidades` (fisiología) | sin entrada propia al inicio | Mismo criterio ya usado con caballo/venado/cabra_montesa: no calibrar a ciegas — si el diagnóstico multi-semilla muestra fragilidad real, se ajusta después con evidencia |

## Deliberadamente fuera de este círculo

- Sin caza en manada — zorro caza en solitario por diseño (su ratio de
  peso ya se lo permite sin depender de aliados, mismo patrón que
  venado).
- Sin ninguna ventaja de terreno específica de bosque/pradera.
- Sin representación visual — motor primero.
- Sin ningún ajuste a lobo/conejo/ardilla — este círculo solo añade la
  especie nueva, no toca el resto del catálogo. Si el diagnóstico
  posterior muestra que zorro desestabiliza a conejo/ardilla o compite
  mal con lobo, será un círculo de calibración aparte.

## Verificación mínima esperada

- Tests: existencia y distinción de la especie, fábricas ECS completas
  (`crear_criatura`/`nacer_criatura`), siembra real en bosque+pradera,
  caza en solitario válida contra conejo y ardilla (con los pesos
  reales del catálogo, no solo razonado).
- `BOSQUE_AUTO_TICKS` y `BOSQUE_CONTINUAR` sin excepciones.
- Diagnóstico multi-semilla (arnés de sesión, sin tocar el repo):
  confirmar que zorro caza de verdad en juego libre y no se extingue
  de inmediato — sin exigir todavía ningún criterio de control
  cuantitativo sobre conejo/ardilla, eso es calibración futura.
