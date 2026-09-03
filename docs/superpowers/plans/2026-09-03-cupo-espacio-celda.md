# Cupo de espacio compartido por celda -- flora vs. construcción

Implementa la spec completa que está en
`docs/superpowers/specs/2026-09-03-cupo-espacio-celda-design.md` -- léela
por completo primero (`cat` o equivalente); es la única fuente de verdad
de lo que hay que construir, no hay ningún código pre-escrito en este
mensaje.

Esta NO es una tarea pequeña: cambia cómo se representa la ocupación de
flora en `Celda` (dos pistas independientes -- una competidora, otra no),
generaliza el cálculo de espacio disponible que hoy solo usa construcción
(`nucleo/construccion.py:espacio_disponible_para_construir`) para que
también cuente flora competidora, cambia el gate de colonización de flora
(`nucleo/flora.py:intentar_colonizar_celda` y `colonizar_por_idoneidad`),
y migra parte de `sistemas/sistema_recursos.py` (COMER y RECOLECTAR) para
consultar entidades `Planta` reales en vez de un campo escalar de `Celda`,
solo para el caso de especies que compiten por espacio.

Tienes libertad total para decidir la forma exacta de la implementación
(nombres de funciones/parámetros, si el nuevo módulo de espacio va en un
fichero nuevo `nucleo/espacio.py` o generalizado dentro de
`nucleo/construccion.py`, cómo estructurar la consulta de `Planta` por
posición) siempre que el comportamiento final cumpla lo que la spec
describe. Si algo en la spec te parece ambiguo, toma la decisión más
coherente con el resto del diseño y documenta por qué en el mensaje de
commit -- no hace falta preguntar, esto se revisará después.

## Qué NO tocar

- No modifiques `CLAUDE.md`, nada bajo `informes/`, ni ningún
  `docs/historial_*.md` -- sin relación con esta tarea.
- No implementes ninguna acción de "tala" ni ningún mecanismo para que
  una criatura destruya una `Planta` -- la spec lo señala explícitamente
  como fuera de alcance, para un círculo futuro.
- No toques ningún límite de densidad de criaturas/fauna -- fuera de
  alcance, ver la spec.
- No añadas especies nuevas al catálogo de flora ni toques biomas -- eso
  es la pieza 4 ("catálogo ampliado de especies"), un círculo aparte, NO
  esta tarea.
- No escales la huella de una `Planta` por su `etapa` de crecimiento --
  huella fija por especie, decisión explícita de la spec.
- No toques nada de `nucleo/armas.py`, `componentes/agarre.py`,
  `componentes/inventario.py`, `nucleo/conflicto.py` -- sin relación con
  esta tarea.
- No toques nada de `nucleo/cueva.py` ni la generación de geometría de
  cuevas -- solo asegúrate de que el filtrado por `zona_idx` ya existente
  (mismo patrón que usa `espacio_disponible_para_construir` hoy) se
  respeta en el código nuevo.
- No cambies ningún esquema de persistencia SQLite -- la spec confirma
  explícitamente que no hace falta ningún cambio de esquema.

## Convenciones del proyecto a seguir

- Los tests se escriben como "ley física": un docstring que explica el
  comportamiento real que se está validando, no solo qué hace el código.
- Los comentarios en el código explican el PORQUÉ no obvio (un
  invariante, una relación entre campos, un motivo causal) -- no narran
  el historial de cómo se llegó a esa decisión.
- Constantes numéricas nuevas en `config/` van marcadas como PROVISIONAL
  en su propio comentario si no las calibras contra el motor en marcha
  (no lo estarán -- no hay tiempo en esta tarea para un harness de
  calibración completo). La propia spec ya da valores PROVISIONAL de
  partida (`huella_m2`: manzano=4.0, cactus=1.5) -- puedes usarlos tal
  cual.

## Al terminar

1. Ejecuta la suite completa de tests (`pytest`) -- debe quedar en verde,
   incluidos los tests que añadas.
2. Corre un smoke test del motor real sin intervención
   (`BOSQUE_AUTO_TICKS`, unos pocos miles de ticks) y confirma que no
   lanza ninguna excepción.
3. Haz commit de tus cambios con un mensaje real que describa qué
   implementaste (no "implementa la spec" sin más -- qué decisiones
   concretas tomaste), terminando con:

```
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01YBndDfdejVJwuWSmWbk1BS
```
