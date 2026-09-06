# Encargo: radio de percepción ampliado para búsqueda activa de pareja

**Spec completa**: `docs/superpowers/specs/2026-09-06-radio-busqueda-pareja-design.md`
-- léela entera antes de diseñar tu plan de implementación. Contiene el
diagnóstico completo, el diseño exacto (dos claves de config nuevas,
cálculo de un radio propio solo en la rama `BUSCAR_PAREJA` de
`sistema_movimiento.py`) y el plan de verificación acordado con Diego.

## Qué NO tocar

- No modifiques `nucleo/memoria.py`, `sistemas/sistema_reproduccion.py`,
  ni `_buscar_conspecifico_mas_cercano` (agrupamiento social genérico,
  no búsqueda de pareja reproductiva) -- fuera de alcance a propósito,
  ver la spec.
- No toques `techo_fraccion_edad_inicial_longevidad`,
  `factor_base_concepcion` de ninguna especie, ni nada del mecanismo de
  "parejas fundadoras" (`main.py:sembrar_poblacion_inicial`,
  `nucleo/entidad.py:crear_criatura`) -- círculo previo ya cerrado, sin
  relación con este cambio.
- No cambies el radio genérico (`radio_minimo_celdas`/
  `radio_maximo_celdas`, ni la variable `radio` ya calculada para el
  resto de acciones en `sistema_movimiento.py:ejecutar`) -- el radio
  nuevo es EXCLUSIVO de la rama `Accion.BUSCAR_PAREJA`.
- No modifiques ninguna aserción de los tests ya existentes en `tests/`.
- No declares `CLAUDE.md` como fichero a modificar.

## Verificación obligatoria, explícita (no opcional)

1. Suite completa de tests en verde (`pytest`).
2. `BOSQUE_AUTO_TICKS=3000` sin intervención, sin ninguna excepción.
3. Comparación dirigida y PEQUEÑA contra el motor real, en DOS
   horizontes de tiempo (no solo uno -- el efecto de la pieza anterior
   de este mismo arco solo se reveló al comparar 4000 contra 6000
   ticks): 5 semillas nuevas (no reutilices semillas de ejecuciones
   anteriores) × 4000 ticks, Y las MISMAS 5 semillas × 6000 ticks. Sin
   persistencia SQLite (arnés directo con
   `main.py:cargar_configuracion`/`instanciar_sistemas`/
   `sembrar_poblacion_inicial`/`sembrar_flora_inicial`/`ejecutar_tick`,
   llamando `bus.limpiar()` cada tick, con un tope de seguridad de
   población de ~800-1000 individuos para evitar corridas
   descontroladamente lentas -- lección real de la investigación previa
   de este mismo arco). Mide población final y extinción por especie
   (gnomo, lobo, conejo, ardilla, caballo) en ambos horizontes.
4. Compara explícitamente tus resultados de gnomo y ardilla a 6000
   ticks contra la cifra YA CONOCIDA sin este cambio: 100% de extinción
   en ambas especies (5/5 semillas). Reporta si el radio ampliado cierra
   esa brecha, la reduce parcialmente, o no tiene efecto -- sé honesto
   si el resultado es ambiguo o parcial, no fuerces una conclusión de
   éxito.

Escribe tu propio plan de implementación real (sobrescribiendo este
fichero, ya movido a `docs/plans/in_progress/`) antes de tocar código,
como siempre.
