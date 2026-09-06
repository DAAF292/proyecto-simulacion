# Conflicto verbal (roce social + contacto por crisis violenta) — diseño

Fecha: 2026-09-06. Primera pieza descompuesta de un informe externo de
"capa de comunicación" (sonido físico, memoria espacial compartida entre
conscientes, comunicación social/ocio/conflicto verbal) evaluado el mismo
día en conversación con Diego. La auditoría contra el código real de ese
informe encontró que "MemoriaSocial" ya existe con otro nombre
(`componentes/relaciones.py:Relaciones`, cerrado el 2026-09-04 en el arco
"hilo individual") y que el visor no es pygame sino un servidor web
(`presentacion/vista_web.py`) — el informe se escribió sin contrastar
contra el repo. Se descompuso el informe en varias piezas independientes
(mismo criterio que "poblar más el mundo"/"hilo individual"); esta es la
primera, elegida por ser la más pequeña y no depender de ninguna otra.

## Motivación

- `nucleo/conflicto.py:resolver_disputa`/`indice_asertividad_social`
  fueron diseñados desde el 30-08-2026 declarando "robo/agravio genérico"
  como consumidores futuros del mismo resolutor, junto al único
  consumidor real hasta hoy (conflicto por refugio ocupado,
  `sistemas/sistema_movimiento.py:_resolver_posible_intruso`). Este
  círculo añade el segundo y tercer consumidor real.
- `Accion.CRISIS_VIOLENTA` existe desde el sistema de crisis mental
  (`PoolMental.estabilidad <= umbral_crisis` + `agresividad >
  umbral_agresividad_violenta`), pero su propio código documenta el
  hueco explícito: *"sin mecánica de daño todavía... es un gesto de
  movimiento, no una resolución de ataque"* (`sistema_movimiento.py`,
  docstring de `_calcular_crisis_violenta`).
- Diego señaló en conversación que restringir el conflicto social SOLO a
  CRISIS_VIOLENTA (un estado raro, exige cruzar un umbral de estabilidad
  mental) dejaría a `Relaciones` fluctuando muy poco — de ahí un segundo
  disparador, más frecuente y graduado, en vez de depender solo del
  primero.

## Decisiones ya cerradas con Diego

- **Dos disparadores independientes, un único resolutor compartido**:
  se extrae la lógica común de `_resolver_posible_intruso` (cálculo de
  urgencia/mismo_grupo/son_familia/bono_arma, llamada a
  `resolver_disputa`, aplicación de consecuencias por desenlace) a un
  helper reutilizado por los tres disparadores (refugio ocupado, ya
  existente, más los dos nuevos).
- **Disparador 1 (CRISIS_VIOLENTA + contacto real)**: aplica a
  CUALQUIER especie, resolución GARANTIZADA (no probabilística). No es
  una fuente nueva de riesgo — CRISIS_VIOLENTA ya ocurre hoy a la misma
  frecuencia para las 4 especies; esta pieza solo le da consecuencia
  real a un estado que ya existe y hoy es un gesto vacío.
- **Disparador 2 (roce social)**: SOLO entre conscientes (gnomo hoy).
  Decisión explícita de NO ampliar a las demás especies, dado el
  trabajo de estabilización de población cerrado hoy mismo (más
  drenaje de `Necesidades.seguridad` aplicado de forma universal
  podría reabrir la fragilidad de conejo/ardilla/lobo que tanto costó
  mitigar).
- **Roce social modulado por proximidad + agresividad combinada +
  gradiente de estrés** (`1 - PoolMental.estabilidad` de cualquiera de
  los dos), no por un umbral duro ni por competencia real de recursos
  — el mismo pool que ya dispara la crisis, aquí como modulador
  continuo de probabilidad en vez de umbral binario.

## Alcance

**Dentro:**

1. Refactor de `_resolver_posible_intruso`: extraer el bloque desde el
   cálculo de urgencia hasta la aplicación de consecuencias en una
   función compartida `_resolver_conflicto_entre(gestor, mundo, a_id,
   b_id, temperamento_a, temperamento_b, tick_actual) ->
   ResultadoDisputa`. `_resolver_posible_intruso` pasa a ser un wrapper
   delgado: localizar refugio + intruso, delegar en el helper.
2. `_calcular_crisis_violenta`: cuando la entidad más cercana está a
   distancia 0 (ya en la misma celda — contacto real, no solo
   aproximación), resolver con el helper compartido en vez de seguir
   devolviendo movimiento hacia ella.
3. Nuevo método `_procesar_roce_social(gestor, mundo, tick_actual)`,
   llamado UNA VEZ por `ejecutar()` (no por entidad): agrupa
   conscientes por `(x, y, zona_idx)`; para cada par que comparte
   celda, sortea la probabilidad de fricción y resuelve con el helper
   si dispara.
4. `config/comportamiento.yaml`, sección `conflicto`:
   `probabilidad_base_roce_social`, `peso_agresividad_roce`,
   `peso_estres_roce` (las tres PROVISIONAL).
5. Tests dirigidos de las tres piezas + verificación obligatoria contra
   el motor real.

**Fuera de alcance, explícito:**

- Cualquier disparador de "robo"/agravio por recurso escaso — círculo
  futuro distinto, mismo resolutor compartido, sin construir aquí.
- Cualquier sistema que LEA `Relaciones` como consecuencia de esta
  pieza para modular comportamiento — este círculo solo ESCRIBE (mismo
  patrón que rencor/amistad ya existentes). El único consumidor lector
  de `Relaciones` sigue siendo pareja estable (círculo 4b, ya cerrado).
- `Accion.SOCIALIZAR` / ocio consciente — pieza independiente del mismo
  informe, sin dependencia de esta ni viceversa.
- Sonido físico, memoria espacial compartida entre conscientes,
  reputación/rumor sobre liderazgo — piezas restantes del informe
  original, cada una su propio círculo futuro, sin tocar aquí.
- Cambiar `_tipo_crisis` o los umbrales de cuándo se entra en
  CRISIS_VIOLENTA — sin tocar; solo se le da consecuencia al estado ya
  existente, no se cambia cuándo ocurre.

## Arquitectura

### Refactor: resolutor compartido

```python
def _resolver_conflicto_entre(
    self, gestor, mundo, a_id, b_id, temperamento_a, temperamento_b, tick_actual,
) -> ResultadoDisputa:
    """Extraído de _resolver_posible_intruso (conflicto por refugio
    ocupado, 2026-08-31). Calcula urgencia (1 - Necesidades.seguridad),
    mismo_grupo (vía asentamiento_de), son_familia (vía
    es_familia_directa) y bono_arma (vía _bono_arma_empunada) para
    ambas partes, resuelve con resolver_disputa, y aplica las
    consecuencias (drenaje de Necesidades.seguridad + rencor vía
    _aplicar_rencor) según el desenlace -- CEDE_A/CEDE_B/ENFRENTAMIENTO/
    COMPARTE, mismas cuatro ramas que _resolver_posible_intruso ya
    tenía. Simétrico: no importa cuál de los dos se pase como 'a' o
    'b', el resultado y las consecuencias son coherentes en ambos
    sentidos. Devuelve el ResultadoDisputa para que el llamador decida
    si necesita reaccionar a él (hoy ninguno lo hace, pero se expone
    por si un disparador futuro lo necesita)."""
```

`_resolver_posible_intruso` conserva íntegra su lógica de localizar el
refugio propio y encontrar un intruso en esa celda; en cuanto identifica
`intruso_id`, delega el resto en `_resolver_conflicto_entre`.

### Disparador 1 — CRISIS_VIOLENTA con contacto

`_entidad_cercana_cualquiera` hoy solo devuelve la posición del
candidato más cercano, no su id — necesita una variante (o ampliarse)
para devolver también el id, ya que el resolutor exige ambos ids. Sin
afectar a `_calcular_huida_erratica`, que solo necesita la posición.

```python
def _calcular_crisis_violenta(
    self, gestor, mundo, entidad_id, pos_x, pos_y, radio, zona_idx=0,
    temperamento=None, tick_actual=0,
) -> tuple[int, int]:
    objetivo_id, objetivo_pos = self._entidad_cercana_cualquiera_con_id(
        gestor, entidad_id, pos_x, pos_y, radio, zona_idx
    )
    if objetivo_id is None:
        return self._paso_aleatorio()
    if objetivo_pos == (pos_x, pos_y):  # contacto real, no solo cercanía
        temp_objetivo = gestor.obtener_componente(objetivo_id, Temperamento)
        if temp_objetivo is not None:
            self._resolver_conflicto_entre(
                gestor, mundo, entidad_id, objetivo_id,
                temperamento, temp_objetivo, tick_actual,
            )
        return (0, 0)
    return self._acercarse_a(pos_x, pos_y, *objetivo_pos)
```

Requiere pasar `mundo` y `temperamento` a `_calcular_crisis_violenta`
(hoy no los recibe) — cambio de firma menor, ya se le pasa
`temperamento` a otras funciones de cálculo (`_calcular_huida`,
`_calcular_dormir`) desde el mismo punto de despacho. Actualizar
también la llamada real en el bucle de despacho (`sistema_movimiento.py`,
rama `elif accion == Accion.CRISIS_VIOLENTA:`) para pasar `mundo`,
`temperamento` y `tick_actual` (ya disponibles en ese scope, mismo
patrón que otras ramas que ya los reciben).

### Disparador 2 — roce social

```python
def _procesar_roce_social(self, gestor, mundo, tick_actual) -> None:
    """Una vez por ejecutar(), no por entidad -- agrupa conscientes por
    celda+zona exacta, sortea fricción para cada par que coincide."""
    por_celda: dict[tuple[int, int, int], list[int]] = {}
    for eid in gestor.entidades_con(Posicion, Temperamento, CapacidadMental, PoolMental, Necesidades):
        cap_mental = gestor.obtener_componente(eid, CapacidadMental)
        if cap_mental.consciencia < self.umbral_consciencia_agencia:
            continue
        pos = gestor.obtener_componente(eid, Posicion)
        por_celda.setdefault((pos.x, pos.y, pos.zona_idx), []).append(eid)

    for ids in por_celda.values():
        if len(ids) < 2:
            continue
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a_id, b_id = ids[i], ids[j]
                temp_a = gestor.obtener_componente(a_id, Temperamento)
                temp_b = gestor.obtener_componente(b_id, Temperamento)
                pm_a = gestor.obtener_componente(a_id, PoolMental)
                pm_b = gestor.obtener_componente(b_id, PoolMental)
                estres = max(1.0 - pm_a.estabilidad, 1.0 - pm_b.estabilidad)
                prob = (
                    self.probabilidad_base_roce_social
                    + self.peso_agresividad_roce * (temp_a.agresividad + temp_b.agresividad) / 2.0
                    + self.peso_estres_roce * estres
                )
                if self.rng.random() < prob:
                    self._resolver_conflicto_entre(
                        gestor, mundo, a_id, b_id, temp_a, temp_b, tick_actual,
                    )
```

Llamado una vez desde `ejecutar()`, **al principio, antes del bucle
principal de movimiento por entidad** — usa las posiciones tal como
quedaron al cierre del tick anterior, igual criterio que el conflicto
por refugio ocupado (que también resuelve sobre la posición vigente al
empezar el tick, no sobre una posición a medio actualizar por el propio
bucle). No compite por ninguna `Accion`, es un chequeo pasivo
independiente de qué esté haciendo cada consciente ese tick.

## Config nueva (PROVISIONAL, sin calibrar)

```yaml
conflicto:
  # ... (umbral_cohesion_comparte, bono_cohesion_familia, etc. ya existentes)
  probabilidad_base_roce_social: 0.01
  peso_agresividad_roce: 0.05
  peso_estres_roce: 0.05
```

Elegidos para que el roce social sea sensiblemente más frecuente que
CRISIS_VIOLENTA (estado raro) pero no dispare en la mayoría de ticks
entre todo par de conscientes que conviva en un mismo asentamiento —
sin verificar contra el motor todavía, mismo criterio "provisional" que
el resto del catálogo de conflicto.

## Testing

- Refactor: los tests existentes que cubren el conflicto por refugio
  ocupado deben seguir en verde sin cambios de comportamiento — mismo
  resultado en los cinco escenarios ya verificados (propietario
  dominante, intruso dominante, empate agresivo, mismo asentamiento con
  alta cohesión, temperamento parejo con seguridad ya baja) antes y
  después del refactor.
- CRISIS_VIOLENTA + contacto: arnés dirigido — dos entidades en la
  misma celda, una despachada en CRISIS_VIOLENTA, confirma que se llama
  a `_resolver_conflicto_entre` y devuelve `(0, 0)` (no se mueve tras
  resolver); confirma que sigue aproximándose sin resolver nada cuando
  la distancia es > 0 (comportamiento actual intacto).
- Roce social: arnés dirigido — la probabilidad efectiva sube con
  agresividad/estrés combinados (comparar dos pares con distinta
  agresividad/estabilidad bajo el mismo rng semillado); ningún efecto
  si solo uno de los dos es consciente (queda fuera del filtro de
  agrupación); un mismo par no se procesa dos veces en el mismo tick.
- **Verificación obligatoria contra el motor real, no opcional**
  (mismo criterio ya fallado una vez en este arco, círculo 2 de
  "hilo individual" — el spec debe forzar el paso, no dejarlo a
  criterio del agente): `BOSQUE_AUTO_TICKS`, midiendo explícitamente
  (no solo "no lanzó excepción") cuántas resoluciones de roce social y
  cuántas de CRISIS_VIOLENTA+contacto ocurren de verdad en juego libre,
  y si `Relaciones` de la población muestra más fluctuación real que
  antes de esta pieza — dado el precedente de círculos correctos pero
  casi invisibles en juego libre en este mismo arco (asentamiento,
  pareja, parentesco), reportar la cifra real con honestidad aunque
  vuelva a ser baja.

## Pendiente real tras esta pieza

- `probabilidad_base_roce_social`/`peso_agresividad_roce`/
  `peso_estres_roce` PROVISIONALES, sin calibrar contra el harness
  completo.
- Robo/agravio por recurso escaso: disparador futuro del mismo
  resolutor compartido, sin construir.
- Sonido físico, memoria espacial compartida entre conscientes, ocio
  consciente + `Accion.SOCIALIZAR`, reputación/rumor sobre liderazgo:
  piezas restantes del informe original evaluado el 2026-09-06, cada
  una su propio círculo futuro, ninguna empezada.
- Ningún sistema nuevo LEE `Relaciones` como resultado de este círculo
  — sigue siendo solo-escritura salvo pareja estable (círculo 4b, ya
  cerrado, sin relación con este).
