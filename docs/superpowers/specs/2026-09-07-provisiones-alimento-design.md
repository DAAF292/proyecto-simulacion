# Provisiones de alimento — almacenamiento personal con caducidad — diseño

Fecha: 2026-09-07. Círculo 1 del arco "robo / intercambio de recursos"
que Diego quiere abrir a continuación — pero esta pieza es
independiente y se cierra sola: ningún consciente guarda comida hoy, y
sin nada que guardar no hay nada que robar ni intercambiar en alimento.
Los círculos siguientes de ese arco (primitivo genérico de
transferencia entre individuos, robo vía `nucleo/conflicto.py`, trueque
vía `Relaciones`) se diseñan por separado, cada uno su propio spec.

## Motivación

Diego, verificando el estado real del motor: "ahora los seres
conscientes... no almacenan alimentos para comer después". Confirmado
contra el código antes de proponer nada: `Accion.RECOLECTAR` solo mete
en `Inventario.contenidos` materiales `apto_construccion`
(`sistemas/sistema_recursos.py:_resolver_recolectar`), nunca alimento;
`Accion.COMER` siempre resuelve in situ, directo de `Celda.recursos` a
`Necesidades.saciedad`
(`sistemas/sistema_recursos.py:_resolver_comer`). No existe ningún
camino para que un consciente cargue comida y la coma más tarde.

## Decisiones cerradas con Diego, en orden

1. **Es primario/innato, no una decisión calculada**: gateado al mismo
   umbral binario de consciencia que ya usan `RECOLECTAR`/`CONSTRUIR`
   (`decision.umbral_consciencia_agencia`) -- sin atarlo a ningún
   atributo variable como `inteligencia`. Cualquier consciente lo hace
   igual; ninguno es "más previsor" que otro. Ley neutra, no una
   habilidad graduada.
2. **Caducidad real**: la comida guardada se degrada con el tiempo,
   mismo patrón que `Necromasa`/`Construccion`
   (`sistema_descomposicion.py`, cadencia diaria) -- sin esto, guardar
   comida sería estrictamente mejor que comer al momento, rompiendo
   cualquier equilibrio.
3. **Corrección real tras la primera propuesta**: la primera versión
   proponía reutilizar `Inventario.contenidos` (la misma bolsa que ya
   usan los materiales de construcción). Diego lo rechazó con razón:
   *"si luego quieren construir que hacen? tiran la comida? o al revés
   si tienen el inventario lleno de materiales no pueden guardar
   comida?"* -- compartir capacidad entre "reserva de supervivencia" y
   "carga de trabajo para un proyecto de construcción" crea un
   conflicto artificial sin resolución natural. Corregido: **provisiones
   vive en su propio campo, con su propia capacidad, pequeña y
   totalmente independiente** de la capacidad de carga general -- nunca
   compite con materiales de construcción ni con objetos discretos
   (`Agarre`/`Inventario.objetos`).
4. **No es "todo lo que quepa"**: la capacidad de provisiones es
   deliberadamente pequeña (una fracción menor del peso propio que la
   capacidad de carga general) -- una reserva de supervivencia de unos
   pocos días, no un almacén personal.
5. **Riesgo aceptado explícitamente**: el disparador de guardar
   excedente solo se evalúa cuando la Utility AI ya eligió `COMER` (por
   hambre real) y de paso cruza un umbral de saciedad alta con comida
   sobrante en la celda -- ventana más estrecha que "siempre que esté
   lleno guarda algo", a propósito para no inventar una Accion/curva de
   utilidad nueva sin necesidad. Se mide la frecuencia real de disparo
   contra el motor, se reporta con honestidad si resulta rara (mismo
   criterio que el resto del proyecto ante piezas "correctas pero
   invisibles").

## Alcance

**Dentro:**

1. `componentes/inventario.py`: `Inventario` gana `provisiones:
   dict[str, float] = field(default_factory=dict)` -- mismo molde que
   `contenidos` (clave→kg), pero espacio de nombres y capacidad
   totalmente separados. Docstring actualizado: `contenidos` sigue
   documentado como catálogo de `materiales.yaml` (construcción)
   exclusivamente; `provisiones` es el único lugar donde vive comida
   guardada, catálogo `flora.yaml` (categoría `alimento`).
2. `nucleo/inventario.py`: dos funciones nuevas, mismo molde que las ya
   existentes:
   ```python
   def capacidad_provisiones_kg(peso_propio: float, fraccion_provisiones_maxima: float) -> float:
       return max(0.0, peso_propio) * max(0.0, fraccion_provisiones_maxima)

   def espacio_disponible_provisiones_kg(
       provisiones: dict[str, float], peso_propio: float, fraccion_provisiones_maxima: float,
   ) -> float:
       return max(
           0.0,
           capacidad_provisiones_kg(peso_propio, fraccion_provisiones_maxima)
           - sum(provisiones.values()),
       )
   ```
   Completamente independientes de `capacidad_carga_kg`/
   `espacio_disponible_kg` -- ninguna de las dos familias de función se
   toca ni se llama entre sí.
3. `config/fisiologia.yaml`, sección `inventario` (junto a
   `fraccion_carga_maxima: 0.25` ya existente):
   ```yaml
   fraccion_provisiones_maxima: 0.05  # PROVISIONAL -- "un par de dias de
     # raciones", deliberadamente mucho menor que fraccion_carga_maxima
     # para que nunca sea "todo lo que quepa"
   ```
   Y en `necesidades.defecto` (junto a los demás umbrales):
   ```yaml
   saciedad_minima_para_guardar_provisiones: 0.9  # PROVISIONAL
   ```
   `tasa_consumo_comer` (ya existente) se reutiliza tal cual como tope
   de cuánto se guarda por tick -- sin constante nueva para esto.
4. `sistemas/sistema_recursos.py:_resolver_comer`, dos puntos de
   inserción exactos:

   a) **Entrada**, al final de la rama `if recursos_disponibles:` (tras
      actualizar `nec.saciedad`/`nec.hidratacion` y la lógica de
      zoocoria ya existente, sin tocar esa lógica): si la entidad es
      consciente (`cap_mental is not None and cap_mental.consciencia >=
      self.umbral_consciencia_agencia`, mismo patrón que ya usa
      `RECOLECTAR` en este mismo fichero), `nec.saciedad >=
      self.saciedad_minima_para_guardar_provisiones`, y queda cantidad
      del recurso en la celda tras el consumo (`celda.recursos[nombre_rec]
      > 0.0`), calcular espacio disponible con
      `espacio_disponible_provisiones_kg` y guardar
      `min(celda.recursos[nombre_rec], self.tasa_consumo_comer,
      espacio_disponible)` kg más en `Inventario.provisiones[nombre_rec]`,
      decrementando `celda.recursos[nombre_rec]` esa misma cantidad
      (segunda extracción de la celda en el mismo tick, aparte del
      consumo ya hecho -- la celda sigue siendo la única fuente real).
      Necesita obtener `Inventario` del `gestor` dentro de
      `_resolver_comer` (hoy no se pasa como parámetro -- añadirlo al
      método, mismo patrón que `inv` ya se obtiene en la rama
      `RECOLECTAR`/`CONSTRUIR` de `ejecutar()`).

   b) **Salida**, en la rama `else:` (hoy solo purga memoria stale
      cuando la celda no tiene nada de la dieta propia) -- ANTES de la
      purga probabilística: comprobar `Inventario.provisiones` por
      cualquier recurso de `dieta` con cantidad > 0. Si hay, consumir
      `min(cantidad_guardada, self.tasa_consumo_comer)` con el mismo
      `val_nut`/`val_hid` (`self.nutricion_flora`/`self.hidratacion_flora`,
      ya cacheados en el sistema) que usa el camino de celda, actualizar
      `nec.saciedad`/`nec.hidratacion` igual, decrementar
      `Inventario.provisiones[recurso]`, purgar la clave si cae a
      `<= config["descomposicion"]["umbral_purga_masa"]` (reutilizado
      tal cual, sin constante nueva), y `return` -- **sin purgar memoria
      ni disparar zoocoria** (comer de la propia despensa no es comer en
      el sitio donde crece la planta). Si `Inventario` es `None` o no
      hay nada aprovechable ahí tampoco, caer al comportamiento actual
      (purga probabilística de memoria) sin cambios.
5. `sistemas/sistema_descomposicion.py`: nuevo paso en `ejecutar()`,
   método privado `_descomponer_provisiones(gestor)` -- itera
   `gestor.entidades_con(Inventario)` (sorted, mismo criterio
   determinista que el resto del sistema), y para cada entrada de
   `inv.provisiones` aplica `cantidad *= (1.0 -
   tasa_descomposicion_dia_alimento)`, purgando la clave si el
   resultado es `<= umbral_purga_masa`. Nueva constante en
   `config/flora.yaml`, sección `descomposicion:` (misma sección exacta
   donde ya vive `umbral_purga_masa: 0.05`):
   ```yaml
   tasa_descomposicion_dia_alimento: 0.15  # PROVISIONAL -- una tasa
     # UNIVERSAL para toda comida guardada, no una por recurso (13
     # recursos de alimento en el catalogo hoy; diferenciar
     # manzana-se-pudre-mas-rapido-que-raiz sin ningun dato real seria
     # adivinar, no medir). Revisitable si el motor real muestra una
     # razon concreta para diferenciar.
   ```
   Deliberadamente SIN dependencia de clima/humedad de zona (a
   diferencia de `Necromasa`) -- simplificación consciente para esta
   primera versión, no un descuido.
6. Persistencia (`nucleo/persistencia.py`): `inventario` ya es una
   única columna JSON (`{"contenidos": ..., "objetos": ...}`,
   `componentes_estado.inventario`, fila 46) -- añadir `"provisiones":
   inv.provisiones` al dict que se serializa (línea ~554) y
   `inventario_dict.get("provisiones", {})` (mismo patrón defensivo que
   ya usan `contenidos`/`objetos`) al reconstruir en la carga. Aunque el
   `.get()` defensivo ya tolera partidas guardadas antes de este
   cambio, `VERSION_ESQUEMA` sube igualmente (mismo criterio de
   higiene ya aplicado a cada pieza anterior, no una migración real de
   datos).

**Fuera de alcance, explícito:**

- Cualquier variación de este comportamiento por atributo individual
  (`inteligencia`, `voluntad`...) -- ley binaria única, sin excepción
  (decisión 1 de arriba).
- Robo, trueque, y el primitivo genérico de transferencia entre
  individuos -- círculos siguientes del mismo arco, sin ninguna
  dependencia de código de esta pieza salvo que ahora SÍ habrá algo
  real que transferir.
- Fauna guardando comida (p.ej. ardilla, que en la vida real sí
  acumula frutos secos) -- aplazado, no descartado; esta pieza queda
  gateada a consciente, mismo criterio que el resto del "hilo
  individual".
- Cualquier acción o decisión consciente de "cuándo comer de la
  despensa en vez de buscar comida fresca" -- el fallback solo se activa
  cuando la celda actual ya no tiene nada, nunca por preferencia.
- Calibración de `tasa_descomposicion_dia_alimento` por recurso
  individual, o de cualquier constante nueva contra el harness
  completo.

## Testing

- `capacidad_provisiones_kg`/`espacio_disponible_provisiones_kg`: cálculo
  correcto, independiente de `contenidos`/`objetos` (un inventario lleno
  de materiales de construcción no reduce el espacio de provisiones, y
  viceversa).
- Entrada: un consciente que come hasta cruzar el umbral de saciedad con
  sobra en la celda guarda la cantidad esperada, topada por espacio
  disponible; por debajo del umbral, o sin sobra en la celda, o sin
  espacio, no guarda nada. Una entidad no consciente nunca guarda nada
  aunque cumpla el resto de condiciones.
- Salida: con la celda vacía de comida propia pero con provisiones
  guardadas, come de ahí (saciedad/hidratación suben, provisiones bajan,
  SIN purgar memoria de "comida" para esa celda); si además las
  provisiones están vacías, cae al comportamiento actual (purga
  probabilística) sin cambios.
- Caducidad: `_descomponer_provisiones` reduce cantidades a diario según
  la tasa configurada, purga claves por debajo del umbral, no toca
  `contenidos` ni `objetos`.
- Persistencia: roundtrip guardar/cargar preserva `Inventario.provisiones`
  exacto; una partida guardada ANTES de esta pieza (sin la clave) carga
  con `provisiones` vacío, sin error.
- **Verificación obligatoria contra `BOSQUE_AUTO_TICKS`, no opcional**:
  medir cuántas veces se dispara de verdad la entrada (guardar
  excedente) y la salida (comer de la despensa) en juego libre, y si
  las provisiones llegan a caducar antes de consumirse en algún caso
  real. Reportar con honestidad si la frecuencia es baja -- el disparador
  es deliberadamente estrecho (decisión 5 de arriba), medir sin inflar
  el resultado.

## Pendiente real tras esta pieza

- `fraccion_provisiones_maxima`, `saciedad_minima_para_guardar_provisiones`,
  y `tasa_descomposicion_dia_alimento` PROVISIONALES, sin calibrar contra
  el harness completo.
- Si el disparador (ligado a elegir `COMER`) resulta demasiado raro en
  juego libre, candidato real para una segunda vuelta: bajar el umbral
  de saciedad, o mover la lógica de entrada a su propia evaluación
  dentro de `RECOLECTAR` en vez de depender de `COMER` -- decidir con
  datos reales, no de antemano.
- Fauna con caché instintivo de comida (ardilla en la vida real
  acumula frutos secos) queda como extensión futura obvia, mismo
  cimiento, sin construir aquí.
- Siguientes círculos del arco: primitivo genérico de transferencia,
  robo, trueque -- ninguno diseñado todavía.
