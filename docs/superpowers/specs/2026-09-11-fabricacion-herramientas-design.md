# Fabricación de herramientas -- Círculo 2 del arco "fabricación y uso de herramientas"

Fecha: 2026-09-11. Continuación directa de "Aptitud vocacional" (Círculo
1, mismo día) -- implementado directamente por Claude (centinela del
pipeline parado desde el incidente de madriguera-física-A, este
contenedor cloud tampoco tiene `OPENROUTER_API_KEY`/`mini-swe-agent`,
misma excepción ya documentada repetidas veces esta semana). Diego dio
la señal de continuar ("sigue") tras cerrar y comitear el Círculo 1.

## Objetivo

Dar el primer efecto físico real y tangible al mismo cimiento de
vocación: fabricar una herramienta de verdad, con materiales crudos ya
existentes (madera/piedra, reutilizados de "armas primitivas v2",
2026-09-03), usando el resolutor de categorías `candidatos_fabricar`
que el rename `Accion.FABRICAR_ARMA -> Accion.FABRICAR` (2026-09-11,
mismo día, sesión de Bloque A) ya dejó preparado para un segundo
candidato ("herramienta" junto a "arma").

## Reutiliza antes de inventar -- inventario de lo ya existente

- **Materiales crudos**: `madera`/`piedra`, mismos `apto_arma` del
  catálogo de armas -- ninguna clave nueva de material.
- **Mecanismo de recolección causal**: mismo patrón "Vía con causa" que
  ya usa armas (`nucleo/armas.py:celda_ofrece_material_arma`/
  `recolectar_material_arma_de_celda`), compartido vía
  `_via_material_crudo` (extraído en la sesión de Bloque A el mismo
  día, sin cambios de comportamiento).
- **Resolutor de categorías**: `candidatos_fabricar` en
  `sistema_decision.py`, ya construido en el rename, gana su segundo
  candidato real.
- **Patrón heredado sin descuento**: RECOLECTAR hereda
  `necesidad_trabajo = max(utilidad_recolectar, utilidad_construir)`
  SIN descontar -- mismo criterio que ya usa "arma" (`1.0 - seguridad`
  sin multiplicador), confirmado necesario tras un bug real encontrado
  al diseñar esto (ver "Errores encontrados" más abajo).
- **Manos libres**: FABRICAR-herramienta pasa por el mismo gate ya
  existente (Círculo previo de la sesión anterior, "manos libres"),
  `manos_requeridas` ya definía 2 para `FABRICAR_ARMA` -- se reutiliza
  igual para la categoría "herramienta" sin ningún cambio.

## Diseño real

- `nucleo/herramientas.py` (nuevo): `tiene_herramienta(objetos, recetas)`
  -- función pura mínima, análoga a `tiene_arma_nivel2_o_mas` pero sin
  niveles (una herramienta fabricada YA es la meta, no hay "todo es una
  herramienta" como sí hay "todo es un arma" -- material crudo sin
  fabricar no tiene ningún efecto de herramienta, a diferencia de un
  palo/piedra crudos que sí son arma de nivel 1). Deliberadamente
  asimétrico con `nucleo/armas.py`, documentado en el propio módulo.
- `config/herramientas.yaml` (nuevo): una única receta,
  `hacha_primitiva` (madera+piedra, nivel 1) -- deliberadamente pequeño
  para este primer círculo. `factor_bono_tasa_recolectar_con_herramienta`
  (1.5) y `factor_bono_tasa_aporte_construccion_con_herramienta` (1.3),
  ambos PROVISIONALES: portar una herramienta fabricada (Inventario u
  Agarre, sin exigir tenerla empuñada -- abstracción deliberada, "la
  lleva en su kit mientras trabaja") acelera la recolección a granel y
  el aporte a construcción.
- `sistemas/sistema_decision.py`: nuevo bloque `utilidad_categoria_
  herramienta`, mismo molde que "arma" -- si consciente, hereda
  `necesidad_trabajo` cuando no hay receta completable con lo que ya se
  porta y la celda actual ofrece material crudo apto_arma; si el
  eslabón heredado gana la utilidad de RECOLECTAR frente a su propio
  valor previo, marca `Intencion.recolectar_motivo_herramienta`.
  `candidatos_fabricar` pasa a `[("arma", ...), ("herramienta", ...)]`.
- `componentes/intencion.py`: `recolectar_motivo_herramienta: bool =
  False`, mismo patrón que `recolectar_motivo_arma`.
- `sistemas/sistema_recursos.py`: Vía 3 en `_resolver_recolectar`
  (`recolectar_herramienta=True`), comparte `_via_material_crudo` con
  la Vía 2 (arma), gateada por `tiene_herramienta` en vez de
  `tiene_arma_nivel2_o_mas`. `_resolver_fabricar` (renombrado de
  `_resolver_fabricar_arma` en el rename) gana una rama `categoria ==
  "herramienta"` -- consume la receta, emite `Evento(tipo=
  "HerramientaFabricada", severidad=NOTABLE)`. Bono multiplicativo de
  velocidad aplicado a la recolección a granel (mineral/flora/sustrato)
  y al aporte a construcción cuando `tiene_herramienta` es verdadero.

## Errores encontrados y corregidos antes de comitear (no al fallar en caliente)

1. **Bug de diseño real -- utilidad heredada con descuento**: el primer
   intento aplicaba `utilidad_categoria_herramienta = necesidad_trabajo
   * factor_urgencia_herramienta` (0.5) -- matemáticamente incapaz de
   ganarle nunca a su propia fuente (`necesidad_trabajo`), así que
   FABRICAR-herramienta nunca habría podido imponerse a RECOLECTAR/
   CONSTRUIR ni completar el ciclo. Detectado por dos tests fallando
   antes de comitear, corregido eliminando el descuento por completo
   (mismo patrón sin descuento que ya usa "arma"), removiendo
   `factor_urgencia_herramienta` de config -- sustituido por un
   comentario documentando por qué se descartó.
2. **Interacción real con el Círculo 1 (aptitud vocacional), mismo
   día**: los tests de decisión que asumían una comparación numérica
   exacta entre `utilidad_recolectar`/`utilidad_construir` quedaban
   rotos por la modulación aleatoria de aptitud (atributos sorteados
   por individuo). Corregido neutralizando los 5 atributos relevantes
   de aptitud a 0.5 en el fixture de test (`factor_aptitud` = 1.0 para
   las 4 cubetas), aislando el comportamiento bajo prueba.

## Verificación

- 12 tests nuevos (`tests/test_fabricacion_herramientas.py`), 497/497
  en verde con el resto de la suite.
- `BOSQUE_AUTO_TICKS=3000` y `BOSQUE_CONTINUAR=1` (roundtrip) sin
  ninguna excepción.
- **Diagnóstico multi-semilla honesto** (arnés de sesión, no en el
  repo, 10 semillas nuevas combinadas entre 2200 y 6500 ticks cada
  una): `HerramientaFabricada` **nunca se disparó** en ninguna semilla
  -- ver el hallazgo real documentado en CLAUDE.md, sección de cierre
  de este círculo.

## Corrección real -- prioridad consciente (mismo día, tras reportar el hallazgo)

Diego, ante el hallazgo de "sin espacio" de arriba, cuestionó la
conclusión de "señalado, sin corregir": *"esto es un problema, y no
tiene sentido, el ser consciente debería poder decidir qué carga, si
quiere fabricar un arma pero no tiene espacio en el inventario para
recolectar los materiales necesarios, lo lógico es que se desprenda de
algo que tenga para liberar el espacio y lograr su intención"*.
Corregido:

- `nucleo/inventario.py:descartar_contenidos_para_liberar(contenidos,
  peso_a_liberar) -> float` -- función pura nueva. Descarta bulto de
  `contenidos` (empezando por el material del que más se porta, el
  sacrificio más eficiente en número de materiales tocados), nunca más
  de lo pedido. El material se pierde sin más -- mismo criterio ya
  establecido el mismo día para la piedra de percusión del fuego
  gastada (círculos pequeños de Bloque A): un descarte deliberado y
  simbólico, no un sistema de "tirar al suelo" con su propia física.
- `sistema_recursos.py:_via_material_crudo` -- si no hay espacio para
  el objeto que la intención causal YA ganadora este tick necesita
  (Vía 2 arma o Vía 3 herramienta, ambas ya motivadas causalmente antes
  de llegar aquí), se descarta justo lo necesario de `contenidos` antes
  de reintentar. Nunca toca `inv.objetos` (armas fabricadas, u otro
  material ya recolectado para la misma intención).
- Contador de observación `_stats_material_descartado_por_prioridad_kg`,
  impreso en `BOSQUE_AUTO_TICKS`.

**Verificado**: 6 tests nuevos (3 de la función pura, 3 de integración
en `_via_material_crudo` -- descarta lo mínimo, no descarta si ya hay
espacio, nunca toca objetos discretos), 503/503 tests en verde,
`BOSQUE_AUTO_TICKS=3000` y roundtrip sin excepciones (6.00 kg y 1.00 kg
descartados respectivamente -- el mecanismo se ejerce de verdad).

**Segundo hallazgo real, distinto y NO resuelto por este fix -- ver
CLAUDE.md para el detalle completo**: el diagnóstico multi-semilla
repetido tras el fix confirma que la falta de espacio no era el único
bloqueo. `con_madera` empieza a aparecer con más frecuencia, pero
`con_piedra` sigue en 0 en todas las semillas probadas -- causa
distinta, ajena a este círculo: la Vía 1 (piedra_suelta para fuego)
corre SIEMPRE primero en `_resolver_recolectar`, sin comprobar si el
motivo real de este RECOLECTAR fue fuego o herramienta/arma, así que
intercepta casi cualquier piedra_suelta disponible antes de que la Vía
2/3 pueda reclamarla como material "piedra". Señalado, no corregido --
decisión de diseño pendiente de Diego.

## Corrección real -- Vía 1 requiere motivo real (2026-09-12)

Recomendado y cerrado el mismo día: dar a Vía 1 (fuego) el mismo
`recolectar_motivo_X` que ya tenían arma/herramienta -- retrofit de un
patrón cronológicamente anterior (piedra suelta, 30-08) que nunca lo
adoptó. `Intencion.recolectar_motivo_fuego` nuevo;
`sistema_recursos.py:_resolver_recolectar` gana `recolectar_fuego:
bool = False`, y Vía 1 solo se dispara con ese flag activo.

**Hallazgo real durante la implementación, corregido antes de
comitear**: la primera versión de los tres flags (fuego/arma/
herramienta) comparaba cada eslabón contra el valor de
`utilidad_recolectar` "hasta ese punto" de la cascada secuencial --
igual que ya hacían arma/herramienta desde su diseño original. Esto
deja un motivo temprano (p.ej. fuego) marcado `True` aunque un eslabón
posterior (arma/herramienta) lo superase después en la misma cascada,
produciendo dos motivos simultáneamente verdaderos para un mismo
RECOLECTAR -- sin sentido físico, y detectado por un test propio antes
de comitear (`test_ley_decision_motivo_fuego_pierde_frente_a_necesidad_
de_trabajo_mayor`). Corregido: los tres eslabones ahora guardan su
valor CRUDO (`valor_heredado_fuego/arma/herramienta`), y los tres flags
se resuelven en un único punto, al final de la cascada, comparando cada
valor crudo contra el resultado YA cerrado de `utilidad_recolectar`
(precedencia fuego > arma > herramienta en empate exacto). Mismo tipo
de bug latente que ya tenían arma/herramienta entre sí (nunca disparado
en la práctica hasta ahora), cerrado de paso para los tres a la vez.

**Verificado**: 5 tests nuevos
(`tests/test_prioridad_consciente_fuego.py`), 508/508 tests en verde,
`BOSQUE_AUTO_TICKS=3000` y roundtrip sin excepciones (312.18 kg y 18.19
kg descartados por prioridad respectivamente -- Vía 2/3 se ejercen
mucho más ahora que Vía 1 ya no les intercepta el recurso).

**Diagnóstico multi-semilla, resultado real -- el bloqueo queda
desbloqueado**: repetido el mismo arnés con 4 semillas NUEVAS
(80301/80302/90401/90402): **3 de 4 produjeron `HerramientaFabricada`
real** (`con_piedra` ya no en 0 en ninguna de las 3), frente a 0 de 10
en toda la investigación previa a este fix. La única semilla sin
fabricación (90401) terminó con solo 2 gnomos vivos -- fragilidad de
población ya conocida, no un fallo del mecanismo.

## Pendiente real, explícito

- `factor_bono_tasa_recolectar_con_herramienta`/
  `factor_bono_tasa_aporte_construccion_con_herramienta` PROVISIONALES,
  sin calibrar contra el harness completo.
- Solo 4 semillas verificadas (3/4 con fabricación real) -- direccional,
  no una calibración cerrada; el harness completo (15×12000) sigue
  pendiente para cualquier cifra de frecuencia real.
- `factor_bono_tasa_recolectar_con_herramienta`/`...aporte_construccion...`
  ahora sí tienen ocasión de observarse en juego libre (herramientas
  reales existen), pero su efecto sobre la velocidad real no se ha
  medido todavía, solo su existencia funcional.
