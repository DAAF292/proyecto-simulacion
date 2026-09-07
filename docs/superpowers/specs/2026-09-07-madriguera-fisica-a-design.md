# Madriguera física (A) — entidad real y capacidad finita — diseño

Fecha: 2026-09-07. Círculo A de "madriguera física", partida en dos
por el mismo criterio ya usado con sonido físico (4a/4b) y pareja
estable (4a/4b) tras dos timeouts consecutivos del pipeline sin ningún
progreso sobre la versión combinada de este spec (2700s cada uno, sin
comitear código ni plan propio -- ver
`docs/plans/failed/2026-09-07-madriguera-fisica.md`, ambos intentos).
Extiende directamente la pieza recién cerrada `Manada` (ver
`docs/superpowers/specs/2026-09-07-manada-fauna-design.md`) — no es
parte del informe de "capa de comunicación" (ya cerrado del todo).

Este círculo (A) es la infraestructura física en sí: la entidad
`Madriguera` persistida, su capacidad sorteada, y la lógica de
admisión con prioridad. El círculo B (beneficios reales de confort y
seguridad) depende de que `madriguera_en` exista ya, y se diseña/
entrega por separado — ver
`docs/superpowers/specs/2026-09-07-madriguera-fisica-b-design.md`.

## Motivación

Diego, tras ver la madriguera compartida funcionando (14897
sincronizaciones, 597 conejos con sitio nuevo), señaló dos huecos
reales: (1) hoy no hay ningún límite — una sola madriguera podría
"contener" a 200 conejos, cuando debería tener una capacidad concreta
y finita que fuerce a que se formen varias comunidades cuando la
población crece; (2) un refugio individual no debería tener bonificación
(decisión ya tomada y documentada, `_calcular_dormir`: "el beneficio es
puramente conductual"), pero una madriguera colonial SÍ debería dar
beneficios reales a quien la usa — hoy no da ninguno, es indistinguible
de cualquier sitio recordado a título personal.

**Hallazgo de diseño clave**: para que la capacidad sea un límite físico
real (no solo un número que se compara y ya), la madriguera tiene que
dejar de ser "solo una coordenada en `MemoriaEspacial`" y convertirse en
una **entidad física real y persistida** — mismo molde exacto que
`Fogata` (`Posicion` + un componente, sin `Identidad` ni `Intencion`,
`crear_fogata` como plantilla de fábrica, `fogata_en`/`hay_refugio_en`
como plantilla de consulta, `fogata_estado` como plantilla de tabla).
Esto es un salto real de complejidad respecto a `Manada` (100%
derivable, nada persistido) — justificado porque "cuánto cabe aquí" es
un hecho físico real que no se puede recalcular gratis cada día.

## Decisiones ya cerradas con Diego

- **Capacidad sorteada UNA VEZ, al crear la madriguera** — mismo patrón
  exacto que el tamaño de una cueva al generarse
  (`rng.randint(min, max)`, nunca se vuelve a sortear después).
  PROVISIONAL, por especie colonial (hoy solo conejo).
- **Cuando el voto de mayoría supera el cupo**: prioridad a quien YA
  tenía ese sitio en su propia memoria (los "ya establecidos") sobre
  quien lo recibiría por primera vez. El resto no se sincroniza ese
  día — su propia memoria individual queda intacta (mecanismo original
  de refugio de fauna, sin cambios).
- **Beneficios reales de usarla quedan para el círculo B** — este
  círculo solo construye la entidad física y su cupo; `madriguera_en`
  se diseña ya pensando en que B la consuma sin tocar este módulo.
- **Sin decaimiento ni acción de excavar** — permanente una vez creada,
  mismo criterio ya aceptado (madriguera instintiva, no consciente).
- **Honestidad explícita sobre "forzar nuevas comunidades"**: el diseño
  garantiza el LÍMITE duro (nunca más de `capacidad` miembros
  admitidos), pero que eso empuje de verdad a los excluidos a fundar
  una madriguera nueva en otro sitio es una consecuencia EMERGENTE, no
  garantizada por el diseño en sí — se mide contra el motor real, no
  se da por hecho en el spec.

## Alcance

**Dentro:**

1. `componentes/madriguera.py` (nuevo): `Madriguera(capacidad: int)` —
   mismo molde que `Fogata`, `Posicion` en la misma entidad.
2. `nucleo/entidad.py`: `crear_madriguera(gestor, pos_x, pos_y,
   capacidad, zona_idx=0) -> int`, mismo molde que `crear_fogata`.
3. `nucleo/madriguera.py` (nuevo): `madriguera_en(gestor, pos_x, pos_y,
   zona_idx) -> int | None`, mismo molde que `fogata_en`.
4. `sistemas/sistema_manada.py:_sincronizar_madriguera`, reescrita:
   - Si NO existe `Madriguera` en el sitio mayoritario, crea una con
     `crear_madriguera` y capacidad sorteada
     (`capacidad_madriguera: [min, max]` por especie).
   - Si YA existe, reutiliza su `capacidad` (nunca se vuelve a sortear).
   - Determina admitidos: primero quienes YA tenían el sitio en su
     memoria (hasta `capacidad`), luego rellena huecos restantes con
     miembros nuevos (orden determinista, p.ej. `sorted(miembros)`).
   - Solo los admitidos reciben `registrar_recuerdo`.
5. `config/poblacion.yaml`: `capacidad_madriguera: [min, max]`
   PROVISIONAL, solo en `conejo`.
6. Persistencia: tabla `madriguera_estado` (mismo molde que
   `fogata_estado`: `entidad_id, x, y, capacidad, zona_idx`),
   `VERSION_ESQUEMA` sube de `"0.33-fase0"` a la siguiente (DROP-and-
   recreate, sin migración, mismo criterio ya establecido).
7. `SistemaManada` gana `rng` en su constructor (hoy no lo recibe) para
   sortear la capacidad — actualizar `main.py:instanciar_sistemas`
   para pasarle `rng_juego`.
8. Tests dirigidos + verificación obligatoria contra el motor real.

**Fuera de alcance, explícito:**

- **Beneficios reales (confort/seguridad) — círculo B, spec aparte**:
  no se toca `sistema_necesidades.py` en este círculo.
  `nucleo/madriguera.py:madriguera_en` se diseña genérica precisamente
  para que B la reutilice sin tocarla.
- Cualquier acción consciente de excavar/ampliar una madriguera ya
  creada — capacidad fija de por vida, igual que el tamaño de una
  cueva.
- Decaimiento o destrucción de una madriguera — permanente, mismo
  criterio que refugio instintivo.
- Garantizar que los excluidos por capacidad fundan una nueva
  madriguera — se mide, no se fuerza con una regla adicional.
- Cualquier beneficio para refugio INDIVIDUAL (no colonial) — se queda
  exactamente como está (sin bono, decisión ya tomada y documentada).
- Liderazgo o jerarquía dentro de una madriguera — sin relación con
  esta pieza.

## Arquitectura

### Componente y fábrica

```python
# componentes/madriguera.py
@dataclass
class Madriguera:
    capacidad: int

# nucleo/entidad.py
def crear_madriguera(gestor, pos_x, pos_y, capacidad, zona_idx=0) -> int:
    mid = gestor.crear_entidad()
    gestor.anadir_componente(mid, Posicion(x=pos_x, y=pos_y, zona_idx=zona_idx))
    gestor.anadir_componente(mid, Madriguera(capacidad=capacidad))
    return mid
```

### Consulta (`nucleo/madriguera.py`)

```python
def madriguera_en(gestor, pos_x, pos_y, zona_idx) -> int | None:
    for mid in gestor.entidades_con(Madriguera, Posicion):
        pos = gestor.obtener_componente(mid, Posicion)
        if pos.x == pos_x and pos.y == pos_y and pos.zona_idx == zona_idx:
            return mid
    return None
```

### `_sincronizar_madriguera` reescrita (`sistemas/sistema_manada.py`)

```python
def _sincronizar_madriguera(self, gestor, especie, zona_idx, miembros) -> None:
    # 1. Recuento de opiniones -- igual que hoy, sin cambios.
    conteo: dict[tuple[int, int], int] = {}
    memorias: dict[int, MemoriaEspacial] = {}
    for mid in miembros:
        mem = gestor.obtener_componente(mid, MemoriaEspacial)
        if mem is None:
            continue
        memorias[mid] = mem
        for sitio in mem.recuerdos.get("refugio", []):
            conteo[sitio] = conteo.get(sitio, 0) + 1
    if not conteo:
        return
    sitio = max(conteo, key=lambda s: conteo[s])

    # 2. Localizar o crear la Madriguera fisica en ese sitio.
    madriguera_id = madriguera_en(gestor, sitio[0], sitio[1], zona_idx)
    if madriguera_id is None:
        rango = self.rangos_raciales.get(especie.value, {}).get("capacidad_madriguera", [10, 10])
        capacidad = self.rng.randint(int(rango[0]), int(rango[1]))
        crear_madriguera(gestor, sitio[0], sitio[1], capacidad, zona_idx)
    else:
        capacidad = gestor.obtener_componente(madriguera_id, Madriguera).capacidad

    # 3. Admision con prioridad para quien YA tenia el sitio.
    ya_establecidos = sorted(mid for mid in memorias if sitio in memorias[mid].recuerdos.get("refugio", []))
    nuevos = sorted(mid for mid in memorias if mid not in ya_establecidos)
    admitidos = ya_establecidos[:capacidad] + nuevos[: max(0, capacidad - len(ya_establecidos))]

    # 4. Solo los admitidos reciben el recuerdo -- resto sin tocar.
    for mid in admitidos:
        cap_mental = gestor.obtener_componente(mid, CapacidadMental)
        if cap_mental is None:
            continue
        capacidad_memoria_ind = capacidad_memoria(cap_mental, self.config)
        registrar_recuerdo(memorias[mid], "refugio", sitio[0], sitio[1], capacidad_memoria_ind)
```

`ejecutar()` pasa ahora `especie` y `zona_idx` explícitos a
`_sincronizar_madriguera` (ya los tiene en su propio bucle por
`(especie, zona_idx)`, solo hay que propagarlos al llamar).

## Config nueva (PROVISIONAL, sin calibrar)

```yaml
# config/poblacion.yaml, solo en conejo
capacidad_madriguera: [10, 25]  # PROVISIONAL -- lejos de "200 conejos
  # en una", fuerza a repartirse en varias madrigueras conforme crece
  # la poblacion
```

## Testing

- `crear_madriguera`/`madriguera_en`: crea y encuentra correctamente,
  respeta `zona_idx`.
- `_sincronizar_madriguera`: primera vez, sortea capacidad dentro del
  rango configurado y crea la entidad; segunda vez (misma coordenada),
  reutiliza la capacidad ya fijada sin volver a sortear.
- Cupo respetado: con más miembros que capacidad, exactamente
  `capacidad` quedan admitidos (nunca más); los ya establecidos tienen
  prioridad sobre los nuevos.
- **Verificación obligatoria contra `BOSQUE_AUTO_TICKS`, no opcional**:
  medir cuántas madrigueras reales se crearon, su capacidad real
  sorteada, cuántos conejos quedaron sin admitir por cupo lleno, y si
  se observan VARIAS madrigueras activas simultáneamente (evidencia,
  aunque no prueba definitiva, de que el cupo empuja a repartirse en
  más de una comunidad). Reportar con honestidad si solo se forma una
  y el resto de la población queda sin sincronizar.

## Pendiente real tras esta pieza

- `capacidad_madriguera` PROVISIONAL, sin calibrar.
- **Círculo B (beneficios reales) es el siguiente paso inmediato** — ya
  puede diseñarse/entregarse en cuanto este círculo esté mergeado,
  reutilizando `madriguera_en` tal cual.
- Si el cupo realmente empuja a fundar nuevas madrigueras o solo dejar
  población sin sincronizar es una pregunta abierta hasta verificarlo
  contra el motor real — candidato a una segunda vuelta de diseño
  (p.ej., un sesgo de movimiento que aleje deliberadamente a los
  excluidos) si el resultado es el segundo caso.
- Ninguna jerarquía ni liderazgo dentro de una madriguera.
