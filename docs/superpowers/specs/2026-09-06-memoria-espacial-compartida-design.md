# Memoria espacial compartida entre conscientes — diseño

Fecha: 2026-09-06. Segunda pieza descompuesta del informe externo de
"capa de comunicación" evaluado el mismo día (ver
`docs/superpowers/specs/2026-09-06-conflicto-verbal-design.md` para el
contexto completo de la descomposición y la auditoría del informe
original). Sin dependencia de "conflicto verbal" (ya cerrado, PR #20)
ni de las piezas futuras del mismo informe (ocio+`SOCIALIZAR`, sonido
físico, reputación/rumor).

## Motivación

`MemoriaEspacial.recuerdos` (`{tipo_recuerdo: [(x,y), ...]}`) hoy solo
crece por experiencia propia — un individuo solo sabe de sitios que él
mismo visitó. El informe original proponía que dos conscientes que
coinciden puedan transferirse coordenadas conocidas (comida, agua...),
reutilizando el componente y las funciones de `nucleo/memoria.py` ya
existentes sin cambiar su forma.

## Decisiones ya cerradas con Diego

- **Solo entre conscientes** (gnomo hoy, `umbral_consciencia_agencia`).
  El aprendizaje por observación en fauna (p.ej. una cría de conejo
  aprendiendo la madriguera por seguir a su madre) es un mecanismo
  DISTINTO — no es comunicación, es imitación — y queda aplazado como
  idea aparte, no descartado, mismo criterio que fauna en nombre
  propio/`Relaciones`.
- **Todas las categorías de `recuerdos` por igual** (comida, agua,
  refugio, asentamiento, cualquier clave futura) — sin lista cerrada
  especial, coherente con que el propio componente ya se documenta
  como abierto a cualquier clave nueva.
- **Modulado por `Temperamento.sociabilidad` de quien comparte**,
  reutilizando literalmente la misma línea que ya usa el sesgo
  gregario de `_calcular_deambular` (`rng.random() <
  temperamento.sociabilidad`) — sin factor ni constante nueva. Cada
  dirección (A→B, B→A) se sortea por separado con la sociabilidad de
  quien comparte en ESA dirección — un individuo poco sociable no
  comparte casi nunca, sin que importe cuán sociable sea el otro.
- **Degradación de la información en el momento de compartir, no al
  recordar** (hallazgo de Diego: "¿una memoria compartida tiene el
  mismo peso que un recuerdo propio?" — no debería). En vez de copiar
  la coordenada exacta que el emisor tiene guardada, se llama a
  `objetivo_recordado()` (ya existente) desde la posición y capacidad
  mental del EMISOR para obtener una versión ya perturbada por su
  propia imprecisión, y es ESA la que se registra en el receptor. El
  recuerdo de segunda mano nace ya menos preciso que el original, y
  vuelve a degradarse cuando el receptor intente usarlo (misma función
  aplicada dos veces, en dos momentos distintos — sin estructura de
  "confianza" nueva, sin metadato de procedencia en `recuerdos`).

## Alcance

**Dentro:**

1. Refactor: extraer de `_procesar_roce_social` (ya mergeado, PR #20)
   el bloque que agrupa conscientes por `(x, y, zona_idx)` en
   `_agrupar_conscientes_por_celda(gestor) -> dict[tuple[int,int,int],
   list[int]]`, filtrando solo por `Posicion, Temperamento,
   CapacidadMental` + el umbral de consciencia — SIN exigir
   `PoolMental`/`Necesidades` en el filtro base (esos son requisitos
   propios de roce social, no de agrupar). `_procesar_roce_social` seguirá
   comprobando `PoolMental`/`Necesidades` por pareja como ya hace hoy
   (`if pm_a is None or ...: continue`) — mismo resultado observable,
   solo cambia DÓNDE se filtra.
2. Nuevo método `_procesar_memoria_compartida(gestor, por_celda)`: para
   cada celda con 2+ conscientes, para cada PAR ORDENADO (a→b y b→a por
   separado), sortea con la sociabilidad de quien comparte; si dispara,
   recorre TODAS las categorías de `MemoriaEspacial.recuerdos` del
   emisor y comparte, por cada una, **el sitio más cercano que conoce
   el emisor desde su propia posición** (una única llamada a
   `objetivo_recordado()` por categoría, no una por coordenada — esa
   función ya hace "encontrar el más cercano + perturbar", no tiene
   sentido llamarla varias veces sobre la misma categoría) y lo
   registra en el receptor vía `registrar_recuerdo()`. No se comparte
   la lista completa de sitios conocidos por categoría, solo el más
   cercano al emisor — ley simple y suficiente ("te cuento del sitio de
   comida que mejor conozco ahora mismo", no un volcado completo de mi
   memoria).
3. `ejecutar()` construye `por_celda` UNA vez por tick (con el helper
   nuevo) y se lo pasa a `_procesar_roce_social` Y a
   `_procesar_memoria_compartida` — evita agrupar dos veces.
4. Tests dirigidos + verificación obligatoria contra el motor real.

**Fuera de alcance, explícito:**

- Aprendizaje por observación en fauna — idea aparte, aplazada.
- Cualquier campo de "confianza"/procedencia en `MemoriaEspacial` —
  deliberadamente NO se distingue estructuralmente un recuerdo propio
  de uno compartido; la degradación en el momento de compartir ya basta.
- Ocio consciente + `Accion.SOCIALIZAR`, sonido físico, reputación/
  rumor — piezas restantes del informe original, cada una su propio
  círculo futuro.
- Ninguna constante de config nueva — la pieza reutiliza
  `Temperamento.sociabilidad`, `objetivo_recordado()` y
  `registrar_recuerdo()` sin ningún parámetro adicional.

## Arquitectura

### Refactor: agrupación compartida

```python
def _agrupar_conscientes_por_celda(
    self, gestor: GestorEntidades,
) -> dict[tuple[int, int, int], list[int]]:
    """Agrupa entidades conscientes por (x, y, zona_idx) exacta.
    Extraido de _procesar_roce_social (2026-09-06) para reutilizarse
    tambien en _procesar_memoria_compartida -- filtra solo por
    Posicion/Temperamento/CapacidadMental + umbral_consciencia_agencia;
    NO exige PoolMental/Necesidades aqui (requisitos propios de roce
    social, comprobados por el llamador que los necesite)."""
    por_celda: dict[tuple[int, int, int], list[int]] = {}
    for eid in gestor.entidades_con(Posicion, Temperamento, CapacidadMental):
        cap_mental = gestor.obtener_componente(eid, CapacidadMental)
        if cap_mental is None or cap_mental.consciencia < self.umbral_consciencia_agencia:
            continue
        pos = gestor.obtener_componente(eid, Posicion)
        if pos is None:
            continue
        por_celda.setdefault((pos.x, pos.y, pos.zona_idx), []).append(eid)
    return por_celda
```

`_procesar_roce_social` pasa a recibir `por_celda` ya construido (en
vez de construirlo él mismo), y sigue comprobando `PoolMental`/
`Necesidades` por pareja exactamente igual que hoy.

### Memoria compartida

```python
def _procesar_memoria_compartida(
    self, gestor: GestorEntidades, por_celda: dict[tuple[int, int, int], list[int]],
) -> None:
    """Disparador 2 del informe de comunicacion (2026-09-06, ver
    docs/superpowers/specs/2026-09-06-memoria-espacial-compartida-design.md):
    para cada par de conscientes que comparte celda, cada direccion se
    sortea por separado con la sociabilidad de quien comparte (misma
    linea que el sesgo gregario de _calcular_deambular). Si dispara, por
    cada categoria de MemoriaEspacial.recuerdos del emisor se comparte el
    sitio mas cercano que el emisor conoce (objetivo_recordado desde SU
    posicion/capacidad mental -- ya perturbado por su propia imprecision)
    hacia el receptor, via registrar_recuerdo()."""
    for ids in por_celda.values():
        if len(ids) < 2:
            continue
        for i in range(len(ids)):
            for j in range(len(ids)):
                if i == j:
                    continue
                emisor_id, receptor_id = ids[i], ids[j]
                self._compartir_memoria(gestor, emisor_id, receptor_id)

def _compartir_memoria(self, gestor: GestorEntidades, emisor_id: int, receptor_id: int) -> None:
    temp_emisor = gestor.obtener_componente(emisor_id, Temperamento)
    if temp_emisor is None or self.rng.random() >= temp_emisor.sociabilidad:
        return
    mem_emisor = gestor.obtener_componente(emisor_id, MemoriaEspacial)
    mem_receptor = gestor.obtener_componente(receptor_id, MemoriaEspacial)
    cap_emisor = gestor.obtener_componente(emisor_id, CapacidadMental)
    cap_receptor = gestor.obtener_componente(receptor_id, CapacidadMental)
    pos_emisor = gestor.obtener_componente(emisor_id, Posicion)
    if mem_emisor is None or mem_receptor is None or cap_emisor is None or cap_receptor is None or pos_emisor is None:
        return
    capacidad_receptor = capacidad_memoria(cap_receptor, self.config)
    for tipo in mem_emisor.recuerdos:
        objetivo = objetivo_recordado(
            mem_emisor, tipo, pos_emisor.x, pos_emisor.y, cap_emisor, self.rng, self.config,
        )
        if objetivo is not None:
            registrar_recuerdo(mem_receptor, tipo, objetivo[0], objetivo[1], capacidad_receptor)
```

Una única llamada a `objetivo_recordado` por categoría (no por
coordenada) — esa función ya combina "encontrar el más cercano a quien
recuerda + perturbar", así que basta una vez por categoría; iterar
sobre cada coordenada guardada y llamarla repetidamente sería
redundante (siempre devolvería el mismo sitio, con una perturbación
distinta cada vez por el sorteo de error, sin ningún propósito real).

## Testing

- `_agrupar_conscientes_por_celda`: mismo comportamiento que el bloque
  que reemplaza — los tests existentes de roce social deben seguir en
  verde sin cambios.
- Memoria compartida: transferencia real de una coordenada de "comida"
  de A a B cuando A comparte (rng forzado a disparar la tirada de A);
  ninguna transferencia si la tirada de A falla; direcciones
  independientes (A comparte con B pero B no comparte con A, verificado
  por separado con temperamentos de sociabilidad distinta); la
  coordenada registrada en B pasa por `objetivo_recordado()` desde la
  posición de A (verificar con A situado LEJOS de su propio recuerdo y
  con memoria imperfecta que la coordenada recibida por B puede diferir
  de la exacta que A tenía guardada — no afirmar que SIEMPRE difiere,
  `error_max` puede salir 0 si A está justo encima del recuerdo); el
  receptor respeta su propio tope de capacidad; ningún efecto si
  cualquiera de los dos no es consciente.
- **Verificación obligatoria contra `BOSQUE_AUTO_TICKS`, no opcional**:
  medir cuántas transferencias ocurren de verdad en juego libre, y
  confirmar mirando la BD que al menos un consciente terminó con una
  coordenada de comida/agua que él mismo nunca visitó directamente
  (evidencia de que la transferencia se ejerce de verdad, no solo en
  el arnés dirigido). Reportar la cifra con honestidad aunque sea baja.

## Pendiente real tras esta pieza

- Aprendizaje por observación en fauna — idea aparte, aplazada.
- Ocio consciente + `Accion.SOCIALIZAR`, sonido físico, reputación/
  rumor sobre liderazgo — piezas restantes del informe original,
  ninguna empezada.
- Sin ninguna constante PROVISIONAL nueva que calibrar — toda la pieza
  reutiliza atributos y funciones ya calibradas (o ya señaladas como
  provisionales) en otro lugar.
