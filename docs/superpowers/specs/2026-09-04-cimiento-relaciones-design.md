# Cimiento de relaciones interpersonales (`Relaciones`) + rencor — diseño

Fecha: 2026-09-04. Segundo círculo del arco "hilo individual" (primer
círculo, nombre propio real, ya cerrado — ver
`docs/superpowers/specs/2026-09-04-nombre-propio-design.md` y CLAUDE.md).
Círculos siguientes del mismo arco (amistad, pareja estable, familia
derivada, biografía consultable, desarrollo personal) quedan
deliberadamente fuera de este spec.

## Motivación

Hoy no existe ningún mecanismo que recuerde "qué siente un individuo
concreto por otro individuo concreto". `Temperamento.empatia`/`lealtad`
señalan en su propio docstring que "esperan vínculos personales con
nombre propio". `nucleo/conflicto.py` fue diseñado desde el principio
como resolutor genérico de disputas con "robo y agravio genérico" como
consumidores futuros explícitos, y declara aparte que "memoria de
agravios entre individuos con nombre propio (rencor persistente) queda
deliberadamente fuera de este módulo" — este círculo es exactamente esa
pieza que faltaba. `nucleo/disposicion.py` (modelo de disposición en
tres capas: racial/histórica/situacional) ya se auto-señala en su propio
docstring, sin relación con esta conversación, como destinado a
reutilizarse "entre dos individuos con nombre".

## Decisiones ya cerradas con Diego (contexto, no reabrir en el plan)

- Alcance del círculo: **cimiento + un primer consumidor real** (no
  cimiento aislado sin efecto observable) — necesario para poder
  verificar contra el motor real (`BOSQUE_AUTO_TICKS`), no solo con
  tests unitarios en aislamiento.
- Primer consumidor: **rencor**, no amistad — ya existe un único
  disparador claro (`nucleo/conflicto.py:resolver_disputa`, vía
  `_resolver_posible_intruso` en `sistema_movimiento.py`, refugio
  ocupado); amistad no tiene un disparador único obvio todavía y queda
  para un círculo posterior.
- Fuente del tope de capacidad: **reutilizar `CapacidadMental.memoria`**,
  el mismo atributo que ya gobierna la capacidad de `MemoriaEspacial`
  (recuerdos de comida/agua/refugio) — un individuo con buena memoria
  recuerda mejor tanto sitios como personas. Mismo patrón ya aceptado en
  el proyecto de que un rasgo sirva a más de un sistema (p.ej.
  `Temperamento.agresividad` ya pesa en percepción de amenaza y en
  evasión de depredación). **Hallazgo real, corregido de paso**: el
  docstring de `componentes/capacidad_mental.py` decía "memoria...
  espera el hilo individual de nombres propios... sin consumidor
  todavía" — desactualizado, `nucleo/memoria.py:capacidad_memoria()` ya
  la consume activamente desde antes de esta sesión (memoria espacial).
  Este círculo la convierte en la fuente de DOS capacidades distintas,
  no en su primer consumidor.

## Alcance

**Dentro de esta pieza:**
1. Componente `Relaciones` nuevo (universal, las 4 especies, mismo
   patrón que `Agarre`/`Semillas`), con su dataclase `Vinculo`.
2. `nucleo/relaciones.py` nuevo: `capacidad_vinculos()` y
   `ajustar_afinidad()`.
3. Consumidor de rencor en `sistema_movimiento.py`, donde ya se llama a
   `resolver_disputa` (refugio ocupado).
4. Persistencia de `Relaciones.vinculos`.
5. Corrección del docstring desactualizado de
   `componentes/capacidad_mental.py` (campo `memoria`).

**Fuera de alcance, explícito:**
- Amistad / simpatía (afinidad positiva) — círculo futuro; este círculo
  solo escribe afinidad negativa (rencor). El campo `afinidad` admite
  positivos por diseño (rango completo `[-1.0, 1.0]`), pero ningún
  camino de código de este círculo produce un valor positivo.
- Decaimiento del rencor con el tiempo — sin él por ahora (YAGNI; un
  agravio no se atenúa solo por el paso de ticks en este círculo).
- Cualquier consumidor que LEA `Relaciones` para cambiar comportamiento
  (p.ej. que `indice_asertividad_social` se vea afectado por rencor
  previo entre las dos partes) — este círculo solo ESCRIBE afinidad, no
  la lee en ningún punto de decisión. Círculo futuro.
- Familia (linaje biológico y convivencia) — decisión ya cerrada de que
  vive fuera de este componente por completo, en sus propias capas
  (`Identidad.id_madre`/`id_padre` ya existente; convivencia vía
  asentamiento).
- Nombre para fauna / relaciones para fauna — fauna lleva el componente
  `Relaciones` (universal, ver Arquitectura) pero nunca se escribe en
  él en este círculo.
- Cambiar la magnitud del drenaje de `Necesidades.seguridad` que
  `_resolver_posible_intruso` ya aplica en cada desenlace — el rencor es
  un efecto ADICIONAL, no sustituye nada existente.

## Arquitectura

### Componente (`componentes/relaciones.py`, nuevo)

```python
@dataclass
class Vinculo:
    afinidad: float = 0.0
    ultima_actualizacion_tick: int = 0

@dataclass
class Relaciones:
    vinculos: dict[int, Vinculo] = field(default_factory=dict)
```

`afinidad` clampada siempre a `[-1.0, 1.0]`. `ultima_actualizacion_tick`
se actualiza en cada escritura — es la clave de purga (ver abajo), no un
dato narrativo. Añadido en `crear_criatura` y `nacer_criatura` (ambas
fábricas ECS, mismo hallazgo ya conocido de `Agarre`/`Semillas`), vacío
al nacer, para las 4 especies por igual.

### Capacidad y purga (`nucleo/relaciones.py`, nuevo)

```python
def capacidad_vinculos(cap_mental: CapacidadMental, config: dict) -> int:
    cfg = config.get("relaciones", {})
    minimo = int(cfg.get("min_vinculos_por_individuo", 2))
    maximo = int(cfg.get("max_vinculos_por_individuo", 6))
    return int(minimo + cap_mental.memoria * (maximo - minimo))
```

Mismo patrón exacto que `capacidad_memoria()`, sección de config propia
(`relaciones.min_vinculos_por_individuo`/`max_vinculos_por_individuo`,
PROVISIONAL, sin calibrar).

```python
def ajustar_afinidad(
    relaciones: Relaciones, entidad_id: int, delta: float,
    tick_actual: int, capacidad: int,
) -> None:
```

Si `entidad_id` ya está en `relaciones.vinculos`: suma `delta`, clampa a
`[-1.0, 1.0]`, actualiza `ultima_actualizacion_tick`. Si no está y
`len(relaciones.vinculos) >= capacidad`: purga primero el vínculo con
`ultima_actualizacion_tick` más antiguo (FIFO por antigüedad de
ACTUALIZACIÓN, no de creación — un vínculo activo no se pierde solo por
ser viejo), luego inserta el nuevo con `afinidad=delta` clampada.

### Consumidor — rencor (`sistema_movimiento.py`)

En el punto donde ya se llama a `resolver_disputa` (refugio ocupado),
tras aplicar el drenaje de `seguridad` ya existente, y **solo para la
parte que sea consciente** (`CapacidadMental.consciencia >=
decision.umbral_consciencia_agencia`, mismo umbral ya reutilizado en
nombre propio):

- `ResultadoDisputa.CEDE_A`: A resta afinidad hacia B
  (`config["relaciones"]["delta_rencor_disputa"]`, PROVISIONAL,
  negativo) si A es consciente. B no cambia.
- `ResultadoDisputa.CEDE_B`: simétrico, B resta afinidad hacia A si B es
  consciente.
- `ResultadoDisputa.ENFRENTAMIENTO`: ambas partes restan afinidad
  mutuamente (cada una hacia la otra), cada una solo si ES consciente —
  un gnomo consciente que se enfrenta a un lobo no-consciente acumula
  rencor hacia él aunque el lobo no acumule nada de vuelta.
- `ResultadoDisputa.COMPARTE`: sin cambio.

Un individuo no-consciente (fauna) nunca ejecuta `ajustar_afinidad`
sobre su propio `Relaciones` en este círculo — su componente se queda
vacío indefinidamente, coherente con "fauna aplazada, no descartada".

### Corrección de docstring

`componentes/capacidad_mental.py`, campo `memoria`: pasa de "sin
consumidor todavía" a documentar sus DOS consumidores reales (capacidad
de `MemoriaEspacial`, capacidad de `Relaciones`) — corrección de
documentación pura, sin cambio de comportamiento.

## Persistencia

`Relaciones.vinculos` como columna JSON nueva en `componentes_estado`
(serializado como `{entidad_id_str: {"afinidad": float,
"ultima_actualizacion_tick": int}}`), mismo molde que `Agarre.objetos`.
`VERSION_ESQUEMA` sube (esquema DROP-and-recreate, mismo criterio ya
establecido en el proyecto — sin migración de datos, sin campañas reales
que conservar).

## Testing

Mismo criterio de "ley física" que el resto de tests del proyecto:

- `capacidad_vinculos()`: interpola correctamente entre mínimo y máximo
  según `CapacidadMental.memoria`.
- `ajustar_afinidad()`: suma y clampa correctamente en `[-1.0, 1.0]`;
  purga el vínculo más antiguo (por `ultima_actualizacion_tick`) al
  superar el tope, conservando los demás intactos; un vínculo ya
  existente se actualiza sin purgar nada aunque esté al tope.
- `sistema_movimiento.py`: los cuatro desenlaces de `resolver_disputa`
  (CEDE_A, CEDE_B, ENFRENTAMIENTO, COMPARTE) producen exactamente el
  efecto sobre `Relaciones` descrito arriba, incluyendo el caso donde
  una de las dos partes no es consciente (no debe escribir en su propio
  `Relaciones`) y el caso donde SÍ lo es (debe escribir aunque la otra
  parte no lo haga).
- `nucleo/entidad.py`: ambas fábricas ECS añaden `Relaciones` vacío a
  las 4 especies.
- Persistencia: roundtrip de guardado/carga conserva `Relaciones.vinculos`
  exacto (afinidad y tick) para al menos dos entidades con vínculos
  reales.
- Verificación contra el motor real, no solo unitaria: `BOSQUE_AUTO_TICKS`
  con población real, inspeccionando la BD tras la corrida para
  confirmar que al menos un gnomo real terminó con una entrada de
  rencor real en `Relaciones.vinculos` (afinidad negativa) tras un
  conflicto de refugio ocupado.

## Pendiente real tras esta pieza

- `relaciones.min_vinculos_por_individuo`/`max_vinculos_por_individuo`/
  `delta_rencor_disputa` son PROVISIONALES, sin calibrar contra el
  harness completo.
- Amistad (afinidad positiva) — círculo futuro, mismo cimiento, sin
  ninguna dependencia de código nueva salvo lo que este círculo ya deja
  construido.
- Ningún consumidor lee `Relaciones` todavía para cambiar comportamiento
  (p.ej. modular `indice_asertividad_social` por rencor previo, o que un
  intruso con rencor acumulado hacia el propietario tenga más
  probabilidad de `ENFRENTAMIENTO`) — círculo futuro real, no
  construido aquí.
- Decaimiento del rencor con el tiempo — sin resolver, señalado como
  hueco honesto, no como bug.
- Nombre/relaciones para fauna — sigue aplazado, no descartado.
