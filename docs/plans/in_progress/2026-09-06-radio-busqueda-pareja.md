# Plan: radio de percepción ampliado para búsqueda activa de pareja

## Objetivo

Aplicar el diseño de `docs/superpowers/specs/2026-09-06-radio-busqueda-pareja-design.md`
(2º círculo del arco de estabilidad de población): dar a `Accion.BUSCAR_PAREJA`
un radio de percepción PROPIO, mayor que el genérico de comida/agua/amenaza, para
que las generaciones posteriores a la fundadora puedan detectar y alcanzar una
pareja a tiempo (brecha conocida: gnomo y ardilla al 100% de extinción a 6000
ticks sin este cambio, aun con "parejas fundadoras" ya mergeado).

## Ficheros a tocar (solo 2, como dice la spec)

### 1. `config/comportamiento.yaml` — sección `percepcion`

Añadir dos claves nuevas con el mismo patrón que las existentes:

```yaml
percepcion:
  radio_minimo_celdas: 0        # existente, sin cambios
  radio_maximo_celdas: 4        # existente, sin cambios
  radio_minimo_pareja_celdas: 3   # NUEVO, PROVISIONAL
  radio_maximo_pareja_celdas: 12  # NUEVO, PROVISIONAL
```

No se toca nada más de este fichero ni de ningún otro `config/*.yaml`.

### 2. `sistemas/sistema_movimiento.py`

Dos cambios, exactamente en los puntos que indica la spec:

a) En `_cachear_configuracion()` (donde ya se cachean `self.radio_min` /
   `self.radio_max` desde `cfg_per`), añadir:

```python
self.radio_min_pareja: int = int(cfg_per.get("radio_minimo_pareja_celdas", 3))
self.radio_max_pareja: int = int(cfg_per.get("radio_maximo_pareja_celdas", 12))
```

b) En `ejecutar()`, dentro de la rama `elif accion == Accion.BUSCAR_PAREJA:`
   (hoy reutiliza la variable genérica `radio`), calcular un radio propio
   y pasarlo a `_calcular_pareja`:

```python
elif accion == Accion.BUSCAR_PAREJA:
    radio_pareja = radio_individual(
        dims.agudeza_sensorial, self.radio_min_pareja, self.radio_max_pareja
    )
    dx, dy = self._calcular_pareja(
        gestor, eid, ident.especie, pos.x, pos.y, radio_pareja, pos.zona_idx
    )
```

Ningún otro cambio en `_calcular_pareja` (ya acepta `radio` por parámetro),
ni en ninguna otra rama de acción. El radio genérico `radio` se sigue
calculando y usando igual para COMER/BEBER/CAZAR/HUIR/DEAMBULAR/etc.

## Fuera de alcance (NO tocar)

- `nucleo/memoria.py`, `sistemas/sistema_reproduccion.py`,
  `_buscar_conspecifico_mas_cercano`, `techo_fraccion_edad_inicial_longevidad`,
  `factor_base_concepcion`, mecánica de parejas fundadoras
  (`main.py:sembrar_poblacion_inicial`, `nucleo/entidad.py:crear_criatura`).
- Tests existentes (sin modificar aserciones). No se declara `CLAUDE.md`.

## Orden de trabajo y verificación

1. Escribir este plan y commit `plan: ...` (obligatorio antes de código).
2. Aplicar los 2 cambios de código (config + sistema_movimiento).
3. Verificación:
   a. Suite completa `pytest` en verde.
   b. `BOSQUE_AUTO_TICKS=3000` sin intervención, sin excepciones.
   c. Arnés directo sin SQLite: `cargar_configuracion`/`instanciar_sistemas`/
      `sembrar_poblacion_inicial`/`sembrar_flora_inicial`/`ejecutar_tick`,
      `bus.limpiar()` cada tick, tope de seguridad ~800-1000 individuos.
      - 5 semillas NUEVAS × 4000 ticks (población final + extinción por especie).
      - LAS MISMAS 5 semillas × 6000 ticks.
   d. Comparar gnomo/ardilla a 6000 ticks contra la cifra ya conocida sin el
      cambio (100% de extinción en ambas, 5/5 semillas). Reportar si el radio
      ampliado cierra, reduce parcialmente o no afecta. Ser honesto si el
      resultado es ambiguo o parcial.
4. Commit final de código y resumen.
