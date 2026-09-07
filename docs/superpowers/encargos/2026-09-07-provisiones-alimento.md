# Provisiones de alimento — almacenamiento personal con caducidad

Implementa la spec completa que está en
`docs/superpowers/specs/2026-09-07-provisiones-alimento-design.md` —
léela por completo primero. Es la única fuente de verdad de qué
construir, incluidos los dos puntos de inserción exactos en
`_resolver_comer` (entrada y salida), las firmas de las funciones
nuevas de `nucleo/inventario.py`, y la ubicación exacta de cada
constante de config nueva.

Esta pieza NO toca la capacidad de carga general (`Inventario.contenidos`/
`objetos`, `capacidad_carga_kg`, `espacio_disponible_kg`) -- son
funciones y campos ya existentes, se quedan exactamente igual.
`Inventario.provisiones` es un campo nuevo, con su propia capacidad
independiente, mismo criterio ya explicado en la spec.

## Qué NO tocar

- Robo, trueque, o cualquier primitivo genérico de transferencia de
  recursos entre individuos -- son círculos futuros del mismo arco, sin
  ninguna dependencia de esta pieza salvo que ahora habrá algo real que
  transferir. No adelantar nada de eso aquí.
- Ninguna variación de este comportamiento por especie no consciente
  (fauna) ni por atributo individual (`inteligencia`, `voluntad`...).
- `tasa_descomposicion_dia_alimento` es UNA tasa universal para toda
  comida guardada -- no crear una tasa distinta por recurso.
- Zoocoria (`Semillas.especie_transportada`) -- comer de las propias
  provisiones nunca dispara ese mecanismo, solo comer fruta en el sitio
  donde crece (comportamiento ya existente, sin cambios).

## Paso obligatorio, no opcional

Además de la suite de tests, corre `BOSQUE_AUTO_TICKS` (unos pocos
miles de ticks) con población real y mide explícitamente: cuántas
veces se dispara de verdad la entrada (guardar excedente al comer) y la
salida (comer de las provisiones cuando la celda está vacía), y si
llega a observarse alguna caducidad real (provisiones que decaen antes
de consumirse). El propio spec ya avisa de que el disparador es
deliberadamente estrecho (solo se evalúa cuando la Utility AI elige
`COMER`) -- **repórtalo con honestidad en el mensaje de commit final
aunque la frecuencia real sea baja**, no lo des por sentado ni lo
adornes.
