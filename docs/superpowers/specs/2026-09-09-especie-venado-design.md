# Especie nueva: venado (herbívoro mediano, presa solitaria de lobo) — diseño

Fecha: 2026-09-09. Segunda especie de la línea de biodiversidad de fauna
abierta el mismo día (ver CLAUDE.md, "Auditoría de estabilización" y la
conversación posterior sobre mamíferos medianos). Hermana de
`2026-09-09-especie-cabra-montes-design.md` — ambas piezas comparten
motivación de biodiversidad, pero solo venado ataca directamente el
problema nutricional de lobo. Trocedadas en dos specs independientes a
petición explícita de Diego para poder soltarlas por separado al
pipeline.

## Motivación

Ya documentado en CLAUDE.md ("Por qué lobo se muere de hambre pese a
cazar más que nadie", 2026-09-04): la fórmula de saciedad por captura
(`saciedad = (peso_presa/peso_cazador) * eficiencia_biomasa_saciedad`)
depende del ratio de masa -- conejo/ardilla apenas alimentan a un lobo
(60-90kg), y el 75% de su nutrición real venía de gnomo, la presa más
fráigil y escasa del motor. `caballo` (2026-09-05) se diseñó para dar a
lobo una presa de ratio favorable, pero exige caza en MANADA (demasiado
pesado para un lobo solo) -- y esta misma sesión confirmó con 73
corridas que esa manada prácticamente nunca se forma (población de lobo
nunca supera 18 individuos, muy lejos del umbral de ~5 cazando a la vez
que exige la fórmula).

Venado cierra el hueco que caballo dejó abierto: una presa de peso
**por debajo** de lobo, cazable en SOLITARIO por la vía normal ya
existente (`dims_p.peso >= peso_cazador` ya permite perseguir cualquier
presa más ligera, sin pasar por el techo de manada) -- cero código
nuevo de depredación, a diferencia de caballo. La hipótesis a verificar:
alimentar a lobo sin depender de manada hace crecer su población lo
bastante como para que la manada -- si alguna vez se forma de verdad --
pueda observarse por primera vez, y solo entonces ver si intenta cazar
caballo.

## Decisiones ya cerradas con Diego

- **Nombre: `venado`** -- sin ninguna connotación de domesticación,
  descartado explícitamente "cabra"/"oveja" por ese motivo en la
  conversación previa a esta spec.
- **Bioma de aparición: bosque**, el mismo que gnomo/lobo/ardilla (no
  pradera) -- decisión deliberada para maximizar la probabilidad de
  encuentro real con lobo sin depender de que cruce a otro bioma.
  `main.py:sembrar_poblacion_inicial` ya tiene la rama `celdas_bosque`
  lista, mismo patrón que gnomo/lobo/ardilla.
- **Peso: 20-40kg, deliberadamente por debajo de todo el rango de
  lobo (60-90kg)** -- garantiza que la caza sea SIEMPRE viable en
  solitario por la vía normal, sin tocar `_es_presa_valida`/
  `_calcular_caza` ni el mecanismo de techo por manada de caballo. Con
  este peso, una captura da entre el 33% y el 67% de saciedad a un lobo
  (según los pesos concretos sorteados), muy por encima del 4.5% de
  conejo o el 0.9% de ardilla.
- **Reproducción calibrada desde el inicio con los valores YA
  aprendidos esta sesión, no con `necesidades.defecto`** -- decisión
  explícita para no repetir el patrón de caballo (nació con valores
  universales, tuvo que corregirse días después tras confirmarse
  fragilidad real). Se arranca directamente con el mismo par de
  hambre/sed (0.0008/0.0004) y la misma concepción moderada (0.015) que
  ya demostraron sostener población en las 4 especies existentes.
- **Sin ningún mecanismo especial de huida/velocidad** -- mismo
  criterio que caballo, reutiliza `Accion.HUIR` tal cual, expresado
  solo con valentía baja en el catálogo.
- **Sin caza en manada ni relación con caballo en este círculo** --
  venado es presa exclusiva de lobo en solitario; no compite ni
  interactúa mecánicamente con caballo (biomas distintos).

## Alcance

**Dentro:**
1. `componentes/identidad.py`: nueva entrada `VENADO` en el enum
   `Especie`.
2. `config/poblacion.yaml`: entrada completa de rangos raciales para
   `venado` (ver Arquitectura), más `venados_iniciales`.
3. `config/fisiologia.yaml`: entrada `venado` bajo `necesidades`, con el
   par de valores ya validado (ver Arquitectura) -- NO se deja en
   `defecto`.
4. `main.py:sembrar_poblacion_inicial`: añadir venado a
   `especies_spawn`, spawneando en `celdas_bosque` junto a gnomo/lobo/
   ardilla.

**Fuera de alcance, explícito:**
- Cualquier cambio a `sistema_depredacion.py`/`sistema_movimiento.py` --
  la caza de venado usa exactamente el mismo camino 1-contra-1 que ya
  usan conejo/ardilla/gnomo, sin ninguna rama nueva.
- Caza en manada, techo de presa -- no aplica a venado por diseño (ya
  es cazable en solitario).
- Presentación (`presentacion/vista_web.py`) -- motor primero, mismo
  criterio que el resto del catálogo sin sprite propio.
- Nombre propio -- consciencia en rango bajo de fauna, sigue el
  fallback `especie_id` existente.
- Manada/`tipo_refugio_fauna` propio -- venado usa el sesgo gregario
  genérico (`sociabilidad`) igual que caballo/ardilla, sin ninguna
  estructura colonial tipo conejo.

## Arquitectura

### `componentes/identidad.py`

```python
class Especie(Enum):
    GNOMO = "gnomo"
    LOBO = "lobo"
    CONEJO = "conejo"
    ARDILLA = "ardilla"
    CABALLO = "caballo"
    VENADO = "venado"  # herbivoro mediano, mas ligero que lobo -- presa
                        # solitaria real, ver CLAUDE.md "Por que lobo se
                        # muere de hambre..." (2026-09-04) y la conversacion
                        # de biodiversidad del 2026-09-09
```

### `config/poblacion.yaml`

Nueva entrada `venado` bajo `rangos_raciales`, mismo molde que las 5
especies existentes. Todos los valores PROVISIONAL, sin calibrar contra
el harness completo -- pero el par de fecundidad/riesgo parte YA de los
valores ya confirmados estables en esta sesión, no de cero:

```yaml
  venado:
    medio_alimentacion: recolectar
    dieta: [hierba, brotes_helecho, bellotas]
    peso: [20, 40]
    altura: [0.8, 1.2]
    longevidad: [10, 18]
    duracion_gestacion_dias: [60, 90]  # deliberadamente corta frente a
                                         # los ~200 dias reales de un
                                         # cervido -- mismo criterio de
                                         # sostenibilidad ya usado en
                                         # caballo, no fidelidad biologica
                                         # estricta
    camada: [1, 2]
    fraccion_madurez: 0.2
    factor_base_concepcion: 0.015
    puntos_agarre: 0  # un venado no sujeta objetos
    fuerza: [0.3, 0.6]
    agilidad: [0.6, 0.9]
    velocidad: [0.6, 0.9]
    resistencia_enfermedad: [0.2, 0.5]
    agudeza_sensorial: [0.5, 0.8]
    vitalidad_maxima: [0.3, 0.6]
    resistencia_maxima: [0.3, 0.6]
    curacion: [0.01, 0.03]
    recuperacion: [0.08, 0.15]
    valentia: [0.1, 0.3]  # baja a proposito, prefiere huir -- mismo
                            # criterio que caballo
    sociabilidad: [0.6, 0.9]  # animal de manada
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

`poblacion.yaml` gana además `venados_iniciales: 10` (PROVISIONAL) junto
a los otros `*_iniciales` ya existentes.

### `config/fisiologia.yaml`

Nueva entrada `venado` bajo `necesidades`, NO se deja en `defecto` --
arranca directamente con el par ya validado esta sesión para gnomo/
lobo/ardilla:

```yaml
  venado:
    # AÑADIDO 2026-09-09 (arco de biodiversidad de fauna). A diferencia
    # de caballo (que nacio con `defecto` y necesito su propio fix dias
    # despues, ver CLAUDE.md "Calibracion de estabilidad del ecosistema"),
    # venado arranca YA con el mismo par de hambre/sed que esta sesion
    # confirmo estable en las 4 especies existentes -- evita repetir el
    # mismo ciclo de "añadir con defecto, descubrir fragilidad una
    # semana despues".
    tasa_perdida_saciedad_por_tick: 0.0008
    probabilidad_muerte_saciedad_critica: 0.0004
    tasa_perdida_hidratacion_por_tick: 0.0008
    probabilidad_muerte_deshidratacion: 0.0004
```

### `main.py:sembrar_poblacion_inicial`

```python
especies_spawn = [
    (Especie.GNOMO, poblacion_cfg.get("gnomos_iniciales", 18), candidatas_bosque),
    (Especie.LOBO, poblacion_cfg.get("lobos_iniciales", 6), candidatas_bosque),
    (Especie.ARDILLA, poblacion_cfg.get("ardillas_iniciales", 30), candidatas_bosque),
    (
        Especie.VENADO,
        poblacion_cfg.get("venados_iniciales", 10),
        candidatas_bosque,
    ),
    (
        Especie.CONEJO,
        poblacion_cfg.get("conejos_iniciales", 30),
        celdas_pradera if celdas_pradera else candidatas_bosque,
    ),
    (
        Especie.CABALLO,
        poblacion_cfg.get("caballos_iniciales", 9),
        celdas_pradera if celdas_pradera else candidatas_bosque,
    ),
]
```

### Por qué no hace falta tocar nada más

`medio_alimentacion: recolectar` cubre exactamente el mismo camino de
comportamiento que gnomo/conejo/ardilla/caballo (RECOLECTAR/COMER
genérico por catálogo). `nucleo/entidad.py:crear_criatura`/
`nacer_criatura` ya son genéricas por especie. La caza de venado por
lobo usa el camino 1-contra-1 ya existente sin ninguna condición nueva
(peso de venado siempre < peso de lobo por diseño, así que
`dims_p.peso >= peso_cazador` nunca bloquea el intento). El narrador no
necesita ningún cambio -- "venado" es gramaticalmente masculino, mismo
criterio por defecto que gnomo/lobo/conejo/caballo.

## Persistencia

Sin cambios de esquema -- `Especie` se persiste como texto
(`especie.value`), añadir un valor nuevo al enum no requiere ninguna
migración.

## Testing

Mismo criterio de "ley física" que el resto del proyecto:

- `Especie.VENADO` existe y es distinto de las 5 especies anteriores.
- `crear_criatura`/`nacer_criatura` con `Especie.VENADO` producen una
  entidad completa (todos los componentes esperados, valores dentro de
  los rangos configurados).
- La siembra inicial coloca venados reales en celdas de bosque sin
  agua, en la cantidad configurada.
- Un lobo puede perseguir/cazar un venado en solitario sin necesitar
  ningún aliado cerca -- confirmar explícitamente que
  `_calcular_caza`/`_es_presa_valida` lo tratan como presa válida por
  la vía normal (peso venado < peso lobo), sin pasar por el código de
  techo de manada.
- Una captura exitosa de venado por un lobo produce un aporte de
  saciedad sustancialmente mayor que una captura de conejo/ardilla
  (confirmar el ratio real con los pesos del catálogo).

**Verificación contra el motor real, OBLIGATORIA, no opcional**:
`BOSQUE_AUTO_TICKS` con población real, confirmando que venado existe,
sobrevive, y que lobo lo caza de verdad en juego libre (contar eventos
de depredación con víctima venado). Reportar también si venado sostiene
su propia población (concepciones/nacimientos) de forma razonable.

## Pendiente real tras esta pieza

- Todos los valores del catálogo de venado son PROVISIONALES, sin
  calibrar contra el harness completo.
- Si lobo empieza a sostener población real gracias a venado, el
  siguiente paso natural (no parte de esta pieza) es remedir si la caza
  en manada sobre caballo empieza a dispararse -- candidato directo de
  seguimiento, no diseñado aquí.
- Sin representación visual -- motor primero.
