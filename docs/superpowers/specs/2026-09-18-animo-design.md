# Ánimo: estado interno dinámico de cada individuo

Fecha: 2026-09-18. Origen: Diego señaló un hueco real -- "no tenemos en
el motor ningún mecanismo que nos permita saber cuál es el estado
anímico de las criaturas, eso es algo cambiante en lo que afecta el
temperamento y muchas otras cosas externas". Verificado contra el
código antes de diseñar nada: no existe. Lo más cercano son
`Temperamento` (rasgos raciales FIJOS de por vida, sin capa dinámica) y
`PoolMental.estabilidad` (dinámico, pero es un eje de riesgo de colapso
mental -- binario en la práctica, sin gradación conductual hasta que
toca fondo). Ninguno modela "cómo se siente este individuo en general
ahora mismo".

Alcance decidido explícitamente por Diego (tres preguntas cerradas,
2026-09-18): un único eje escalar (no varias dimensiones de afecto);
fuentes desde el primer círculo = fisiológico + clima + eventos
sociales (no solo fisiológico+clima, pese a que la opción más pequeña
se ofreció como recomendada); efecto de vuelta = AMBOS (modula
decisión de forma continua Y alimenta `PoolMental` como fuente
adicional). Advertencia dejada explícita a Diego antes de cerrar: esto
es más superficie de una vez de lo que el principio 2 ("círculos
pequeños") recomendaría por defecto -- se mitiga estructurando el
propio círculo en sub-fases internas verificables por separado (ver
"Orden de implementación" al final), no repartiendo el trabajo en
varios círculos con nombre propio.

## Componente nuevo: `componentes/animo.py`

```python
@dataclass
class Animo:
    estado: float = 0.5       # 0.0 decaido / 1.0 eufórico -- misma convención 0/1 que el resto del motor
    punto_base: float = 0.5   # ancla individual, capa racial + sorteo (ver mas abajo)
```

Universal: se añade a las 4 especies por igual (mismo criterio que
`Agarre`/`Semillas`/`Relaciones`/`Vocacion`/`Satisfaccion`) -- fauna
recibe fuentes fisiológica y térmica igual que consciente; la fuente
social (ver más abajo) solo se activa para individuos conscientes, ya
que fauna nunca escribe en su propio `Relaciones`.

### `punto_base`: capa racial + sorteo individual, CON herencia

Reutiliza el patrón "atributo con rango racial y sorteo individual" ya
documentado en `CLAUDE.md`, con el mismo tratamiento que `Temperamento`
(no como `Necesidades`/`PoolMental`, que resetean frescos en cada
nacimiento): `punto_base` SÍ se hereda (promedio de ambos progenitores
+ mutación, acotado al rango racial), porque es la capa análoga al
"carácter de fondo" del individuo, no un estado transitorio.

Rango racial nuevo `punto_base` bajo `rangos_raciales.<especie>` en
`config/poblacion.yaml`. **PROVISIONAL, decisión explícita no
completada por iniciativa propia**: sin ninguna base empírica de que
una especie deba nacer estructuralmente más optimista que otra, las 4
especies existentes parten del MISMO rango neutro `[0.4, 0.6]`
(centrado en 0.5) -- diferenciarlo por especie es una calibración
futura, no una suposición de partida.

**Decisión de diseño explícita, no derivarlo de `Temperamento`**: pese
a que Diego preguntó si debía atarse a algún rasgo existente, se opta
por un rango racial INDEPENDIENTE. Razón: `Temperamento` y `Animo` son
capas conceptualmente distintas (predisposición fija vs. estado que se
mueve) -- acoplar el ancla de una al valor de otra mezclaría dos
mecanismos que hoy están limpiamente separados, y el propio patrón de
`CapacidadMental` (distinta de `Temperamento` "aunque comparta plano")
ya establece precedente de mantenerlas separadas incluso compartiendo
mecanismo de sorteo/herencia.

`estado` NO se hereda -- empieza igual a `punto_base` en cada
nacimiento (mismo criterio que `PoolFisico`/`PoolMental`: el "techo"/
"ancla" hereditario existe, el valor dinámico del día a día siempre
arranca fresco).

## Deriva: fisiológico + térmico (sistema_necesidades.py)

Mismo patrón exacto que `confort_termico`/`comodidad` (deriva hacia un
objetivo cambiante, a una tasa configurable) -- nuevo bloque en el
mismo bucle de entidades que ya calcula ambos, sección "4c. Deriva de
Animo":

```
urgencia_fisiologica = max(1-saciedad, 1-hidratacion, 1-energia)
```
Reutiliza el criterio de "cuello de botella" que ya usa
`sistema_decision.py` para el Utility AI (Maslow: la necesidad peor
cubierta manda), no una suma nueva.

```
objetivo_animo = punto_base
                  - peso_fisiologico_animo * urgencia_fisiologica
                  - peso_termico_animo * (1.0 - confort_termico)
objetivo_animo = clamp(objetivo_animo, 0.0, 1.0)
```

`confort_termico` ya es la síntesis real de clima+estación+refugio+
fogata+pareja (`nucleo/clima.py::objetivo_confort_termico` +
sus consumidores en `sistema_necesidades.py`) -- Ánimo NO lee
`Clima`/`Estacion` directamente, evita duplicar una lectura que ya
tiene dueño.

`estado` deriva hacia `objetivo_animo` a `tasa_deriva_animo` (mismo
patrón `min`/`max` que el resto).

## Eventos puntuales (fuente social, mismo bloque de sistema_necesidades.py)

Catálogo DELIBERADAMENTE CORTO para este primer círculo -- no un
listado exhaustivo de eventos sociales, para no repetir el error de
"varias fuentes de complejidad a la vez sin poder aislar cuál causa
qué" en un catálogo además del propio circulo ya grande. Ampliable en
círculos futuros (rumor, reputación, robo quedan fuera).

Leídos de `bus_eventos.eventos_del_tick` (mismo patrón que
`sistema_capacidad_mental.py` con `"Muerte"`):

- **Duelo**: al procesar un evento `"Muerte"`, para cada individuo
  consciente vivo que tenga `Relaciones.vinculos[id_fallecido]` con
  `afinidad >= umbral_afinidad_duelo` (vínculo positivo fuerte, no
  cualquier conocido), impulso puntual NEGATIVO a `estado`
  proporcional a esa afinidad -- sin exigir cercanía espacial (a
  diferencia del trauma genérico de `PoolMental`, que sí exige
  percibir la muerte en el momento; el duelo por un vínculo fuerte no
  depende de haber estado presente).
- **Nacimiento propio**: al procesar un evento `"Nacimiento"`, impulso
  puntual POSITIVO a `estado` de la madre (`datos["id_madre"]`, ya
  presente en el evento).
- **Entrada/salida de CrisisMental**: reutiliza la misma detección por
  transición que ya usa `sistema_decision.py` para emitir el evento
  (accion_previa vs actual) -- impulso NEGATIVO al entrar en crisis,
  impulso POSITIVO menor al salir. Implementación: leer el evento
  `"CrisisMental"` ya emitido (entrada) para el impulso negativo;
  la salida se detecta en el propio bloque de Ánimo comparando
  `Intencion.accion` de este tick contra el tick anterior (no hay
  evento de "fin de crisis" hoy, no se inventa uno nuevo solo para
  esto -- se deriva de datos ya disponibles).

Todos los impulsos puntuales sesgan `estado` directamente (suma/resta
acotada a [0,1]), no el objetivo continuo -- se dejan absorber por la
propia deriva hacia `objetivo_animo` en los ticks siguientes, mismo
mecanismo que ya usa el shock puntual de `PoolMental` por presenciar
una muerte.

## Efectos de vuelta

### 1. Sobre decisión (`sistema_decision.py`), acotado a explícitamente NO tocar supervivencia dura

- `utilidad_socializar *= (0.5 + 0.5 * animo.estado)` -- en
  `estado=0.0` la motivación social efectiva se reduce a la mitad de
  lo que darían sociabilidad+curiosidad solas; en `estado=1.0` queda
  intacta (SIN bonus por encima del rasgo fijo -- un ánimo alto no
  hace a nadie más sociable de lo que su temperamento ya permite, solo
  uno bajo lo frena).
- `utilidad_deambular = base_deambular + peso_animo_deambular *
  (1.0 - animo.estado)` -- ánimo bajo empuja hacia deambular sin rumbo
  (inquietud/aislamiento), mismo rol que ya cumple `base_deambular`
  como "utilidad de fondo cuando nada más urge".

**Explícitamente NO tocado en este círculo**: huir, comer/cazar, beber,
dormir, aliviarse, buscar pareja, construir. La estabilidad de
población sigue bajo escrutinio activo (ver
`docs/historial_estabilidad_poblacion.md`, 2026-09-18) -- introducir un
canal más de varianza sobre esas utilidades sería sumar una fuente de
complejidad exactamente donde el proyecto menos puede permitírselo
ahora mismo.

### 2. Sobre `PoolMental` (`sistema_capacidad_mental.py`)

Nuevo término, sección "4 (nueva). Fuente adicional: ánimo sostenido":
```
if animo.estado < umbral_animo_bajo:
    drenaje_animo = (umbral_animo_bajo - animo.estado) * tasa_drenaje_animo_bajo / estabilidad_mental_maxima
    estabilidad -= drenaje_animo
elif animo.estado > umbral_animo_alto:
    alivio_animo = (animo.estado - umbral_animo_alto) * tasa_alivio_animo_alto
    estabilidad += alivio_animo  # NO dividido por estabilidad_mental_maxima, mismo criterio que curacion/recuperacion
```
Reutiliza el pool y el umbral de crisis ya existentes -- ningún segundo
mecanismo de colapso nuevo.

## Persistencia (`nucleo/persistencia.py`)

**Hallazgo colateral, señalado aparte, no arreglado en este círculo por
alcance**: `Satisfaccion` (introducido 2026-09-17) NO tiene columna en
`nucleo/persistencia.py` -- se pierde por completo al recargar una
partida guardada (resetea a 1.0). Mismo patrón exacto de gap que
`docs/superpowers/specs/...-nombre-propio-design.md` ya advirtió para
otros componentes nuevos en su momento. `Animo` SÍ se persiste
correctamente desde este círculo (columna nueva, guardar y cargar,
mismo patrón que `Relaciones`) -- no se repite el mismo error, pero el
hueco de `Satisfaccion` queda pendiente aparte en `CLAUDE.md`.

## Config nuevo: `config/animo.yaml`

Todas las constantes de este círculo, PROVISIONAL (hipótesis de
partida razonada, sin calibrar contra el motor en marcha):
```yaml
animo:
  tasa_deriva_animo: 0.02
  peso_fisiologico_animo: 0.4
  peso_termico_animo: 0.3
  umbral_afinidad_duelo: 0.5
  impulso_duelo: 0.3
  impulso_nacimiento: 0.15
  impulso_entrada_crisis: 0.25
  impulso_salida_crisis: 0.1
  peso_animo_deambular: 0.15
  umbral_animo_bajo: 0.3
  umbral_animo_alto: 0.8
  tasa_drenaje_animo_bajo: 0.01
  tasa_alivio_animo_alto: 0.005
```

## Qué NO se toca

- Ningún componente/sistema existente cambia de comportamiento salvo
  los puntos explícitos de arriba (`utilidad_socializar`,
  `utilidad_deambular`, `PoolMental.estabilidad`).
- El catálogo de eventos sociales que alimentan Ánimo es
  deliberadamente corto (3 fuentes) -- no se amplía en este círculo.
- No se toca ninguna utilidad de supervivencia física dura.

## Orden de implementación (mitigación de "círculos pequeños" dentro del alcance ya decidido)

1. Componente + config + sorteo/herencia + persistencia (sin ningún
   efecto todavía -- Ánimo existe y se guarda, nada lo lee ni lo
   mueve).
2. Deriva fisiológica+térmica (sin eventos sociales, sin efectos de
   vuelta) -- verificable de forma aislada (correr el motor, observar
   que `estado` responde a hambre/frío).
3. Eventos sociales puntuales -- verificable por separado con tests
   dirigidos (duelo, nacimiento, crisis).
4. Efectos de vuelta (decisión + PoolMental) -- último paso, el más
   sensible por tocar código de decisión ya delicado.

Cada paso se verifica (tests + smoke test corto) antes de sumar el
siguiente, aunque los cuatro se entreguen en el mismo círculo/commit
lógico.

## Verificación real (2026-09-18)

Implementado íntegramente en esta sesión (excepción del centinela
caído, ver `CLAUDE.md`). Diferencias reales entre este spec preliminar
y la implementación final, y hallazgos durante la verificación -- no
solo lectura de código:

- **Ubicación real de los impulsos puntuales, distinta del boceto
  inicial**: el nacimiento se aplica directamente en
  `sistema_reproduccion.py` (no leyendo el bus desde
  `sistema_necesidades.py`) -- `SistemaReproduccion` corre DESPUÉS de
  `SistemaNecesidades` en el orden de fases del tick (`main.py`), así
  que leerlo desde el bus habría llegado con un tick de retraso. Mismo
  motivo para crisis mental: entrada y salida se aplican directamente
  en `sistema_decision.py` (que ya calcula la transición para el propio
  evento `CrisisMental`), no vía bus. Solo el DUELO se centraliza en
  `sistema_necesidades.py` leyendo el bus -- es el único caso que
  necesita recorrer TODA la población (cualquiera pudo tener un vínculo
  con el fallecido), no solo la entidad que originó el evento.
- **Bug real encontrado al verificar, no al leer código**: la primera
  pasada solo sorteaba/instanciaba `Animo` en `crear_criatura()`
  (siembra fundadora) y se me olvidó el paso simétrico en
  `nacer_criatura()` (nacimientos reales durante la partida) -- un test
  de herencia (`test_nacer_criatura_hereda_punto_base_acotado_al_rango_racial`)
  falló con `AttributeError: 'NoneType' object has no attribute
  'estado'` antes de corregirlo. Confirma por qué el proyecto insiste
  en verificar con tests reales, no dar una implementación por completa
  tras escribirla.
- **Tres tests preexistentes rotos por el nuevo efecto sobre
  `utilidad_socializar`** (`test_ocio_consciente_socializar.py` x2,
  `test_vocacion.py` x1): estaban calibrados exactamente al punto de
  empate esperando el valor SIN el factor de ánimo -- el `punto_base`
  sorteado (0.4-0.6) de un gnomo recién creado introducía un factor no
  controlado. Corregido añadiendo `Animo.estado = 1.0` a los helpers de
  "neutralización" ya existentes en esos ficheros (mismo criterio que
  ya usan para saciedad/energía/confort_termico/comodidad).
- **Hallazgo colateral real, ajeno a Animo pero descubierto verificando
  su persistencia end-to-end**: `sistema_colonizacion.py` (círculo del
  2026-09-17) creaba la pareja colonizadora sin registrarla en la tabla
  histórica `entidades` de `nucleo/persistencia.py` -- el INNER JOIN de
  `Persistencia.cargar_snapshot()` las descartaba en silencio en
  cualquier partida guardada tras dispararse ese sistema, desde el
  mismo día en que se introdujo. Corregido en el mismo círculo (una
  línea en `sistema_colonizacion.py` para incluir `entidades_id` en el
  evento, y el manejo simétrico en `main.py`) por ser una corrección
  pequeña y directamente en el dominio de persistencia que este círculo
  ya estaba tocando -- no se dejó como pendiente sin arreglar.
- **Persistencia verificada end-to-end con un smoke test real** (no
  solo tests unitarios de guardar/cargar aislados): 600 ticks con
  gnomo/lobo/conejo/colonización espontánea activa, guardado y
  recargado -- todas las entidades vivas conservan `Animo.estado`/
  `punto_base` exactos tras el roundtrip.
- **Observación honesta sobre la calibración, PROVISIONAL, no
  ajustada por iniciativa propia**: en el mismo smoke test de 600
  ticks, `Animo.estado` cae con fuerza real -- media 0.10, la mayoría
  de individuos en 0.0 -- correlacionado con `Necesidades.energia`
  llegando a 0.0 en varias criaturas (sin tiempo/oportunidad de dormir
  lo suficiente en un mapa recién generado con poca población). Esto es
  coherente con el diseño (`urgencia_fisiologica` como cuello de
  botella, `peso_fisiologico_animo=0.4` ya basta para arrastrar el
  objetivo a 0 con una sola necesidad en crisis), pero **no se sabe
  todavía si es el comportamiento deseado o una calibración demasiado
  agresiva** -- ninguna de las constantes de `config/animo.yaml` se
  tocó a partir de esta única observación de 600 ticks con 12 individuos,
  seed única. Igual que el resto de constantes PROVISIONAL del
  proyecto, necesita observarse contra el harness completo antes de
  recalibrar con criterio.
- Suite completa tras el círculo: 772 passed (759 antes de esta sesión
  + 12 tests nuevos de `test_animo.py` + 1 test nuevo del fix de
  colonización).
