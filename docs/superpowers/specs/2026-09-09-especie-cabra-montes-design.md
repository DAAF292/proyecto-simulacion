# Especie nueva: cabra montés (herbívoro mediano, primera fauna de montaña) — diseño

Fecha: 2026-09-09. Primera especie que puebla `TipoTerreno.MONTANA`,
uno de los tres biomas (junto a desierto y tundra) que hoy tienen flora
propia desde el catálogo ampliado (2026-09-03) pero **cero fauna** --
`main.py:sembrar_poblacion_inicial` solo siembra hoy en bosque y
pradera. Hermana de `2026-09-09-especie-venado-design.md` -- ambas
piezas comparten motivación de biodiversidad de fauna, pero solo venado
ataca directamente el problema nutricional de lobo. Troceadas en dos
specs independientes a petición explícita de Diego.

## Motivación

Diego pidió explícitamente ampliar la biodiversidad de fauna
aprovechando que esta sesión terminó de entender cómo ajustar las
palancas de supervivencia de una especie nueva (criterio maestro de
Diego pasó de 13% a 88% en el mismo día, ver CLAUDE.md "Auditoría de
estabilización"). Propuesta original de Diego ("cabras y ovejas")
descartada en conversación por connotación de domesticación real (cabra
y oveja son de los primeros animales domesticados del mundo real) --
sustituida por **cabra montés**, especie genuinamente salvaje (nunca
domesticada, endémica de terreno alpino) que preserva la idea original
sin ese cariz.

A diferencia de venado, cabra montés **no ataca directamente ningún
problema nutricional de lobo** -- honestidad explícita: hoy ningún
depredador ronda montaña (lobo nace y vive en bosque, sin ninguna razón
mecánica para cruzar hasta allí), así que esta pieza no crea una
dinámica presa-depredador real todavía. Su valor es biodiversidad
genuina -- el primer bioma de fauna que deja de estar vacío -- no una
pieza del rompecabezas de fragilidad de lobo.

## Decisiones ya cerradas con Diego

- **Nombre: `cabra_montes`** -- especie real, nunca domesticada,
  endémica de terreno de montaña (distinta de la cabra doméstica).
- **Bioma de aparición: montaña**, primer bioma de fauna real del
  motor -- requiere extender `sembrar_poblacion_inicial` con una rama
  nueva (`celdas_montana`), a diferencia de venado que reutiliza una
  rama ya existente.
- **Peso: 25-45kg** -- similar orden de magnitud a venado,
  deliberadamente por debajo del rango de lobo (60-90kg) por
  consistencia con el resto del catálogo, aunque sin depredador
  presente hoy esto no tiene efecto práctico inmediato.
- **Dieta: `liquen` + `bayas_montanas`** -- las DOS únicas fuentes de
  alimento que ya existen en montaña (`config/flora.yaml`: `liquen`,
  categoría alimento; `bayas_montanas` de `arbusto_montano`, también
  alimento, marcada `toxico_crudo` -- sin problema, la fauna ya está
  exenta de intoxicación por diseño desde el círculo "cómo cocinar",
  2026-09-08). Coincide con la dieta real de una cabra/gamuza de altura
  (líquenes, arbustos).
- **Reproducción calibrada desde el inicio con los valores YA
  aprendidos esta sesión** -- mismo criterio que venado, arranca
  directamente con el par de hambre/sed 0.0008/0.0004 y concepción
  0.015, no con `necesidades.defecto`.
- **Sin ningún mecanismo especial de escalada/terreno** -- una cabra
  montés real trepa terreno que otras especies no pueden, pero eso
  exigiría tocar `nucleo/relieve.py:pendiente_maxima_transitable` (el
  mismo mecanismo que ya bloquea el paso por diferencia de elevación) --
  explícitamente FUERA de esta pieza, ver Alcance. Cabra montés se mueve
  con las mismas reglas de terreno que cualquier otra fauna.
- **Sin ninguna relación mecánica con venado o caballo** -- biomas
  distintos, sin competencia ni interacción directa en este círculo.

## Alcance

**Dentro:**
1. `componentes/identidad.py`: nueva entrada `CABRA_MONTES` en el enum
   `Especie`.
2. `config/poblacion.yaml`: entrada completa de rangos raciales para
   `cabra_montes` (ver Arquitectura), más `cabras_montes_iniciales`.
3. `config/fisiologia.yaml`: entrada `cabra_montes` bajo `necesidades`,
   mismo par de valores ya validado que venado.
4. `main.py:sembrar_poblacion_inicial`: **cambio real, no solo una
   entrada de catálogo** -- añadir recolección de `celdas_montana`
   (mismo guard `not celda.tiene_agua` que bosque/pradera) y una nueva
   rama en `especies_spawn` para cabra_montes, spawneando ahí. Sin
   ningún fallback a bosque/pradera si `celdas_montana` está vacía
   (mismo comportamiento que el `continue` ya existente para listas
   vacías -- si una semilla concreta no genera montaña suficiente,
   simplemente esa partida no tiene cabras montesas, ley neutra, no un
   error).

**Fuera de alcance, explícito:**
- Cualquier ventaja de movimiento/escalada en terreno de montaña --
  cabra montés usa las mismas reglas de `pendiente_maxima_transitable`
  que el resto de fauna, sin excepción. Si en el futuro se quiere dar
  ventaja real de escalada, es su propio círculo de diseño aparte.
- Cualquier depredador nuevo o relación presa-depredador en montaña --
  no se toca `sistema_depredacion.py`, y no se fuerza a lobo (ni a
  ninguna otra especie) a rondar montaña.
- Presentación (`presentacion/vista_web.py`) -- motor primero.
- Nombre propio -- consciencia en rango bajo de fauna, fallback
  `especie_id` existente.
- Manada/`tipo_refugio_fauna` propio -- sesgo gregario genérico
  (`sociabilidad`), sin estructura colonial.

## Arquitectura

### `componentes/identidad.py`

```python
class Especie(Enum):
    GNOMO = "gnomo"
    LOBO = "lobo"
    CONEJO = "conejo"
    ARDILLA = "ardilla"
    CABALLO = "caballo"
    VENADO = "venado"
    CABRA_MONTES = "cabra_montes"  # primera fauna de TipoTerreno.MONTANA --
                                     # ver CLAUDE.md, conversacion de
                                     # biodiversidad del 2026-09-09
```

### `config/poblacion.yaml`

Nueva entrada `cabra_montes` bajo `rangos_raciales`, mismo molde que el
resto del catálogo. Todos los valores PROVISIONAL, sin calibrar contra
el harness completo:

```yaml
  cabra_montes:
    medio_alimentacion: recolectar
    dieta: [liquen, bayas_montanas]
    peso: [25, 45]
    altura: [0.7, 0.9]
    longevidad: [10, 16]
    duracion_gestacion_dias: [60, 90]  # mismo criterio de sostenibilidad
                                         # ya usado en caballo/venado, no
                                         # fidelidad biologica estricta
    camada: [1, 2]
    fraccion_madurez: 0.2
    factor_base_concepcion: 0.015
    puntos_agarre: 0  # una cabra montes no sujeta objetos
    fuerza: [0.3, 0.6]
    agilidad: [0.7, 0.95]  # buena movilidad, aunque sin ventaja de
                             # escalada real en este circulo (ver Alcance)
    velocidad: [0.5, 0.8]
    resistencia_enfermedad: [0.2, 0.5]
    agudeza_sensorial: [0.5, 0.8]
    vitalidad_maxima: [0.3, 0.6]
    resistencia_maxima: [0.3, 0.6]
    curacion: [0.01, 0.03]
    recuperacion: [0.08, 0.15]
    valentia: [0.15, 0.4]
    sociabilidad: [0.5, 0.85]  # rebaños pequeños de montaña
    agresividad: [0.05, 0.2]
    dominancia: [0.15, 0.4]
    empatia: [0.4, 0.7]
    lealtad: [0.4, 0.7]
    fe: [0.0, 0.1]
    curiosidad: [0.2, 0.5]
    inteligencia: [0.1, 0.3]
    memoria: [0.2, 0.5]
    voluntad: [0.1, 0.3]
    resiliencia: [0.3, 0.6]
    estabilidad_mental_maxima: [0.4, 0.6]
    consciencia: [0.0, 0.1]
```

`poblacion.yaml` gana además `cabras_montes_iniciales: 8` (PROVISIONAL)
junto a los otros `*_iniciales` ya existentes.

### `config/fisiologia.yaml`

```yaml
  cabra_montes:
    # AÑADIDO 2026-09-09 (arco de biodiversidad de fauna, hermana de
    # venado). Mismo par ya validado esta sesion en gnomo/lobo/ardilla --
    # arranca estable desde el primer dia, no con `defecto`.
    tasa_perdida_saciedad_por_tick: 0.0008
    probabilidad_muerte_saciedad_critica: 0.0004
    tasa_perdida_hidratacion_por_tick: 0.0008
    probabilidad_muerte_deshidratacion: 0.0004
```

### `main.py:sembrar_poblacion_inicial`

```python
celdas_bosque: list[tuple[int, int]] = []
celdas_pradera: list[tuple[int, int]] = []
celdas_montana: list[tuple[int, int]] = []  # NUEVO

for y in range(zona.alto):
    for x in range(zona.ancho):
        celda = zona.obtener_celda(x, y)
        if celda.tipo_terreno == TipoTerreno.BOSQUE and not celda.tiene_agua:
            celdas_bosque.append((x, y))
        elif celda.tipo_terreno == TipoTerreno.PRADERA and not celda.tiene_agua:
            celdas_pradera.append((x, y))
        elif celda.tipo_terreno == TipoTerreno.MONTANA and not celda.tiene_agua:  # NUEVO
            celdas_montana.append((x, y))

# ... (candidatas_bosque sin cambios)

especies_spawn = [
    # ... entradas existentes sin cambios ...
    (
        Especie.CABRA_MONTES,
        poblacion_cfg.get("cabras_montes_iniciales", 8),
        celdas_montana,  # SIN fallback a bosque/pradera -- si una
                          # semilla no genera montaña suficiente, esa
                          # partida simplemente no tiene cabras montesas
                          # (el guard "if not celdas_candidatas: continue"
                          # ya existente lo cubre sin cambios)
    ),
]
```

### Por qué no hace falta tocar nada más

`medio_alimentacion: recolectar` cubre el mismo camino genérico que el
resto del catálogo herbívoro. `crear_criatura`/`nacer_criatura` ya son
genéricas por especie. El `guard not celda.tiene_agua` para montaña es
idéntico al ya usado en bosque/pradera -- mismo patrón, sin necesidad
de ninguna comprobación nueva de terreno (la ausencia de ventaja de
escalada real significa que cabra montés se mueve con las mismas reglas
de `pendiente_maxima_transitable` que cualquier fauna, así que no hace
falta ningún cambio en `nucleo/relieve.py`). El narrador no necesita
ningún cambio -- "cabra montés" es gramaticalmente femenino
("una cabra montés" ya es correcto sin artículo especial, pero
`_ESPECIES_FEMENINAS` de `presentacion/narrador.py` sí necesita ganar
`"cabra_montes"` para que la concordancia de género sea correcta (mismo
patrón ya usado para "ardilla") -- único cambio de presentación real de
esta pieza, mínimo y mecánico.

## Persistencia

Sin cambios de esquema -- `Especie` se persiste como texto
(`especie.value`), añadir un valor nuevo al enum no requiere ninguna
migración.

## Testing

Mismo criterio de "ley física" que el resto del proyecto:

- `Especie.CABRA_MONTES` existe y es distinto de las 6 especies
  anteriores (incluyendo venado si esa pieza ya está mergeada, o de las
  5 anteriores si se implementa antes).
- `crear_criatura`/`nacer_criatura` con `Especie.CABRA_MONTES` producen
  una entidad completa (todos los componentes esperados, valores dentro
  de los rangos configurados).
- La siembra inicial coloca cabras montesas reales en celdas de
  `TipoTerreno.MONTANA` sin agua, en la cantidad configurada -- y NO en
  ninguna celda de bosque/pradera (confirmar explícitamente el
  aislamiento por bioma, a diferencia de conejo/caballo que sí
  comparten fallback).
- Si `celdas_montana` está vacía (semilla sin montaña generada), la
  siembra de cabra_montes no crea ninguna entidad y no lanza ninguna
  excepción -- mismo comportamiento ya cubierto por el guard genérico.
- `_ESPECIES_FEMENINAS` de `presentacion/narrador.py` incluye
  `"cabra_montes"` -- test de concordancia de género, mismo patrón que
  el test ya existente de ardilla.

**Verificación contra el motor real, OBLIGATORIA, no opcional**:
`BOSQUE_AUTO_TICKS` con población real, confirmando que cabra_montes
existe y sobrevive un tramo razonable de la corrida sin excepciones.
Dado que esta pieza NO introduce ningún depredador en montaña, es
esperable (y debe reportarse como hallazgo, no como fallo) que cabra
montés sobreviva casi sin depredación -- reportar también si sostiene
su propia población (concepciones/nacimientos) de forma razonable, y si
la especie efectivamente aparece en la corrida (dado que montaña es una
fracción del mapa, confirmar con al menos 2-3 semillas distintas que
`celdas_montana` no queda vacía en juego normal).

## Pendiente real tras esta pieza

- Todos los valores del catálogo de cabra_montes son PROVISIONALES, sin
  calibrar contra el harness completo.
- Sin ningún depredador real en montaña -- si en el futuro se quiere
  una dinámica presa-depredador ahí (fauna subterránea/de montaña
  propia, ya mencionada como horizonte lejano en CLAUDE.md), es un
  círculo de diseño aparte, no asumido aquí.
- Sin ventaja de escalada/movimiento propio de terreno de montaña --
  señalado explícitamente como fuera de alcance, candidato futuro real
  si se quiere diferenciar mecánicamente a cabra montés más allá del
  catálogo de atributos.
- Sin representación visual -- motor primero.
- Desierto y tundra siguen siendo los otros dos biomas sin fauna
  propia -- no se tocan en esta pieza, quedan como horizonte futuro ya
  señalado en la conversación de biodiversidad.
