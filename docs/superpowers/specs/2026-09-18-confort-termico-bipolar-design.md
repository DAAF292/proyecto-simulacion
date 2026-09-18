# Confort térmico bipolar: hipotermia y golpe de calor

Fecha: 2026-09-18. Origen: al proponer un mecanismo de mortalidad por
frío para `Necesidades.confort_termico` (que hasta hoy se movía pero
nunca mataba), Diego cuestionó el propio modelo del eje: "y si le damos
un enfoque distinto, de 0 a 1. si la criatura está en 0.5 significa que
esta en un termino medio, lo ideal. si ese valor baja empieza el frio,
si ese valor sube empieza el calor. los grados cercanos a los extremos
desencadenan hipotermia, golpe de calor" -- una idea mejor que la
propuesta original (un eje monótono, "más alto = siempre mejor", nunca
modelaba "demasiado calor").

Se le señaló a Diego, antes de diseñar, que esto no era "añadir
mortalidad térmica" sino redefinir la semántica de un componente que
ya usan 4 sitios (`nucleo/clima.py`, `sistema_decision.py`,
`sistema_necesidades.py` -- los seis bonos de calor --, y `Animo`,
cerrado el mismo día). Diego eligió el alcance completo (opción "A":
todo en un único círculo, igual que `Animo`) y pidió además "más
variabilidad" de clima -- sin eso, los extremos del eje bipolar nunca
son alcanzables en la práctica (con solo despejado/lluvioso/tormenta,
ningún combo real se acerca a un extremo peligroso).

## 1. Reinterpretación del eje

`confort_termico`: 0.0 = hipotermia extrema, **0.5 = ideal**, 1.0 =
golpe de calor extremo. Sustituye al eje monótono anterior (0=malo,
1=bueno).

## 2. Recalibración de `config/clima.yaml`

- **Estaciones**, base moderada alrededor de 0.5 (ninguna extrema por
  sí sola, simétricas invierno/verano respecto al ideal):
  primavera 0.5, verano 0.65, otoño 0.45, invierno 0.35.
- **Climas existentes**, ajustes recalibrados: despejado 0.0 (antes
  +0.05 -- bajo el modelo bipolar, un día despejado no es
  intrínsecamente "mejor", es neutro), lluvioso -0.05, tormenta -0.1
  (sin cambios, ambos ya enfriaban).
- **Dos climas nuevos**, deliberadamente restringidos a UNA sola
  estación cada uno (no también a estaciones limítrofes -- más simple
  y auditable en este primer círculo):
  - `OLA_CALOR` (`nucleo/clima.py::Clima`): ajuste_confort +0.35, solo
    sorteable en verano (`probabilidades_por_estacion.verano`).
  - `VENTISCA`: ajuste_confort -0.35, solo sorteable en invierno.
  
  Son los ÚNICOS dos climas capaces de acercar de verdad a un extremo
  peligroso (verificado: verano+ola_calor ≥ umbral_golpe_calor,
  invierno+ventisca ≤ umbral_hipotermia, ver tests).
- `sortear_clima()` (`nucleo/clima.py`) no necesitó ningún cambio de
  lógica -- ya itera solo las claves presentes en la tabla de
  probabilidades de cada estación; los climas nuevos simplemente no
  aparecen en la tabla de las estaciones donde no deben sortearse.
- `desastres.multiplicador_riesgo_por_clima`: ola_calor 2.5 (sequedad,
  más riesgo de incendio), ventisca 0.05 (casi anulado).

Todo PROVISIONAL, hipótesis de partida razonada, sin calibrar contra
el harness completo.

## 3. Bonos de confort: techo/suelo simétrico en 0.5

Los seis bonos de CALOR ya existentes (refugio, fogata, madriguera,
salón común, cocina común, pareja estable) sumaban antes sin ninguna
condición -- bajo el eje bipolar eso ya no tiene sentido (una fogata en
pleno verano empeoraría un golpe de calor). Ahora se acumulan en un
único `bono_calor` y se aplican con un TECHO en 0.5: `if bono_calor >
0.0 and obj_termico < 0.5: obj_termico = min(0.5, obj_termico +
bono_calor)`. Por encima de 0.5, no hacen nada.

**Contrapunto de FRESCOR, nuevo** (petición explícita de Diego, "dale
con todo" tras preguntarle si diseñaba también la mitigación del
calor): reutiliza patrones ya existentes en vez de inventar una acción
de Utility AI nueva --
- `bono_confort_agua` (0.2): `nucleo.agua.hay_agua_potable(celda)`, ya
  existente (mismo criterio que la asfixia por inmersión).
- `bono_confort_sombra_bosque` (0.15): `celda.tipo_terreno ==
  TipoTerreno.BOSQUE`, mismo criterio que ya usa `sistema_desastres.py`
  para el riesgo de ignición.

Ambos son bonos PASIVOS por posición (sin ninguna construcción ni
decisión consciente de por medio), mismo patrón exacto que refugio/
fogata -- de ahí su magnitud menor. Se aplican con SUELO simétrico en
0.5: `if bono_frescor > 0.0 and obj_termico > 0.5: obj_termico =
max(0.5, obj_termico - bono_frescor)`.

**Decisión explícita, no resuelta por iniciativa propia y confirmada
por Diego ("adelante con todo")**: no se diseña ninguna ACCIÓN nueva de
Utility AI para "buscar sombra/refrescarse" -- la mitigación del calor
es, en este primer círculo, tan pasiva como ya lo es el calentamiento
por refugio/fogata (ningún individuo "decide" ir a la fogata, solo se
beneficia si ya está ahí por otro motivo).

## 4. Mortalidad térmica dual

Dos causas nuevas en la cascada `if/elif` de mortalidad de
`sistema_necesidades.py` (mutuamente excluyente con
ahogamiento/inanición/deshidratación, añadidas al final):
- `umbral_confort_termico_hipotermia` (PROVISIONAL 0.15) /
  `umbral_confort_termico_golpe_calor` (PROVISIONAL 0.85).
- `probabilidad_muerte_hipotermia` / `probabilidad_muerte_golpe_calor`
  (PROVISIONAL 0.005 cada una, mismo orden de magnitud que
  saciedad/hidratación), moduladas por `(1 - resistencia_enfermedad)`
  -- **reutilización directa y exacta** del patrón que ya usa la
  intoxicación por comer crudo tóxico (`sistema_recursos.py`), no un
  atributo nuevo de "resistencia al frío/calor".

## 5. Consumidores existentes adaptados

- **`sistema_decision.py`**: `utilidad_encender_fuego` (y su eslabón
  heredado hacia RECOLECTAR) pasa de `1.0 - confort_termico` a
  `max(0.0, 0.5 - confort_termico) * 2.0` -- fuego SOLO mitiga el frío;
  la fórmula da 0.0 automáticamente en todo el rango >= 0.5 (calor),
  sin gate adicional. La vieja fórmula monótona habría seguido dando
  utilidad no-nula con calor extremo, un absurdo bajo el nuevo modelo.
- **`Animo`** (círculo del mismo día, ver `docs/historial_componentes.md`):
  `peso_termico_animo * (1.0 - confort_termico)` pasa a
  `peso_termico_animo * abs(confort_termico - 0.5) * 2.0` -- la
  urgencia térmica ahora es la DISTANCIA al ideal, no "1 - valor".
  Verificado: frío extremo y calor extremo bajan el ánimo por igual
  (simetría exacta, ver test).

## Verificación real

- 789 tests pasan (772 antes de este círculo + 17 nuevos,
  `tests/test_confort_termico_bipolar.py`).
- 5 tests preexistentes rotos por la recalibración de estaciones
  (invierno+despejado pasó de 0.2 a 0.35): `test_madriguera_fisica.py`,
  `test_pareja_estable.py` (x3), `test_salon_comun.py` -- todos
  actualizados al nuevo valor real, no forzados a pasar. Uno de ellos
  (`test_ley_bono_confort_pareja_se_acumula_con_refugio_y_fogata`) tuvo
  que rediseñarse por completo: refugio+fogata (0.3+0.3=0.6) ya
  saturaban por sí solos el nuevo techo de 0.5, ocultando el efecto de
  pareja que el test pretendía demostrar -- se cambió a un escenario de
  ventisca real con solo fogata, dejando margen suficiente para
  observar la acumulación.
- **Smoke test real, 6000 ticks, 24 individuos iniciales (gnomo/lobo/
  conejo/caballo), mapa 20x20**: ambos climas nuevos se sortean con
  frecuencia real (ola_calor 864 ticks, ventisca 1152 ticks, sobre
  6000). **Ambas causas de muerte térmica se ejercen de verdad, ni
  inertes ni catastróficas**: hipotermia 25468, golpe_calor 5790 (sobre
  el total de eventos "Muerte" del bus en toda la corrida, no
  individuos distintos -- cifras del bus de eventos, no de población).
- **Observación honesta, PROVISIONAL, no ajustada por iniciativa
  propia**: hipotermia es ~4.4x más frecuente que golpe_calor en esa
  corrida, pese a que la exposición climática es solo ~1.33x mayor
  (ventisca/ola_calor). Con seis fuentes de mitigación de frío (refugio,
  fogata, madriguera, salón, cocina, pareja) frente a solo dos de calor
  (agua, sombra), cabría esperar lo contrario si las mitigaciones se
  ejercieran con la misma eficacia -- la desproporción real sugiere que
  las mitigaciones de frío exigen infraestructura que la población no
  siempre tiene a tiempo (construcción, vínculos), mientras que
  agua/sombra son puramente posicionales. Hipótesis no probada con una
  sola corrida y semilla única -- necesita el harness completo para
  decidir si hace falta recalibrar.
- **Hallazgo colateral, ajeno a este círculo, señalado sin investigar
  a fondo (fuera de alcance)**: en la misma corrida, `ahogamiento` fue
  la causa de muerte dominante con mucha diferencia (71981) --
  mecanismo que este círculo no tocó (usa `profundidad_agua_potable`,
  distinta de `hay_agua_potable` que sí se introdujo aquí para el bono
  de frescor). Podría ser una particularidad del mapa 20x20 de esta
  semilla concreta (mucha agua) o un problema preexistente sin
  relación con este círculo -- queda como pendiente a investigar
  aparte, no se tocó nada del mecanismo de ahogamiento.
