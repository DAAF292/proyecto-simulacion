# Manada — estructuras gregarias reales en fauna

Implementa la spec completa que está en
`docs/superpowers/specs/2026-09-07-manada-fauna-design.md` — léela por
completo primero. Es la única fuente de verdad de qué construir,
incluido el pseudocódigo de `SistemaManada.ejecutar`,
`_sincronizar_madriguera` y el consumidor en `_calcular_deambular`.

## Paso obligatorio, no opcional

Además de la suite de tests, corre `BOSQUE_AUTO_TICKS` (unos pocos
miles de ticks) con población real y **mide explícitamente**: cuántas
manadas se forman por especie (comparar frecuencia entre especies), y
si algún conejo terminó con una coordenada de refugio que él mismo
nunca visitó directamente (evidencia de madriguera compartida real).
Repórtalo en el mensaje de commit final aunque el resultado sea bajo o
nulo — no lo omitas ni lo des por hecho solo porque los tests
unitarios pasan.

## Qué NO tocar

- No implementes liderazgo ni "macho alfa" de manada — extensión
  futura explícitamente fuera de esta pieza.
- No toques `contar_conspecificos_cercanos`, el bono de caza en grupo,
  ni el "techo de presa por manada" de lobo
  (`sistema_depredacion.py`/`sistema_movimiento.py:_calcular_caza`) —
  se quedan exactamente iguales, sin migrar a la nueva estructura.
- No implementes ninguna acción consciente de "excavar" — la
  madriguera es instintiva (memoria, vía `registrar_recuerdo`), nunca
  una `Construccion` ni una `Accion` nueva.
- No añadas ningún rasgo racial nuevo de tipo de manada más allá de
  `tipo_refugio_fauna` (y solo con el valor `"colonial"`, solo en
  `conejo`) — lobo/caballo/ardilla se diferencian con rasgos que ya
  existen (`medio_alimentacion`, `sociabilidad`), sin tocarlos.
- No persistas `Manada` en SQLite — igual que `Asentamiento`, 100%
  derivable cada día, no se guarda.
- No implementes ninguna de las piezas del informe de "capa de
  comunicación" (ya cerrado) — sin relación con esta.
- No modifiques `CLAUDE.md`, nada bajo `informes/`, ni ningún
  `docs/historial_*.md`.
- No cambies ningún esquema de persistencia SQLite.
