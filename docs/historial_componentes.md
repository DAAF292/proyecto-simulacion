# Historial de diseño — `componentes/`

Extraído de los comentarios en línea el 2026-09-02 (ver CLAUDE.md,
sección "Comentarios técnicos vs narrativa histórica"). Un componente
por sección; solo se listan los que tenían narrativa real que mover.

## `posicion.py` — `zona_idx`

Círculo 1 de profundidad (2026-08-30, ver conversación de diseño con
Diego y nucleo/territorio.py). 0 = superficie, para TODA entidad
existente antes de este campo (valor por defecto, ninguna entidad ni
sistema previo necesitó tocarse). Reutiliza el índice de la lista ya
existente (Territorio.zonas, deliberadamente una lista desde el 23-08
"para el día que un territorio contenga varias zonas") en vez de
inventar un término nuevo -- evita la colisión con "Zona de bioma", que
ya significa algo distinto en la jerarquía Mundo → Territorio →
ZonaBioma → Celda.

## `pool_mental.py`

Pool de estabilidad mental (criatura.docx, sección 4.2): "un pool
nuevo, paralelo a vitalidad". El drenaje continuo proporcional a
(1 - seguridad) se eligió en vez de un umbral de "muchos ticks" con
contador porque el documento original no fijaba ese número -- se optó
por continuo para no inventar estado nuevo.

## `memoria_espacial.py`

Diseño discutido y confirmado con Diego (conversación sobre "la memoria
como base de la civilización" -- asentamientos, relaciones,
profesiones, conocimiento, magia, quedan explícitamente FUERA de esta
pieza): recuerdos es un diccionario en vez de campos sueltos por tipo
(antes se pensó en ubicaciones_alimento/ubicaciones_agua como dos
campos fijos) -- misma información, forma más general, para no tener
que reescribir la estructura cuando llegue una clave nueva.

## `pool_fisico.py`

Pools de capacidad física (criatura.docx, sección 3.2): distintos de
las Necesidades -- no son una presión que se satisface periódicamente,
sino una reserva que se agota con el daño o el esfuerzo. La división
por escalar (vitalidad_maxima/resistencia_maxima) fue una corrección
posterior, discutida y confirmada con Diego.

## `fogata.py`

Segunda pieza del arco de herramientas/fuego/comida elaborada -- "usar
dos rocas para hacer un fuego" (2026-08-31, ver componentes/agarre.py y
conversación de diseño con Diego). Los efectos futuros (punto de unión
social, cimiento de cocina) fueron mencionados por Diego en esa misma
conversación, señalados para que un consumidor futuro sepa que el
componente está pensado para soportarlos sin rediseño.

## `reproduccion.py`

Tercera pieza de la secuencia de ciclo vital acordada con Diego el
2026-08-19 (edad → esperanza de vida/envejecimiento → reproducción).
Informe técnico, sección 6.3, literal: "Nuevos atributos de raza: sexo
(binario por defecto) y duración de gestación (rango racial, en días)".
50/50 para sexo es la hipótesis más neutra dado que el informe no
especifica proporción racial distinta.

## `temperamento.py`

Bloque B del plan de migración (sustituye a la vieja Categoría, que
mezclaba esto con dimensiones físicas). Corrección tras auditoría de
coherencia: en la práctica solo agresividad tenía consumidor real en
ese momento; sociabilidad ganó el suyo más tarde, fuera de orden
alfabético (el sesgo gregario en deambular, surgido de una pregunta
directa de Diego, no del plan por bloques). Bloque E completa los ocho
rasgos de criatura.docx 4.1.

## `capacidad_mental.py`

Bloque F1 del plan de migración a criatura.docx. resiliencia y
estabilidad_mental_maxima ganaron su consumidor real en una corrección
posterior, discutida y confirmada con Diego. consciencia comparte
componente con el resto de 4.2 por mecanismo compartido -- si la lógica
de gating futura (apaga fe/necesidades superiores en fauna, reduce
varios rasgos a una versión animal) llega a necesitar consultarla con
mucha frecuencia, ese sería el momento de reconsiderar un componente
propio, no antes.

## `planta.py`

Fase terreno 4 -- flora como entidad con crecimiento. Corrección
discutida y confirmada con Diego, posterior a esa fase: el campo
original era `tipo_terreno: TipoTerreno` -- una planta llevaba su
BIOMA, no su ESPECIE, error de modelo que confundía "dónde crece" con
"qué es".

## `identidad.py`

tick_nacimiento es fundamento de "6. Ciclo vital" (informe técnico) --
primer paso hacia esperanza de vida/envejecimiento y reproducción,
secuencia acordada con Diego el 2026-08-19. id_madre/id_padre saldan un
PENDIENTE que el propio informe técnico se autoseñaló ("ningún
individuo guarda quiénes son sus progenitores... sin parentesco
registrado, ninguna crónica futura puede hablar de generaciones reales
o linajes"). CONEJO/ARDILLA se introdujeron el 2026-08-20.

## `gestacion.py`

tamano_camada nació de la investigación "sostenibilidad de caza del
lobo" (2026-08-21, ver sistema_depredacion.py y config/poblacion.yaml,
sección depredación). Antes de este cambio, `_resolver_nacimientos()`
creaba exactamente UN hijo por gestación resuelta, para cualquier
especie -- simplificación que nunca se había cuestionado hasta que el
diagnóstico de 2026-08-21 encontró que era la pieza que rompía la
sostenibilidad del ecosistema a cualquier tamaño de mapa o población:
la presión de caza escala con el número de cazadores, pero un solo
hijo por concepción no compensaba esa presión en las especies presa
reales.

## `dimensiones_fisicas.py`

Bloque B del plan de migración (sustituye a la vieja Categoría, que
mezclaba esto con temperamento). Bloque C1: vitalidad_maxima/
resistencia_maxima ganaron su consumidor real en una corrección
posterior, discutida y confirmada con Diego -- llevaban desde ese mismo
bloque sin ninguno. Bloque G completa las 12 dimensiones físicas fijas
de criatura.docx 3.3. agudeza_sensorial: deuda saldada a petición
expresa de Diego, poco después de cerrar el Bloque G ("la deuda hay que
afrontarla ya") -- antes de eso, todas las especies compartían el mismo
radio de percepción uniforme; nucleo/percepcion.py explica cómo se
eligieron los bordes del mapeo tras detectar que un primer intento daba
variación cero dentro de lobo.

## `necesidades.py`

Convención unificada: informe técnico, sección 8.1, migración Bloque A
del plan de adaptación a criatura.docx. hambre se renombró a saciedad
en ese mismo paso. oxigenacion (Bloque D3) es la mecánica que
criatura.docx (3.1) preveía exactamente: "sin mecánica hasta que exista
riesgo real de asfixia (agua profunda, humo)" -- agua profunda ya
existe, humo NO (los incendios asustan vía seguridad/amenaza pero no
consumen oxigenación todavía). confort_termico (Bloque D3) fue
corregido el 2026-08-29 -- antes solo leía la estación, ignorando el
clima pese a que la función que combina ambos ya existía; un comentario
anterior decía por error que NO se persistía, corregido. impulso_
reproductivo nació el 2026-08-20, diseño conjunto tras investigar por
qué la reproducción casi nunca ocurría.

## `construccion.py`

FUNDAMENTO de la pieza "refugio construido" (2026-08-30, ver
conversación de diseño con Diego). propietario_id=None para "almacen":
"el almacén debe ser un objeto físico... no es una entidad nueva de
propiedad compartida [a nivel de refugio], pero el almacén sí es del
asentamiento" (Diego). completado_alguna_vez nació de una corrección de
diseño (2026-08-30, Diego, tras ver que SistemaAsentamiento filtraba
por progreso>=1.0 exacto): "no debería salir del asentamiento a la
mínima degradación, una casa dañada sigue perteneciendo a un pueblo".

## `inventario.py`

FUNDAMENTO de la fase de interacción física (2026-08-30, ver
conversación de diseño con Diego). Sin límite de variedad: "da igual
cuántos materiales sean, depende de tu capacidad física de portarlos"
(Diego).

## `agarre.py`

FUNDAMENTO (2026-08-31, conversación de diseño con Diego): primera
pieza de "capacidad de sostener/usar objetos" como cimiento de
sociedad. Nombre rechazado antes de Agarre: "Empuñadura" -- Diego lo
corrigió: "si creamos una raza que tenga 4 manos que, o una con dos
manos y una cola prensil... es parte de la criatura, una capacidad que
tiene como tiene la de andar o comer".
