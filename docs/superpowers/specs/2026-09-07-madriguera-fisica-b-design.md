# Madriguera física (B) — beneficios reales para quien la usa — diseño

Fecha: 2026-09-07. Círculo B de "madriguera física" — segunda mitad,
partida por tamaño tras dos timeouts consecutivos del pipeline sobre
la versión combinada (ver
`docs/superpowers/specs/2026-09-07-madriguera-fisica-a-design.md` para
el contexto completo, la motivación original, y el círculo A ya
diseñado: entidad `Madriguera` real, persistida, con capacidad finita).

**Dependencia dura**: exige que A esté YA MERGEADO — reutiliza
`nucleo/madriguera.py:madriguera_en` tal cual, sin tocarlo.

## Motivación

Diego: un refugio individual no debería tener bonificación (decisión
ya tomada y documentada en `_calcular_dormir`: "el beneficio es
puramente conductual"), pero una madriguera colonial SÍ debería dar
beneficios reales a quien la usa. Con la entidad física ya construida
en A, dar el beneficio es mecánico: reutilizar el mismo patrón aditivo
que ya usan `bono_confort_refugio`/`bono_confort_fogata`/
`bono_seguridad_pareja` en `sistema_necesidades.py`, dos veces más.

## Decisiones ya cerradas con Diego

- **Dos beneficios, ambos reutilizando el mismo patrón aditivo ya
  existente**: confort térmico Y seguridad — sin inventar ningún
  mecanismo nuevo, exactamente la misma forma que ya tienen
  `bono_confort_fogata`/`bono_seguridad_pareja`.
- **Se aplican a CUALQUIERA que esté físicamente en la celda de la
  madriguera en ese momento** — mismo criterio que `hay_refugio_en`
  ("una choza abriga a quien esté dentro"), no solo a quien tiene la
  coordenada en su propia memoria. Desacopla deliberadamente "quién la
  usa de hecho" (bono) de "quién está admitido para que se le
  sincronice como destino de navegación" (círculo A).

## Alcance

**Dentro:**

1. `sistemas/sistema_necesidades.py`: dos bonos nuevos, en los mismos
   bloques que ya aplican `bono_confort_refugio`/`bono_confort_fogata`
   y `bono_seguridad_pareja` — si
   `madriguera_en(gestor, pos.x, pos.y, pos.zona_idx) is not None`,
   sumar `bono_confort_madriguera` a `obj_termico`, y
   `bono_seguridad_madriguera` a `Necesidades.seguridad` (capado a
   `1.0`).
2. `config/fisiologia.yaml`, sección `necesidades.defecto`:
   `bono_confort_madriguera`, `bono_seguridad_madriguera` (PROVISIONAL).
3. Tests dirigidos + verificación obligatoria contra el motor real.

**Fuera de alcance, explícito:**

- Cualquier cambio a `nucleo/madriguera.py`, `componentes/madriguera.py`
  o `sistemas/sistema_manada.py` — se consumen tal cual, ya cerrados en
  el círculo A.
- Cualquier beneficio para refugio INDIVIDUAL (no colonial) — se queda
  exactamente como está (sin bono, decisión ya tomada y documentada).
- Ninguna otra necesidad más allá de confort térmico y seguridad
  (hidratación, saciedad, etc.) — solo las dos ya decididas.

## Arquitectura

En el bloque donde ya se aplica `bono_confort_refugio`/
`bono_confort_fogata` (buscar `hay_refugio_en`/`fogata_en` en
`sistema_necesidades.py` como referencia exacta de dónde insertar):

```python
if madriguera_en(gestor, pos.x, pos.y, pos.zona_idx) is not None:
    obj_termico += self.bono_confort_madriguera
```

En el bloque donde ya se aplica `bono_seguridad_pareja` (recuperación
de `Necesidades.seguridad`):

```python
if madriguera_en(gestor, pos.x, pos.y, pos.zona_idx) is not None:
    nec.seguridad = min(1.0, nec.seguridad + self.bono_seguridad_madriguera)
```

`self.bono_confort_madriguera`/`self.bono_seguridad_madriguera` se
cachean en `__init__` desde `config["necesidades"]["defecto"]`, mismo
patrón que los bonos ya existentes.

## Config nueva (`config/fisiologia.yaml`, sección `necesidades.defecto`, PROVISIONAL)

```yaml
bono_confort_madriguera: 0.3  # PROVISIONAL, mismo orden que refugio/fogata
bono_seguridad_madriguera: 0.1  # PROVISIONAL, mayor que bono_seguridad_pareja
  # (0.05) -- una madriguera protege mas que la sola compania de la pareja
```

## Testing

- Un conejo en la celda de una `Madriguera` real gana ambos bonos
  (verificar valores exactos, incluido el tope de `1.0` en seguridad).
- Un conejo en un sitio de refugio puramente individual (sin
  `Madriguera` física ahí) no gana ninguno de los dos — confirma que
  la diferenciación individual/colonial es real, no solo nominal.
- Cualquier especie (no solo conejo) que por algún motivo comparta
  celda con una `Madriguera` también se beneficia — mismo criterio
  "cualquiera que esté dentro", sin gating por especie.
- **Verificación obligatoria contra `BOSQUE_AUTO_TICKS`, no opcional**:
  medir cuántas veces se aplicó cada bono de verdad en juego libre.
  Reportar con honestidad aunque sea bajo.

## Pendiente real tras esta pieza

- Con A y B cerrados, la extensión completa de "madriguera física"
  sobre `Manada` queda cerrada.
- `bono_confort_madriguera`/`bono_seguridad_madriguera` PROVISIONALES,
  sin calibrar contra el harness completo.
- Sigue abierta la pregunta de si el cupo (círculo A) empuja de verdad
  a fundar nuevas madrigueras — señalada ahí, sin relación directa con
  este círculo.
