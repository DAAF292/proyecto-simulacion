# Rumor social — propagación de opiniones sobre terceros (5a) — diseño

Fecha: 2026-09-06. Círculo 5a de la quinta y última pieza descompuesta
del informe externo de "capa de comunicación" (ver
`docs/superpowers/specs/2026-09-06-conflicto-verbal-design.md` para el
contexto completo de la descomposición). Partida en dos círculos por el
mismo criterio ya usado con pareja estable y sonido físico — este
círculo es el primitivo de confianza/opinión en sí; el círculo 5b
(lealtad + liderazgo con inercia real, spec aparte:
`docs/superpowers/specs/2026-09-06-lealtad-liderazgo-design.md`) es su
primer consumidor real, y depende de que este esté ya mergeado.

Sin dependencia de conflicto verbal / memoria espacial compartida / ocio
consciente / sonido físico (ya cerrados, PR #20-#24).

## Motivación

El informe original: *"la propagación de rumores (transferencia de
afinidades de un tercero) alterará el estatus social"*. Diego lo
reencuadró en conversación como **cimiento para relaciones más
complejas a futuro** (mercadería, encargos, confiar en alguien para
pedirle o contarle algo) — no una pieza aislada de una sola vez, sino
un primitivo genérico de "opinión de segunda mano" reutilizable, mismo
espíritu que `Relaciones` cuando se diseñó como cimiento del arco
"hilo individual".

## Decisiones ya cerradas con Diego

- **Disparo**: mismo mecanismo ya usado tres veces en este arco —
  `_agrupar_conscientes_por_celda` (roce social, memoria compartida),
  reutilizado tal cual, sin cambios.
- **Modulado por `sociabilidad` del que comparte**, misma línea literal
  ya reutilizada en memoria compartida y ocio consciente
  (`rng.random() < temperamento.sociabilidad`) — sin factor nuevo.
- **Contenido del rumor**: el emisor comparte su propia opinión
  (afinidad) sobre un TERCERO elegido al azar de entre quienes ya
  conoce (`Relaciones.vinculos`) — nunca sobre sí mismo (no está en su
  propio `vinculos`) ni sobre el propio receptor (excluido
  explícitamente: contarle a alguien tu opinión sobre ÉL no es un
  rumor, sería una confrontación directa, fuera de alcance aquí).
- **Sin rumor si el emisor no conoce a nadie más que al receptor** —
  si tras excluir al receptor no queda ningún tercero candidato, esa
  dirección simplemente no transmite nada ese tick.
- **Degradación de segunda mano, mismo criterio que memoria espacial
  compartida**: el receptor NO adopta la opinión del emisor de golpe —
  su propia afinidad hacia ese tercero se desplaza una FRACCIÓN
  (`peso_credibilidad_rumor`, PROVISIONAL) hacia la del emisor, no se
  sobrescribe. Sin opinión previa, el receptor parte de neutral (0.0).
- **Cero funciones nuevas en `nucleo/relaciones.py`** — el desplazamiento
  se calcula como un delta normal en el llamador
  (`sistema_movimiento.py`) y se pasa tal cual a `ajustar_afinidad`
  (ya existente, ya usado por rencor/amistad/concepción/socializar).

## Alcance

**Dentro:**

1. Nuevo método `_procesar_rumor(gestor, por_celda, tick_actual)` en
   `SistemaMovimiento`, tercera pasada sobre `por_celda` (junto a
   `_procesar_roce_social` y `_procesar_memoria_compartida`, todas
   construidas sobre la misma agrupación calculada una vez por tick en
   `ejecutar()`).
2. `_compartir_rumor(gestor, emisor_id, receptor_id, tick_actual)`:
   sortea con la sociabilidad del emisor; si dispara, elige un tercero
   al azar de `Relaciones.vinculos` del emisor (excluyendo al receptor),
   calcula `delta = peso_credibilidad_rumor * (opinion_emisor -
   opinion_actual_receptor)`, y llama `ajustar_afinidad(rel_receptor,
   tercero_id, delta, tick_actual, capacidad_vinculos(...))`.
3. `config/relaciones.yaml`: `peso_credibilidad_rumor` nueva
   (PROVISIONAL).
4. Tests dirigidos + verificación obligatoria contra el motor real.

**Fuera de alcance, explícito:**

- Cualquier consumidor real del rumor — es el círculo 5b, spec aparte,
  no se toca `nucleo/asentamiento.py` aquí.
- Distorsión, exageración, o pérdida de información al propagarse
  varias veces (rumor de rumor) — la degradación de segunda mano ya
  existente (fracción hacia la opinión reportada) es suficiente para
  este círculo; encadenar rumores sobre rumores sin límite sería una
  fuente de complejidad no pedida.
- Cualquier gating por especie más allá del ya heredado de
  `_agrupar_conscientes_por_celda` (solo conscientes).
- Mercadería, encargos, o cualquier otro consumidor futuro del
  primitivo de confianza — quedan fuera, mencionados solo como
  motivación de por qué este círculo se diseña genérico.

## Arquitectura

```python
def _procesar_rumor(
    self, gestor: GestorEntidades, por_celda: dict[tuple[int, int, int], list[int]],
    tick_actual: int,
) -> None:
    """Tercera pasada sobre la agrupacion de conscientes por celda
    (2026-09-06, rumor social -- ver
    docs/superpowers/specs/2026-09-06-rumor-social-design.md): cada
    direccion (emisor->receptor) se sortea por separado con la
    sociabilidad del emisor, mismo patron que _procesar_memoria_compartida."""
    for ids in por_celda.values():
        if len(ids) < 2:
            continue
        for i in range(len(ids)):
            for j in range(len(ids)):
                if i == j:
                    continue
                self._compartir_rumor(gestor, ids[i], ids[j], tick_actual)


def _compartir_rumor(
    self, gestor: GestorEntidades, emisor_id: int, receptor_id: int, tick_actual: int,
) -> None:
    temp_emisor = gestor.obtener_componente(emisor_id, Temperamento)
    if temp_emisor is None or self.rng.random() >= temp_emisor.sociabilidad:
        return
    rel_emisor = gestor.obtener_componente(emisor_id, Relaciones)
    rel_receptor = gestor.obtener_componente(receptor_id, Relaciones)
    cap_receptor = gestor.obtener_componente(receptor_id, CapacidadMental)
    if rel_emisor is None or rel_receptor is None or cap_receptor is None:
        return
    candidatos = [tid for tid in rel_emisor.vinculos if tid != receptor_id]
    if not candidatos:
        return
    tercero_id = self.rng.choice(candidatos)
    opinion_emisor = rel_emisor.vinculos[tercero_id].afinidad
    opinion_actual = (
        rel_receptor.vinculos[tercero_id].afinidad
        if tercero_id in rel_receptor.vinculos else 0.0
    )
    delta = self.peso_credibilidad_rumor * (opinion_emisor - opinion_actual)
    capacidad = capacidad_vinculos(cap_receptor, self.config)
    ajustar_afinidad(rel_receptor, tercero_id, delta, tick_actual, capacidad)
    self._stats_rumores_propagados += 1
```

`ejecutar()` llama las tres pasadas sobre el mismo `por_celda`:
`_procesar_roce_social`, `_procesar_memoria_compartida`,
`_procesar_rumor` — orden sin importancia real entre ellas (caminos de
efecto independientes).

Nota de implementación: si `emisor_id == tercero_id` fuera posible
(el emisor apareciendo en su propio `vinculos`), excluirlo también —
en la práctica no debería ocurrir (nada escribe una entidad hacia sí
misma hoy), pero es una comprobación defensiva barata de incluir.

## Config nueva (`config/relaciones.yaml`, PROVISIONAL)

```yaml
relaciones:
  # ... (existentes)
  peso_credibilidad_rumor: 0.15  # PROVISIONAL -- fraccion del camino que el
    # receptor recorre hacia la opinion reportada del emisor, no una
    # sustitucion completa. Mismo espiritu que la degradacion de segunda
    # mano de memoria espacial compartida.
```

## Testing

- `_compartir_rumor`: transfiere y desplaza correctamente cuando la
  tirada del emisor dispara; ningún efecto si falla; ningún efecto si
  el emisor no conoce a nadie más que al receptor; el tercero nunca es
  el propio receptor; el receptor sin opinión previa parte de 0.0
  (verificar el valor exacto resultante); el receptor con opinión
  previa se desplaza una fracción, no se sobrescribe (verificar con una
  opinión previa contraria a la del emisor).
- `_procesar_rumor`: direcciones independientes (igual que memoria
  compartida) — un par de conscientes puede transmitir en una
  dirección y no en la otra.
- **Verificación obligatoria contra `BOSQUE_AUTO_TICKS`, no opcional**:
  medir cuántos rumores se propagaron de verdad, y si algún consciente
  terminó con una opinión sobre un tercero que él mismo nunca formó
  directamente (evidencia de que el rumor se ejerce en juego libre, no
  solo en el arnés dirigido). Reportar la cifra con honestidad aunque
  sea baja.

## Pendiente real tras esta pieza

- `peso_credibilidad_rumor` PROVISIONAL, sin calibrar.
- Círculo 5b (lealtad + liderazgo) es el consumidor real, spec aparte,
  siguiente paso inmediato tras mergear esto.
- Mercadería/encargos/confianza para pedir-o-contar-algo — ideas
  futuras mencionadas por Diego como motivación, ninguna diseñada
  todavía; este círculo solo construye el primitivo, no sus usos
  futuros.
