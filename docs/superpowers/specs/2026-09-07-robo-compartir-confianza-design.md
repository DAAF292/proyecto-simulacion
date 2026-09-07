# Robo + compartir por confianza — círculos 2, 3 y 4 del arco
# "robo / intercambio de recursos" — diseño

Fecha: 2026-09-07. Cierra el arco abierto el mismo día (círculo 1:
provisiones de alimento, ya mergeado). Diego pidió implementar el resto
directamente después de confirmar el diseño en conversación (incluida
una pregunta directa sobre el enfoque de "trueque", respondida:
compartir por confianza unidireccional, no un trueque bidireccional
real — menos superficie de diseño, sin curvas nuevas que inventar para
equilibrar un intercambio).

## Decisiones cerradas con Diego

- **Trueque real descartado por ahora**: modelar "qué necesita cada uno
  a cambio de qué" exigiría una noción de utilidad marginal por
  individuo que el motor no tiene hoy. Sustituido por **compartir por
  confianza**: unidireccional, sin nada a cambio, mismo patrón que
  `disposicion_a_aportar` (almacén comunal) pero entre dos individuos.
- **Alcance de recurso: solo `Inventario.provisiones`** (comida), no
  `contenidos` (materiales de construcción) -- mismo alcance que el
  círculo 1, coherente, sin abrir una segunda fuente de complejidad.
- **Robo reutiliza el resolutor de conflicto ya existente**
  (`nucleo/conflicto.py:resolver_disputa`, vía el wrapper compartido
  `sistema_movimiento.py:_resolver_conflicto_entre`) -- el propio
  wrapper ya devuelve el `ResultadoDisputa` con un comentario explícito
  ("por si un disparador futuro lo necesita") escrito pensando en
  exactamente esto. Mismo grupo/familia → `COMPARTE` automático (nadie
  roba a los suyos, sin lógica nueva).
- **Compartir por confianza NO pasa por el resolutor de conflicto** --
  no es una disputa, es cooperación. No hay ganador/perdedor, no drena
  seguridad, no genera rencor.
- **Ninguno de los dos modifica `Relaciones`** -- leen afinidad para
  decidir, no escriben como consecuencia. Evita una fuente más de
  complejidad no pedida; candidato de extensión futura si hace falta.

## Alcance

**Dentro:**

1. `nucleo/intercambio.py` (nuevo): `transferir_recurso(origen, destino,
   recurso, cantidad_max, espacio_destino_max) -> float`. Función pura,
   neutra sobre el motivo de la transferencia -- mismo espíritu que
   `resolver_disputa` no sabe qué se disputa.
2. `sistemas/sistema_movimiento.py:_resolver_conflicto_entre` gana DOS
   parámetros opcionales, `urgencia_a: float | None = None` y
   `urgencia_b: float | None = None` -- si no se pasan, comportamiento
   IDÉNTICO al actual (calculados desde déficit de seguridad); si se
   pasan, los sustituyen. Los tres consumidores actuales (refugio
   ocupado, roce social, CRISIS_VIOLENTA) no cambian ni una línea.
3. `sistemas/sistema_movimiento.py:_procesar_robo` (nuevo), mismo
   molde que `_procesar_roce_social`: recorre `por_celda` (ya
   construido, compartido), por cada par de conscientes en la misma
   celda comprueba en un orden fijo (a robando a b, si no aplica b
   robando a a -- un único intento por par y tick, mismo criterio de
   dedup que ya impone `_pares_conflicto_resueltos_este_tick`):
   - Candidato a "ladrón": `Necesidades.saciedad < umbral_saciedad_para_robar`
     Y su propio `Inventario.provisiones` está vacío (si ya tiene algo
     guardado, se come lo suyo, no roba).
   - Candidato a "víctima": `Inventario.provisiones` no vacío.
   - Si ambas condiciones se cumplen, sortea intento con
     `probabilidad_base_robo * (1.0 - saciedad_ladron)` -- cuanto más
     hambriento, más probable que lo intente.
   - Si dispara: llama a `_resolver_conflicto_entre(..., urgencia_a=1.0
     - saciedad_ladron)` (urgencia propia del hambre, no del déficit de
     seguridad genérico) pasando al ladrón como el lado cuya urgencia se
     sobreescribe. Si el resultado implica que el ladrón se impone
     (cede la víctima), usa `transferir_recurso` para llevarse TODO lo
     que la víctima tenga del primer recurso no vacío (topado por el
     espacio de provisiones del ladrón). Drenaje de seguridad + rencor
     en el perdedor ya vienen gratis del wrapper compartido.
4. `sistemas/sistema_movimiento.py:_procesar_compartir_confianza`
   (nuevo), mismo molde de recorrido que `_procesar_robo` pero SIN
   pasar por `_resolver_conflicto_entre`:
   - Candidato a "donante": `Inventario.provisiones` no vacío, y su
     afinidad HACIA el receptor (`Relaciones.vinculos`, unidireccional
     -- no exige reciprocidad) supera `umbral_confianza_compartir`.
   - Candidato a "receptor": `Necesidades.saciedad <
     saciedad_maxima_para_recibir_compartido` (le falta comida de
     verdad, no se regala a quien ya está bien).
   - Si ambas condiciones se cumplen, sortea con
     `probabilidad_base_compartir_confianza` (constante, sin modular
     por urgencia -- es una decisión de carácter, no de necesidad
     propia).
   - Si dispara: `transferir_recurso` mueve TODO lo que el donante tenga
     del primer recurso no vacío, topado por el espacio del receptor.
     Sin ningún efecto sobre seguridad, rencor, ni Relaciones.
5. Config nueva:
   - `config/comportamiento.yaml`, sección `conflicto:` (junto a
     `probabilidad_base_roce_social`): `umbral_saciedad_para_robar: 0.3`,
     `probabilidad_base_robo: 0.05` -- PROVISIONALES.
   - `config/relaciones.yaml`: `umbral_confianza_compartir: 0.3`,
     `probabilidad_base_compartir_confianza: 0.05`,
     `saciedad_maxima_para_recibir_compartido: 0.5` -- PROVISIONALES.
     De paso, corrige el comentario de cabecera del fichero ("Nadie LEE
     Relaciones para cambiar comportamiento todavía") -- ya desactualizado
     desde pareja estable (círculo 4b, 2026-09-04); compartir por
     confianza es el segundo consumidor real, no el primero.
6. Tests dirigidos + verificación obligatoria contra el motor real.

**Fuera de alcance, explícito:**

- Trueque bidireccional real -- descartado por Diego en esta ronda, no
  aplazado con intención de retomarlo pronto.
- Robo/compartir de `Inventario.contenidos` (materiales de
  construcción) -- solo `provisiones`.
- Cualquier escritura sobre `Relaciones` como consecuencia de estos dos
  mecanismos.
- Memoria de agravios con nombre propio por haber sido robado --
  conecta con lo que `Temperamento.empatia`/`lealtad` ya señalan como
  pendiente, no resuelto aquí (el rencor genérico ya aplicado por
  `_resolver_conflicto_entre` cubre el caso de forma indirecta, vía el
  mismo mecanismo que refugio ocupado/conflicto verbal).

## Testing

- `transferir_recurso`: mueve la cantidad correcta, topada por
  disponibilidad y espacio; purga la clave de origen al vaciarse;
  devuelve 0.0 sin mutar nada si no hay nada que mover.
- `_resolver_conflicto_entre` con `urgencia_a`/`urgencia_b` explícitos:
  sustituye el cálculo por defecto; sin pasarlos, comportamiento idéntico
  al actual (regresión de los tres consumidores existentes).
- Robo: ladrón hambriento sin provisiones propias que gana la disputa
  se lleva las provisiones de la víctima; si pierde, no se lleva nada
  (pero sí paga el coste de seguridad ya existente); mismo
  grupo/familia nunca roba (cae en COMPARTE); víctima sin nada guardado
  nunca dispara el intento.
- Compartir por confianza: donante con afinidad suficiente y provisiones
  reales comparte con un receptor hambriento; sin afinidad suficiente,
  o receptor ya saciado, o donante sin nada guardado, no comparte nada;
  no muta `Relaciones` ni `Necesidades.seguridad`.
- **Verificación obligatoria contra `BOSQUE_AUTO_TICKS`, no opcional**:
  medir cuántos robos y cuántos repartos por confianza ocurren de
  verdad en juego libre. El círculo 1 (provisiones) ya midió una
  frecuencia baja de consumo real (6 en 3000 ticks) -- reportar con
  honestidad si eso limita también la frecuencia de estos dos
  mecanismos nuevos, sin inflar el resultado.

## Pendiente real tras esta pieza

- Las cinco constantes nuevas PROVISIONALES, sin calibrar contra el
  harness completo.
- Si la frecuencia real resulta muy baja (candidato ya señalado en el
  círculo 1: pocas provisiones circulando limita cuánto hay para robar
  o compartir), revisar el umbral de entrada de provisiones antes que
  estos dos mecanismos nuevos -- la causa más probable estaría aguas
  arriba, no aquí.
- Trueque bidireccional real, memoria de agravios por robo, y extender
  el alcance a materiales de construcción quedan como extensiones
  futuras explícitamente no perseguidas ahora.
