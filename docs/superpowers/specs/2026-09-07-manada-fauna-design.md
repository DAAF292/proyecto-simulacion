# Manada — estructuras gregarias reales en fauna — diseño

Fecha: 2026-09-07. Arranca un arco nuevo, independiente del informe de
"capa de comunicación" ya cerrado (aunque reutiliza infraestructura de
varios arcos previos: `Asentamiento`, `MemoriaEspacial`,
`medio_alimentacion`, `sociabilidad`).

## Motivación

Diego: los seres conscientes ya tienen asentamiento/liderazgo/almacén
(arco "hilo individual" + "capa de comunicación"); la fauna debería
tener sus propias estructuras gregarias cuando su comportamiento real
lo justifique — pero **no todas las especies se agrupan igual**
(pregunta explícita: "¿una manada de lobos se comporta como una
manada de conejos?").

**Hallazgo real, verificado especie por especie antes de proponer nada
nuevo**: la mayor parte de esa diferenciación YA EXISTE, repartida en
rasgos ya construidos:

| Especie | Comportamiento real | Ya cubierto por |
|---|---|---|
| Lobo | Manada de caza | `medio_alimentacion == "cazar"` (único de las 4) — bono de caza en grupo y techo de presa por manada YA son específicos de lobo |
| Caballo | Rebaño de defensa/pastoreo | `sociabilidad` más alta del catálogo (0.7-0.95) + bono de defensa en grupo genérico (ya existe) |
| Ardilla | Mayormente solitaria | `sociabilidad` más baja del catálogo (0.3-0.6) — rara vez formará grupo cohesionado sin excluirla a mano |
| Conejo | Madriguera excavada y compartida | **Nada todavía — la única pieza genuinamente nueva** |

Consecuencia de diseño: **no hace falta ninguna categoría nueva de
"tipo de manada"** (repetiría el error ya identificado y corregido una
vez en este proyecto con las cuevas categorizadas por tamaño/bioma) —
la sociabilidad y `medio_alimentacion`, ya continuos/existentes, bastan
para que cada especie se comporte de forma distinta de manera
emergente. Solo la madriguera compartida de conejo exige un rasgo
racial nuevo, mismo patrón categórico y físico que `medio_alimentacion`
(un hecho real de la especie, no autoría de un suceso concreto).

## Decisiones ya cerradas con Diego

- **`Manada` como objeto real, recalculado periódicamente** (mismo
  patrón que `Asentamiento`: sin identidad persistida entre
  recálculos), no solo un ajuste del sesgo gregario ya existente.
- **Formación por pura proximidad, sin gate de sociabilidad** —
  cualquier 2+ conespecíficos cercanos cuentan como manada ese día. La
  sociabilidad de cada individuo sigue decidiendo, como ya hace hoy,
  cuánto tira hacia el centro del grupo (ver Consumidor 1) — así una
  especie poco sociable rara vez se comporta como manada real aunque
  la geometría la agrupe por casualidad, sin necesitar ninguna
  categoría nueva.
- **Cadencia diaria**, igual que `Asentamiento` — simplificación
  aceptada explícitamente (la fauna se mueve más que un refugio fijo,
  así que la manada puede quedar algo desfasada durante el día);
  calibración futura si hace falta, no bloqueante ahora.
- **Sin liderazgo/macho alfa en este círculo** — reutilizaría
  `calcular_liderazgo` tal cual (`dominancia` ya existe para las 4
  especies), extensión futura obvia pero fuera de aquí.
- **Refactor incluido**: `agrupar_por_proximidad`/`calcular_centro`
  viven hoy dentro de `nucleo/asentamiento.py` pero son genéricas (nada
  de refugios/gnomo en su lógica) — se extraen a `nucleo/agrupacion.py`,
  del que importan tanto `asentamiento.py` como el nuevo `manada.py`,
  sin cambiar su comportamiento.
- **Madriguera compartida (conejo)**: nuevo rasgo racial
  `tipo_refugio_fauna` (config, valores `"colonial"` / sin declarar =
  ninguno), mismo patrón categórico que `medio_alimentacion`. Miembros
  coloniales de una misma manada sincronizan su memoria de "refugio"
  por VOTO DE MAYORÍA entre lo que los miembros YA recuerdan
  individualmente (no una coordenada elegida a dedo) — la madriguera
  emerge y se estabiliza sola con los días porque la persistencia real
  vive en la `MemoriaEspacial` ya persistida de cada individuo, no en
  `Manada` (que sigue sin identidad entre días).
- **Sin gating por especie en el consumidor de movimiento** — el
  mismo mecanismo aplica a cualquier especie con `Posicion`/
  `Temperamento`, gnomo incluido (que ya es en su mayoría exento vía el
  sesgo de territorio, pero no se excluye por decreto); si resulta
  raro en la práctica, se reporta como hallazgo, no se previene a
  priori.

## Alcance

**Dentro:**

1. `nucleo/agrupacion.py` (nuevo): `agrupar_por_proximidad` y
   `calcular_centro`, extraídas tal cual de `nucleo/asentamiento.py`
   (sin cambios de comportamiento). `nucleo/asentamiento.py` y
   `sistemas/sistema_asentamiento.py` actualizan sus imports.
2. `nucleo/manada.py` (nuevo): dataclass `Manada` (`id`, `centro`,
   `miembros: frozenset[int]`, `especie`, `zona_idx`) — mismo molde que
   `Asentamiento` sin `lideres`/`almacen_id`.
3. `sistemas/sistema_manada.py` (nuevo), cadencia diaria: agrupa
   posiciones de fauna por especie + zona (una manada nunca mezcla
   especies distintas, ley neutra evidente — un lobo y un conejo no
   forman manada juntos) vía `agrupar_por_proximidad`; puebla
   `mundo.manadas`. Para especies con `tipo_refugio_fauna == "colonial"`,
   sincroniza la memoria de "refugio" de los miembros por voto de
   mayoría (ver Arquitectura).
4. `Mundo` gana `manadas: dict[int, Manada]` (mismo patrón que
   `asentamientos`).
5. `config/comportamiento.yaml`, sección `manada:`:
   `radio_manada_celdas` (PROVISIONAL).
6. `config/poblacion.yaml`: `tipo_refugio_fauna: colonial` añadido
   SOLO a `conejo`.
7. Consumidor: `sistema_movimiento.py:_calcular_deambular`, sesgo
   gregario — si la entidad pertenece hoy a una `Manada`, tira hacia su
   `centro` en vez de (o antes que) el conespecífico más cercano; sin
   manada, comportamiento actual sin cambios.
8. Tests dirigidos + verificación obligatoria contra el motor real.

**Fuera de alcance, explícito:**

- Liderazgo/macho-alfa de manada — extensión futura, no aquí.
- Cualquier cambio a "techo de presa por manada"/bono de caza en grupo
  de lobo (`contar_conspecificos_cercanos`) — se queda exactamente
  igual, sin migrar a la nueva estructura.
- Excavar como acción consciente — la madriguera es instintiva
  (memoria, no `Construccion`), mismo criterio que el refugio
  individual de fauna hoy.
- Cualquier categoría nueva de "tipo de manada" más allá del binario
  colonial/no-colonial ya justificado — lobo/caballo/ardilla se
  diferencian solo por rasgos ya existentes (`medio_alimentacion`,
  `sociabilidad`), sin rasgo nuevo para ellos.
- Persistencia de `Manada` en SQLite — igual que `Asentamiento`, 100%
  derivable, no se guarda.

## Arquitectura

### Formación diaria (`sistemas/sistema_manada.py`)

```python
def ejecutar(self, gestor, mundo, reloj, bus_eventos) -> None:
    posiciones_por_especie_zona: dict[tuple[Especie, int], dict[int, tuple[int,int]]] = {}
    for eid in gestor.entidades_con(Identidad, Posicion, Temperamento):
        ident = gestor.obtener_componente(eid, Identidad)
        pos = gestor.obtener_componente(eid, Posicion)
        clave = (ident.especie, pos.zona_idx)
        posiciones_por_especie_zona.setdefault(clave, {})[eid] = (pos.x, pos.y)

    nuevas: dict[int, Manada] = {}
    siguiente_id = 1
    for (especie, zona_idx), posiciones in posiciones_por_especie_zona.items():
        for grupo in agrupar_por_proximidad(posiciones, self.radio_manada):
            if len(grupo) < 2:
                continue
            centro = calcular_centro(posiciones, grupo)
            nuevas[siguiente_id] = Manada(
                id=siguiente_id, centro=centro, miembros=frozenset(grupo),
                especie=especie, zona_idx=zona_idx,
            )
            siguiente_id += 1
            if self._es_colonial(especie):
                self._sincronizar_madriguera(gestor, grupo)
    mundo.manadas = nuevas
```

### Madriguera compartida (voto de mayoría)

```python
def _sincronizar_madriguera(self, gestor, miembros) -> None:
    conteo: dict[tuple[int,int], int] = {}
    for mid in miembros:
        mem = gestor.obtener_componente(mid, MemoriaEspacial)
        if mem is None:
            continue
        for sitio in mem.recuerdos.get("refugio", []):
            conteo[sitio] = conteo.get(sitio, 0) + 1
    if not conteo:
        return  # nadie recuerda ningun sitio todavia -- nada que sincronizar
    sitio_mayoritario = max(conteo, key=conteo.get)
    for mid in miembros:
        mem = gestor.obtener_componente(mid, MemoriaEspacial)
        cap_mental = gestor.obtener_componente(mid, CapacidadMental)
        if mem is not None and cap_mental is not None:
            capacidad = capacidad_memoria(cap_mental, self.config)
            registrar_recuerdo(mem, "refugio", *sitio_mayoritario, capacidad)
```

Sin coordenada elegida a dedo: el sitio que gana es el que YA conoce
más gente del grupo (empieza vacío, se estabiliza solo con los días
porque cada `registrar_recuerdo` refuerza la posición del sitio en el
FIFO individual, ya persistido).

### Consumidor — cohesión de movimiento (`_calcular_deambular`)

En el sesgo gregario actual (probabilidad = `sociabilidad`), antes de
buscar el conespecífico más cercano: si `manada_de(mundo, entidad_id)`
devuelve una `Manada`, el objetivo es su `centro`; si no, cae al
comportamiento actual (`_buscar_conspecifico_mas_cercano`). Mismo
umbral de distancia deseada (`dist_deseada_conspecifico`) para decidir
si merece la pena moverse.

## Config nueva (PROVISIONAL, sin calibrar)

```yaml
# config/comportamiento.yaml
manada:
  radio_manada_celdas: 8  # PROVISIONAL -- mayor que radio_cluster_celdas
    # de asentamiento (6) porque la fauna roza mas terreno que un refugio fijo

# config/poblacion.yaml, SOLO en conejo
tipo_refugio_fauna: colonial  # PROVISIONAL
```

## Testing

- `agrupar_por_proximidad`/`calcular_centro`: el refactor no cambia
  comportamiento — tests existentes de asentamiento siguen en verde
  sin modificarlos.
- `SistemaManada.ejecutar`: agrupa por especie Y zona (un lobo y un
  conejo cercanos no forman manada juntos; dos lobos en zonas distintas
  tampoco); grupos de 1 no cuentan; centro calculado correctamente.
- Madriguera: sin ningún miembro con memoria de refugio previa, no
  sincroniza nada; con mayoría clara, todos los miembros terminan con
  ese sitio en su propia memoria; especie no colonial nunca sincroniza
  aunque forme manada.
- `_calcular_deambular`: con manada, tira hacia el centro (verificar
  con un centro lejano y un conespecífico cercano en dirección
  opuesta, confirmando que gana el centro); sin manada, comportamiento
  idéntico a antes de esta pieza.
- **Verificación obligatoria contra `BOSQUE_AUTO_TICKS`, no opcional**:
  medir cuántas manadas se forman por especie (esperable: caballo/
  conejo con más frecuencia que lobo/ardilla, dado el orden real de
  sociabilidad), y si algún conejo terminó con una coordenada de
  refugio que él mismo nunca visitó (evidencia de madriguera
  compartida real). Reportar con honestidad aunque sea bajo.

## Pendiente real tras esta pieza

- `radio_manada_celdas`/`tipo_refugio_fauna` PROVISIONALES, sin
  calibrar contra el harness completo.
- Liderazgo/macho-alfa de manada — extensión futura obvia, mismo
  primitivo (`calcular_liderazgo`) ya reutilizable.
- Unificación futura posible entre "techo de presa por manada" (conteo
  instantáneo) y esta nueva estructura persistente-por-día — no hecha
  aquí, evita un refactor no pedido.
- Aprendizaje por observación en fauna (crías siguiendo a un adulto)
  sigue aplazado desde memoria espacial compartida (2026-09-06) — no
  es parte de este círculo pero es un candidato natural relacionado.
