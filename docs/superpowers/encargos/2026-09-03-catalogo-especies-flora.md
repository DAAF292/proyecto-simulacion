# Catálogo ampliado de especies de flora (pieza 4, "poblar más el mundo")

Añade 10 especies nuevas a `config/flora.yaml`, reutilizando EXACTAMENTE
el mismo patrón que ya usan las 5 especies existentes (`hierba_silvestre`,
`manzano`, `cactus`, `liquen`, `musgo`) -- ningún mecanismo nuevo, solo
entradas de catálogo. Lee primero las 5 especies existentes en
`config/flora.yaml` para copiar su forma exacta (campos, estructura de
`recursos`, comentarios PROVISIONAL).

## Especies a añadir

Para cada una: `biomas`, `tasa_crecimiento_por_dia`, `prob_propagacion_por_dia`,
`preferencia_lluvia`/`preferencia_temperatura`/`preferencia_fertilidad`
(rangos ecológicamente razonables para el nombre y bioma de la especie,
PROVISIONAL, sin calibrar -- usa buen juicio, no hace falta precisión),
`tipo_propagacion`, `compite_espacio_fisico` (y si es `true`, `huella_m2`
razonado frente a `manzano`=4.0/`cactus`=1.5 ya existentes -- un árbol
grande como pino/roble puede tener huella mayor que manzano; un arbusto,
menor), y `recursos` (con `categoria: alimento` y/o `categoria: material`
según corresponda, siguiendo el patrón de nombre+capacidad_maxima+
tasa_regeneracion(+valor_nutricional/valor_hidratacion si es alimento)
ya usado).

| Especie | Bioma | Compite espacio | Propagación | Recursos |
|---|---|---|---|---|
| `flor_silvestre` | pradera | No | viento | alimento (néctar/semillas, bajo valor) |
| `arbusto_espinoso` | pradera | Sí | caida | alimento (bayas) + material |
| `roble` | bosque | Sí | zoocoria | material (madera) -- sin recurso de alimento directo |
| `helecho` | bosque | No | viento (esporas) | alimento (bajo valor) |
| `arbusto_desertico` | desierto | Sí | caida | material |
| `hierba_desertica` | desierto | No | viento | alimento (escaso, baja hidratación) |
| `pino` | montana | Sí | viento | material (madera) -- sin recurso de alimento directo |
| `arbusto_montano` | montana | Sí | caida | alimento + material |
| `arbusto_artico` | tundra | Sí | caida | material |
| `hierba_artica` | tundra | No | viento | alimento (escaso) |

## Decisiones de diseño ya cerradas -- no las reabras

- `tipo_propagacion` sigue siendo UN valor por especie (dispatch
  exclusivo en `sistema_flora.py:_propagar_planta`, sin cambios) -- NO
  implementes propagación multi-vector simultánea. Si una especie
  "lógicamente" podría dispersarse de dos formas (p.ej. el roble por
  caída Y por ardillas), elige solo la más representativa de la lista
  de arriba -- ya está decidido cuál para cada una.
- Zoocoria ya es genérica (cualquier criatura que coma el recurso puede
  dispersar la semilla al aliviarse) -- no hace falta ligarla a una
  especie de fauna en concreto, ni tocar `_resolver_comer`/
  `_resolver_aliviarse`.
- Producción (lluvia/temperatura/estación/clima/humedad de subsuelo/
  fertilidad) ya es genérica vía `factor_produccion`/
  `factor_humedad_subsuelo` -- se aplica sola a toda `Planta` nueva sin
  tocar `sistema_flora.py`.

## Qué NO tocar

- No modifiques `CLAUDE.md`, nada bajo `informes/`, ni ningún
  `docs/historial_*.md`.
- No toques `sistema_flora.py`, `nucleo/flora.py`, `nucleo/espacio.py`
  ni ningún mecanismo -- solo `config/flora.yaml` y el test nuevo.
- No cambies nada de las 5 especies existentes.
- No añadas ningún campo nuevo al esquema de especie que las 5
  existentes no tengan ya -- reutiliza el patrón tal cual.

## Test a añadir

Un fichero de test nuevo (mismo criterio "ley física" del resto del
proyecto -- docstring explicando el comportamiento real validado) que
confirme, para las 10 especies nuevas:

- Cada una carga correctamente desde `config/flora.yaml` con todos los
  campos requeridos presentes.
- Cada una participa en `idoneidad_colonizacion`/`colonizar_por_idoneidad`
  sin lanzar excepción (usando datos de celda de ejemplo razonables
  para su bioma).
- Las especies con `compite_espacio_fisico: true` tienen `huella_m2 > 0`;
  las que son `false` no dependen de ese campo.
