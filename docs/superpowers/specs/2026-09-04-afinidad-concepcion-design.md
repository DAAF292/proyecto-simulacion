# Afinidad por concepción — diseño

Fecha: 2026-09-04. Círculo 4a del arco "hilo individual" (círculos 1-3,
nombre propio real / cimiento `Relaciones` + rencor / amistad por
convivencia, ya cerrados — ver CLAUDE.md). Escritor mínimo, primera
mitad de "pareja estable" — el círculo 4b (lector: derivar "¿son
pareja?" de la afinidad acumulada + un efecto de comportamiento) queda
deliberadamente fuera de este spec, círculo separado a propósito (mismo
criterio de círculo pequeño ya aplicado tres veces en este arco).

## Motivación

`sistema_reproduccion.py` resuelve la concepción como un instante
puramente momentáneo: dos individuos conciben y no queda ningún vínculo
entre ellos después, más allá de `Gestacion` (transitorio, se consume al
nacer) e `Identidad.id_madre`/`id_padre` en el hijo. No hay ningún rastro
de la relación entre LOS DOS PROGENITORES. Este círculo añade ese
rastro, reutilizando el cimiento `Relaciones` ya construido — la
concepción exitosa también es, ante todo, un momento de vínculo
compartido.

## Decisiones ya cerradas con Diego

- Partido en dos círculos: este (4a, solo escritor) y un futuro 4b
  (lector, con su propio spec cuando se aborde).
- Sin ningún efecto de comportamiento en este círculo — solo se
  escribe afinidad, exactamente igual que rencor y amistad no leen nada
  todavía.

## Alcance

**Dentro:**
1. En `sistemas/sistema_reproduccion.py`, en el punto donde ya se
   resuelve una concepción exitosa (construcción de `Gestacion`, antes
   de emitir el evento `Concepcion`): cada progenitor consciente escribe
   afinidad positiva mutua hacia el otro.
2. Nueva constante `relaciones.delta_afinidad_concepcion` en
   `config/relaciones.yaml`.

**Fuera de alcance, explícito:**
- Cualquier noción de "pareja estable" derivada de la afinidad — círculo
  4b, futuro, spec propia.
- Cualquier efecto de comportamiento (compartir refugio, aportar al
  almacén juntos, prioridad de nada) — círculo 4b.
- Tocar `Gestacion`, el evento `Concepcion`, o el resto de la lógica de
  reproducción (probabilidad de concepción, tamaño de camada, herencia)
  — sin cambios.
- Cualquier interacción con rencor/amistad ya existentes hacia la misma
  pareja — `ajustar_afinidad` ya suma y clampa correctamente sin ningún
  caso especial, igual que en los círculos anteriores.

## Arquitectura

En `sistemas/sistema_reproduccion.py`, en la función donde ya se
construye `Gestacion` tras una concepción exitosa: obtener
`CapacidadMental` de la hembra (hoy no se obtiene ahí — `capacidad_macho`
sí se obtiene ya para la instantánea del padre en `Gestacion`) y
`Relaciones` de ambos progenitores. Para cada progenitor consciente
(`CapacidadMental.consciencia >= decision.umbral_consciencia_agencia`,
mismo umbral ya reutilizado en los tres círculos anteriores de este
arco), llamar `ajustar_afinidad` hacia el otro progenitor con
`delta = relaciones.delta_afinidad_concepcion` (positivo), usando la
`capacidad_vinculos` propia de quien escribe — mismo patrón exacto que
ya usan rencor (`sistema_movimiento.py`) y amistad
(`sistema_asentamiento.py`), sin ninguna función nueva en
`nucleo/relaciones.py`. `tick_actual` para `ultima_actualizacion_tick`:
el mismo `tick_actual` que ya recibe la función (usado también para
`Gestacion.tick_inicio` y el evento `Concepcion`).

Fauna (lobo/conejo/ardilla, no conscientes) sigue sin escribir nada —
mismo criterio ya aplicado en rencor y amistad.

### Config (`config/relaciones.yaml`)

```yaml
relaciones:
  # ... (min/max_vinculos_por_individuo, delta_rencor_disputa,
  #      delta_amistad_convivencia_dia, ya existentes)
  delta_afinidad_concepcion: 0.15  # PROVISIONAL, sin calibrar
```

## Persistencia

Sin cambios de esquema — reutiliza `Relaciones.vinculos` ya persistido.

## Testing

Mismo criterio de "ley física" que el resto del proyecto:

- Una concepción exitosa entre dos progenitores conscientes escribe
  afinidad positiva mutua en ambos sentidos.
- Un progenitor no-consciente (fauna) no escribe nada hacia el otro,
  aunque el otro sí sea consciente y escriba hacia él (mismo criterio ya
  aplicado en rencor/amistad: un consciente escribe aunque la otra parte
  no lo sea).
- Una pareja que ya tenía rencor o amistad previa entre sí ve su
  afinidad ajustarse correctamente por la suma, sin ningún caso especial
  en el código.
- El tope de capacidad y la purga FIFO se respetan igual que en los
  otros dos consumidores.
- No se emite ni se modifica el evento `Concepcion` de ninguna forma.

**Verificación contra el motor real, OBLIGATORIA, no opcional** (misma
exigencia que el círculo anterior, que funcionó bien): `BOSQUE_AUTO_TICKS`
con población real, inspeccionando la BD tras la corrida para confirmar
que al menos una concepción real entre dos gnomos conscientes produjo
una entrada de afinidad positiva real en `Relaciones.vinculos`. Si no
ocurre en una corrida razonable, señalarlo explícitamente como hallazgo,
no forzar un escenario artificial sin avisar.

## Pendiente real tras esta pieza

- `relaciones.delta_afinidad_concepcion` PROVISIONAL, sin calibrar.
- Círculo 4b (pareja estable derivada + efecto de comportamiento) —
  siguiente pieza real, spec propia, sin empezar.
- Familia derivada, biografía consultable — círculos futuros del mismo
  arco, sin empezar.
- Fauna sigue sin `Relaciones` real — aplazado, no descartado.
