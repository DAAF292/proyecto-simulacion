# Historial de diseño — `sistemas/sistema_reproduccion.py`

Extraído de los comentarios en línea el 2026-09-02 (ver CLAUDE.md,
sección "Comentarios técnicos vs narrativa histórica"). Este sistema
acumuló la mayor densidad de narrativa histórica de todo `sistemas/` --
buena parte ya está documentada en detalle en CLAUDE.md (sección
"Sobrepoblación sin techo aparente..."), así que este documento se
centra en lo que era específico del código, no una repetición completa.

## Origen (informe técnico 6.3)

Primera pieza CONDUCTUAL de la secuencia de ciclo vital acordada con
Diego el 2026-08-19: edad -> esperanza de vida/envejecimiento ->
sexo/gestación/madurez -> emparejamiento (este sistema) -> nacimiento
con herencia/parentesco.

No se inventó una acción nueva de "cortejo" en la Utility AI -- decisión
deliberada: la proximidad que sociabilidad ya produce (sesgo gregario
dentro de DEAMBULAR) es suficiente, evaluar emparejamiento sobre ella es
reutilizar un mecanismo existente.

Sociabilidad es el ÚNICO rasgo de Temperamento reutilizado para la
probabilidad de concepción -- el único que ya significaba algo coherente
con esto en el motor (tendencia a vincularse con coespecíficos).
Dominancia (competencia por pareja, plausible en teoría) se descartó
deliberadamente: el motor no tenía ningún concepto de jerarquía o
competencia en ese momento, incorporarla habría sido inventar, no
reutilizar. A diferencia del sesgo gregario de sociabilidad (que SÍ usa
sociabilidad directa, sin escalar), aquí hizo falta un factor de escala
nuevo (`factor_base_concepcion`): sociabilidad directa como probabilidad
de concebir dispararía la población sin control.

## Corrección 2026-08-20 -- diferenciación por especie y cadencia por tick

Investigación de por qué la reproducción casi nunca ocurría, con dos
causas raíz distintas:

1. **Diferenciación por especie**: `factor_base_concepcion` pasó de un
   único valor global (0.08, leído como probabilidad DIARIA) a un valor
   POR ESPECIE en `rangos_raciales` (config/constantes.yaml) -- un solo
   número no podía representar la diferencia real de fecundidad entre un
   lobo (K-strategy) y un conejo (r-strategy).
2. **Evaluación por tick en vez de por día**: el muestreo diario perdía
   contactos reales -- una pareja podía tocarse y separarse otra vez
   entre dos cortes de día sin que el sistema lo viera nunca, sobre todo
   antes de que existiera `Accion.BUSCAR_PAREJA`. Los valores por
   especie quedaron calibrados como el equivalente por tick de la vieja
   probabilidad diaria (dividido entre TICKS_POR_DIA), para no reabrir
   de golpe la calibración ya validada el 2026-08-19.

`_resolver_nacimientos()` pasó a evaluarse cada tick como efecto
colateral de quitar el `return` temprano que envolvía a ambas mitades de
la función -- sin downside real, su propia comparación ya era correcta a
cualquier cadencia.

## Corrección 2026-08-21 -- tamaño de camada real

Antes de este cambio, cada gestación resuelta producía exactamente un
hijo para cualquier especie -- la investigación encontró que esa
simplificación era la pieza que impedía que la reproducción compensara
la presión de caza a ningún tamaño de mapa o población (la caza escala
con el número de cazadores, un solo hijo por concepción no escala con
nada). No se tocó el criterio de contacto/elegibilidad -- seguir
necesitando coincidir en la misma celda es una ley física real, no el
cuello de botella que se estaba corrigiendo.

## Corrección 2026-08-31 -- gate de nutrición (ver también CLAUDE.md)

Investigación de sobrepoblación sin techo aparente (ver CLAUDE.md,
migración 24-08-2026): el hallazgo real fue que no era "sin techo", era
un ciclo boom-bust que en la semilla más extrema llegaba a densidad
0.34, con extinción total en otra semilla. La simplificación de antes
("no exige necesidades físicas resueltas") producía algo que no se
sentía natural: dos elegibles que se tocaban por casualidad (huyendo,
migrando hacia comida, deambulando) concebían sin que importara si
estaban muriendo de hambre, porque el único gate de necesidades físicas
existente (`umbral_atencion_pareja`) actuaba sobre la UTILIDAD de
BUSCAR_PAREJA, no sobre el roll de concepción en sí.

Descartada deliberadamente la alternativa de un contador de densidad
local (freno artificial pensado para el síntoma observado en conejo, no
una ley que pudiera producirlo entre otros -- violaría el principio 5,
leyes neutras). La ley natural real es la contraria: desnutrición
suprime la fertilidad.

**RONDA 1** (mismo día) gateaba por las 4 necesidades físicas completas
en ambos progenitores a la vez -- sobrecorregía: con 4 semillas de
control, 3 de 4 pasaron de "sin techo" a colapsar muy por debajo del
rango de referencia (0.05-0.07; semilla 42 estabilizó en 0.0037, semilla
1 en caída hacia 0.0031). **RONDA 2** estrechó el gate a saciedad
únicamente -- coherente con que el escalado de camada ya solo miraba
saciedad, y con que la petición original de Diego fue específicamente
sobre nutrición ("un conejo mal alimentado lo normal es que produzca
menos crías"), no sobre el estado físico general.

Riesgo señalado a Diego antes de implementar, no resuelto por este
cambio en sí: si el recurso del que vive una especie se regenera lo
bastante rápido como para mantener la saciedad alta incluso a densidad
extrema, este freno no se activará -- en ese caso el problema pasa a ser
de calibración de `sistema_flora.py`, no de reproducción.

Ver CLAUDE.md para el detalle completo de la verificación final (14
semillas hasta 8000 ticks, dos modos de fallo residuales sin resolver:
colapso/extinción y overshoot lento).
