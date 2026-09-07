# Salón común — primer edificio de dinámicas internas de asentamiento — diseño

Fecha: 2026-09-08. Primera pieza del arco "dinámicas internas de
asentamiento" (Diego: "ahora tenemos un almacén, pero hay que hacer
más... un salón común donde socializar al calor de un fuego"). Ciudad
enana queda explícitamente fuera de este arco por decisión de Diego --
pertenece a una raza enana todavía sin plantear, no se menciona aquí.
Cocinas y edificio de liderazgo quedan como siguientes círculos del
mismo arco, sin diseñar todavía.

## Motivación

Hoy `Accion.SOCIALIZAR` (`sistema_movimiento.py:_calcular_socializar`)
busca al consciente más cercano de forma puramente oportunista -- nadie
"va a ningún sitio" a socializar, solo se encuentran por casualidad si
ya están cerca. Un salón común real cambia eso: da un destino físico
real al que caminar, concentrando gente en un mismo punto en vez de
depender de coincidencias.

## Decisiones cerradas con Diego

- **Ciudad enana fuera de alcance por completo** -- no se menciona en
  este documento salvo esta nota.
- **Cimiento ya existente, sin mecanismo nuevo que inventar**:
  `Construccion.tipo` ya es un catálogo abierto; `CONSTRUIR`/
  `RECOLECTAR`, el cupo de espacio por celda
  (`espacio_disponible_para_construir`) y el deterioro
  (`sistema_descomposicion.py:_descomponer_construcciones`) ya
  funcionan para cualquier tipo nuevo sin tocar código -- exactamente
  el mismo cimiento que ya sirve a refugio y almacén.
- **Efecto núcleo real, no decoración**: el salón común es el destino
  preferente de `SOCIALIZAR` cuando existe y está completado -- un
  consciente que decide socializar camina hacia él en vez de perseguir
  al más cercano al azar. Esto amplifica gratis todo lo que ya se
  dispara cuando varios conscientes comparten celda (roce social,
  rumor, compartir por confianza, memoria compartida) sin tocar ninguno
  de esos sistemas.
- **"Al calor de un fuego" -- bonos propios, mismo patrón aditivo ya
  usado por refugio/fogata/madriguera/pareja**: confort térmico y
  seguridad, sin necesitar una `Fogata` real aparte (el salón ya
  implica su propio hogar).
- **Prioridad de construcción**: refugio > almacén > salón común
  (supervivencia individual → supervivencia comunal → calidad de
  vida) -- extensión directa de la cadena de prioridad que
  `objetivo_construccion_actual` ya impone entre refugio y almacén.
- **Ubicación**: centro del asentamiento, mismo criterio que almacén
  -- hay que llegar hasta ahí, no se crea donde a cada gnomo le pille.

## Alcance

**Dentro:**

1. `nucleo/asentamiento.py:almacen_cercano` gana un parámetro
   `tipo: str = "almacen"` (por defecto, sin romper a los dos
   consumidores existentes que no lo pasan) -- mismo criterio ya usado
   en el proyecto para generalizar una función cuando aparece un
   segundo consumidor real (`agrupar_por_proximidad`/`calcular_centro`,
   extraídas para Manada). El nombre de la función se conserva (mismo
   criterio ya aceptado en `espacio_disponible_para_construir`, que
   también conserva un nombre histórico por los consumidores que ya lo
   importan) -- no se renombra a algo más genérico para no ensuciar el
   diff de una pieza pequeña.
2. `nucleo/construccion.py:objetivo_construccion_actual`: la rama de
   almacén se reescribe para dejar de ser terminal. Hoy es: si el
   almacén existe y está completo, `return None` (nada más que hacer);
   si no, `return ("almacen", cid_o_None, asen.centro)` (exista ya a
   medias o no exista todavía). El salón común sigue exactamente la
   MISMA forma, encadenado en vez de terminal: solo se comprueba
   (`almacen_cercano(..., tipo="salon_comun")`) una vez el almacén está
   completo; si el salón no existe o no está completo, `("salon_comun",
   cid_o_None, asen.centro)`; si también está completo, ENTONCES sí
   `None` (nada más que construir, comportamiento terminal se traslada
   al final de la cadena en vez de cortar en almacén).
3. `nucleo/construccion.py` (nuevo, junto a las demás funciones puras
   sobre `Construccion`): `hay_construccion_de_tipo_en(gestor, pos_x,
   pos_y, zona_idx, tipo) -> bool` -- generaliza
   `nucleo/fuego.py:hay_refugio_en` (hoy hardcodeado a `tipo=="refugio"`)
   para que un segundo consumidor (salón común) no duplique el mismo
   bucle. `hay_refugio_en` pasa a ser un alias de una línea
   (`hay_construccion_de_tipo_en(gestor, pos_x, pos_y, zona_idx,
   "refugio")`) -- comportamiento idéntico, cero consumidores rotos.
4. `sistemas/sistema_movimiento.py:_calcular_socializar`: nuevo
   parámetro implícito vía `mundo` (ya se recibe) -- tras comprobar
   contacto real (sin cambios en esa rama), si
   `asentamiento_de(mundo, entidad_id)` existe y su salón común
   (`almacen_cercano(gestor, asen.centro, self.radio_cluster_asentamiento,
   zona_idx=asen.zona_idx, tipo="salon_comun")`) está completado
   (`Construccion.completado_alguna_vez`) y no coincide ya con la
   posición actual, camina hacia sus coordenadas
   (`_acercarse_a`) EN VEZ DE hacia el consciente más cercano. Sin
   salón común disponible, comportamiento IDÉNTICO al actual (busca al
   más cercano, o paso aleatorio si no hay nadie). La resolución de
   afinidad por contacto real (ya existente) no cambia en absoluto --
   sigue disparándose igual cuando dos conscientes coinciden en una
   celda, sea porque ambos caminaron al salón o por pura casualidad.
5. `sistemas/sistema_necesidades.py`: dos bonos nuevos, mismo bloque y
   patrón exacto que `bono_confort_madriguera`/`bono_seguridad_madriguera`
   -- si `hay_construccion_de_tipo_en(gestor, pos.x, pos.y, pos.zona_idx,
   "salon_comun")`, sumar `bono_confort_salon_comun` a `obj_termico` y
   `bono_seguridad_salon_comun` a `Necesidades.seguridad` (capado a
   1.0). Aplica a CUALQUIERA en la celda, no solo a quien lo construyó
   -- mismo criterio ya establecido para refugio/fogata/madriguera ("un
   sitio abriga a quien esté dentro").
6. Config nueva (PROVISIONAL, sin calibrar):
   - `config/materiales.yaml`, sección `construccion:` (junto a
     `masa_minima_almacen`/`huella_m2_almacen`): `masa_minima_salon_comun:
     70.0` (algo más que el almacén -- un edificio comunal más grande),
     `huella_m2_salon_comun: 45.0`.
   - `config/fisiologia.yaml`, sección `necesidades.defecto` (junto a
     `bono_confort_madriguera`/`bono_seguridad_madriguera`):
     `bono_confort_salon_comun: 0.3` (mismo orden que refugio/fogata),
     `bono_seguridad_salon_comun: 0.1` (mismo orden que madriguera --
     una comunidad reunida protege más que estar solo).
7. Tests dirigidos + verificación obligatoria contra el motor real.

**Fuera de alcance, explícito:**

- Ciudad enana -- no se menciona, no se toca nada relacionado con
  cuevas en esta pieza.
- Cocinas, edificio de liderazgo -- círculos futuros del mismo arco,
  sin diseñar.
- Cualquier variación del efecto por atributo individual -- ley binaria
  (existe/no existe, completado/no completado), sin variar por
  inteligencia/sociabilidad más allá de lo que ya modula la elección de
  `SOCIALIZAR` en sí (fuera de esta pieza).
- Ninguna estructura multi-celda -- mismo límite ya conocido y aceptado
  para refugio/almacén, el salón común es una celda más.
- Requerir una `Fogata` real para dar el bono de confort -- el salón ya
  da el bono por sí mismo, una Fogata real (si alguien la enciende ahí)
  se sumaría encima sin ningún caso especial (mismo comportamiento
  aditivo que ya combina refugio+fogata hoy).

## Testing

- `almacen_cercano(..., tipo="salon_comun")`: encuentra un salón común
  real y no un almacén en la misma búsqueda; sin pasar `tipo`,
  comportamiento IDÉNTICO al actual (regresión de los dos consumidores
  existentes).
- `objetivo_construccion_actual`: con refugio y almacén ya completos,
  devuelve `("salon_comun", ...)` si no existe o no está completo;
  `None` si el salón común ya está completo (nada más que construir).
- `hay_construccion_de_tipo_en`/`hay_refugio_en`: `hay_refugio_en` sigue
  devolviendo exactamente lo mismo que antes (regresión).
- `_calcular_socializar`: con un salón común completado en el
  asentamiento, camina hacia él en vez de hacia un conspecífico más
  cercano puesto deliberadamente en otra dirección; sin salón común (o
  sin asentamiento), comportamiento IDÉNTICO al actual; ya en contacto
  real con alguien, resuelve afinidad exactamente igual que hoy sin
  mirar el salón común en absoluto.
- Los dos bonos: se aplican a cualquiera en la celda del salón común
  completado, con el mismo tope de 1.0 en seguridad; un salón a medio
  construir (sin `completado_alguna_vez`) no da ningún bono.
- **Verificación obligatoria contra `BOSQUE_AUTO_TICKS`, no opcional**:
  medir cuántos salones comunes reales se construyen, y si el
  contacto/afinidad de `SOCIALIZAR` sube de verdad frente a lo medido
  antes de esta pieza (ver CLAUDE.md, cifras de "socializar contactos
  resueltos" de corridas anteriores) -- reportar con honestidad si el
  efecto es bajo o nulo, sin inflar el resultado.

## Pendiente real tras esta pieza

- `masa_minima_salon_comun`, `huella_m2_salon_comun`,
  `bono_confort_salon_comun`, `bono_seguridad_salon_comun`
  PROVISIONALES, sin calibrar contra el harness completo.
- Cocinas (comida elaborada, aparcado desde el arco de fuego) y
  edificio de liderazgo (efecto mecánico todavía sin definir) son los
  siguientes círculos reales del arco, sin diseñar.
- Si el salón común nunca llega a completarse en juego libre (candidato
  real: refugio+almacén ya consumen buena parte de la capacidad
  reproductiva/tiempo de un asentamiento, mismo patrón ya visto con
  otras piezas "correctas pero raras" de este proyecto), medirlo con
  honestidad antes de dar la pieza por buena.
