# Convivencia familiar: bono de parentesco en la afinidad diaria

Fecha: 2026-09-17. Cuarto círculo de la sesión, continuación del arco
"vida familiar" tras "emancipación gateada por adultez + parto dirigido
a refugio" (mismo día, ya en master). Diseñado en conversación con
Diego: "los lazos de sangre inciten a los conscientes a hacer una vida
común más estrecha... es más probable que vayas a comer con tu hijo o
tu abuela que con un vecino del pueblo".

## Hallazgo que motiva este círculo

`_acrecion_amistad_convivencia` (`sistema_asentamiento.py:257-297`) daba
el MISMO delta diario de afinidad (`delta_amistad_convivencia_dia`,
0.05) a cualquier par de miembros conscientes del mismo asentamiento —
un hijo y un vecino cualquiera generaban exactamente el mismo vínculo
por "convivir". Sin ningún sesgo de parentesco.

## Nota sobre "abuela" (límite real, ya documentado, no resuelto aquí)

`nucleo/parentesco.py` deriva todo de `Identidad.id_madre/id_padre` EN
VIVO. "Abuela" es derivable hoy de forma transitoria -- mientras el
progenitor intermedio siga vivo, "mi madre → su madre" es una cadena de
dos saltos consultable -- pero `GestorEntidades.eliminar_entidad` purga
TODA la `Identidad` al morir, así que el vínculo con la abuela se pierde
para siempre en el instante en que el intermedio muere, aunque la abuela
siga viva. Limitación técnica real, ya documentada en el propio módulo y
en `CLAUDE.md` ("abuelos/tíos en parentesco, bloqueados por la purga de
Identidad al morir") -- fuera de alcance de este círculo.

## Alcance: dos círculos, trocear (decisión explícita de Diego)

- **Círculo A**: bono de afinidad -- la convivencia genera más vínculo
  entre familia directa que entre el resto.
- **Círculo B**: comportamiento real de agrupamiento -- los sesgos
  gregarios (deambular, fundar refugio, dormir, socializar) dejan de
  elegir "el más cercano" a secas y compiten afinidad ya acumulada
  contra distancia. Generaliza A: en vez de tratar "familia" como caso
  especial en el movimiento, se reutiliza la MISMA afinidad de
  `Relaciones` que A ya hace crecer más rápido entre familiares --
  familia, amistad y pareja quedan cubiertas gratis, sin volver a
  consultar parentesco en `sistema_movimiento.py`. Rencor entra con
  signo negativo (evasión, no exclusión dura).

Ambos círculos cerrados el mismo día.

## Diseño (Círculo A)

`_acrecion_amistad_convivencia` gana un multiplicador
`factor_amistad_convivencia_familia` (PROVISIONAL 2.0, hipótesis de
partida sin calibrar) aplicado al delta diario cuando el par es
`es_familia_directa()` (hermanos, o padre/madre-hijo -- reutiliza
`nucleo/parentesco.py` sin ningún componente nuevo). El resto del
mecanismo (gate de consciencia, escritura bidireccional, purga FIFO de
`Relaciones.vinculos`) no cambia.

### Config nueva (`config/relaciones.yaml`, PROVISIONAL)

- `factor_amistad_convivencia_familia: 2.0`

## Diseño (Círculo B)

### Qué se toca, y qué deliberadamente no

`_buscar_conspecifico_mas_cercano` (`sistema_movimiento.py`) es
consumida por tres sesgos gregarios -- `_calcular_deambular`,
`_calcular_construir` (buscar conspecífico antes de fundar refugio
propio) y `_calcular_dormir` (mismo sesgo al decidir dónde
establecerse) -- los tres comparten la misma función, así que un único
cambio los cubre a la vez. `_calcular_socializar` usaba una función
independiente (`_consciente_mas_cercano_con_id`, sobre
`_buscar_entidad_cercana`); se creó una variante nueva,
`_consciente_mas_cercano_por_afinidad`, en vez de tocar
`_buscar_entidad_cercana` directamente -- esa función también la
comparten `HUIDA_ERRATICA` y `CRISIS_VIOLENTA` (estados de crisis
mental), que NUNCA deben razonar sobre relaciones interpersonales.
`_consciente_mas_cercano_con_id` se deja intacta (tiene tests propios
que la validan como comportamiento base) aunque ya no tenga consumidor
en producción.

### Fórmula (`_elegir_candidato_social`, función compartida nueva)

Solo para individuos **conscientes** (fauna conserva el comportamiento
anterior sin cambios, gate por `CapacidadMental.consciencia`):

```
utilidad(candidato) = peso_afinidad_social * afinidad_hacia(candidato)
                     - peso_distancia_social * (dist / radio)
```

`afinidad_hacia`: la ya acumulada en `Relaciones.vinculos`, 0.0 sin
vínculo (ni preferido ni evitado -- así se conoce gente nueva). Gana el
candidato de mayor utilidad dentro del radio de percepción ya
existente (no se amplía). Si la afinidad del elegido cae por debajo de
`umbral_evasion_social` (rencor real, no solo neutral), se prefiere NO
acercarse a nadie (cae a paso aleatorio) en vez de acercarse igual --
evasión por umbral, no exclusión dura del candidato del cálculo.

`SOCIALIZAR` incluido deliberadamente pese a ser la vía primaria de
generar vínculos nuevos (afinidad al contacto) -- decisión de Diego
("si soy un ser con alta sociabilidad, busco estar con los míos
mientras como, paseo, hablo"): el riesgo de "círculo cerrado" (nunca
conocer gente nueva) se acepta como calibración pendiente de los
pesos, no como defecto estructural -- con afinidad neutra=0.0 para
desconocidos, un candidato desconocido pero mucho más cercano sigue
pudiendo ganar.

### Config nueva (`config/comportamiento.yaml`, sección `social`, PROVISIONAL)

- `peso_afinidad_social: 1.0`
- `peso_distancia_social: 1.0`
- `umbral_evasion_social: -0.3`
