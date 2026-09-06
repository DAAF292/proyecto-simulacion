# Conflicto verbal (roce social + contacto por crisis violenta)

Implementa la spec completa que está en
`docs/superpowers/specs/2026-09-06-conflicto-verbal-design.md` — léela
por completo primero. Es la única fuente de verdad de qué construir.

## Paso obligatorio, no opcional

Además de la suite de tests, corre `BOSQUE_AUTO_TICKS` (unos pocos
miles de ticks) con población real y **mide explícitamente** (no solo
"no lanzó excepción"): cuántas resoluciones de roce social ocurrieron,
cuántas de CRISIS_VIOLENTA con contacto, y si `Relaciones` de la
población muestra más fluctuación real que antes de esta pieza. Repórtalo
en el mensaje de commit final aunque el resultado sea bajo o nulo — no
lo omitas ni lo des por hecho solo porque los tests unitarios pasan. Este
paso se saltó una vez antes en este mismo proyecto (círculo "cimiento
Relaciones") pese a que su spec también lo pedía; esta vez va aparte y
explícito para que no vuelva a pasar.

## Qué NO tocar

- No implementes ningún disparador de "robo" o agravio por recurso
  escaso — la spec lo señala como círculo futuro, fuera de esta tarea.
- No implementes `Accion.SOCIALIZAR` ni ningún mecanismo de ocio
  consciente — pieza independiente, sin relación con esta.
- No implementes sonido físico ni memoria espacial compartida entre
  conscientes — piezas aparte del mismo informe original, fuera de
  alcance aquí.
- No cambies `_tipo_crisis` ni los umbrales de cuándo una entidad entra
  en CRISIS_VIOLENTA (`umbral_estabilidad_crisis`,
  `umbral_agresividad_violenta`) — solo se le da consecuencia al estado
  ya existente, no se cambia cuándo ocurre.
- No hagas que ningún sistema LEA `Relaciones` para modular
  comportamiento — esta tarea solo escribe (rencor), igual que ya
  hacían refugio ocupado/amistad/concepción. El único lector existente
  (pareja estable) no se toca.
- No modifiques `config/nombres.yaml`, `componentes/relaciones.py` ni
  `nucleo/relaciones.py` — ya existen y se reutilizan tal cual, sin
  cambios de forma.
- No cambies el comportamiento de `_calcular_huida_erratica` — solo
  `_calcular_crisis_violenta` gana la resolución de contacto; huida
  errática sigue exactamente igual.
- No modifiques `CLAUDE.md`, nada bajo `informes/`, ni ningún
  `docs/historial_*.md`.
- No cambies ningún esquema de persistencia SQLite — la spec no
  introduce ningún componente ni campo nuevo que persistir.
