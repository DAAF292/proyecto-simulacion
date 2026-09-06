# Ocio consciente — `Accion.SOCIALIZAR` — diseño

Fecha: 2026-09-06. Tercera pieza descompuesta del informe externo de
"capa de comunicación" (ver
`docs/superpowers/specs/2026-09-06-conflicto-verbal-design.md` para el
contexto completo de la descomposición). Sin dependencia de conflicto
verbal ni memoria espacial compartida (ya cerradas, PR #20/#21), ni de
sonido físico/reputación-rumor (piezas futuras del mismo informe).

## Motivación

El informe original proponía una `Accion.SOCIALIZAR` que compite por el
"tiempo de ocio" (hoy ganado por `DEAMBULAR`, utilidad fija 0.1) cuando
las necesidades están cubiertas, modulada por `sociabilidad`/`curiosidad`.

**Hallazgo real al explorar el código, antes de diseñar**: ya existe un
"sesgo gregario" dentro de `_calcular_deambular`
(`sistemas/sistema_movimiento.py`) — con probabilidad =
`Temperamento.sociabilidad`, cualquier especie se acerca al conspecífico
más cercano cuando deambula. Pero al llegar no pasa nada: es un gesto de
movimiento sin consecuencia, el mismo tipo de hueco que tenía
`CRISIS_VIOLENTA` antes de "conflicto verbal". Se evaluaron dos enfoques
con Diego — extender ese sesgo existente (más barato, pero mezcla
"vagar sin rumbo" con "ir a socializar" en una sola acción y no da uso
real a `curiosidad`) frente a una `Accion.SOCIALIZAR` genuinamente
nueva (más fiel al informe, distingue el ocio consciente del
vagabundeo instintivo). **Diego eligió la segunda.**

`Temperamento.curiosidad` no tiene ningún consumidor real hoy (su
propio docstring lo señala) — esta pieza es su primer uso real.

## Decisiones ya cerradas con Diego

- **`Accion.SOCIALIZAR` nueva**, no una extensión del sesgo gregario ya
  existente dentro de `DEAMBULAR` (que sigue intacto, sin cambios,
  para todas las especies).
- **Gateada a consciente** (`umbral_consciencia_agencia`, gnomo hoy) y
  al MISMO gate físico que ya usa `BUSCAR_PAREJA`
  (`_NECESIDADES_FISICAS` por debajo de `umbral_atencion_pareja` →
  utilidad 0.0) — reutilizado, no inventado: un individuo no socializa
  si está en apuros físicos.
- **Utilidad**: `utilidad_socializar_base × (sociabilidad + curiosidad)
  / 2` — primer consumidor real de `curiosidad`, modulando en pie de
  igualdad con `sociabilidad`.
- **Búsqueda de objetivo: cualquier consciente, no solo la misma
  especie** — a diferencia del sesgo gregario de `DEAMBULAR`
  (`_buscar_conspecifico_mas_cercano`, restringido a la misma especie),
  socializar es un acto consciente sin esa restricción biológica (ley
  neutra: hoy solo hay una especie consciente, así que es idéntico en
  la práctica, pero el mecanismo no debe asumirlo).
- **Resolución por contacto, mismo patrón que CRISIS_VIOLENTA**: si el
  consciente más cercano está lejos, se acerca; si ya está a distancia
  0, se resuelve una ganancia de afinidad MUTUA y la entidad se queda
  quieta ese tick (no sigue moviéndose tras "conseguir" socializar).
- **La ganancia de afinidad es incondicional al contacto** — no
  depende de que la otra parte también esté "eligiendo" `SOCIALIZAR`
  ese tick, igual que `CRISIS_VIOLENTA` no comprueba qué acción tenía
  su objetivo.

## Alcance

**Dentro:**

1. `componentes/intencion.py`: `Accion.SOCIALIZAR = "socializar"` nueva.
2. `sistemas/sistema_decision.py`: `utilidad_socializar`, calculada
   junto al resto de utilidades, entra en el argmax final.
3. `sistemas/sistema_movimiento.py`:
   - Nuevo `_consciente_mas_cercano_con_id` (cualquier especie, filtra
     por `CapacidadMental.consciencia >= umbral_consciencia_agencia`,
     excluye a quien busca) — mismo molde que
     `_entidad_cercana_cualquiera_con_id` (conflicto verbal) pero con
     el filtro de consciencia en vez de "cualquier tipo".
   - Nuevo `_calcular_socializar`, despachado desde `ejecutar()` igual
     que el resto de acciones.
   - Refactor: extraer el cuerpo de `_aplicar_rencor` (gate de
     consciencia + `ajustar_afinidad`) a un helper genérico
     `_aplicar_afinidad(gestor, autor_id, otro_id, delta, tick_actual)`
     que acepta el delta como parámetro. `_aplicar_rencor` pasa a ser
     un wrapper de una línea (`self._aplicar_afinidad(gestor, autor_id,
     otro_id, self.delta_rencor_disputa, tick_actual)`), sin cambio de
     comportamiento. El efecto positivo de `SOCIALIZAR` reutiliza el
     mismo helper con `self.delta_afinidad_socializar`.
4. `utilidad_socializar_base` nueva en `config/fisiologia.yaml` sección
   `decision:` (junto a `utilidad_deambular_base`/
   `umbral_atencion_pareja`, ya en ese fichero); `delta_afinidad_socializar`
   nueva en `config/relaciones.yaml` sección `relaciones:` (junto a
   `delta_rencor_disputa`/`delta_amistad_convivencia_dia`, ya ahí) —
   ambas PROVISIONAL.
5. Tests dirigidos + verificación obligatoria contra el motor real.

**Fuera de alcance, explícito:**

- Cualquier cambio al sesgo gregario ya existente de `DEAMBULAR` — se
  queda exactamente igual, para todas las especies, sin tocar.
- Sonido físico, reputación/rumor sobre liderazgo — piezas restantes
  del informe original, cada una su propio círculo futuro.
- Cualquier "drive" dinámico de socialización (un campo tipo
  `Necesidades.impulso_social` que decaiga/se recupere) — la utilidad
  usa directamente los rasgos de `Temperamento`, ya fijos por
  individuo, sin estado dinámico nuevo. Más simple, coherente con que
  `DEAMBULAR` tampoco tiene un drive propio.
- Ningún tope o cooldown explícito para que la misma pareja no repita
  la ganancia de afinidad tick tras tick si `SOCIALIZAR` sigue ganando
  el argmax — se acepta como consecuencia honesta del diseño (la
  afinidad ya está capada en `[−1, 1]` por `ajustar_afinidad`, así que
  se autolimita); si la verificación contra el motor real muestra que
  esto satura de forma poco realista, es candidato a revisar en una
  calibración futura, no aquí.

## Arquitectura

### Utilidad (`sistema_decision.py`)

```python
fisica_bajo_umbral_ocio = any(
    getattr(necesidades, n) < umbral_atencion_pareja
    for n in _NECESIDADES_FISICAS
)
utilidad_socializar = (
    0.0
    if (cap_mental.consciencia < self.umbral_consciencia_agencia or fisica_bajo_umbral_ocio)
    else self.utilidad_socializar_base * (temperamento.sociabilidad + temperamento.curiosidad) / 2.0
)
```

Se añade a la tupla del argmax junto al resto
(`(utilidad_socializar, Accion.SOCIALIZAR)`). `fisica_bajo_umbral` ya
se calcula para `BUSCAR_PAREJA` en el mismo bucle — reutilizar esa
misma variable en vez de recalcularla si el orden del código lo
permite; si no, recalcular es aceptable (misma fórmula, ya barata).

### Movimiento (`sistema_movimiento.py`)

```python
def _consciente_mas_cercano_con_id(
    self, gestor, entidad_id, pos_x, pos_y, radio, zona_idx=0,
) -> tuple[int | None, tuple[int, int] | None]:
    """Variante de _entidad_cercana_cualquiera_con_id filtrada a
    conscientes -- cualquier especie, no solo la propia (a diferencia
    de _buscar_conspecifico_mas_cercano, que sí filtra por especie)."""
    mejor_id, mejor = None, None
    mejor_dist = radio + 1
    for otro_id in gestor.entidades_con(Posicion, CapacidadMental):
        if otro_id == entidad_id:
            continue
        cap_otro = gestor.obtener_componente(otro_id, CapacidadMental)
        if cap_otro is None or cap_otro.consciencia < self.umbral_consciencia_agencia:
            continue
        pos_o = gestor.obtener_componente(otro_id, Posicion)
        if pos_o is None or pos_o.zona_idx != zona_idx:
            continue
        dist = abs(pos_o.x - pos_x) + abs(pos_o.y - pos_y)
        if dist <= radio and dist < mejor_dist:
            mejor_id, mejor, mejor_dist = otro_id, (pos_o.x, pos_o.y), dist
    return mejor_id, mejor

def _calcular_socializar(
    self, gestor, mundo, entidad_id, pos_x, pos_y, radio, zona_idx=0, tick_actual=0,
) -> tuple[int, int]:
    objetivo_id, objetivo_pos = self._consciente_mas_cercano_con_id(
        gestor, entidad_id, pos_x, pos_y, radio, zona_idx
    )
    if objetivo_id is None:
        return self._paso_aleatorio()
    if objetivo_pos == (pos_x, pos_y):
        self._aplicar_afinidad(gestor, entidad_id, objetivo_id, self.delta_afinidad_socializar, tick_actual)
        self._aplicar_afinidad(gestor, objetivo_id, entidad_id, self.delta_afinidad_socializar, tick_actual)
        return (0, 0)
    return self._acercarse_a(pos_x, pos_y, *objetivo_pos)
```

### Refactor: `_aplicar_afinidad` genérico

```python
def _aplicar_afinidad(self, gestor, autor_id, otro_id, delta, tick_actual) -> None:
    """Generico: ajusta la afinidad de autor_id hacia otro_id en `delta`
    (positivo o negativo). Extraido de _aplicar_rencor (2026-09-06,
    ocio consciente) para reutilizarse tambien en SOCIALIZAR. Solo
    escribe si autor_id es consciente -- fauna nunca ajusta su propio
    Relaciones."""
    cap_mental = gestor.obtener_componente(autor_id, CapacidadMental)
    if cap_mental is None or cap_mental.consciencia < self.umbral_consciencia_agencia:
        return
    relaciones = gestor.obtener_componente(autor_id, Relaciones)
    if relaciones is None:
        return
    capacidad = capacidad_vinculos(cap_mental, self.config)
    ajustar_afinidad(relaciones, otro_id, delta, tick_actual, capacidad)

def _aplicar_rencor(self, gestor, autor_id, otro_id, tick_actual) -> None:
    self._aplicar_afinidad(gestor, autor_id, otro_id, self.delta_rencor_disputa, tick_actual)
```

## Config nueva (PROVISIONAL, sin calibrar)

```yaml
decision:
  utilidad_socializar_base: 0.3  # PROVISIONAL -- por encima de deambular
                                  # (0.1) para que un consciente muy
                                  # sociable/curioso prefiera socializar
                                  # sobre vagar sin rumbo cuando ambas
                                  # compiten con necesidades ya cubiertas.
relaciones:
  delta_afinidad_socializar: 0.02  # PROVISIONAL -- mas pequeno que
                                     # delta_amistad_convivencia_dia
                                     # (0.05/dia) porque esto puede
                                     # dispararse cada tick que la
                                     # pareja siga junta, no una vez al dia.
```

## Testing

- `_consciente_mas_cercano_con_id`: encuentra al consciente más cercano
  de CUALQUIER especie (verificar con dos especies distintas si el
  arnés lo permite, o documentar que hoy solo gnomo puede probarse
  directamente); excluye no-conscientes y a quien busca.
- `_calcular_socializar`: a distancia > 0 se acerca sin resolver nada;
  a distancia 0 aplica afinidad MUTUA (ambas direcciones) y devuelve
  `(0, 0)`; sin ningún consciente cercano, cae a paso aleatorio.
- `utilidad_socializar`: 0.0 si no es consciente; 0.0 si cualquier
  necesidad física está bajo `umbral_atencion_pareja` aunque sociabilidad/
  curiosidad sean altas; sube con sociabilidad y con curiosidad por
  separado (verificar que ambas modulan, no solo una).
- `_aplicar_afinidad`/`_aplicar_rencor`: el refactor no cambia el
  comportamiento de rencor — los tests existentes de conflicto verbal
  deben seguir en verde sin modificarlos.
- **Verificación obligatoria contra `BOSQUE_AUTO_TICKS`, no opcional**:
  medir cuántas veces se elige `SOCIALIZAR` de verdad, cuántas
  resoluciones de contacto ocurren, y si `Relaciones` muestra ganancias
  de afinidad positivas atribuibles a esta pieza (distintas de amistad
  por convivencia o afinidad por concepción, ya existentes) — reportar
  la cifra con honestidad aunque sea baja, mismo criterio que las dos
  piezas anteriores de este arco.

## Pendiente real tras esta pieza

- `utilidad_socializar_base`/`delta_afinidad_socializar` PROVISIONALES,
  sin calibrar contra el harness completo.
- Sonido físico, reputación/rumor sobre liderazgo — piezas restantes
  del informe original, ninguna empezada. Con esto, 3 de 5 piezas
  quedarían cerradas.
- Sin cooldown ni tope de repetición por pareja — aceptado
  explícitamente, candidato a revisar si la verificación muestra
  saturación poco realista.
