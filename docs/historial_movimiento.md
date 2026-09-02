# Historial de diseño — `sistemas/sistema_movimiento.py`

Extraído de los comentarios en línea el 2026-09-02 (ver CLAUDE.md,
sección "Comentarios técnicos vs narrativa histórica"). El archivo más
grande de todo el repositorio (1102 líneas antes de podar) -- historia
consolidada aquí en vez de en el documento compartido de `sistemas/`.

## Fixes de auditoría (2026-08-29)

Una única sesión de auditoría encontró y corrigió varios bugs
silenciosos, todos del mismo tipo: código escrito pero nunca ejercido en
la práctica porque una condición previa lo mantenía siempre inactivo.

- **`Gestacion` importada del módulo antiguo**: se separó a su propio
  módulo (`componentes/gestacion.py`) para no mezclar el rasgo fijo de
  por vida (`Reproduccion`) con el estado de un embarazo concreto, pero
  este archivo seguía importando del módulo viejo.
- **Coste de pendiente reimplementado inline**: `_aplicar_movimiento`
  duplicaba la fórmula de `nucleo/relieve.py:costo_resistencia_por_pendiente`
  en vez de llamar a la función centralizada -- mismo riesgo de
  divergencia que el proyecto se advierte a sí mismo en
  `nucleo/percepcion.py` y `nucleo/disposicion.py`.
- **`_calcular_huida` con `TypeError` latente**: llamaba a
  `posicion_amenaza_mas_cercana` sin cachear `peso_propio` ni
  `umbral_disposicion`, que la función exige sin valores por defecto.
  Nunca había ocurrido en la práctica porque, hasta esa misma sesión,
  `Necesidades.seguridad` no drenaba nunca y `utilidad_huir` era 0.0
  siempre (ver el fix hermano en `sistema_necesidades.py`).
- **`HUIDA_ERRATICA`/`CRISIS_VIOLENTA` sin rama en `ejecutar()`**: caían
  a `dx=dy=0` por defecto, indistinguibles de `CATATONIA` en sus efectos
  reales, pese a que `componentes/intencion.py` ya describía un
  comportamiento propio para cada una ("huye de cualquiera cercano, sin
  amenaza real" / "se acerca a cualquiera cercano -- sin mecánica de
  daño todavía, deliberado"). Corregido con `_entidad_cercana_cualquiera`
  y las dos ramas `_calcular_huida_erratica`/`_calcular_crisis_violenta`.
- **`_calcular_forrajeo` con código muerto**: llamaba a
  `mem.obtener_recuerdos(tipo)` (método que `MemoriaEspacial` no tiene) y
  luego a `objetivo_recordado()` con una firma posicional que no
  coincidía con la real de `nucleo/memoria.py` -- crashearía en cuanto
  se alcanzara (no había ocurrido porque el candidato directo por
  percepción casi siempre existe antes).

## `_calcular_caza` -- dos filtros de presa válida (2026-08-23)

Pregunta de Diego: "un lobo intenta depredar una mosca si se
introduce" -- confirmado real: antes de este cambio, la única condición
para ser "presa válida" aquí era `peso_p < peso_cazador`, sin ningún
suelo. `sistema_depredacion.py:_es_presa_valida` sí tenía un umbral de
disposición, pero esa magnitud CRECE sin techo cuanto más pequeña es la
presa -- una mosca frente a un lobo lo habría superado con más margen
que un conejo, exactamente al revés de lo que hace falta. De ahí los dos
filtros (viabilidad energética, detectabilidad por tamaño) documentados
en el propio docstring de la función. Ninguno de los dos umbrales se ha
calibrado con el harness completo.

## `_calcular_deambular` -- orden de la cascada territorio/gregario (2026-08-22 a 23)

**Sesgo de territorio** (2026-08-22, propuesta de Diego, confirmada: "a
nivel biológico lo común es mantenerse cerca de las fuentes de
alimentación, agua y seguridad").

**Orden invertido** (2026-08-23, decisión de Diego): la primera versión
de esta cascada probaba el gregario primero, por una reconstrucción
razonada sin respaldo directo de Diego. Consultado explícitamente sobre
cuál debía ir primero, Diego no tenía un criterio cerrado pero señaló el
norte del proyecto: "nuestra atención es crear la simulación lo más
apegada a la realidad". Bajo ese criterio, la fidelidad al área de
campeo es el instinto más fuerte y mejor documentado en fauna real -- un
animal no abandona su territorio conocido por aproximarse a un
congénere de paso; el agrupamiento social real ocurre DENTRO del área de
campeo compartida, no en lugar de ella.

**Nota de reconstrucción del sesgo gregario** (2026-08-23): el sesgo
gregario existió y se confirmó con Diego en algún momento anterior --
constaba, con esas palabras, en el docstring de
`componentes/temperamento.py` ("el sesgo gregario en deambular, surgido
de una pregunta directa de Diego") y en el de
`sistema_reproduccion.py` ("SistemaMovimiento ya se encarga de acercar a
los coespecíficos"). No sobrevivió al refactor de necromasa/pipeline
trifásico del 22-08 -- mismo patrón de pérdida por colisión de ediciones
diagnosticado ese mismo día para `nacer_criatura`, solo que este caso no
lanzaba ninguna excepción (la clave de config quedaba leída y sin usar),
así que no se detectó hasta auditar el código funcionalidad por
funcionalidad.

## `_calcular_dormir` -- refugio instintivo (2026-08-30)

Pieza 1 de interacción física, confirmado con Diego: "el impulso es el
mismo, buscar comodidad, seguridad, un entorno en el que estar seguro
con los tuyos... el hecho de poder construir te lo da tu consciencia".
Hasta esa pieza, `Accion.DORMIR` no hacía NADA en este sistema
(`continue` directo): la criatura se quedaba dormida donde le pillara el
sueño, sin buscar refugio ni compañía.

Las dos capas del mecanismo (refugio recordado individual, sesgo
gregario como fallback) evitan deliberadamente inventar memoria
compartida -- Diego señaló el problema real: "no tenemos una memoria
común y no sé cómo plantearlo" -- la respuesta fue que no hacía falta:
"si no sé dónde dormir seguro, no duermo solo" ya produce el resultado
práctico (una manada tiende a dormir agrupada) sin memoria compartida.

## `_resolver_posible_intruso` -- conflicto por refugio ocupado (2026-08-30/31)

Primer consumidor de `nucleo/conflicto.py`, de una conversación de
diseño con Diego: "no es el hecho de poder o no poder [entrar]... esa
acción deberá tener una consecuencia. ¿qué hace el gnomo propietario si
llega y se encuentra a otro en su refugio?".

El filtrado por `zona_idx` (2026-08-31) fue un ajuste de merge con el
Círculo de profundidad: "misma celda" ya no bastaba con comparar (x, y)
-- con varias zonas (superficie + cuevas) dos entidades en zonas
DISTINTAS podían compartir coordenadas numéricas por pura coincidencia,
mismo hallazgo que ya obligó a filtrar
`almacen_cercano`/`agrupar_por_proximidad` por zona.

## `_calcular_construir` -- refugio/almacén construido (2026-08-30/31)

Pieza 2 de interacción física, de la conversación de diseño con Diego
sobre refugio construido/recolección/asentamiento (ver CLAUDE.md). La
comprobación de capacidad por celda (`espacio_disponible_para_construir`)
es del 2026-08-31, del mismo círculo que introdujo `huella_m2_refugio`/
`huella_m2_almacen` en `config/materiales.yaml`.
