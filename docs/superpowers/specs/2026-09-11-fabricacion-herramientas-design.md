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

## Pendiente real, explícito

- `factor_bono_tasa_recolectar_con_herramienta`/
  `factor_bono_tasa_aporte_construccion_con_herramienta` PROVISIONALES,
  sin calibrar -- y sin observarse en juego libre todavía (ningún
  gnomo llegó a fabricar una herramienta en la muestra medida).
- El hallazgo real del diagnóstico (competencia por capacidad de carga
  entre material a granel y objeto discreto) queda señalado, sin
  ninguna corrección aplicada en este círculo -- decisión pendiente de
  Diego sobre si merece un círculo de corrección propio.
