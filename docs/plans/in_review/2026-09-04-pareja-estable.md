# Plan de implementacion: Pareja estable derivada + bono de cercania

Fuente de verdad: `docs/superpowers/specs/2026-09-04-pareja-estable-design.md`.

## Ficheros a tocar (en orden)

1. `nucleo/relaciones.py` — anadir dos funciones puras:
   - `son_pareja(rel_a, rel_b, id_a, id_b, umbral)`: True solo si existe
     vinculo en AMBAS direcciones y ambas afinidades `>= umbral`. No
     impone monogamia ni decaimiento.
   - `pareja_presente(gestor, entidad_id, relaciones, pos_x, pos_y,
     zona_idx, umbral)`: busqueda lineal O(N) sobre entidades con
     (Relaciones, Posicion) en la celda EXACTA (mismo x, y, zona_idx),
     excluyendo la propia, que cumpla `son_pareja` con la entidad
     consultada. Sigue el patron de `hay_refugio_en`/`fogata_en`.

2. `config/relaciones.yaml` — anadir `umbral_pareja: 0.3` (PROVISIONAL).

3. `config/fisiologia.yaml` (seccion `necesidades.defecto`) — anadir
   `bono_confort_pareja: 0.15` y `bono_seguridad_pareja: 0.05`
   (PROVISIONALES), junto a bono_confort_refugio/fogata.

4. `sistemas/sistema_necesidades.py`:
   - En `_cachear_configuracion`: leer `bono_confort_pareja`,
     `bono_seguridad_pareja`, `umbral_pareja` y
     `umbral_consciencia_agencia`.
   - En `ejecutar`: importar/fetch `Relaciones`; calcular si la entidad
     es consciente y tiene pareja presente (celda exacta). Si es asi:
     - sumar `bono_confort_pareja` a `obj_termico` (un sumando mas junto
       a refugio/fogata) antes de la deriva.
     - sumar `bono_seguridad_pareja` a `nec.seguridad` tras el bloque de
       drenaje/recuperacion, capado a 1.0.
   - No se tocan sistema_reproduccion/movimiento/asentamiento.

5. `tests/test_pareja_estable.py` — tests unitarios:
   - `son_pareja`: ambas direcciones, una sola direccion, falta un
     vinculo, afinidad insuficiente.
   - `pareja_presente`: celda exacta (true), otra celda (false), otra
     zona_idx (false), entidad presente no es pareja (false).
   - `sistema_necesidades`: confort se suma con refugio+fogata+pareja;
     seguridad se aplica y respeta tope 1.0; no se aplican a entidad
     no-consciente; ni cuando la otra parte no es realmente pareja.

6. Verificacion OBLIGATORIA contra el motor real: `BOSQUE_AUTO_TICKS`
   con poblacion real, inspeccion de la BD resultante para confirmar (o
   negar explicitamente, y por que) si hubo al menos un par de gnomos
   conscientes que supero `umbral_pareja` en ambas direcciones.

## No tocar

- No refugio compartido, aporte conjunto al almacen, monogamia,
  decaimiento de afinidad, radio de percepcion.
- No tocar sistema_reproduccion.py, sistema_movimiento.py (rencor),
  sistema_asentamiento.py (amistad).
- No modificar CLAUDE.md, informes/, docs/historial_*.md.
