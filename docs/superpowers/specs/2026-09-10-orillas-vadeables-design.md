# Orillas vadeables — acceso real a agua para criaturas pequeñas — diseño

Fecha: 2026-09-10. Arranca de una pregunta de Diego sobre por qué
`tasa_perdida_hidratacion_por_tick`/`probabilidad_muerte_deshidratacion`
se calibran especie por especie sin ninguna relación con
`DimensionesFisicas.peso`/`altura` -- el propio docstring de
`componentes/dimensiones_fisicas.py` ya reconocía el hueco para peso
("el enlace peso -> tasa de saciedad vía metabolismo queda pendiente,
sin construir"). Investigado con Diego en conversación: el eslabón causal
real no está en la tasa de pérdida (tocarla reabriría la investigación de
estabilidad ya cerrada, y en la dirección contraria a lo que el motor
necesitó empíricamente), sino en el ACCESO físico a fuentes de agua --
`profundidad_agua_potable(celda) <= altura` es un umbral binario duro sin
ningún gradiente real aprovechable por una criatura pequeña.

## Motivación, con datos medidos contra el motor real

Arnés de diagnóstico (scratchpad de sesión, no en el repo) sobre 8
semillas nuevas (mundo 40×40):

1. **Agua permanente (río/lago/poza) es casi inaccesible para las
   especies pequeñas del catálogo**: de 632 celdas de agua permanente,
   solo el 5.1-9.5% es vadeable para ardilla (altura 0.15-0.25m) y
   7.6-11.4% para conejo (0.2-0.3m) -- frente a 44.3-49.2% para gnomo y
   54.7-62.2% para caballo. Mediana real de profundidad: 1.263m, muy por
   encima de cualquier altura pequeña del catálogo.
2. **Charcos efímeros mitigan mucho, pero no cierran el hueco**: cuando
   llueve, la cobertura de charco sube al 57-82% de todo el mapa
   (`techo_profundidad_charco=0.03m`, vadeable por cualquiera). Pero hay
   rachas reales de sequía total de 70-190 ticks (~3-8 días) sin un solo
   charco en el mapa -- en esas ventanas, ardilla/conejo dependen
   enteramente de ese 5-11% de agua permanente vadeable.
3. **Vía descartada, medida y no elegida**: curvar el mapeo de
   profundidad ya existente dentro de cada cuenca
   (`nucleo/agua.py:_profundidades_cuenca`, hoy lineal en
   `[0, banda]`) con un exponente >1 mejora la vadeabilidad de forma
   real (9.5%→20.4% con exponente 2.5) pero con techo bajo: incluso con
   exponente 5.0 (mediana global cayendo de 1.26m a 0.96m, un cuerpo de
   agua notablemente menos profundo en general) solo llega a 27-29% --
   la mayoría de celdas de una cuenca caen cerca del mínimo/centro por
   la propia resolución del grid (10m/celda), curvar el mapeo no puede
   inventar celdas de borde que la geometría no produjo. Descartada por
   Diego a favor de la vía siguiente.
4. **Vía elegida, medida antes de diseñarla**: el anillo de celdas de
   tierra firme 4-vecinas de cualquier celda de agua tiene,
   medido en las mismas 8 semillas, **el mismo tamaño que el propio
   cuerpo de agua** (634 celdas de anillo frente a 632 de agua, ratio
   1.00) -- todo cuerpo de agua, grande o pequeño, ya tiene un perímetro
   completo de tierra firme adyacente. Si ese perímetro se vuelve
   vadeable de verdad (la erosión/vado natural que produce cualquier
   cuerpo de agua real), la cobertura para especies pequeñas deja de
   depender de la geometría interna de la cuenca.

## Decisiones cerradas con Diego

- **Física real, no parche de juego**: un cuerpo de agua real tiene
  orilla por el propio desgaste del agua sobre la tierra -- un anillo de
  vado perimetral, no una redistribución de lo que ya hay dentro de la
  cuenca.
- **Capa geográfica independiente, mismo patrón que `profundidad_charco`/
  `deposito_mineral`/`piedra_suelta`**: la celda de orilla sigue siendo
  tierra de verdad -- mismo `tipo_sustrato`, sigue colonizable por flora,
  sigue construible. NO se le asigna `tipo_agua`/`tiene_agua=True` --
  evita reabrir bioma/fertilidad/exclusión de flora-sobre-agua
  (`celdas_con_agua`, fix de 2026-09-02) sin necesidad.
- **Estática, no climática**: se calcula una vez en generación (mismo
  momento que `profundidad_agua`/`tipo_agua`), nunca cambia en marcha --
  a diferencia de `profundidad_charco`, no se persiste (se regenera
  siempre igual desde la semilla, mismo criterio que `profundidad_agua`/
  `tipo_agua` hoy).
- **Ancho fijo: 1 celda** (10m reales) -- el ratio 1:1 ya medido entre
  anillo y cuerpo de agua confirma que sobra para cubrir cualquier
  cuerpo de agua sin necesitar un parámetro de ancho configurable.
- **Profundidad fija, no graduada**: un único valor bajo
  (`profundidad_orilla_metros`, PROVISIONAL 0.1m -- por debajo incluso
  de la altura mínima de ardilla, 0.15m) para toda celda de anillo, sin
  segunda curva. El objetivo es garantizar acceso, no modelar un
  degradado fino.
- **Igual para río, lago y poza** -- mismo mecanismo aplicado sobre el
  resultado ya unificado de `generar_cuerpos_agua`, sin distinción por
  tipo (ley neutra).
- **Solo superficie**: `nucleo/cueva.py` no genera agua permanente
  (confirmado, sin ningún `generar_cuerpos_agua`/`profundidad_agua` en
  ese módulo) -- nada que hacer ahí, no se toca.

## Alcance

**Dentro:**

1. `nucleo/celda.py`: nuevo campo `profundidad_orilla: float = 0.0` en
   `Celda` -- docstring explicando que es capa estática análoga a
   `profundidad_agua` (no climática como `profundidad_charco`), presente
   solo en el anillo perimetral de tierra firme alrededor de un cuerpo de
   agua permanente, sin afectar `tiene_agua`/`tipo_agua`/sustrato/flora.
2. `nucleo/agua.py`, función nueva `generar_orillas_vadeables(cuerpos_agua:
   dict[tuple[int,int], InfoAgua], ancho: int, alto: int,
   profundidad_orilla_metros: float) -> dict[tuple[int,int], float]`:
   para toda celda `(x,y)` con `cuerpos_agua.get((x,y))` vacío/ausente
   que sea 4-vecina (mismo helper `_vecinos` ya existente en el módulo)
   de al menos una celda presente en `cuerpos_agua`, devuelve
   `profundidad_orilla_metros`. Llamada una vez, al final de
   `generar_cuerpos_agua`, sobre el dict ya unificado de río+lago+poza
   (no dentro de cada función individual -- una sola pasada sobre el
   resultado completo).
3. `nucleo/zona_bioma.py:generar_zona_bioma`: recoge el dict devuelto por
   `generar_orillas_vadeables` y lo pasa a cada `Celda(...)` como
   `profundidad_orilla=orillas.get((x, y), 0.0)` (línea ~370, junto a
   `tiene_agua`/`profundidad_agua`) -- sin tocar `celdas_con_agua`
   (línea ~289, sigue siendo solo `info.tipo != ""`, el anillo NO cuenta
   como sumergido para la exclusión de colonización de flora).
4. `nucleo/agua.py`: `hay_agua_potable`/`profundidad_agua_potable`
   extendidas para mirar también `celda.profundidad_orilla`, mismo
   patrón que ya combinan `profundidad_agua`/`profundidad_charco`:
   ```python
   def hay_agua_potable(celda) -> bool:
       return celda.tiene_agua or celda.profundidad_charco > 0.0 or celda.profundidad_orilla > 0.0

   def profundidad_agua_potable(celda) -> float:
       return max(celda.profundidad_agua, celda.profundidad_charco, celda.profundidad_orilla)
   ```
   Como estas dos funciones ya son las que consumen
   `sistema_movimiento.py:_calcular_hidratacion` (búsqueda de destino) y
   la validación de cruce de celda (línea ~550-551), el enganche es
   automático en ambos sitios sin tocar nada más -- una criatura pequeña
   camina hasta la celda de orilla y bebe ahí, sin necesitar entrar en la
   parte honda del cuerpo de agua.
5. Config nueva (PROVISIONAL, sin calibrar): `config/hidrologia.yaml`,
   sección `agua:`, `profundidad_orilla_metros: 0.1`.
6. Tests dirigidos + verificación obligatoria contra el motor real.

**Fuera de alcance, explícito:**

- Curvar `_profundidades_cuenca` (la vía del exponente) -- medida y
  descartada, no se implementa.
- Cuevas/zonas subterráneas -- no generan agua permanente hoy, nada que
  tocar.
- Ancho de anillo configurable o mayor a 1 celda -- el ratio 1:1 ya
  medido no lo justifica.
- Profundidad de orilla graduada/variable por posición -- valor único
  fijo, sin segunda curva.
- Cualquier cambio a `celdas_con_agua`/exclusión de flora-sobre-agua, a
  `tipo_sustrato`/fertilidad, o a construcción sobre la celda de orilla
  -- la celda sigue siendo tierra normal en todo lo demás.
- Persistencia: no se persiste `profundidad_orilla` (se regenera
  siempre igual desde la semilla, mismo criterio que `profundidad_agua`/
  `tipo_agua` hoy, ninguno de los dos se persiste).
- Recalibración de `tasa_perdida_hidratacion_por_tick`/
  `probabilidad_muerte_deshidratacion` por especie -- fuera de esta
  pieza, candidato a revisar en una calibración futura una vez el acceso
  real mejore (podría permitir revertir parte de los alivios ya
  aplicados por especie, pero eso es una investigación aparte, no se
  toca aquí).

## Testing

- `generar_orillas_vadeables`: celda de tierra firme 4-vecina de agua
  recibe `profundidad_orilla_metros`; celda de agua en sí NO recibe
  orilla (ya tiene su propia `profundidad_agua`); celda de tierra firme
  sin ninguna vecina de agua no recibe nada (0.0); celda ya en el dict
  de `cuerpos_agua` (aunque sea 4-vecina de otra celda de agua) no se
  sobrescribe.
- `hay_agua_potable`/`profundidad_agua_potable`: una celda con solo
  `profundidad_orilla>0` (sin agua, sin charco) cuenta como potable, con
  la profundidad correcta; regresión explícita de los casos ya
  existentes (solo `profundidad_agua`, solo `profundidad_charco`, ambos
  a la vez) sin cambio de comportamiento.
- `generar_zona_bioma`: una celda de orilla conserva su `tipo_sustrato`
  original y sigue pudiendo ser colonizada por flora (no aparece en
  `celdas_con_agua`) -- regresión explícita contra el fix de
  flora-sobre-agua del 2026-09-02, confirmando que sigue intacto.
- `_calcular_hidratacion`/validación de movimiento
  (`sistema_movimiento.py`): una criatura con altura menor que
  `profundidad_orilla_metros` (si alguna existiera) seguiría sin poder
  vadear ni la orilla -- el chequeo `<= altura` se mantiene igual, sin
  ningún caso especial para esta capa nueva.
- **Verificación obligatoria contra `BOSQUE_AUTO_TICKS`, no opcional**:
  medir vadeabilidad real de agua para ardilla/conejo antes/después (con
  el mismo arnés de diagnóstico de esta sesión, o uno equivalente) y
  confirmar que se acerca a la cobertura casi total esperada por el
  ratio 1:1 medido; reportar con honestidad si el efecto observado en
  juego real difiere de lo medido en generación pura.

## Pendiente real tras esta pieza

- `profundidad_orilla_metros=0.1` PROVISIONAL, sin calibrar contra el
  harness completo.
- `tasa_perdida_hidratacion_por_tick`/`probabilidad_muerte_deshidratacion`
  por especie (lobo/ardilla/gnomo/conejo, todas ya rebajadas del valor
  universal durante la investigación de estabilidad de población de
  2026-09-05/06/09) quedan sin tocar en esta pieza -- con acceso real
  mejorado, podría haber margen para revisar si esos alivios siguen
  haciendo falta con la misma magnitud, pero eso exige su propia
  investigación A/B contra el motor real, no se asume aquí.
- La vía de "ganancia por bocado escalada por peso" (saciedad, distinta
  del problema de acceso a hidratación) sigue sin diseñar -- quedó
  aparcada en la misma conversación que esta pieza, en favor de resolver
  primero el acceso a agua.
- Ninguna gradación de erosión por caudal/tipo de cuerpo de agua (un río
  de corriente fuerte vs. una poza estancada) -- ley uniforme, sin
  distinguir por tipo, mismo criterio de leyes neutras.
