# Memoria espacial compartida entre conscientes

Implementa la spec completa que está en
`docs/superpowers/specs/2026-09-06-memoria-espacial-compartida-design.md`
— léela por completo primero. Es la única fuente de verdad de qué
construir, incluido el pseudocódigo de `_agrupar_conscientes_por_celda`,
`_procesar_memoria_compartida` y `_compartir_memoria` (una única llamada
a `objetivo_recordado` por categoría, no una por coordenada — la spec ya
explica por qué).

## Paso obligatorio, no opcional

Además de la suite de tests, corre `BOSQUE_AUTO_TICKS` (unos pocos miles
de ticks) con población real y **mide explícitamente**: cuántas
transferencias de memoria ocurrieron de verdad, y confirma mirando la
BD si algún consciente terminó con una coordenada de comida/agua que él
mismo nunca visitó directamente. Repórtalo en el mensaje de commit final
aunque el resultado sea bajo o nulo — no lo omitas ni lo des por hecho
solo porque los tests unitarios pasan.

## Qué NO tocar

- No implementes ningún mecanismo de aprendizaje por observación para
  fauna (crías siguiendo a un adulto) — la spec lo señala como idea
  aparte, aplazada, fuera de esta tarea.
- No añadas ningún campo de "confianza" o procedencia a
  `MemoriaEspacial` ni a `recuerdos` — la degradación se resuelve solo
  con `objetivo_recordado()` en el momento de compartir, sin metadato
  nuevo. La spec es explícita sobre esto.
- No implementes `Accion.SOCIALIZAR`, sonido físico, ni reputación/rumor
  — piezas independientes del mismo informe, sin relación con esta.
- No añadas ninguna constante nueva a `config/` — la pieza reutiliza
  `Temperamento.sociabilidad` y las funciones de `nucleo/memoria.py`
  sin ningún parámetro adicional.
- No cambies el comportamiento observable de `_procesar_roce_social` —
  el refactor de agrupación debe dar exactamente el mismo resultado que
  antes; los tests de roce social ya existentes deben seguir en verde
  sin modificarlos.
- No toques `nucleo/conflicto.py`, `componentes/relaciones.py` ni
  `nucleo/relaciones.py` — sin relación con esta tarea.
- No modifiques `CLAUDE.md`, nada bajo `informes/`, ni ningún
  `docs/historial_*.md`.
- No cambies ningún esquema de persistencia SQLite — `MemoriaEspacial`
  ya se persiste tal cual, sin campos nuevos que guardar.
