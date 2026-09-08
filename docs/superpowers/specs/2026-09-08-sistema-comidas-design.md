# Sistema de comidas — catálogo real y modelo de comida elaborada — diseño

Fecha: 2026-09-08. Precede al diseño de "cocina" (edificio + acción de
cocinar, círculo siguiente del arco "dinámicas internas de
asentamiento") -- Diego pidió explícitamente separar "qué es la comida"
de "cómo se cocina". Este círculo cierra lo primero: un catálogo de
dieta más sensato para gnomo, y el MODELO de datos de comida elaborada
(sin activar todavía ningún mecanismo que lo consuma).

## Motivación

Diego, revisando la dieta real de gnomo (13 recursos -- literalmente
todo el catálogo de flora, herencia del círculo de "alimentos huérfanos"
del 2026-09-07): "no tiene sentido que un gnomo coma hierba". Dieta
reducida a cuatro categorías reales: raíces, manzanas, bayas, néctar de
semillas -- una dieta de forrajero humanoide plausible, no "come
absolutamente cualquier cosa que exista en el mundo".

De ahí surgió una pregunta real y más interesante: ¿qué de esa dieta
podría ser tóxico en crudo? Diego: "las raíces y las bayas pueden llegar
a ser tóxicas" -- primer caso REAL (no hipotético) para
`DimensionesFisicas.resistencia_enfermedad`, sorteado por individuo
desde hace tiempo sin ningún consumidor (mismo patrón que valentía/
empatía antes de su primer uso).

## Decisiones cerradas con Diego, en orden

1. **Dieta de gnomo reducida a 6 claves reales** (dos recursos por cada
   categoría, porque "raíces"/"bayas" existen con el mismo nombre
   genérico en biomas distintos): `raices` + `raices_deserticas`
   (raíces), `manzanas`, `bayas_espinosas` + `bayas_montanas` (bayas),
   `nectar_semillas` (néctar). Se cae todo lo demás (`hierba`,
   `fruto_de_cactus`, `liquen`, `musgo`, `bellotas`, `brotes_helecho`,
   `brotes_articos`) -- sigue existiendo en el mundo para otras especies
   (ardilla ya come bellotas, conejo/caballo su propio subconjunto),
   solo deja de ser comestible para gnomo.
2. **Toxicidad como propiedad del catálogo, no lógica de especie**:
   nuevo campo `toxico_crudo: true/false` por recurso de
   `config/flora.yaml`, mismo patrón que `apto_construccion`/
   `compite_espacio_fisico` -- un hecho del alimento, no una regla
   escrita para gnomo en particular. `true` en las 4 claves de
   raíces/bayas; `false` en manzanas y néctar (confirmado explícitamente
   con Diego).
3. **Universal, no específico de especie ni de "vegetal"**: hoy ningún
   consciente come carne, así que la carne nunca entra por este camino
   -- pero el mecanismo (catálogo de toxicidad + mejora por elaboración)
   no excluye la carne por diseño. El día que exista una raza consciente
   carnívora, usaría el mismo campo `toxico_crudo` y el mismo mecanismo
   de elaboración, sin ningún caso especial que escribir.
4. **Comida elaborada, modelo de datos SIN tabla de recetas**: cocinar
   un recurso en `Inventario.provisiones` lo convertiría en una clave
   nueva con sufijo (`"<recurso>_elaborado"`), con un multiplicador
   ÚNICO y universal sobre `valor_nutricional`/`valor_hidratacion` --
   sin una entrada de config por cada uno de los 13 alimentos del
   catálogo (mismo criterio ya aplicado a la caducidad de provisiones:
   una tasa universal en vez de 13 específicas, sin ningún dato real
   que justifique diferenciarlas todavía).
5. **Secuenciación explícita, para no introducir un riesgo sin cura**:
   activar la toxicidad de crudo AHORA, sin que exista todavía ninguna
   forma de cocinar, introduciría un riesgo real y permanente para
   gnomo sin ningún modo de evitarlo -- cocinar es la única cura
   planteada. Este círculo cierra el CATÁLOGO (qué es tóxico, qué
   mejoraría al cocinarse) como dato inerte; el círculo de "cocina"
   activa el mecanismo real (probabilidad de intoxicación, consumo de
   `resistencia_enfermedad`, la transformación en sí) -- los dos
   círculos se implementan juntos, no éste antes suelto.
6. **Visión a futuro, anotada, NO diseñada aquí**: Diego conecta esto
   con una futura alquimia -- un sistema de procesado genérico
   compartido entre comida, refinamiento de metales (ya existe minería
   de vetas), y un futuro sistema de magia. El hecho de que el
   mecanismo de elaboración de hoy ya sea genérico (multiplicador
   universal, sin tabla por receta) es justo lo que dejaría la puerta
   abierta a esa reutilización futura, sin comprometerse a nada de eso
   ahora.

## Alcance

**Dentro (implementable ya, sin activar ningún mecanismo nuevo):**

1. `config/poblacion.yaml`, `rangos_raciales.gnomo.dieta`: reducir a
   `[raices, raices_deserticas, manzanas, bayas_espinosas,
   bayas_montanas, nectar_semillas]`.
2. `config/flora.yaml`: campo nuevo `toxico_crudo` en las entradas de
   recurso relevantes (dentro de cada `recursos:` de una especie de
   flora) -- `true` en `raices` (hierba_silvestre), `raices_deserticas`
   (hierba_desertica), `bayas_espinosas` (arbusto_espinoso),
   `bayas_montanas` (arbusto_montano); el resto del catálogo, sin el
   campo (equivalente a `false` por `.get()` permisivo, mismo criterio
   ya usado en todo el proyecto -- no hace falta escribir `false`
   explícito en los otros 9 recursos).
3. Tests dirigidos sobre el catálogo (dieta real de gnomo, flag de
   toxicidad presente donde corresponde) + verificación obligatoria
   contra el motor real de que la dieta reducida no rompe nada
   (recolección/forrajeo, provisiones, propagación zoocoria de las
   claves que se quitan de la dieta de gnomo -- esas especies de flora
   siguen intactas, solo deja de comerlas gnomo).

**Fuera de alcance, explícito -- círculo siguiente ("cómo cocinar")**:

- La acción/mecanismo de elaborar comida en sí (disparador, requisito
  de fuego, quién puede hacerlo).
- Activar la probabilidad de intoxicación por comer crudo tóxico, y su
  modulación por `resistencia_enfermedad` -- el campo `toxico_crudo` se
  añade aquí, pero NADA lo lee todavía.
- El multiplicador `factor_mejora_elaboracion` y cualquier constante de
  probabilidad de intoxicación -- no se añaden en este círculo (sin
  consumidor todavía, se añadirían junto con el mecanismo que las usa).
- Cualquier cambio a `Inventario.provisiones` (estructura, claves con
  sufijo) -- se diseña en detalle cuando se diseñe la acción de cocinar.
- Alquimia, refinamiento de metales, magia -- visión a futuro, sin
  diseñar.

## Testing

- Dieta de gnomo: exactamente las 6 claves acordadas, ni más ni menos
  (regresión explícita de las 7 que se quitan).
- `toxico_crudo`: `True` en las 4 claves esperadas, ausente/`False` en
  manzanas y néctar (y en el resto del catálogo que gnomo ya no come).
- **Verificación obligatoria contra `BOSQUE_AUTO_TICKS`**: gnomo sigue
  alimentándose con normalidad con la dieta reducida (sin regresión de
  saciedad/hidratación ni de la mecánica de provisiones ya construida),
  sin ninguna excepción. Reportar si la dieta más estrecha afecta de
  forma medible a la estabilidad de gnomo (candidato a vigilar, no a
  corregir preventivamente sin datos).

## Pendiente real tras esta pieza

- El círculo de "cocina" (acción de elaborar, activación real de
  toxicidad + `resistencia_enfermedad`, `factor_mejora_elaboracion`) es
  el siguiente paso inmediato de este mismo arco.
- Dieta de conejo/ardilla/caballo no revisada en este círculo -- Diego
  solo pidió corregir la de gnomo.
- Alquimia como sistema de procesado genérico compartido con
  metalurgia/magia, mencionada por Diego, sin ningún diseño todavía.
