# Plan: Ocio consciente (Accion.SOCIALIZAR)

Spec fuente de la verdad: `docs/superpowers/specs/2026-09-06-ocio-consciente-socializar-design.md` (leida completa primero).

## Objetivo

Accion nueva e independiente `SOCIALIZAR` que compite por el tiempo de ocio
(hoy ganado por DEAMBULAR, utilidad fija 0.1) cuando ninguna necesidad fisica
esta bajo `umbral_atencion_pareja`, modulada por
`Temperamento.sociabilidad`/`curiosidad` (primer consumidor real de
curiosidad). Al contacto a distancia 0 escribe afinidad POSITIVA MUTUA en
`Relaciones` (reutilizando el cimiento existente), misma logica de
acercamiento/sin resolver que CRISIS_VIOLENTA a distancia > 0. El sesgo
gregario de `_calcular_deambular` NO se toca. Sin drive dinamico, sin
cooldown, sin sonido, sin reputacion.

## Ficheros a tocar (en orden)

1. `componentes/intencion.py`
   - Anadir `SOCIALIZAR = "socializar"` al enum `Accion` con comentario
     (ocio consciente, compite con DEAMBULAR por el tiempo de ocio).

2. `config/fisiologia.yaml`
   - En `decision:` anadir `utilidad_socializar_base: 0.3` (PROVISIONAL,
     por encima de `utilidad_deambular_base` 0.1).

3. `config/relaciones.yaml`
   - En `relaciones:` anadir `delta_afinidad_socializar: 0.02` (PROVISIONAL,
     menor que `delta_amistad_convivencia_dia` 0.05 porque puede dispararse
     cada tick).

4. `sistemas/sistema_decision.py`
   - `SistemaDecision.__init__`: contador de observacion
     `self._stats_socializar_elegidas` (solo observacion, ningun camino de
     decision lo lee -- mismo patron que los stats de SistemaMovimiento).
   - `actualizar(...)`: leer `utilidad_socializar_base` de config;
     calcular `utilidad_socializar` con la formula exacta de la spec
     (gate consciencia + gate fisica_bajo_umbral, reutilizando la variable
     ya calculada para BUSCAR_PAREJA); anadir
     `(utilidad_socializar, Accion.SOCIALIZAR)` a `candidatas` justo antes
     de DEAMBULAR. Incrementar el contador cuando la accion FINAL (tras el
     compromiso ley B) sea SOCIALIZAR.

5. `sistemas/sistema_movimiento.py`
   - `_cachear_configuracion`: leer `delta_afinidad_socializar` de
     config_relaciones.
   - `__init__`: contadores de observacion `_stats_socializar_contacto` y
     `_stats_socializar_afinidad_pares` (pares dirigidos que recibieron
     afinidad positiva por esta pieza, para la verificacion vs Relaciones).
   - Refactor: extraer el cuerpo de `_aplicar_rencor` (gate de consciencia +
     `ajustar_afinidad`) a `_aplicar_afinidad(gestor, autor_id, otro_id,
     delta, tick_actual)`; `_aplicar_rencor` pasa a wrapper de una linea.
     Comportamiento exactamente igual.
   - Nuevo `_consciente_mas_cercano_con_id`: mismo molde que
     `_entidad_cercana_cualquiera_con_id` pero filtrando por
     `CapacidadMental.consciencia >= umbral_consciencia_agencia`, CUALQUIER
     especie (a diferencia de `_buscar_conspecifico_mas_cercano`).
   - Nuevo `_calcular_socializar`: sin objetivo -> `_paso_aleatorio()`;
     a distancia 0 -> aplica afinidad MUTUA (ambas direcciones) y devuelve
     (0, 0); a distancia > 0 -> `_acercarse_a`.
   - Dispatch en `ejecutar()`: rama `Accion.SOCIALIZAR`.

6. `main.py`
   - En el bloque final de `BOSQUE_AUTO_TICKS`, imprimir (solo observacion):
     socializar elegidas, contactos resueltos, y cuantos vinculos dirigidos
     con afinidad positiva en `Relaciones` corresponden a pares que tocaron
     esta pieza (atribuible a SOCIALIZAR) frente al total de positivos.

7. `tests/test_ocio_consciente_socializar.py` (nuevo)
   - `_consciente_mas_cercano_con_id`: cualquier especie, excluye
     no-conscientes y a quien busca, el mas cercano.
   - `_calcular_socializar`: distancia > 0 se acerca sin resolver;
     distancia 0 aplica afinidad MUTUA y devuelve (0, 0); sin consciente
     cercano cae a paso aleatorio.
   - `utilidad_socializar` (via `actualizar` + argmax): 0.0 si no
     consciente; 0.0 si una necesidad fisica bajo
     `umbral_atencion_pareja` aunque sociabilidad/curiosidad altas; sube
     con sociabilidad y con curiosidad por separado.
   - `_aplicar_afinidad`/`_aplicar_rencor`: el refactor no cambia rencor
     (los tests de conflicto verbal ya existentes quedan intactos).

## Verificacion obligatoria

- Suite completa en verde (incluidos tests de conflicto verbal sin
  modificarlos).
- `BOSQUE_AUTO_TICKS` con poblacion real (miles de ticks): medir y reportar
  en el mensaje de commit cuantas veces se eligio SOCIALIZAR, cuantas
  resoluciones de contacto, y si Relaciones muestra ganancias positivas
  atribuibles a esta pieza -- con honestidad aunque sea bajo/nulo.

## Fuera de alcance (expli[\u0301]cito en la spec)

- No tocar `_buscar_conspecifico_mas_cercano` ni el sesgo gregario de
  DEAMBULAR.
- Sin drive dinamico en Necesidades, sin cooldown por pareja.
- Sin sonido fisico ni reputacion/rumor.
- No tocar nucleo/relaciones.py, componentes/relaciones.py, nucleo/memoria.py,
  componentes/memoria_espacial.py, CLAUDE.md, informes/, docs/historial_*.
- Sin cambios de esquema SQLite.
