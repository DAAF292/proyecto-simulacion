# Radio de percepción ampliado para búsqueda activa de pareja

Fecha: 2026-09-06
Estado: aprobado por Diego en brainstorming, pendiente de encargo al pipeline.

## Contexto y motivación

Segundo círculo del arco de estabilidad de población, tras "parejas
fundadoras" (`docs/superpowers/specs/2026-09-06-parejas-fundadoras-design.md`,
ya mergeado). Ver `CLAUDE.md`, secciones "Reestructuración de la siembra
fundadora" y su corrección, y la "Síntesis" al final del documento, para
el diagnóstico completo -- resumen aquí:

"Parejas fundadoras" resolvía que la GENERACIÓN FUNDADORA no tenía
ninguna ventaja estructural para encontrar pareja a tiempo. Confirmado
con datos reales (5 semillas nuevas × 6000 ticks, el doble de lo
verificado antes de fusionar aquel PR): la mejora es real y DURADERA
para lobo y caballo (0/5 extinción), pero PARCIAL Y TEMPORAL para gnomo
y ardilla -- ambas vuelven al 100% de extinción exactamente igual que
antes del fix, una vez pasada la ventana inicial. Hipótesis causal:
lobo/caballo tienen reproducción suficientemente rápida para construir
densidad de población real antes de que la generación fundadora muera
de vieja; gnomo/ardilla no llegan a tiempo -- cuando el impulso fundador
se apaga, las crías (dispersas por el mapa igual que siempre) vuelven al
mismo problema de partida disperso, sin el colchón de una generación
fundadora completa.

**Investigación de código que identificó la causa real de este círculo**:
`sistemas/sistema_movimiento.py:_calcular_pareja` YA hace búsqueda
activa de pareja -- barre todos los individuos con
`Reproduccion`+`Posicion`+`Identidad`, filtra por especie/sexo
opuesto/no gestando, se acerca al candidato válido más cercano DENTRO
del radio de percepción. La lógica de aproximación funciona bien. El
cuello de botella real es el RADIO: `radio_individual` (escalado por
`agudeza_sensorial`, tope hoy 0-4 celdas vía
`percepcion.radio_minimo_celdas`/`radio_maximo_celdas`) es mucho más
pequeño que la distancia media medida al conespecífico de sexo opuesto
más cercano (5.4-19 celdas, medido en la siembra fundadora -- mismo
orden de magnitud esperado para nacimientos posteriores).
`_calcular_pareja` nunca llega a intentar acercarse si el candidato está
más lejos que ese radio pequeño.

## Objetivo de este círculo

Dar a `BUSCAR_PAREJA` un radio de percepción propio, mayor que el
genérico usado por comida/agua/amenaza, para que las generaciones
POSTERIORES a la fundadora (no solo la primera) puedan detectar y
alcanzar una pareja a tiempo. Ley general aplicada por igual a las 5
especies -- ninguna excepción de código por especie, aunque el radio
resultante tras escalar por `agudeza_sensorial` varíe naturalmente entre
ellas, como ya pasa con la percepción normal.

Deliberadamente el segundo círculo pequeño de este arco, no el
definitivo: la fragilidad estructural específica de ardilla (comparte
bioma con dos competidores/depredadores, dieta subconjunto de la de
gnomo) queda aparcada para después si hace falta, no se aborda aquí.

## Diseño

### Por qué esto evita el problema del "objetivo móvil"

`_calcular_pareja` recalcula la lista de candidatos desde cero, con las
posiciones ACTUALES, en cada tick -- no memoriza ninguna posición. Si el
candidato se mueve, el siguiente tick simplemente actualiza el rumbo
hacia su nueva posición. Ampliar el radio de percepción no reintroduce
ningún problema de objetivo desactualizado (a diferencia de una vía de
memoria, que si se hubiera elegido habría heredado exactamente ese
problema -- descartada en brainstorming por este motivo, ver el propio
histórico de la conversación).

### Coste computacional

El barrido de candidatos en `_calcular_pareja` ya es O(N) sobre TODOS
los individuos con `Reproduccion` en el mapa, con independencia del
radio -- el radio solo filtra al final (`if dist > radio: continue`).
Ampliar el radio no añade ningún coste computacional real, solo cambia
cuántos candidatos ya barridos pasan el filtro.

### `config/comportamiento.yaml`, sección `percepcion`

Dos claves nuevas, mismo patrón que las ya existentes:

```yaml
percepcion:
  radio_minimo_celdas: 0        # ya existente, sin cambios
  radio_maximo_celdas: 4        # ya existente, sin cambios
  radio_minimo_pareja_celdas: 3   # NUEVO, PROVISIONAL
  radio_maximo_pareja_celdas: 12  # NUEVO, PROVISIONAL
```

### `sistemas/sistema_movimiento.py`

En `__init__`/`_cachear_configuracion` (el punto donde ya se cachean
`self.radio_min`/`self.radio_max`), añadir:

```python
cfg_per = self.config.get("percepcion", {})
self.radio_min_pareja: int = int(cfg_per.get("radio_minimo_pareja_celdas", 3))
self.radio_max_pareja: int = int(cfg_per.get("radio_maximo_pareja_celdas", 12))
```

En el método `ejecutar`, en la rama `elif accion == Accion.BUSCAR_PAREJA:`
(hoy reutiliza la variable `radio` genérica, ya calculada una vez por
entidad y tick con `radio_individual(dims.agudeza_sensorial,
self.radio_min, self.radio_max)` para todas las acciones), calcular un
radio propio SOLO en esa rama:

```python
elif accion == Accion.BUSCAR_PAREJA:
    radio_pareja = radio_individual(
        dims.agudeza_sensorial, self.radio_min_pareja, self.radio_max_pareja
    )
    dx, dy = self._calcular_pareja(
        gestor, eid, ident.especie, pos.x, pos.y, radio_pareja, pos.zona_idx
    )
```

Ningún otro cambio en `_calcular_pareja` en sí (su firma ya acepta
`radio` como parámetro) ni en ninguna otra rama de acción -- el radio
genérico `radio` sigue calculándose y usándose exactamente igual para
COMER, BEBER, CAZAR, HUIR, DEAMBULAR, etc.

### Alcance

Dos ficheros tocados (`config/comportamiento.yaml`, sección
`percepcion`, y `sistemas/sistema_movimiento.py`). No se toca
`nucleo/memoria.py`,
`sistema_reproduccion.py`, ni `_buscar_conspecifico_mas_cercano`
(agrupamiento social genérico, no búsqueda de pareja reproductiva --
fuera de alcance a propósito).

## Qué NO cubre este círculo (aparcado, no descartado)

- Fragilidad estructural específica de ardilla (bioma compartido con
  gnomo y lobo, dieta subconjunto).
- Enfoque B original (ventana de resiliencia temprana en el modelo de
  mortalidad) -- sigue aparcado como complemento de menor prioridad.
- Cualquier ajuste de `techo_fraccion_edad_inicial_longevidad`,
  `factor_base_concepcion`, o de la propia mecánica de "parejas
  fundadoras" -- todos investigados por separado, sin relación con este
  cambio.

## Verificación

**Obligatoria, en dos horizontes de tiempo** (Diego señaló
explícitamente que el efecto de "parejas fundadoras" solo se reveló al
comparar 4000 contra 6000 ticks -- verificar aquí ambos desde el
principio, no solo el más corto):

1. `pytest` -- suite completa en verde (216/216 esperados, o la cifra
   vigente).
2. `BOSQUE_AUTO_TICKS=3000` sin intervención, sin ninguna excepción.
3. Lote pequeño (Diego pidió explícitamente no lanzar baterías largas):
   5 semillas NUEVAS × 4000 ticks, midiendo población final y extinción
   por especie (gnomo, lobo, conejo, ardilla, caballo).
4. El MISMO lote de 5 semillas × 6000 ticks -- comparar explícitamente
   gnomo y ardilla contra las cifras ya conocidas SIN este cambio (100%
   de extinción en ambas a 6000 ticks, medido en la investigación
   previa) para confirmar si el radio ampliado realmente cierra esa
   brecha, no solo si "algo mejora".
5. Sin persistencia SQLite (arnés directo con
   `cargar_configuracion`/`instanciar_sistemas`/
   `sembrar_poblacion_inicial`/`sembrar_flora_inicial`/`ejecutar_tick`,
   `bus.limpiar()` cada tick, con tope de seguridad de población tipo
   800-1000 individuos para evitar corridas descontroladamente lentas si
   la población crece mucho -- lección real de esta misma investigación,
   ver nota en `feedback_diagnosticos_rapidos` en memoria persistente).

Reportar los números tal cual salgan en ambos horizontes como parte del
resumen final -- si el resultado es ambiguo o solo mejora parcialmente
(p.ej. ayuda a uno de los dos, gnomo o ardilla, pero no al otro),
decirlo explícitamente en vez de forzar una conclusión de éxito.

## Pendiente real, explícito

`radio_minimo_pareja_celdas`/`radio_maximo_pareja_celdas` son
PROVISIONALES, sin calibrar contra el harness completo (15 semillas ×
12000 ticks) que el proyecto tiene pendiente desde "Sobrepoblación..."
(2026-08-31). Si este círculo no basta para estabilizar gnomo/ardilla a
6000+ ticks, la fragilidad estructural específica de ardilla (bioma
compartido, dieta) y el Enfoque B (ventana de resiliencia) quedan como
candidatos directos de un tercer círculo.
