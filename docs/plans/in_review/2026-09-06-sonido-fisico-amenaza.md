# Plan: Sonido físico — infraestructura y detección temprana de amenaza (4a)

## Fuente de verdad
`docs/superpowers/specs/2026-09-06-sonido-fisico-amenaza-design.md` (leída
completa). No se implementa el círculo 4b (pista de caza), ni reputación,
ni decaimiento gradual, ni sonido desde acciones no violentas.

## Ficheros a tocar (en este orden)

1. `nucleo/celda.py`
   - Dos campos nuevos al final de `Celda` (mismo patrón que `en_llamas`):
     `sonido_tick_emitido: int = -1` (sentinel "nunca") y
     `sonido_magnitud: float = 0.0`. Sin migración de esquema: son estado
     efímero, no se persisten; los defaults ya son los correctos al cargar.

2. `nucleo/sonido.py` (NUEVO módulo, genérico)
   - `emitir_sonido(celda, tick_actual, magnitud)` — sobrescribe.
   - `_sonido_activo(celda, tick_actual, duracion_ticks)` — ventana binaria.
   - `_radio_audible(magnitud, agudeza_sensorial, config)` — escala lineal
     con `radios_sonido_base * (magnitud / peso_referencia_sonido) *
     (0.5 + 0.5*agudeza_sensorial)`.
   - `sonido_mas_cercano(zona, pos_x, pos_y, radio_busqueda_maxima,
     tick_actual, agudeza_sensorial, config)` — patrón del pseudocódigo de
     la spec. Devuelve `tuple[int,int] | None`.
   - Contador de observación `SONIDOS_EMITIDOS_TOTALES` para la
     verificación `BOSQUE_AUTO_TICKS` (solo observación).

3. `config/combate.yaml`
   - Sección nueva `sonido:` al final (PROVISIONAL):
     `radio_sonido_base: 3`, `peso_referencia_sonido: 90.0`,
     `duracion_sonido_ticks: 5`, `radio_busqueda_maxima_sonido: 12`.
     NO reutiliza `peso_referencia_deteccion_plena`.

4. `nucleo/amenaza.py`
   - `posicion_amenaza_mas_cercana` gana parámetros opcionales
     `tick_actual=0, agudeza_sensorial=0.0, radio_busqueda_sonido=0,
     config=None` (default sin efecto, backward-compatible).
   - Añade candidato por sonido (`sonido_mas_cercano(...)`) cuando
     `radio_busqueda_sonido > 0 and config is not None`.
   - Combina los TRES candidatos por distancia Manhattan; desempate:
     criatura > ambiental/sonido (sonido se trata como ambiental).
   - Contador de observación `AMENAZAS_POR_SONIDO` para `BOSQUE_AUTO_TICKS`
     (se incrementa cuando el candidato devuelto ES el de sonido).

5. `sistemas/sistema_depredacion.py`
   - `ejecutar(self, gestor, mundo, reloj, bus_eventos)` — firma ampliada.
   - `_resolver_ataque(...)` gana `mundo` y `tick_actual`; en TODO intento
     de ataque (éxito o fallo) emite sonido en la celda del encuentro con
     magnitud `dims_cazador.peso + dims_presa.peso`.

6. `sistemas/sistema_movimiento.py`
   - `_resolver_conflicto_entre(...)` gana `pos_x, pos_y, zona_idx`; en la
     rama `ENFRENTAMIENTO` emite sonido con la celda del encuentro y la suma
     de pesos de ambas partes (obtener `DimensionesFisicas`).
   - Actualizar sus 3 call sites (`_resolver_posible_intruso`,
     `_procesar_roce_social`, `_calcular_crisis_violenta`) pasando la
     posición de contacto (los tres ya la conocen en su scope).
   - `_calcular_huida` gana `tick_actual` y `agudeza_sensorial` y pasa los
     parámetros nuevos a `posicion_amenaza_mas_cercana`.
   - Cachear `self.radio_busqueda_maxima_sonido` en `__init__`.

7. `sistemas/sistema_necesidades.py`
   - Call site de `posicion_amenaza_mas_cercana` pasa `tick_actual`,
     `dims.agudeza_sensorial`, `self.radio_busqueda_maxima_sonido`,
     `self.config`.
   - Cachear `self.radio_busqueda_maxima_sonido` en `_cachear_configuracion`.

8. `sistemas/sistema_decision.py`
   - Call site de `posicion_amenaza_mas_cercana` en `actualizar()` pasa
     `tick_actual`, `dims.agudeza_sensorial`, el radio cacheado en
     `SistemaDecision` (o fallback a config si `sistema_decision` es None)
     y `config`.

9. `main.py`
   - Actualizar `sistemas["depredacion"].ejecutar(gestor, mundo, reloj,
     bus_eventos)`.
   - Bloque `BOSQUE_AUTO_TICKS`: reportar `SONIDOS_EMITIDOS_TOTALES` y
     `AMENAZAS_POR_SONIDO`.

10. `tests/test_sonido_fisico_amenaza.py` (NUEVO)
    - Tests de `emitir_sonido`/`_sonido_activo`/`_radio_audible`/
      `sonido_mas_cercano`.
    - Depredación emite sonido en la celda correcta con magnitud correcta
      (éxito y fallo).
    - `ENFRENTAMIENTO` emite sonido; CEDE_A/CEDE_B/COMPARTE no emiten nada.
    - Amenaza: sonido reciente y fuerte devuelto como amenaza sin criatura
      visible; sin sonido activo comportamiento idéntico a antes.

11. `tests/test_especie_caballo.py`
    - Actualizar la única llamada directa a `_resolver_ataque` (pasa
      `mundo` y `tick_actual`).

## Verificación
- `pytest tests/test_sonido_fisico_amenaza.py -v` (y el resto de tests
  tocados) durante desarrollo.
- Suite completa una vez al final.
- `BOSQUE_AUTO_TICKS` con población real: medir `SONIDOS_EMITIDOS_TOTALES`
  y `AMENAZAS_POR_SONIDO`; reportar en el commit final con honestidad.
