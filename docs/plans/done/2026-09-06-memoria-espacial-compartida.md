# Plan: Memoria espacial compartida entre conscientes

Fuente de verdad: `docs/superpowers/specs/2026-09-06-memoria-espacial-compartida-design.md`.

## Ficheros a tocar

1. `sistemas/sistema_movimiento.py` (nucleo de la pieza):
   - Importar `capacidad_memoria` y `registrar_recuerdo` desde
     `nucleo.memoria` (junto a `objetivo_recordado` ya importado).
   - `__init__`: añadir contador de observacion
     `_stats_memoria_compartida_transferencias` y un detalle
     `_stats_memoria_transferida_detalle` (set de
     `(receptor_id, tipo, x, y)`) para la verificacion contra
     BOSQUE_AUTO_TICKS/BD. Solo observacion, ningun camino de decision
     los lee (mismo patron que `_stats_roce_social_resueltos`).
   - Refactor: extraer de `_procesar_roce_social` el bloque de agrupacion
     a `_agrupar_conscientes_por_celda(self, gestor)` — filtra SOLO por
     Posicion/Temperamento/CapacidadMental + umbral_consciencia_agencia
     (NO exige PoolMental/Necesidades en el filtro base).
   - `_procesar_roce_social(self, gestor, mundo, tick_actual,
     por_celda=None)`: si no llega `por_celda` pre-construido, lo
     construye con el helper (compatibilidad con los tests existentes,
     que lo llaman sin ese argumento). Por pareja comprueba
     Temperamento/PoolMental/**Necesidades** (anadido el chequeo de
     Necesidades por pareja) para conservar EXACTAMENTE el mismo
     resultado observable que antes, cuando Necesidades se filtraba en
     el filtro base. Resto identico.
   - Nuevo `_procesar_memoria_compartida(self, gestor, por_celda)` per
     el pseudocodigo de la spec: para cada celda con 2+ conscientes,
     cada PAR ORDENADO a→b y b→a por separado, `_compartir_memoria`.
   - Nuevo `_compartir_memoria(self, gestor, emisor_id, receptor_id)`
     per el pseudocodigo de la spec: tirada con `Temperamento.
     sociabilidad` del emisor; si dispara, por cada categoria de
     `mem_emisor.recuerdos` UNA llamada a `objetivo_recordado(...)` desde
     la posicion/capacidad del emisor (ya perturbado) y `registrar_
     recuerdo(...)` en el receptor con su propia `capacidad_memoria`.
     Cuando registra de verdad, incrementa los contadores de observacion.
   - `ejecutar()`: construir `por_celda` UNA vez por tick con el helper
     y pasarlo a `_procesar_roce_social` Y a `_procesar_memoria_compartida`.

2. `main.py` (solo gancho de verificacion, no cambia el comportamiento
   de juego): al terminar una tanda `BOSQUE_AUTO_TICKS > 0`, imprimir el
   contador de transferencias de memoria compartida del SistemaMovimiento
   (mismo patron de observacion de los contadores existentes).

3. `tests/test_memoria_compartida.py` (nuevo): tests dirigidos per la
   seccion Testing de la spec:
   - transferencia real comida/agua de A a B cuando la tirada de A dispara;
   - sin transferencia si la tirada de A falla;
   - direcciones independientes (A→B pero no B→A) con sociabilidades
     distintas;
   - la coordenada recibida pasa por `objetivo_recordado` desde la
     posicion de A (puede diferir de la exacta guardada; no afirmar que
     siempre difiere);
   - el receptor respeta su propio tope de capacidad;
   - ningun efecto si cualquiera de los dos no es consciente;
   - `_agrupar_conscientes_por_celda` agrupa por (x,y,zona) exacta
     filtrando solo por consciencia.

4. Orden de ejecucion:
   a. Plan (este fichero) + commit `plan: ...`.
   b. Implementar `sistema_movimiento.py` (+ main.py hook).
   c. Escribir tests nuevos.
   d. pytest tests/test_conflicto_verbal.py (sin cambios, verde) +
      tests/test_memoria_compartida.py.
   e. BOSQUE_AUTO_TICKS con poblacion real (miles de ticks) + consulta a
      la BD (`componentes_estado`) para confirmar que algun consciente
      tiene comida/agua no visitada directamente. Reportar cifras en el
      commit final.
   f. Suite completa una sola vez antes de entregar.

## Restricciones respetadas

- No se toca fauna/aprendizaje por observacion.
- No se anade campo de confianza/procedencia a MemoriaEspacial ni a
  recuerdos: la degradacion se resuelve con objetivo_recordado() en el
  momento de compartir.
- No SOCIALIZAR/sonido/reputacion.
- No constantes nuevas en config/.
- No cambia el comportamiento observable de _procesar_roce_social (los
  tests de roce social existentes no se modifican).
- No nucleo/conflicto.py, componentes/relaciones.py, nucleo/relaciones.py.
- Sin cambios de esquema SQLite: MemoriaEspacial se persiste tal cual.
