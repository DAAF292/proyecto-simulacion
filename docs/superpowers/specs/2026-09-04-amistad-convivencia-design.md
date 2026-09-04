# Amistad por convivencia en el asentamiento — diseño

Fecha: 2026-09-04. Tercer círculo del arco "hilo individual" (círculo 1,
nombre propio real, y círculo 2, cimiento `Relaciones` + rencor, ya
cerrados — ver `docs/superpowers/specs/2026-09-04-nombre-propio-design.md`,
`docs/superpowers/specs/2026-09-04-cimiento-relaciones-design.md` y
CLAUDE.md). Círculos siguientes del mismo arco (pareja estable, familia
derivada, biografía consultable, desarrollo personal) quedan
deliberadamente fuera de este spec.

## Motivación

El cimiento `Relaciones` (círculo 2) solo tiene un consumidor real hoy:
rencor, siempre negativo, disparado por conflicto (refugio ocupado). No
existe ningún camino que produzca afinidad POSITIVA — el campo lo admite
por diseño (`Vinculo.afinidad` en `[-1.0, 1.0]`) pero ningún código lo
usa todavía. Este círculo cierra ese hueco con amistad: afinidad
positiva emergente de convivencia real en el mismo asentamiento, sin
ninguna acción nueva de la Utility AI — efecto colateral de vivir juntos,
no una decisión consciente de "hacerse amigos".

## Decisiones ya cerradas con Diego (contexto, no reabrir en el plan)

- **Disparador: convivencia diaria en el asentamiento**, no reutilizar la
  rama `COMPARTE` del conflicto por refugio ocupado (alternativa más
  pequeña que se planteó y se descartó explícitamente) — Diego prefirió
  el mecanismo más fiel a "amistad emerge de tiempo compartido" aunque
  sea círculo más grande.
- **Sin excluir parentesco**: un padre y su hijo adulto conviviendo en el
  mismo asentamiento SÍ acumulan amistad por convivencia, además de su
  vínculo de sangre ya existente por separado (`Identidad.id_madre`/
  `id_padre`) — son capas distintas por diseño, coherente con la decisión
  ya cerrada de "familia como dos capas separadas". El mecanismo de este
  círculo no consulta parentesco en absoluto.
- **Verificación contra el motor real es OBLIGATORIA para el pipeline
  en este círculo**, no opcional — lección aprendida en el círculo
  anterior (el agente se saltó `BOSQUE_AUTO_TICKS` pese a que el spec ya
  lo pedía). El propio encargo (no solo este spec) debe nombrarlo como
  paso explícito.

## Alcance

**Dentro de esta pieza:**
1. Función de acreción diaria de amistad, cadencia diaria, en
   `sistemas/sistema_asentamiento.py` (mismo sistema que ya recalcula
   `mundo.asentamientos` cada día).
2. Nueva constante de config (`relaciones.delta_amistad_convivencia_dia`).
3. Verificación real obligatoria (ver Testing).

**Fuera de alcance, explícito:**
- Cualquier lectura de `Relaciones` para cambiar comportamiento (p.ej.
  que la amistad module `indice_asertividad_social`, o que dos amigos se
  ayuden en una disputa) — círculo futuro, este círculo solo ESCRIBE.
- Pareja estable, familia derivada, biografía — círculos futuros
  distintos, ya identificados en el arco.
- Cualquier límite de tamaño de asentamiento para esta acreción (sin
  cap, O(N²) aceptado a la escala actual) — si algún día un asentamiento
  crece mucho, es un problema de rendimiento a resolver entonces, no
  ahora.
- Decaimiento de la amistad con el tiempo (o con la distancia, si dos
  antiguos convivientes se separan) — sin él por ahora, YAGNI, mismo
  criterio ya aplicado al rencor en el círculo anterior.
- Cualquier interacción entre amistad y rencor ya existentes hacia la
  MISMA entidad (p.ej. si alguien tiene rencor y a la vez gana amistad
  por convivencia hacia la misma persona, `ajustar_afinidad` ya suma y
  clampa correctamente sin cambios — no hace falta ninguna lógica nueva
  de "prioridad" entre ambos).

## Arquitectura

### Acreción diaria (`sistemas/sistema_asentamiento.py`)

Justo después de recalcular `mundo.asentamientos` cada día (mismo punto
donde ya se recalcula membresía, liderazgo y aporte al almacén — ver
"Interacción física y social" en CLAUDE.md), para cada `Asentamiento`:

1. Filtrar sus miembros a los que sean conscientes
   (`CapacidadMental.consciencia >= decision.umbral_consciencia_agencia`,
   mismo umbral ya reutilizado en los dos círculos anteriores de este
   arco).
2. Para cada PAR distinto de esos miembros conscientes (sin repetir un
   par en ambos órdenes), llamar `ajustar_afinidad` en AMBAS direcciones
   con `delta = relaciones.delta_amistad_convivencia_dia` (positivo),
   usando `capacidad_vinculos(cap_mental, config)` de cada uno
   respectivamente (mismo patrón ya usado por rencor: la capacidad es
   propia de quien recibe el ajuste, no compartida entre el par).
3. `tick_actual` para `ultima_actualizacion_tick`: el tick del día en
   curso (mismo que ya usa el resto de la cadencia diaria de este
   sistema).

Sin ninguna acción nueva de la Utility AI — esto ocurre siempre que
existan asentamientos con 2+ miembros conscientes, sin que ningún
individuo "decida" hacerse amigo de nadie.

### Config (`config/relaciones.yaml`, sección ya existente)

```yaml
relaciones:
  # ... (min_vinculos_por_individuo, max_vinculos_por_individuo,
  #      delta_rencor_disputa, ya existentes del círculo 2)
  delta_amistad_convivencia_dia: 0.05  # PROVISIONAL, sin calibrar
```

Con este valor, dos miembros del mismo asentamiento durante 20 días
consecutivos llegarían al tope de afinidad `1.0` -- solo como referencia
de orden de magnitud, no un objetivo de diseño calibrado.

## Persistencia

Sin cambios de esquema — reutiliza `Relaciones.vinculos` ya persistido
desde el círculo 2, sin ningún campo nuevo.

## Testing

Mismo criterio de "ley física" que el resto de tests del proyecto:

- La función de acreción diaria: dos miembros conscientes del mismo
  asentamiento ganan afinidad positiva mutua tras un día de convivencia;
  un miembro no-consciente del mismo asentamiento no escribe ni recibe
  nada; dos individuos de asentamientos DISTINTOS no ganan nada entre sí
  aunque ambos sean conscientes; un asentamiento con un único miembro
  consciente no genera ningún par (sin errores).
- Interacción con rencor ya existente: un par que ya tenía rencor
  (afinidad negativa) hacia el otro y convive en el mismo asentamiento
  ve su afinidad subir (menos negativa o positiva) tras la acreción,
  sin ningún caso especial en el código — confirma que `ajustar_afinidad`
  ya lo maneja bien sin cambios.
- Tope de capacidad: la acreción de amistad respeta el mismo tope y la
  misma purga FIFO ya implementados en `ajustar_afinidad` — un individuo
  con muchos convivientes y capacidad limitada purga el vínculo más
  antiguo igual que ya hace el rencor.

**Verificación contra el motor real, OBLIGATORIA, no opcional**:
`BOSQUE_AUTO_TICKS` con población real corriendo varios días, inspeccionando
la BD tras la corrida para confirmar que al menos un asentamiento real
generó al menos una entrada de afinidad POSITIVA real en
`Relaciones.vinculos` entre dos miembros conscientes. Si tras una corrida
razonable (varios miles de ticks) no aparece ningún asentamiento con 2+
miembros conscientes formado de forma espontánea, señalarlo explícitamente
como hallazgo (no forzar un escenario artificial para "que pase algo" sin
avisar que en juego libre no ocurrió).

## Pendiente real tras esta pieza

- `relaciones.delta_amistad_convivencia_dia` PROVISIONAL, sin calibrar
  contra el harness completo.
- Ningún consumidor lee la afinidad (positiva o negativa) para cambiar
  comportamiento todavía — círculo futuro real.
- Decaimiento de amistad/rencor con el tiempo — sin resolver, mismo hueco
  honesto ya señalado en el círculo anterior.
- Pareja estable, familia derivada, biografía — círculos futuros del
  mismo arco, sin empezar.
- Fauna sigue sin `Relaciones` real — aplazado, no descartado.
