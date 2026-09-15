# Conocimiento colectivo transmisible — fusión de dos arcos

Fecha: 2026-09-15
Fusiona: Pieza 3 del roadmap "asentamientos/profesiones" (2026-09-12,
"conocimiento como componente propio, transmisible y mejorable, no solo
un stat que muere con el individuo") + Piezas 2 y 3 del informe
"asentamiento como entidad propia" (2026-09-15, "necesidades/capacidades
colectivas agregadas" + "efecto de vuelta hacia los miembros").

## Motivación

El 2026-09-12, al plantear el roadmap de asentamientos/profesiones,
"conocimiento como componente propio" quedó aparcado sin spec porque
`Asentamiento` no tenía identidad estable entre recálculos diarios —
cualquier valor acumulado se habría perdido en cuanto el id cambiara.
La Pieza 1 de hoy (identidad persistente, `Asentamiento.id` estable vía
`resolver_identidades_persistentes`) es exactamente el prerrequisito que
faltaba. Este círculo lo cierra: un valor agregado que vive en el
asentamiento (no en el individuo), alimentado por el trabajo real de sus
miembros, que sobrevive a la muerte de cualquiera de ellos, y que
repercute de vuelta en la producción del pueblo.

## Diseño

### Qué es "conocimiento" mecánicamente

Cuatro cubetas, las mismas ya existentes de `nucleo/vocacion.py:CUBETAS`
("forrajero", "constructor", "artesano", "cocinero") — sin catálogo
nuevo. Por cada una, un valor bruto acumulado (mismas unidades que
`Vocacion.conteo_X`: ticks de trabajo real) que vive en
`Mundo.asentamiento_conocimiento: dict[int, dict[str, float]]`
(llave externa = `Asentamiento.id`), persistido igual que
`asentamiento_registro_identidad`/`asentamiento_tick_fundacion` (tabla
genérica `configuracion_ejecucion`, sin bump de esquema).

### Acumulación (ley neutra, sin autoría de sucesos)

Cada tick que un individuo consciente despacha una de las 4 acciones
vocacionales (mismo punto donde ya se incrementa `Vocacion`, en
`SistemaRecursos._incrementar_vocacion`), SI pertenece a un asentamiento
(`nucleo.asentamiento.asentamiento_de`, ya existente desde Pieza 1) se
suma +1.0 a la cuenta bruta de esa cubeta en el asentamiento — reutiliza
exactamente el mismo evento que ya dispara el contador individual, sin
ningún disparador nuevo. Topado a `escala_saturacion_conocimiento`
(mismo valor que el divisor de la conversión a nivel [0,1], ver abajo,
así que el nivel nunca supera 1.0).

Crucial: esto vive en `Mundo`, no en el individuo — si el individuo
muere, lo ya aportado a su pueblo se queda ahí. Es "transmisible" en el
sentido más simple posible: no hace falta ningún mecanismo de contacto
persona-a-persona (a diferencia de memoria compartida/rumor social),
porque nunca fue propiedad de una persona en primer lugar.

### Erosión diaria (mismo patrón que Relaciones, mucho más lenta)

Cadencia diaria, en `SistemaAsentamiento.ejecutar()`: cada categoría de
cada asentamiento decae multiplicativamente
(`tasa_erosion_conocimiento_dia`, PROVISIONAL 0.005 — 4x más lento que
`relaciones.tasa_decaimiento_dia_afinidad`=0.02, porque el oficio de un
pueblo no se olvida a la misma velocidad que un vínculo emocional
individual). Entradas que caen por debajo de un umbral mínimo se
purgan, mismo criterio que `_decaer_relaciones`.

### Nivel [0,1] y efecto de vuelta

`nivel = min(1.0, bruto / escala_saturacion_conocimiento)` — saturación
lineal simple, PROVISIONAL, sin curva más sofisticada (círculo pequeño).
`factor_conocimiento_colectivo(nivel, peso) = 1.0 + peso * nivel` —
**sin penalización por debajo de 1.0**: un asentamiento recién fundado
(nivel=0) no es peor que un individuo disperso sin asentamiento
(factor=1.0 en ambos casos), solo un pueblo con práctica acumulada real
produce más rápido. Distinto a propósito de `factor_aptitud` (que sí
penaliza por debajo de 1.0 porque una aptitud baja es una desventaja
racial real, sorteada al nacer) — aquí no hay ninguna desventaja
narrable para un pueblo joven, solo ausencia de bonus todavía.

Aplicado como multiplicador de TASA (no de utilidad — el conocimiento
colectivo no decide SI alguien trabaja, decide cuán rápido produce el
pueblo cuando ya se trabaja), en los tres puntos donde ya existe un
bono equivalente por herramienta:

- RECOLECTAR (cubeta "forrajero"): `tasa_recoleccion_efectiva`.
- CONSTRUIR (cubeta "constructor"): `tasa_aporte_efectiva` y
  `tasa_mejora_refugio` (mejora de vivienda, Pieza D de comodidad).
- COCINAR (cubeta "cocinero"): `tasa_cocinar_kg_tick`.

**Deliberadamente sin efecto para "artesano" en este círculo**: FABRICAR
es determinista/instantáneo (no tiene ninguna tasa continua que acelerar
— se resuelve de golpe si hay receta completable), así que no hay ningún
consumidor de tasa donde aplicar el bono. La cubeta "artesano" acumula y
se puede consultar igual que las otras tres, pero sin ningún efecto de
comportamiento todavía — hueco honesto, no un error, documentado como
pendiente explícito (candidato real para cuando exista "tipos de
construcción nuevos", que podría gatear recetas por nivel de
conocimiento artesano del pueblo).

### Config nueva (`config/comportamiento.yaml`, sección `asentamiento`)

```yaml
tasa_erosion_conocimiento_dia: 0.005
escala_saturacion_conocimiento: 2000.0
peso_conocimiento_colectivo: 0.3
```

Todas PROVISIONALES, sin calibrar contra el harness completo.

## Fuera de alcance de este círculo

- Tipos de construcción nuevos (Pieza 4 del roadmap de profesiones) —
  círculo siguiente, consumidor de esto.
- Interacción entre asentamientos (Pieza 4 del informe de hoy) —
  círculo independiente, sin dependencia de código de este.
- Cualquier forma de "compartir conocimiento entre dos asentamientos" —
  no pedido, no se autora.
- Niveles de construcción categóricos con nombre (cabaña/casa) — sigue
  siendo la pregunta abierta señalada en la conversación de fusión de
  arcos, sin decidir.

## Verificación esperada

- Tests dirigidos de las funciones puras (`nucleo/conocimiento.py`):
  acumulación con techo, erosión multiplicativa con purga, nivel [0,1],
  factor sin penalización por debajo de 1.0.
- Integración real: dos miembros conscientes del mismo asentamiento
  despachando RECOLECTAR suben el conocimiento colectivo del pueblo;
  un individuo sin asentamiento no aporta a nada; el bono de tasa se
  mide con una comparación directa (mismo material, con/sin
  conocimiento acumulado).
- `BOSQUE_AUTO_TICKS` y `BOSQUE_CONTINUAR` sin excepciones, roundtrip de
  persistencia del nuevo estado.
