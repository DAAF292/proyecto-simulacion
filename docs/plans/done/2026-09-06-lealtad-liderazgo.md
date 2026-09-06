# Plan real de implementacion -- Lealtad y liderazgo con inercia real (5b)

Fuente de verdad: `docs/superpowers/specs/2026-09-06-lealtad-liderazgo-design.md`,
leida completa antes de tocar codigo.

## Ficheros a tocar (y que cambia en cada uno)

1. `nucleo/asentamiento.py`
   - Importar `Relaciones` desde `componentes.relaciones` (hoy no importado).
   - Anadir contadores de observacion a nivel de modulo (mismo patron que
     `nucleo/sonido.py:SONIDOS_EMITIDOS_TOTALES`), solo lectura desde main.py:
     - `STATS_REPUTACION_DESCALIFICADOS`: candidatos dominantes sacados por
       reputacion (< umbral).
     - `STATS_DESEMPATE_REPUTACION_CAMBIO`: veces que el ganador del desempate
       final cambio respecto a la formula anterior `(dominancia, valentia)`.
   - `calcular_liderazgo`: SIN CAMBIAR la firma (zero parametros nuevos) ni el
     filtro de dominancia (`margen_dominancia_elite`) ni la formula de
     consejo-vs-unico. Tras filtrar candidatos por dominancia:
       1. `_reputacion(candidato_id)`: afinidad MEDIA que el resto de `miembros`
          le tiene, calculada SOLO sobre quienes ya tienen vinculo hacia el
          candidato dentro de `Relaciones.vinculos`; sin datos, reputacion 0.0
          (neutro, comportamiento identico al previo).
       2. Descalificar: `candidatos = [c for c in candidatos if reputaciones[c] >= umbral_descalifica]` con
          `umbral_reputacion_descalificante` (config nuevo, PROVISIONAL).
       3. Si no queda ninguno: `return set()` (sin lider ese dia, legitimo).
       4. Consejo vs. unico: sin cambios, pero sobre los candidatos YA filtrados.
       5. Desempate final de lider unico con orden nuevo
          `(dominancia, reputacion, valentia)`.
       Los contadores se incrementan aqui con `global`.

2. `sistemas/sistema_asentamiento.py`
   - `__init__`: `self._stats_lealtad_aplicada: int = 0`.
   - Nuevo metodo `_acrecion_lealtad_liderazgo(gestor, mundo, reloj)` siguiendo
     EXACTAMENTE el pseudocodigo de la spec: para cada asentamiento con
     `lideres` no vacio, cada miembro no-lider aporta
     `delta_lealtad_liderazgo` hacia cada lider via `_ajustar_amistad`
     (reutilizado tal cual, ya gatea consciencia del autor).
   - `_ajustar_amistad` pasa a devolver `bool` (True si escribio afinidad) sin
     cambiar su comportamiento; los llamadores actuales ignoran el retorno.
   - `ejecutar()`: llamar `_acrecion_lealtad_liderazgo` justo despues de
     `_acrecion_amistad_convivencia` (misma cadencia diaria).

3. `config/relaciones.yaml`
   - `delta_lealtad_liderazgo: 0.03` (PROVISIONAL, menor que
     `delta_amistad_convivencia_dia` 0.05: admirar a un lider es mas
     especifico que la convivencia general del grupo).

4. `config/comportamiento.yaml`
   - En seccion `asentamiento:`, anadir
     `umbral_reputacion_descalificante: -0.4` (PROVISIONAL, negativo).

5. `main.py`
   - Importar `from nucleo import asentamiento as nucleo_asentamiento`.
   - En el bloque de reporte de `BOSQUE_AUTO_TICKS`, imprimir las tres
     metricas obligatorias: aplicaciones de lealtad diaria
     (`sistemas["asentamiento"]._stats_lealtad_aplicada`), candidatos
     dominantes descalificados por reputacion
     (`nucleo_asentamiento.STATS_REPUTACION_DESCALIFICADOS`) y desempates
     finales cuyo desenlace cambio respecto a la formula anterior
     dominancia+valentia (`nucleo_asentamiento.STATS_DESEMPATE_REPUTACION_CAMBIO`).
     Solo observacion, no cambia la simulacion.

6. `tests/test_lealtad_liderazgo.py` (nuevo, estilo del resto del proyecto)
   - `_acrecion_lealtad_liderazgo`:
     * aplica lealtad miembro->lider para CADA lider de un consejo;
     * no se aplica al lider hacia si mismo;
     * no se aplica si `lideres` esta vacio;
     * respeta el gate de consciencia ya existente en `_ajustar_amistad`.
   - `calcular_liderazgo`:
     * descalificacion: candidato con reputacion bajo el umbral queda excluido
       aunque tenga la dominancia mas alta;
     * todos descalificados -> `set()` (sin lider ese dia);
     * desempate: dos candidatos con dominancia empatada y distinta reputacion
       -> gana el de mejor reputacion (verificar que no se llega a comparar
       valentia);
     * sin datos de reputacion (candidato nuevo, sin vinculos formados):
       reputacion 0.0, comportamiento identico al previo.

## Orden de trabajo

1. Escribir este plan y commit `plan: <resumen>` ANTES de tocar codigo.
2. Implementar `nucleo/asentamiento.py`.
3. Implementar `sistemas/sistema_asentamiento.py`.
4. Config: `config/relaciones.yaml` y `config/comportamiento.yaml`.
5. `main.py`: reporte BOSQUE_AUTO_TICKS.
6. Escribir `tests/test_lealtad_liderazgo.py`; correr SOLO ese fichero.
7. Suite completa exactamente una vez.
8. `BOSQUE_AUTO_TICKS` (pocos miles de ticks) con poblacion real y medir las
   tres metricas obligatorias; reportar con honestidad en el commit final,
   incluso si el resultado es bajo o nulo (documentado en la spec: los
   asentamientos son raros en juego libre).
9. Commit final con el reporte de metricas.
