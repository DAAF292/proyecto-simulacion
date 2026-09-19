# Leyendas / memoria oral: el primer consumidor real de idiomas

Fecha: 2026-09-18. Continuación directa de
`2026-09-18-idiomas-design.md` (catálogo de lenguas y
`nucleo/idioma.py:comprension()`, sin ningún consumidor todavía). Diego
pidió explorar qué otros mecanismos de comunicación se podían plantear
además de los cuatro ya existentes (roce social/conflicto verbal,
memoria espacial compartida, rumor, liderazgo); de la lista de ideas
futuras que ya constaba en `docs/historial_capa_comunicacion.md`
("robo/agravio genérico, llamada de alarma, trueque, encargos/
cooperación dirigida, leyendas/memoria oral, facciones entre
asentamientos"), leyendas/memoria oral es la única que transmite
**contenido simbólico real** (un suceso concreto) en vez de un número
opaco (coordenada/afinidad/magnitud) -- el candidato natural para que la
matriz de comprensión recién diseñada tenga textura real: una leyenda
que cruza de lengua puede perderse en la traducción, un rumor de opinión
no tiene "traducción" que perder.

## Qué es una leyenda en términos de datos

Componente nuevo `MemoriaNarrativa`, mismo espíritu que
`MemoriaEspacial` (estado dinámico, capacidad acotada derivada de
`CapacidadMental`, universal a las 4 especies conscientes-o-no por
igual, vacío al nacer):

```python
@dataclass
class RecuerdoNarrativo:
    tipo_suceso: str          # mismo texto libre que Evento.tipo
    protagonista_id: int | None  # None para sucesos sin entidad (IncendioIniciado, RayoImpacto)
    tick_suceso: int
    fidelidad: float          # [0, 1] -- 1.0 = testigo directo

@dataclass
class MemoriaNarrativa:
    recuerdos: list[RecuerdoNarrativo] = field(default_factory=list)
```

Lista, no diccionario por categoría (a diferencia de `MemoriaEspacial`):
cada leyenda es un suceso independiente, no hay "la mejor leyenda de tipo
Muerte" que tenga sentido conservar como si fuera una coordenada.

## Nacimiento de una leyenda: registro de testigo

Cuando se emite un `Evento` con `severidad == Severidad.HISTORICO`
**y sus `datos` incluyen `x`/`y`** (no todos los HISTORICO los llevan --
ver "Fuera de alcance" abajo), todo consciente dentro de su radio de
percepción normal (`radio_individual(dims.agudeza_sensorial,
self.radio_min, self.radio_max)`, exactamente el mismo usado para
detectar amenaza/presa/pareja) de esa celda registra un
`RecuerdoNarrativo(tipo_suceso=ev.tipo, protagonista_id=ev.entidad_id,
tick_suceso=ev.tick, fidelidad=1.0)`.

Catálogo real de eventos HISTORICO con posición hoy (confirmado leyendo
el código emisor, no supuesto): `Muerte` (vejez, depredación, incendio,
rayo -- todas incluyen x/y), `IncendioIniciado`, `RayoImpacto`,
`ColonizacionEspontanea`, `AsentamientoFundado`. `entidad_id` es `None`
en `IncendioIniciado`/`RayoImpacto` -- una leyenda sin protagonista
("hubo un incendio aquí") es válida, no un caso especial.

**Implementación**: nuevo método en `SistemaMovimiento` (tiene ya toda
la infraestructura -- `self.rng`, `radio_min`/`radio_max` cacheados,
`radio_individual`), `procesar_testigos_narrativos(gestor, mundo,
eventos_historicos)`, invocado desde `main.py` junto al bucle existente
que ya recorre `eventos_tick` para `Nacimiento`/`Muerte`/
`ColonizacionEspontanea` (línea ~645), antes de `bus_eventos.limpiar()`.
Filtra `ev.severidad == Severidad.HISTORICO and "x" in ev.datos and "y"
in ev.datos`. `zona_idx` se lee de `ev.datos.get("zona_idx", 0)` --
ningún evento HISTORICO existente declara `zona_idx` explícito hoy
(coherente con que el resto del motor ya asume `zona_idx == 0` como
único caso real ejercido, ver "Selector de zona real en el visor web" en
`CLAUDE.md`).

Recorre directamente `gestor.entidades_con(Posicion, DimensionesFisicas,
CapacidadMental, MemoriaNarrativa)` (SIN pasar por
`IndiceEspacial`/`self._indice_actual` -- ese índice es estado
transitorio, poblado solo durante `SistemaMovimiento.ejecutar()`, y este
método se invoca en otro punto del tick; coste aceptable porque el
número de eventos HISTORICO por tick y de conscientes en el mundo es
bajo), filtra por `cap_mental.consciencia >= self.umbral_consciencia_
agencia` (mismo umbral que el resto de la capa de comunicación) y por
distancia Manhattan dentro del radio.

## Transmisión boca a boca

Calco exacto de `_procesar_rumor`/`_compartir_rumor`
(`sistema_movimiento.py:1504-1556`): quinta pasada sobre la misma
`por_celda` ya construida por `_agrupar_conscientes_por_celda`, cada
dirección sorteada por separado con la sociabilidad del emisor
(`_pares_ordenados`, no `_pares_no_ordenados` -- efecto asimétrico,
igual que memoria compartida y rumor).

```python
def _compartir_leyenda(self, gestor, emisor_id, receptor_id):
    temp_emisor = ...
    if rng.random() >= temp_emisor.sociabilidad: return
    mem_emisor = MemoriaNarrativa del emisor
    if not mem_emisor.recuerdos: return
    recuerdo = rng.choice(mem_emisor.recuerdos)
    ident_emisor, ident_receptor = Identidad de cada uno
    factor = comprension(ident_emisor.especie.value, ident_receptor.especie.value, config)
    fidelidad_nueva = recuerdo.fidelidad * factor_perdida_transmision_leyenda * factor
    if fidelidad_nueva < fidelidad_minima_leyenda: return  # se pierde del todo, no se registra
    registrar_leyenda(mem_receptor, recuerdo.tipo_suceso, recuerdo.protagonista_id,
                       recuerdo.tick_suceso, fidelidad_nueva, capacidad_receptor)
```

Con una sola especie consciente hoy, `factor` siempre vale 1.0
(`comprension("gnomo", "gnomo", config) == 1.0`) -- el único efecto
observable en juego libre actual es la degradación por
`factor_perdida_transmision_leyenda` en cada salto (el "teléfono roto"
por número de bocas, ya observable sin ninguna segunda raza). El efecto
de la barrera lingüística de verdad (una leyenda feérica que muere al
llegar a un bruto) solo será observable con una segunda especie
consciente real, o con un test dirigido que la fuerce sintéticamente.

## Config nueva (`config/comportamiento.yaml`, junto a la sección `memoria` ya existente)

```yaml
memoria_narrativa:
  min_leyendas_capacidad: 1
  max_leyendas_capacidad: 5
  factor_perdida_transmision_leyenda: 0.9   # PROVISIONAL
  fidelidad_minima_leyenda: 0.05            # PROVISIONAL -- por debajo, la leyenda no se registra
```

`capacidad_memoria_narrativa(cap_mental, config)` en
`nucleo/memoria_narrativa.py`, mismo cálculo lineal que
`nucleo/memoria.py:capacidad_memoria` mueve sobre `CapacidadMental.
memoria`. `registrar_leyenda` es FIFO por lista completa (a diferencia
de `registrar_recuerdo`, que es FIFO por categoría) -- no hay categorías
aquí, cada leyenda compite por el mismo cupo.

## Persistencia

`MemoriaNarrativa` se persiste igual que `MemoriaEspacial`/`Relaciones`
(estado dinámico acumulado a lo largo de la vida del individuo, perderlo
al recargar sería una regresión real, no una simplificación aceptable
como el estado de clima no persistido). Nueva columna
`memoria_narrativa_json` en `componentes_estado`
(`nucleo/persistencia.py`), bump de `VERSION_ESQUEMA` (sin migración de
datos entre versiones, mismo criterio que el resto del proyecto en esta
fase). Serializa como lista de objetos
`{tipo_suceso, protagonista_id, tick_suceso, fidelidad}`.

## Explícitamente FUERA de este círculo

- **Mutación del protagonista** al degradarse la fidelidad ("la leyenda
  cambia de quién habla" -- el efecto más vistoso del teléfono roto
  narrativamente, pero exige elegir un sustituto de los vínculos del
  receptor y fijar un segundo umbral; segunda fuente de complejidad real
  que Diego aceptó dejar para un tercer círculo si este se valida bien).
- **Decaimiento temporal** de una leyenda ya registrada por el simple
  paso del tiempo sin volver a contarse -- la fidelidad solo baja al
  transmitirse.
- **Eventos HISTORICO sin `x`/`y` en sus datos** (ninguno detectado hoy,
  pero si apareciera uno futuro sin posición, simplemente no genera
  testigos -- no es un caso a resolver, es un límite documentado del
  registro de testigo).

## Verificación (honesta sobre su límite real)

Tests dirigidos: registro de testigo dentro/fuera de radio, filtro de
consciencia, evento sin `x`/`y` no genera testigos, transmisión boca a
boca con degradación por `factor_perdida_transmision_leyenda`,
degradación adicional por `comprension()` < 1.0 (especie sintética
forzada con otra lengua en el test -- no observable en juego libre hoy),
poda por `fidelidad_minima_leyenda`, capacidad acotada FIFO,
persistencia round-trip.

**Sin harness de escala real para esta pieza**: a diferencia de
desastres naturales (verificado con smoke tests de miles de ticks contra
fauna real), el único comportamiento observable en juego libre hoy con
una sola especie consciente es la degradación por número de bocas -- se
confirma con un smoke test corto, no con un harness completo. El efecto
central de la pieza (barrera lingüística real entre razas) queda sin
verificación empírica posible hasta que exista una segunda raza
consciente, igual que ya se advirtió en el spec de idiomas -- el test
`test_compartir_leyenda_barrera_linguistica_bloquea_transmision` la
cubre de forma sintética (gnomo + lobo forzado a consciente), no en
juego libre.

**Resultado real del smoke test (4000 ticks, población inicial real vía
`sembrar_poblacion_inicial`, semilla 42/43/1)**: 19 testigos directos
registrados, 358 leyendas propagadas boca a boca, 386 perdidas del todo
por caer bajo `fidelidad_minima_leyenda` -- el mecanismo se ejerce de
verdad, no queda inerte. Al cierre quedaban 7 leyendas repartidas en 3
individuos con `MemoriaNarrativa` (población fuertemente reducida tras
4000 ticks en esta semilla concreta, no medido contra un harness de
estabilidad). Las leyendas de segunda mano observadas tenían fidelidad
entre 0.052 y 0.387 -- coherente con varios saltos de transmisión
acumulando `factor_perdida_transmision_leyenda=0.9` en cada uno, no un
valor plano de un único salto (0.9¹=0.9), confirmando que la cadena de
"boca en boca" se ejerce más de un salto de largo en la práctica.
