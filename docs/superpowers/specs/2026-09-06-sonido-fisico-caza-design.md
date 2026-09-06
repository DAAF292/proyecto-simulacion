# Sonido físico — pista de caza para depredadores (4b) — diseño

Fecha: 2026-09-06. Círculo 4b de la cuarta pieza descompuesta del
informe externo de "capa de comunicación" — segunda mitad de "sonido
físico", partida en dos por decisión explícita de Diego dado el tamaño
real de la pieza completa (ver
`docs/superpowers/specs/2026-09-06-sonido-fisico-amenaza-design.md`
para el contexto completo, la motivación original, y el círculo 4a ya
diseñado: infraestructura de sonido + detección temprana de amenaza).

**Dependencia dura**: este círculo exige que 4a esté YA MERGEADO —
reutiliza `nucleo/sonido.py:sonido_mas_cercano` tal cual, sin tocarlo.
No se entrega al pipeline hasta confirmar que 4a está en `master`.

## Motivación

Idea de Diego en la conversación de diseño de 4a: el sonido no debería
ser solo una señal de peligro — un depredador debería poder usarlo
como pista de caza, dándole un propósito real más allá de la huida.
`_calcular_forrajeo` (usado por `Accion.COMER`, cualquier especie) ya
busca `Necromasa` cercana automáticamente en el vecindario — así que
si un depredador llega a investigar un sonido y encuentra un cadáver
de una caza ajena ya resuelta, el carroñeo ya funciona sin tocar nada
de "cómo se come". Lo único que falta es la parte de **llegar hasta
ahí**: un fallback de movimiento cuando `Accion.CAZAR` no encuentra
presa válida por los medios normales (percepción directa, memoria).

## Decisiones ya cerradas con Diego

- **Fallback en `_calcular_caza`, no una `Accion` nueva** — cuando
  `presas` queda vacío (ningún objetivo válido dentro del radio
  sensorial normal), en vez de caer directo a `_paso_aleatorio()`, se
  intenta primero `sonido_mas_cercano(...)`.
- **Incertidumbre real, aceptada explícitamente** — al llegar al punto
  del sonido puede no haber nada (la presa escapó hace tiempo, o era
  un `ENFRENTAMIENTO` sin cadáver), puede haber una presa real todavía
  cerca (un encuentro de caza genuino, resuelto por los sistemas ya
  existentes sin cambios), o un cadáver de una caza ajena (carroñeo
  automático vía `_calcular_forrajeo`, también sin cambios). Ningún
  "guion": el motor no garantiza premio, solo da una pista razonable.
- **Sin gating por consciencia** — aplica a cualquier especie con
  `medio_alimentacion == "cazar"` (lobo hoy), igual que el resto de
  `_calcular_caza` ya es agnóstico de consciencia.
- **Reutiliza `radio_busqueda_maxima_sonido`** (ya definido en 4a,
  `config/combate.yaml:sonido`) — sin ninguna constante nueva de
  config. El alcance real percibido sigue siendo dinámico (magnitud
  del evento + agudeza sensorial del propio cazador), exactamente la
  misma fórmula que ya usa la detección de amenaza en 4a.

## Alcance

**Dentro:**

1. `sistemas/sistema_movimiento.py:_calcular_caza`: al final, donde hoy
   `if not presas: return self._paso_aleatorio()`, se intenta primero
   `sonido_mas_cercano(...)` (importado de `nucleo/sonido.py`, ya
   existente desde 4a) y, si devuelve una posición, se avanza hacia
   ella con `_acercarse_a`; si no, cae a `_paso_aleatorio()` como hoy.
2. Ampliar la firma de `_calcular_caza` con tres parámetros nuevos:
   `zona` (objeto `ZonaBioma`, para poder consultar celdas — hoy la
   función no lo recibe, solo `zona_idx`), `tick_actual`, y
   `agudeza_sensorial: float` (el escalar del cazador, mismo patrón que
   `peso_cazador: float` ya recibido tal cual en vez del componente
   completo).
3. Actualizar el despacho en `ejecutar()` (la rama `elif accion ==
   Accion.CAZAR:`) para pasar `zona`, `tick_actual` y
   `dims.agudeza_sensorial` en la llamada.
4. Tests dirigidos + verificación obligatoria contra el motor real.

**Fuera de alcance, explícito:**

- Cualquier cambio a `nucleo/sonido.py` — se consume tal cual, tal y
  como 4a lo dejó diseñado para este propósito.
- Cualquier cambio a `_calcular_forrajeo`/carroñeo/`Necromasa` — el
  "premio" de encontrar un cadáver ya funciona solo por percepción
  normal una vez el cazador esté cerca, sin ninguna conexión especial
  que construir aquí.
- Cualquier prioridad o preferencia entre "ir al sonido" y otras
  acciones — esto es un fallback DENTRO de `_calcular_caza`, no cambia
  cuándo la Utility AI elige `CAZAR` en primer lugar.
- Ninguna constante de config nueva — reutiliza
  `radio_busqueda_maxima_sonido` de 4a sin más.

## Arquitectura

```python
def _calcular_caza(
    self, gestor, cazador_id, especie, pos_x, pos_y, peso_cazador, radio,
    zona_idx=0, zona=None, tick_actual=0, agudeza_sensorial=0.0,
) -> tuple[int, int]:
    ...  # filtros de presa valida (viabilidad energetica, detectabilidad,
         # techo de manada) sin cambios
    if not presas:
        if zona is not None:
            objetivo_sonido = sonido_mas_cercano(
                zona, pos_x, pos_y, self.radio_busqueda_maxima_sonido,
                tick_actual, agudeza_sensorial, self.config,
            )
            if objetivo_sonido is not None:
                return self._acercarse_a(pos_x, pos_y, *objetivo_sonido)
        return self._paso_aleatorio()

    presas.sort()
    _, px, py = presas[0]
    return self._acercarse_a(pos_x, pos_y, px, py)
```

`self.radio_busqueda_maxima_sonido` ya se cachea en `__init__` desde
4a (constante compartida con el consumidor de amenaza) — sin volver a
leerla de `self.config` en cada llamada.

## Testing

- Sin presa válida y con sonido reciente dentro de alcance: el cazador
  se dirige hacia la posición del sonido (`_acercarse_a`), no hacia
  `_paso_aleatorio()`.
- Sin presa válida y sin sonido activo (o fuera de alcance): cae a
  `_paso_aleatorio()`, comportamiento idéntico a antes de 4a/4b.
- Con presa válida disponible: el sonido NUNCA se consulta (el camino
  normal ya resuelve antes de llegar al fallback) — verificar que
  `sonido_mas_cercano` no se llama si `presas` no está vacío (o que su
  resultado se ignora aunque exista un sonido más cercano que la presa
  — la spec no reordena prioridades, presa real > sonido siempre).
- Aplica a cualquier especie con `medio_alimentacion == "cazar"`, no
  solo lobo (verificar con el filtro ya existente, sin gating nuevo).
- **Verificación obligatoria contra `BOSQUE_AUTO_TICKS`, no opcional**:
  medir cuántas veces se usó el fallback de sonido, y de esas, cuántas
  llevaron a un encuentro de caza real, cuántas a carroñeo real, y
  cuántas a nada (pista falsa) — reportar los tres números con
  honestidad, sea cual sea el resultado.

## Pendiente real tras esta pieza

- Con 4a y 4b cerrados, **4 de las 5 piezas del informe de "capa de
  comunicación" quedarían cerradas** — solo faltaría reputación/rumor
  sobre liderazgo.
- Ninguna calibración de `radio_sonido_base`/`peso_referencia_sonido`/
  `duracion_sonido_ticks`/`radio_busqueda_maxima_sonido` contra el
  harness completo (heredado de 4a, sin cambios aquí).
- Ninguna preferencia de "qué sonido perseguir" si hay varios en rango
  simultáneamente distintos entre amenaza (4a) y caza (4b) — cada
  consumidor hace su propia búsqueda independiente, no hay conflicto
  real porque son caminos de decisión distintos (huir vs. cazar) que
  nunca compiten por el mismo turno.
