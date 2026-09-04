# Especie nueva: caballo (herbívoro grande, presa sostenible de lobo) — diseño

Fecha: 2026-09-05. Primera pieza de una línea de investigación distinta
de "hilo individual": el colapso de población de lobo (ver CLAUDE.md,
"Por qué lobo se muere de hambre pese a cazar más que nadie"). Esta
pieza es SOLO la especie nueva; la caza en manada (varios lobos
coordinándose contra una presa) queda explícitamente aparcada para una
sesión de diseño aparte -- no se construye aquí.

## Motivación

Medido contra el motor real (4 semillas × 6000 ticks): lobo caza conejo
más que a ninguna otra presa (40 capturas, frente a 28 de ardilla y 27
de gnomo), así que no tiene ningún problema real para encontrar o cazar
presa. El problema es que la fórmula de saciedad por captura
(`sistema_depredacion.py`: `saciedad = (peso_presa/peso_cazador) *
eficiencia_biomasa_saciedad`) depende del RATIO DE MASA -- con los pesos
reales del catálogo (lobo ~75kg, conejo ~2.25kg, ardilla ~0.45kg), cada
captura de conejo solo da ~4.5% de saciedad y cada ardilla ~0.9%. El 75%
de toda la nutrición real que obtiene un lobo viene de sus capturas de
gnomo (~23% de saciedad por captura), pese a ser la presa menos
frecuente -- y gnomo es también la especie más frágil/escasa del motor.
Un herbívoro de peso comparable o mayor al de lobo le daría una fuente
de alimento con ratio de masa favorable, sin depender de que gnomo
sobreviva.

## Decisiones ya cerradas con Diego

- **Nombre: `caballo`** -- un caballo salvaje (no domesticado) es
  biológicamente real y legítimo, sin ninguna connotación de
  domesticación que resolver.
- **Bioma de aparición: pradera**, junto a conejo -- ya confirmado hoy
  con datos reales que bosque (donde nace lobo) y pradera son biomas
  CONTIGUOS (distancia mínima borde a borde de 1 celda), y que lobo ya
  caza conejo en pradera sin ningún problema de acceso.
- **Población inicial: 8-10 fundadores.**
- **Sin ningún mecanismo especial de huida/velocidad** -- se reutiliza
  el `Accion.HUIR` ya existente (depende de valentía/urgencia del
  individuo, con la magnitud de amenaza ya calculada por diferencia de
  peso en `nucleo/disposicion.py`). El "caballo prefiere huir antes que
  pelear" se expresa dándole valentía BAJA en el catálogo, no inventando
  mecánica nueva.
- **Reproducción calibrada para SOSTENIBILIDAD, no fidelidad biológica
  estricta** -- decisión consciente y documentada: un caballo real
  gesta ~340 días con cría única, la MISMA combinación que ya causa el
  colapso de gnomo bajo el riesgo de fondo medido hoy. Se prioriza que
  caballo cumpla su propósito real (presa sostenible) sobre el realismo
  exacto de gestación.
- **Sin caza en manada en este círculo** -- un lobo solo cazará a
  caballo con las MISMAS reglas 1 contra 1 que ya existen
  (`_resolver_ataque`, ratio de fuerza). Si eso da una probabilidad de
  éxito baja para un lobo solo contra un animal mucho más grande, es el
  resultado CORRECTO y esperado para este círculo -- no forzar que se
  cace con facilidad. El valor real de caballo sin caza en manada es
  limitado (una presa grande que un lobo solo rara vez abate) pero
  honesto; la caza en manada es la pieza que lo completaría, aparcada
  aparte.

## Alcance

**Dentro:**
1. `componentes/identidad.py`: nueva entrada `CABALLO` en el enum `Especie`.
2. `config/poblacion.yaml`: entrada completa de rangos raciales para
   `caballo` (ver Arquitectura).
3. `main.py:sembrar_poblacion_inicial`: añadir caballo a
   `especies_spawn`, spawneando en `celdas_pradera` junto a conejo.

**Fuera de alcance, explícito:**
- Caza en manada -- círculo futuro aparte, sin empezar.
- Cualquier mecanismo nuevo de huida/velocidad/detección -- se reutiliza
  `Accion.HUIR` tal cual.
- Presentación (`presentacion/vista_web.py`) -- sin sprite ni
  representación visual específica para caballo en este círculo; el
  visor ya está diseñado para no romperse con una categoría vacía
  (mismo criterio que otras especies sin arte propio).
- Nombre propio para caballo -- su consciencia queda en el rango bajo
  de fauna (igual que lobo/conejo/ardilla), así que sigue el fallback
  `especie_id` existente, sin entrada en `config/nombres.yaml`.
- Cualquier cambio a la fórmula de saciedad por captura
  (`eficiencia_biomasa_saciedad`) -- esta pieza da a lobo una presa con
  mejor ratio de masa, no cambia la fórmula en sí.

## Arquitectura

### `componentes/identidad.py`

```python
class Especie(Enum):
    GNOMO = "gnomo"
    LOBO = "lobo"
    CONEJO = "conejo"
    ARDILLA = "ardilla"
    CABALLO = "caballo"  # herbívoro grande, presa sostenible de lobo
                          # por ratio de masa -- ver CLAUDE.md, "Por qué
                          # lobo se muere de hambre pese a cazar más que
                          # nadie" (2026-09-04/05)
```

### `config/poblacion.yaml`

Nueva entrada `caballo` bajo `rangos_raciales`, siguiendo exactamente el
mismo molde que las 4 especies existentes (mismos campos, mismo
mecanismo de rango + sorteo individual). Todos los valores PROVISIONAL,
sin calibrar contra el harness completo:

```yaml
  caballo:
    medio_alimentacion: recolectar
    dieta: [hierba, raices]
    peso: [400, 500]
    altura: [1.4, 1.8]
    longevidad: [15, 25]
    duracion_gestacion_dias: [60, 90]  # deliberadamente corta frente a
                                         # los ~340 dias reales -- ver
                                         # decision de sostenibilidad
    camada: [1, 2]
    fraccion_madurez: 0.2
    factor_base_concepcion: 0.005
    puntos_agarre: 0  # un caballo no sujeta objetos
    fuerza: [0.6, 0.9]
    agilidad: [0.4, 0.7]
    velocidad: [0.4, 0.7]
    resistencia_enfermedad: [0.3, 0.6]
    agudeza_sensorial: [0.4, 0.7]
    vitalidad_maxima: [0.5, 0.8]
    resistencia_maxima: [0.5, 0.8]
    curacion: [0.01, 0.03]
    recuperacion: [0.08, 0.15]
    valentia: [0.1, 0.3]  # baja a proposito -- prefiere huir, ver
                            # decision de diseño
    sociabilidad: [0.7, 0.95]  # animal de manada
    agresividad: [0.05, 0.2]
    dominancia: [0.2, 0.5]
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

### `main.py:sembrar_poblacion_inicial`

```python
especies_spawn = [
    (Especie.GNOMO, poblacion_cfg.get("gnomos_iniciales", 18), candidatas_bosque),
    (Especie.LOBO, poblacion_cfg.get("lobos_iniciales", 6), candidatas_bosque),
    (Especie.ARDILLA, poblacion_cfg.get("ardillas_iniciales", 30), candidatas_bosque),
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

`config/poblacion.yaml` gana `caballos_iniciales: 9` (PROVISIONAL) junto
a los otros `*_iniciales` ya existentes.

### Por qué no hace falta tocar nada más

`medio_alimentacion: recolectar` ya cubre exactamente el mismo camino
de comportamiento que gnomo/conejo/ardilla (RECOLECTAR/COMER genérico
por catálogo, sin ninguna rama específica de especie en
`sistema_decision.py`/`sistema_recursos.py`). `nucleo/entidad.py:crear_criatura`/
`nacer_criatura` ya son genéricas por especie (leen `rangos_raciales[especie.value]`
sin ningún caso especial). `radio_individual`/percepción se derivan de
`agudeza_sensorial` (atributo genérico), no de una tabla por especie.
El narrador no necesita ningún cambio -- "caballo" es gramaticalmente
masculino en español, mismo criterio por defecto que gnomo/lobo/conejo
(solo ardilla necesitó entrar en `_ESPECIES_FEMENINAS`). La persistencia
guarda `especie.value` como texto libre, sin lista cerrada que
actualizar.

## Persistencia

Sin cambios de esquema -- `Especie` se persiste como texto
(`especie.value`), añadir un valor nuevo al enum no requiere ninguna
migración.

## Testing

Mismo criterio de "ley física" que el resto del proyecto:

- `Especie.CABALLO` existe y es distinto de las 4 especies anteriores.
- `crear_criatura`/`nacer_criatura` con `Especie.CABALLO` producen una
  entidad completa (todos los componentes esperados, valores dentro de
  los rangos configurados) -- mismo test que ya existe implícitamente
  para las otras 4 especies, extendido a caballo.
- La siembra inicial (`sembrar_poblacion_inicial`) coloca caballos
  reales en celdas de pradera sin agua, en la cantidad configurada.
- `magnitud_disposicion_por_peso`/`_resolver_ataque`: con los pesos
  reales de caballo (400-500kg) y lobo (60-90kg), un lobo solo tiene
  una probabilidad de éxito de captura baja frente a caballo -- test
  que confirma explícitamente que esto es el comportamiento ESPERADO
  (no un bug a corregir), documentado como tal en el propio test.
- Una captura exitosa de caballo por un lobo produce un aporte de
  saciedad sustancialmente mayor que una captura de conejo/gnomo,
  confirmando el ratio de masa favorable que motiva esta pieza.

**Verificación contra el motor real, OBLIGATORIA, no opcional**:
`BOSQUE_AUTO_TICKS` con población real, confirmando que caballo existe
y sobrevive un tramo razonable de la corrida sin excepciones. Dado que
esta pieza NO incluye caza en manada, es razonable (y debe reportarse
como hallazgo, no como fallo) si pocos o ningún caballo muere de
depredación en la corrida -- eso sería la limitación ya conocida y
aceptada de este círculo, no un defecto. Reportar también si caballo
sostiene su propia población (concepciones/nacimientos) de forma
razonable, dado que su reproducción se calibró para sostenibilidad.

## Pendiente real tras esta pieza

- Todos los valores del catálogo de caballo son PROVISIONALES, sin
  calibrar contra el harness completo.
- **Caza en manada** -- la pieza que completaría el propósito real de
  caballo (que lobo pueda derribarlo de forma viable coordinándose con
  otros lobos), círculo futuro aparte, sin diseñar todavía.
- Sin representación visual (`presentacion/vista_web.py`) -- motor
  primero, presentación después, mismo criterio de siempre.
- Las propuestas A'/B' de la investigación de fragilidad de hoy
  (revisar riesgo de fondo de inanición universal; investigar la
  relación depredador-presa de lobo más a fondo) siguen sin empezar --
  esta pieza (especie nueva) es una vía complementaria, no sustituye a
  esa investigación.
