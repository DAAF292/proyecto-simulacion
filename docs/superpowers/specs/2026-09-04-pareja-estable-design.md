# Pareja estable derivada + bono de cercanía — diseño

Fecha: 2026-09-04. Círculo 4b del arco "hilo individual" (círculos 1-3 y
4a, ya cerrados — ver CLAUDE.md). Segunda mitad de "pareja estable": el
círculo 4a (`docs/superpowers/specs/2026-09-04-afinidad-concepcion-design.md`)
ya escribe afinidad positiva mutua entre progenitores al concebir; este
círculo es el primero de todo el arco que LEE la afinidad acumulada para
decidir algo.

## Motivación

Hasta ahora, `Relaciones` solo se escribe (rencor negativo, amistad
positiva, afinidad por concepción) — ningún sistema lo consulta para
cambiar comportamiento. "Pareja estable" es el concepto que el informe
original de alternativas ya proponía leer de la afinidad acumulada en
vez de decretarla por evento: no existe un componente `Pareja` ni una
institución fija, es un HECHO que se lee cada vez que hace falta, igual
que `mundo.asentamientos` se deriva completo cada día sin persistir
identidad propia.

## Decisiones ya cerradas con Diego

- **Derivación mutua**: dos individuos son pareja si la afinidad
  supera un umbral en AMBAS direcciones (A hacia B Y B hacia A) — no
  basta con una sola dirección.
- **Primer efecto de comportamiento: bono de confort/seguridad por
  cercanía**, mismo patrón aditivo ya usado por refugio/fogata en
  `sistema_necesidades.py` — no se tocan construcción, movimiento, ni
  asentamiento/almacén en este círculo.
- **Limitación honesta, aceptada explícitamente, no resuelta aquí**: sin
  decaimiento de afinidad implementado en este arco (decisión ya
  tomada en el círculo 2), una pareja formada no puede "diluirse" solo
  por dejar de convivir — solo un evento negativo real (rencor) podría
  bajar la afinidad después. El propio informe original hablaba de
  "si no se refuerza, se diluye"; hoy eso solo es parcialmente cierto.

## Alcance

**Dentro:**
1. `nucleo/relaciones.py`: `son_pareja()` (pura) y `pareja_presente()`
   (búsqueda por celda exacta, mismo patrón que `hay_refugio_en`/
   `fogata_en` de `nucleo/fuego.py`).
2. `relaciones.umbral_pareja` en `config/relaciones.yaml`.
3. `sistema_necesidades.py`: bono aditivo a `confort_termico` (mismo
   mecanismo que `bono_confort_refugio`/`bono_confort_fogata`) y un
   extra de recuperación de `seguridad` (capado a 1.0) cuando la pareja
   está presente en la misma celda. Dos constantes nuevas
   (`bono_confort_pareja`, `bono_seguridad_pareja`).

**Fuera de alcance, explícito:**
- Prioridad de refugio compartido, aporte conjunto al almacén — círculos
  futuros más grandes, descartados para este círculo.
- Decaimiento de afinidad con el tiempo — sin resolver, ver limitación
  honesta arriba.
- Cualquier cambio a `sistema_reproduccion.py` (círculo 4a, ya cerrado)
  o a los consumidores de rencor/amistad ya existentes.
- Radio de percepción — el efecto es por celda EXACTA, no por cercanía
  aproximada, igual que refugio/fogata.
- Monogamia o cualquier regla que impida tener más de una "pareja"
  simultánea derivada — `son_pareja()` no impone exclusividad, es
  simplemente verdad o mentira para cada par consultado; si la afinidad
  de un individuo supera el umbral con dos personas distintas a la vez,
  ambas relaciones se leen como "pareja" sin conflicto — no se autora
  ninguna norma social de exclusividad aquí.

## Arquitectura

### Derivación (`nucleo/relaciones.py`)

```python
def son_pareja(rel_a: Relaciones, rel_b: Relaciones, id_a: int, id_b: int, umbral: float) -> bool:
    v_ab = rel_a.vinculos.get(id_b)
    v_ba = rel_b.vinculos.get(id_a)
    return v_ab is not None and v_ba is not None and v_ab.afinidad >= umbral and v_ba.afinidad >= umbral
```

```python
def pareja_presente(gestor, entidad_id: int, relaciones: Relaciones, pos_x: int, pos_y: int, zona_idx: int, umbral: float) -> bool:
    # Búsqueda lineal O(N) sobre entidades con (Relaciones, Posicion) en
    # la celda exacta, excluyendo la propia -- mismo criterio de escala
    # ya aceptado en hay_refugio_en/fogata_en.
```

### Config (`config/relaciones.yaml`)

```yaml
relaciones:
  # ... (existentes)
  umbral_pareja: 0.3  # PROVISIONAL -- una sola concepción (0.15) no basta sola
```

### Efecto (`sistema_necesidades.py`)

En el mismo bloque donde ya se aplican `bono_confort_refugio`/
`bono_confort_fogata` (ver `hay_refugio_en`/`fogata_en`): si
`pareja_presente(...)` es verdadero para la posición actual de la
entidad, sumar `bono_confort_pareja` al `obj_termico` antes de aplicar
la deriva ya existente (mismo mecanismo, un sumando más). Por separado,
en el bloque donde ya se actualiza `Necesidades.seguridad`
(drenaje/recuperación existente): si hay pareja presente, sumar
`bono_seguridad_pareja` a `nec.seguridad`, capado a `1.0` — un término
aditivo más, independiente de si hay una amenaza drenándola ese mismo
tick (la seguridad emocional de estar con la pareja no depende de que
no haya peligro cerca).

Ambos bonos requieren que la propia entidad sea consciente (mismo
umbral `decision.umbral_consciencia_agencia` reutilizado en todo el
arco) — fauna no consulta `pareja_presente` en absoluto.

`bono_confort_refugio`/`bono_confort_fogata` viven hoy en
`config["necesidades"]["defecto"]` (`self.defecto` en
`SistemaNecesidades.__init__`, `sistemas/sistema_necesidades.py`) — las
dos constantes nuevas van en la misma sección:

```yaml
necesidades:
  defecto:
    # ... (bono_confort_refugio, bono_confort_fogata, ya existentes)
    bono_confort_pareja: 0.15  # PROVISIONAL
    bono_seguridad_pareja: 0.05  # PROVISIONAL
```

## Persistencia

Sin cambios de esquema — `son_pareja`/`pareja_presente` son puramente
derivadas, no se persiste ningún estado nuevo (mismo criterio que
`mundo.asentamientos`).

## Testing

- `son_pareja()`: verdadero solo si AMBAS direcciones superan el
  umbral; falso si falta una dirección, si solo una lo supera, o si no
  existe vínculo en alguna dirección.
- `pareja_presente()`: verdadero si la pareja (según `son_pareja`) está
  en la celda exacta; falso si está en otra celda, si está en la misma
  celda pero en otra `zona_idx`, o si la entidad presente no es
  realmente su pareja (afinidad insuficiente).
- `sistema_necesidades.py`: el bono de confort se suma correctamente al
  objetivo cuando hay pareja presente (verificar con y sin refugio/
  fogata simultáneos, deben sumarse los tres); el bono de seguridad se
  aplica y respeta el tope de `1.0`; ninguno de los dos bonos se aplica
  a una entidad no-consciente ni cuando la otra parte presente no es
  realmente pareja.

**Verificación contra el motor real, OBLIGATORIA, no opcional**:
`BOSQUE_AUTO_TICKS` con población real, inspeccionando la BD tras la
corrida para confirmar al menos un caso real de dos gnomos que superan
`umbral_pareja` en ambas direcciones. Dado que el círculo 4a ya
confirmó que la concepción SÍ ocurre en juego libre con frecuencia
razonable, y que una sola concepción da 0.15 (mitad del umbral
PROVISIONAL de 0.3), señalar explícitamente si hace falta más de una
concepción entre la misma pareja para cruzar el umbral, o si el umbral
resulta demasiado alto/bajo en la práctica — sin ajustar los números a
ciegas, solo reportar lo observado.

## Pendiente real tras esta pieza

- `umbral_pareja`, `bono_confort_pareja`, `bono_seguridad_pareja`
  PROVISIONALES, sin calibrar contra el harness completo.
- Decaimiento de afinidad — sin resolver, limitación honesta ya
  señalada.
- Prioridad de refugio compartido, aporte conjunto al almacén —
  círculos futuros si se decide ampliar el efecto de pareja.
- Familia derivada, biografía consultable — círculos futuros del mismo
  arco, sin empezar.
- Con esto, el arco "hilo individual" tendría 5 de 6 piezas cerradas
  (nombre, cimiento+rencor, amistad, afinidad por concepción, pareja
  estable) — solo quedarían familia derivada y biografía consultable.
