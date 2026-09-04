# Plan: Afinidad por concepción (círculo 4a)

## Ficheros a tocar (en orden)

1. `config/relaciones.yaml` — añadir constante `delta_afinidad_concepcion: 0.15`
   (POSITIVA, provisional, sin calibrar), comentada en el mismo estilo que
   `delta_rencor_disputa` / `delta_amistad_convivencia_dia`.

2. `sistemas/sistema_reproduccion.py` — reutilizar el cimiento `Relaciones`:
   - Importar `Relaciones` (componentes.relaciones) y
     `ajustar_afinidad` / `capacidad_vinculos` (nucleo.relaciones).
   - Añadir helper `_escribir_afinidad_concepcion(gestor, config, autor_id,
     otro_id, tick_actual)`: si el autor es CONSCIENTE
     (CapacidadMental.consciencia >= decision.umbral_consciencia_agencia)
     escribe afinidad POSITIVA (delta_afinidad_concepcion) hacia el otro,
     usando su propia capacidad_vinculos — mismo patrón exacto que el
     rencor (sistema_movimiento.py) y la amistad (sistema_asentamiento.py).
   - En el bloque donde ya se construye `Gestacion` (concepción exitosa),
     ANTES de emitir el evento `Concepcion`: llamar al helper en ambos
     sentidos (hembra→macho y macho→hembra), con el mismo `tick_actual`.
   - No se toca `Gestacion`, el evento `Concepcion` ni el resto de la
     lógica de reproducción.

3. `tests/test_relaciones.py` — añadir tests "ley física" del nuevo
   consumidor, en el estilo de los tests de amistad/rencor ya presentes
   (escenario SistemaReproduccion.actualizar con una pareja adulta en la
   misma celda, nutrición OK y rng forzado a concebir):
   - concepción entre dos conscientes → afinidad positiva mutua en ambos
     sentidos.
   - un progenitor no-consciente no escribe nada hacia el otro aunque el
     otro sea consciente y escriba hacia él.
   - una pareja con rencor/amistad previa ve su afinidad ajustarse por la
     suma.

## Verificación

- Ejecutar solo `pytest tests/test_relaciones.py -v` durante el desarrollo.
- Suite completa justo antes de terminar.
- Verificación OBLIGATORIA contra el motor real: `BOSQUE_AUTO_TICKS` con
  miles de ticks e inspección de la BD (`componentes_estado.relaciones`)
  buscando una entrada de afinidad POSITIVA real entre dos gnomos
  conscientes que concibieron.
