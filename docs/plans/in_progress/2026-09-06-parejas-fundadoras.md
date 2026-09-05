# Encargo: parejas fundadoras en la siembra de población inicial

**Spec completa**: `docs/superpowers/specs/2026-09-06-parejas-fundadoras-design.md`
-- léela entera antes de diseñar tu plan de implementación, contiene el
diagnóstico, el diseño exacto de los dos cambios (firma nueva de
`crear_criatura`, reestructuración del bucle de `sembrar_poblacion_inicial`)
y el plan de verificación acordado con Diego.

## Qué NO tocar

- No modifiques `sistemas/sistema_reproduccion.py`, `sistemas/sistema_movimiento.py`,
  `sistemas/sistema_necesidades.py` ni ningún otro sistema del motor --
  este círculo es exclusivamente sobre cómo se siembra la población
  fundadora en tick 0 (`nucleo/entidad.py`, `main.py`), nada de las
  reglas que rigen el resto de la partida.
- No toques `techo_fraccion_edad_inicial_longevidad`,
  `factor_base_concepcion` de ninguna especie, ni ninguna tasa de
  `config/fisiologia.yaml` -- ya investigadas hoy por separado, fuera de
  alcance de este círculo.
- No modifiques ninguna aserción de los tests ya existentes en `tests/`.
- No declares `CLAUDE.md` como fichero a modificar.

## Verificación obligatoria, explícita (no opcional)

1. Suite completa de tests en verde (`pytest`).
2. `BOSQUE_AUTO_TICKS=3000` sin intervención, sin ninguna excepción.
3. Comparación dirigida y PEQUEÑA contra el motor real: 5 semillas
   nuevas (no reutilices semillas de ejecuciones anteriores) × 4000
   ticks cada una, sin persistencia SQLite (arnés directo con
   `main.py:cargar_configuracion`/`instanciar_sistemas`/
   `sembrar_poblacion_inicial`/`sembrar_flora_inicial`/`ejecutar_tick`,
   llamando `bus.limpiar()` cada tick), midiendo población final y
   extinción por especie (gnomo, lobo, conejo, ardilla, caballo) CON el
   cambio. No hace falta un lote más grande ni comparar contra un
   baseline aparte para este círculo -- reporta los números tal cual
   salgan como parte de tu resumen final. Si algún resultado es
   ambiguo, dilo explícitamente en vez de forzar una conclusión.

Escribe tu propio plan de implementación real (sobrescribiendo este
fichero, ya movido a `docs/plans/in_progress/`) antes de tocar código,
como siempre.
