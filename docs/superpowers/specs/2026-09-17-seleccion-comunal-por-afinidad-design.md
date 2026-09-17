# Selección de tipo comunal por afinidad de carácter, no por progreso ya invertido

Fecha: 2026-09-17. Origen: diagnóstico solicitado por Diego sobre por qué
"taller" (mobiliario) lleva cerrado desde el 2026-09-16 con 0 muebles
fabricados en todas las semillas probadas, pese a que el resto de la
cadena comunal (almacén, salón común, cocina) sí se ejerce con fuerza
(ver `CLAUDE.md`, sección de pendientes).

## Diagnóstico que motiva este círculo (verificado contra el motor real)

La selección de `tipo_objetivo` entre los cuatro tipos comunales
(`sistema_decision.py:833-862`, dentro de `actualizar()`) no compara
"cuánto le interesa este tipo a este individuo" -- compara **cuánto
progreso ya tiene invertido cada tipo**, una propiedad del EDIFICIO
compartida por todo el asentamiento, no del carácter de quien decide.
En empate (típicamente 0.0 de progreso para cualquier tipo que nadie ha
empezado aún), gana el primero en aparecer en
`TIPOS_COMUNALES = ("almacen", "salon_comun", "cocina", "taller")`
(`nucleo/construccion.py:332`) -- `taller` está en último lugar.

Confirmado con dos escenarios controlados contra `sistema_decision.py:actualizar()`
real (no solo lectura de código):

1. Un individuo cuyo carácter califica IGUAL DE BIEN para `salon_comun`
   Y para `taller` (ambos gates propios pasan, ningún comunal empezado
   todavía) elige `salon_comun` -- por orden de tupla, no por carácter.
2. El mismo individuo, con carácter que SOLO califica para `taller`
   (falla los otros tres gates), sí elige `taller` -- confirma que
   `taller` no está roto, solo pierde sistemáticamente cualquier empate
   contra los otros tres.

Consecuencia estructural: en cuanto CUALQUIER individuo empieza
`almacen`/`salon_comun`/`cocina` (progreso pasa de 0.0 a >0.0), todo
individuo futuro que califique para ESE tipo Y para `taller` a la vez
elegirá el que ya tiene progreso, indefinidamente -- una dinámica "el
que arranca antes acapara" que no depende de qué tan bien calce el
carácter del individuo con cada tipo. `taller` solo recibe contribución
de la población "sobrante" que no calificó para nada más, lo que basta
para explicar por qué nunca completa en la práctica (nunca llega a
tiempo a que exista un taller terminado, así que `Accion.FABRICAR`
categoría "mobiliario" -- que exige un taller completado -- nunca se
desbloquea).

## Qué NO es el problema (confirmado, para no repetir el diagnóstico)

- El gate propio de `taller` (`necesidades.comodidad < 1.0`) es, de los
  cuatro, el MÁS FÁCIL de pasar -- casi universal. El cuello de botella
  no es que nadie lo quiera.
- El gate de FABRICAR-mobiliario en sí (`sistema_decision.py:1207-1239`,
  taller completado + conocimiento "artesano" ≥ umbral) funciona
  exactamente como se diseñó -- confirmado por
  `tests/test_taller_mobiliario_almacen.py`. El problema es anterior:
  nunca se llega a tener un taller completado.

## Diseño

### Principio: afinidad de carácter como criterio PRIMARIO, progreso como desempate SECUNDARIO

No se elimina el criterio de progreso -- sigue existiendo una razón
real para preferirlo en caso de empate genuino (evitar dispersar el
esfuerzo entre varias obras a medio empezar en vez de rematar una, el
mismo criterio de convergencia que el código ya cita como validado en
otro sitio del motor). Lo que cambia es CUÁNDO se usa: solo para
desempatar entre tipos con afinidad de carácter similar, nunca como
criterio principal.

### Magnitud de afinidad por tipo -- reutiliza los valores que YA calcula cada gate, sin dato nuevo

Cada gate actual es una comparación booleana (`valor >= umbral`). La
afinidad es la MISMA resta, sin booleanizar -- cuánto sobra o falta
respecto al umbral, en la misma escala [0,1] normalizada que ya usa
todo el motor (sin necesidad de reescalar nada):

| Tipo | Gate (sin cambios) | Afinidad (nueva, para desempate) |
|---|---|---|
| `almacen` | `min(saciedad, hidratacion) >= disposicion_a_aportar(...)` | `min(saciedad, hidratacion) - disposicion_a_aportar(...)` |
| `cocina` | `saciedad >= disposicion_a_aportar(...)` | `saciedad - disposicion_a_aportar(...)` |
| `salon_comun` | `(sociabilidad+curiosidad)/2 >= umbral_prosocial_comunal` | `(sociabilidad+curiosidad)/2 - umbral_prosocial_comunal` |
| `taller` | `comodidad < 1.0` (sin cambios) | `(1.0 - comodidad) - umbral_prosocial_comunal` |

**Corrección aplicada durante la implementación (no en el diseño
original de este documento)**: la primera versión de la afinidad de
`taller` era `1.0 - comodidad` sin restar ningún umbral -- a diferencia
de las otras tres, que sí restan uno. Verificado contra la suite real
(3 tests rotos): esto hacía que `taller` ganase casi siempre por
ventaja de escala de la fórmula (su techo real era 1.0, el de las
demás 0.5-0.85), el mismo tipo de sesgo estructural que este círculo
vino a corregir, solo que invertido. Corregido reutilizando
`umbral_prosocial_comunal` (ya existente) también como umbral de
`taller` -- mismo "esto me importa lo suficiente para actuar" que ya
usa `salon_comun`, sin inventar una constante nueva. El gate de
`taller` en sí NO cambió (sigue siendo `comodidad < 1.0`), solo la
magnitud de afinidad usada para desempatar.

Los GATES no cambian -- quién califica para cada tipo sigue siendo
exactamente lo mismo que hoy. Lo único nuevo es que, entre los que
califican, ya no gana el de más progreso a secas.

Nueva función auxiliar en `sistemas/sistema_decision.py` (local al
módulo, no exportada -- mismo criterio que el resto de helpers internos
de este fichero):

```python
def _gate_y_afinidad_comunal(
    tipo: str,
    temperamento: Temperamento,
    temperamento_prosocial: Temperamento,
    necesidades: Necesidades,
    config_asentamiento: dict,
    umbral_prosocial_comunal: float,
) -> tuple[bool, float]:
    """Gate (idéntico al actual, sin cambios de comportamiento) +
    magnitud de afinidad de carácter hacia `tipo` (2026-09-17, ver
    docs/superpowers/specs/2026-09-17-seleccion-comunal-por-afinidad-
    design.md) -- cuánto sobra o falta respecto al umbral del propio
    gate, para desempatar por carácter en vez de por progreso ya
    invertido en el edificio."""
    if tipo == "almacen":
        umbral = disposicion_a_aportar(temperamento_prosocial, config_asentamiento)
        valor = min(necesidades.saciedad, necesidades.hidratacion)
        return valor >= umbral, valor - umbral
    if tipo == "cocina":
        umbral = disposicion_a_aportar(temperamento_prosocial, config_asentamiento)
        valor = necesidades.saciedad
        return valor >= umbral, valor - umbral
    if tipo == "salon_comun":
        valor = (temperamento.sociabilidad + temperamento.curiosidad) / 2.0
        return valor >= umbral_prosocial_comunal, valor - umbral_prosocial_comunal
    # taller: el gate no cambia, pero la magnitud SI resta
    # umbral_prosocial_comunal -- ver "Corrección aplicada durante la
    # implementación" mas arriba.
    return (
        necesidades.comodidad < 1.0,
        (1.0 - necesidades.comodidad) - umbral_prosocial_comunal,
    )
```

### Selección (reemplaza el bucle de `sistema_decision.py:833-862`)

En vez de una variable `mejor_progreso` actualizada en una sola pasada
(orden-dependiente, causa raíz del sesgo por tupla), dos pasadas
explícitas sin dependencia de orden:

```python
candidatos_validos = []
for tipo_c, cid_c, _pos_c in candidatos_comunales_pendientes(
    gestor, mundo, id_entidad, config, radio_cluster_asentamiento
):
    gate, afinidad_c = _gate_y_afinidad_comunal(
        tipo_c, temperamento, temperamento_prosocial, necesidades,
        config_asentamiento, umbral_prosocial_comunal,
    )
    if not gate:
        continue
    progreso_c = 0.0
    if cid_c is not None:
        construccion_c = gestor.obtener_componente(cid_c, Construccion)
        progreso_c = construccion_c.progreso if construccion_c is not None else 0.0
    candidatos_validos.append((tipo_c, cid_c, afinidad_c, progreso_c))

if candidatos_validos:
    mejor_afinidad = max(c[2] for c in candidatos_validos)
    finalistas = [
        c for c in candidatos_validos
        if c[2] >= mejor_afinidad - tolerancia_empate_afinidad_comunal
    ]
    tipo_objetivo, cid_objetivo, _, _ = max(finalistas, key=lambda c: c[3])
```

Primero se calcula la afinidad máxima real entre quienes pasan su gate
(sin importar orden de iteración); después se toman como "finalistas"
todos los que queden dentro de `tolerancia_empate_afinidad_comunal` de
ese máximo (empate real de carácter, no solo dos floats
casualmente distintos); y solo entre esos finalistas gana quien más
progreso ya lleve -- el criterio de convergencia se conserva intacto,
pero acotado a cuando de verdad hay empate de carácter.

Con `tolerancia_empate_afinidad_comunal = 0.0` (no es el valor
propuesto, solo ilustra el límite): se reduce a "solo empates exactos
de afinidad usan progreso", el caso más estricto. Con un valor muy alto
se reduce al comportamiento ACTUAL (progreso decide casi siempre). El
valor propuesto (ver config abajo) busca un punto intermedio.

### Config nueva (`config/comportamiento.yaml`, sección `asentamiento`, PROVISIONAL)

- `tolerancia_empate_afinidad_comunal: 0.05` -- PROVISIONAL, sin
  calibrar contra el harness completo. Un valor demasiado alto
  reproduce el sesgo actual (progreso manda casi siempre); uno
  demasiado bajo (o 0.0) podría dispersar el esfuerzo entre los cuatro
  tipos con más frecuencia de la deseable, retrasando la finalización
  de cualquiera de ellos.

## Qué NO se toca

- Los cuatro gates individuales -- quién califica para cada tipo no
  cambia en absoluto, solo cómo se desempata entre los que califican.
- `candidatos_comunales_pendientes` (`nucleo/construccion.py`) -- sigue
  devolviendo exactamente los mismos candidatos y dejando de listar un
  tipo en cuanto se completa (progreso >= 1.0), sin cambios.
- El gate de FABRICAR-mobiliario (taller completado + conocimiento
  artesano ≥ umbral) -- circuito totalmente separado, corriente abajo
  de este círculo.
- `sesgo_prosocial` / `prioriza_comunal` (decide "comunal en general
  vs. mejora de mi propio refugio") -- lee `tipo_objetivo != ""`, no le
  importa CUÁL tipo concreto ganó, así que no se ve afectado.

## Riesgo real, comunicado sin maquillar (no verificado, solo razonado)

Hoy, todo individuo que califica para más de un tipo converge en el que
ya tiene progreso -- eso es precisamente lo que hace que
`almacen`/`cocina`/`salon_comun` se completen con fuerza. Al repartir
por afinidad de carácter, es esperable que la población se reparta más
entre los cuatro tipos en vez de amontonarse en uno -- podríamos estar
cambiando "taller nunca se construye" por "los cuatro tardan más en
completarse, mejor repartido". Es una hipótesis razonada a partir del
mecanismo, no una medición: exige confirmarse con un run real más largo
que el smoke test de humo, idealmente el harness completo (pendiente
desde antes de este círculo).

## Verificación planeada

- Tests nuevos (`tests/test_seleccion_comunal_por_afinidad.py`):
  reproducen los dos escenarios ya confirmados en este diagnóstico
  (afinidad empatada pierde por tupla hoy / afinidad exclusiva gana)
  como regresión permanente, más un caso de desempate real por
  `tolerancia_empate_afinidad_comunal` (dos tipos con afinidad MUY
  cercana, gana el de más progreso) y un caso de afinidad claramente
  distinta (gana la afinidad, con independencia de qué tipo tenga más
  progreso).
- Re-correr la suite completa -- `test_salon_comun.py`,
  `test_cocinas_comunes.py`, `test_taller_mobiliario_almacen.py` y
  `test_pertenencia_colocacion_necesidad_comunal.py` construyen
  escenarios con un único tipo calificando a la vez en su mayoría, así
  que no deberían verse afectados -- se confirma corriendo la suite,
  no se asume.
- Smoke test headless (2000+ ticks) -- confirmar que `taller` empieza a
  acumular progreso >0.0 en juego libre, algo que nunca se ha observado
  hasta ahora.
