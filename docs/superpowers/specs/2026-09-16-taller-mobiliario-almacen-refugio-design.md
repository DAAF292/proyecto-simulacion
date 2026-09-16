# Taller de artesano + mobiliario/comodidad + almacén de refugio

Fecha: 2026-09-16. Primera pieza real de "tipos de construcción nuevos"
(roadmap unificado "asentamientos/profesiones" + "asentamiento como
entidad propia"). Diego pidió explícitamente empaquetar dos ideas
relacionadas en el mismo círculo ("ambas juntas, mismo círculo"), pese
a que el criterio habitual del proyecto prefiere una fuente de
complejidad a la vez -- decisión suya, documentada, no autorada.

## Pieza A: Taller → mobiliario → comodidad

### Motivación

`Necesidades.comodidad` (Pieza C del arco "comodidad", 2026-09-14) hoy
deriva EXCLUSIVAMENTE de `calidad_media_construccion(refugio.materiales,
catalogo)` -- la calidad de los materiales de CONSTRUCCIÓN (arcilla,
piedra, hierro), nunca de nada fabricado. La cubeta "artesano" de
conocimiento colectivo (cerrada el 15-09) acumula desde el primer día
pero no tiene ningún consumidor -- FABRICAR es determinista/instantáneo,
sin ninguna tasa continua que un bono pueda acelerar, así que el patrón
ya usado para forrajero/constructor/cocinero no se puede reutilizar tal
cual.

### Diseño

- `Construccion.tipo="taller"` -- **tercer paralelo** en la cadena de
  `objetivo_construccion_actual` (`tipos_paralelos = ["salon_comun",
  "cocina", "taller"]`, el punto de extensión ya preparado desde el
  15-09: "generaliza limpio a un tercer paralelo futuro sin tocar la
  forma de la función"). `masa_minima_taller`/`huella_m2_taller` nuevos
  en `config/materiales.yaml`, mismo criterio que salón/cocina.
- `Accion.FABRICAR` gana una cuarta categoría, **"mobiliario"**. A
  diferencia de arma/herramienta/mineria (utilidad heredada de
  `necesidad_trabajo`), mobiliario es una TERCERA VÍA del bloque "MEJORA
  DE VIVIENDA" ya existente (junto a RECOLECTAR-mejora y
  CONSTRUIR-mejora) -- hereda `deficit_comodidad = 1.0 -
  Necesidades.comodidad` (mismo valor ya calculado ahí), no un valor
  nuevo. Condiciones, dentro del mismo bloque `if not
  prioriza_comunal:` ya existente:
  1. Refugio propio `completado_alguna_vez` (gate ya compartido).
  2. El individuo está en la celda de un taller **completado** del
     propio asentamiento (`construccion_de_tipo_en`, ya existente).
  3. El nivel de conocimiento colectivo "artesano" del asentamiento
     supera `asentamiento.umbral_conocimiento_taller` (PROVISIONAL) --
     **primer efecto real de esa cubeta**.
  4. Hay una receta de mobiliario completable con los materiales
     crudos ya portados (`mejor_receta_completable`, reutilizada tal
     cual), y su `calidad_construccion` (ver más abajo) supera la ya
     invertida en el refugio (`calidad_actual_refugio`, ya calculada
     ahí) -- mismo criterio de autolimitación que las otras dos vías,
     sin techo autorado.
- **Simplificación clave**: el mueble fabricado NO es un objeto
  discreto como arma/herramienta (`Inventario.objetos`) -- se produce
  como **cantidad en kg añadida a `Inventario.contenidos`** (receta
  nueva gana `cantidad_kg`). Al tratarse como un "material" más con
  `calidad_construccion` muy alta (por encima de hierro=0.95) en
  `config/materiales.yaml`, el mecanismo YA CONSTRUIDO de
  CONSTRUIR-mejora (`_resolver_mejora_refugio`, que ya busca en
  `contenidos` el material de mayor calidad portado y sustituye lo peor
  invertido) lo reconoce e instala **sin tocar ese código en absoluto**
  -- ninguna Accion nueva de "instalar mueble".
- Catálogo (`config/herramientas.yaml:recetas_mobiliario`, mismo fichero
  que agrupa ya todas las categorías de FABRICAR):
  - `utensilios_domesticos` (madera, nivel 1, 3.0 kg, calidad 0.7)
  - `mueble_tallado` (madera+piedra, nivel 2, 5.0 kg, calidad 0.9)
  Ambos nuevos en `config/materiales.yaml` con `apto_construccion:
  true` -- nunca aparecen en `Celda.recursos`/`tipo_sustrato`, solo se
  originan vía FABRICAR.
- Evento `MuebleFabricado` (NOTABLE), mismo molde que
  `HerramientaFabricada`/`PicoFabricado`.

## Pieza B: Almacén personal en el refugio

### Diseño

Diego: "un refugio propio tenga su almacén también, para que alguien
guarde sus pertenencias" -- mecánica resuelta con criterio razonado,
marcada PROVISIONAL, sin especificación previa más allá de la idea.

- `Construccion` gana `almacen: dict[str, float] = field(default_factory=dict)`
  -- mismo molde que `provisiones` (alacena de cocina), universal en el
  componente. Solo material a GRANEL (`Inventario.contenidos`), no
  objetos discretos -- un arma/herramienta se sigue portando por su
  efecto activo, un material sobrante no.
- **Sin Acción nueva** (mismo criterio que el ajuste automático de
  Agarre): cada tick, un consciente en la celda de su refugio propio ya
  `completado_alguna_vez`, con material a granel en `Inventario.
  contenidos` que NO hace falta para su objetivo de construcción actual
  (ni para completar el propio refugio -- ya completado -- ni para una
  mejora de vivienda en curso ese mismo tick), deposita el excedente en
  `Construccion.almacen` del refugio, liberando capacidad de carga
  real.
- Efecto real, deliberadamente mínimo en este círculo: libera espacio
  de inventario (medible directamente) y sirve de reserva futura --
  **sin ningún mecanismo de retirada/consumo del almacén todavía**
  (haría falta una segunda pieza para "usar lo guardado", fuera de
  alcance aquí, señalada como pendiente honesto).

## Fuera de alcance de este círculo

- Retirar/consumir material del almacén de refugio (solo depósito).
- Cualquier receta de mobiliario con metal (cobre/hierro) -- aplazado,
  ya hay dos entradas con madera/piedra suficientes para verificar el
  mecanismo.
- Compartir el almacén entre miembros de un mismo hogar (hoy el refugio
  ya es de un único propietario).

## Verificación esperada

- Tests dirigidos: receta de mobiliario produce cantidad en
  `contenidos`, no en `objetos`; gate de taller+conocimiento en
  `sistema_decision.py`; `_resolver_mejora_refugio` reconoce mobiliario
  sin ningún cambio de código (test de regresión); depósito automático
  en almacén de refugio con y sin excedente real.
- `BOSQUE_AUTO_TICKS`/`BOSQUE_CONTINUAR` sin excepciones.
