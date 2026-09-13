# Terminal — prototipo del nuevo sistema visual

Pivote decidido con Diego: se aparca el Códice Cartográfico
(`presentacion/vista_web.py`, pergamino/acuarela) y se prueba un sistema
nuevo con estética de terminal informática antigua (fondo negro, ámbar,
CRT) — mapa híbrido ASCII+sprite, con paneles de ficha, narrador,
estadísticas y eventos.

Estado real: **prototipo estático, no está enchufado a `main.py`**. No hay
servidor propio ni actualización en vivo — `datos.json`/`datos.js` es una
instantánea real del motor (generada con `generar_datos.py`, corriendo el
motor de verdad sin persistencia) en un tick concreto (600, semilla 42).
Para verla:

```
python3 -m http.server 8877 --directory presentacion/terminal_prototipo
# abrir http://localhost:8877/terminal.html
```

Para refrescar la instantánea con otra semilla/duración, edita
`generar_datos.py` y vuelve a correrlo desde la raíz del proyecto.

`sprites/` es una copia local de una parte de `presentacion/assets/`
(flora de los 5 biomas, criaturas, agua) — se sincroniza a mano, no lee
`presentacion/assets/` directamente todavía.

Pendiente real, sin resolver aquí: decidir si este prototipo sustituye a
`vista_web.py` en producción (serverificarlo en vivo, panel de eventos con
filtro real, catálogo de comandos) o se queda como referencia de diseño.
