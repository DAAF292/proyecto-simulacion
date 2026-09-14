# Terminal — prototipo del nuevo sistema visual

Pivote decidido con Diego: se aparca el Códice Cartográfico
(`presentacion/vista_web.py`, pergamino/acuarela) y se prueba un sistema
nuevo con estética de terminal informática antigua (fondo negro, ámbar,
CRT) — mapa híbrido ASCII+sprite, con paneles de ficha, narrador,
estadísticas y eventos.

Estado real: **prototipo estático, no está enchufado a `main.py`**. No hay
servidor propio ni actualización en vivo — `datos.json`/`datos.js` es una
instantánea real del motor (generada con `generar_datos.py`, corriendo el
motor de verdad sin persistencia) en un tick concreto (2500, semilla 42
-- subido desde 600 el 2026-09-13: con solo 600 ticks ninguna
construcción llegaba nunca a completarse, así que `DATA.construcciones`
quedaba siempre vacío en la instantánea de referencia). Para verla:

```
python3 -m http.server 8877 --directory presentacion/terminal_prototipo
# abrir http://localhost:8877/terminal.html
```

Para refrescar la instantánea con otra semilla/duración, corre
`python presentacion/terminal_prototipo/generar_datos.py [N_TICKS]`
desde la raíz del proyecto (por defecto 2500 si se omite el argumento).
**CORREGIDO (2026-09-13)**: el script tenía dos rutas absolutas
hardcodeadas de otra máquina/sesión (`/home/user/proyecto-simulacion` y
un directorio de scratch que no existía aquí) -- nunca había corrido de
verdad en este entorno hasta que se arregló. Ahora usa rutas relativas
al propio fichero y escribe `datos.json` **y** `datos.js` junto a sí
mismo.

`sprites/` ya NO es una copia de `presentacion/assets/` -- esa carpeta
se borró del repositorio (commit `0c625cb`, "borrar assets viejos") el
mismo día que se creó este prototipo; la nota anterior quedó
desactualizada sin corregir. El catálogo real hoy son dos capas
independientes: la biblioteca base "recortada/clasificada por Diego"
(flora de los 5 biomas, criaturas, agua -- estilo pixel art retro,
sprites nativos de 40-370px) más un segundo lote de
`inspiracion/procesado/` (2026-09-13, mismo fondo transparente,
resolución nativa 2048px sin downscalear a petición explícita de Diego)
integrado con `presentacion/arnes/integrar_inspiracion_terminal.py` --
variantes nuevas para 6 de las 7 especies de fauna (falta `caballo`,
sin material en `inspiracion/`) y para gran parte del catálogo de flora,
más dos categorías que el visor nunca había dibujado hasta ahora:
`SPRITES_CONSTRUCCION` (refugio/almacen -- `salon_comun`/`cocina`
existen como tipo real en el motor pero sin sprite propio todavía) y
`SPRITES_OBJETOS` (roca/rama, decoración ambiental ligada a
`Celda.recursos.piedra_suelta`/`madera` reales, ver `terminal.html`).
`presentacion/vista_web.py:construir_instantanea` ganó la clave
`"construcciones"` en el DTO para que esto tuviera datos reales que
consumir -- antes ninguna versión del visor (ni el Códice Cartográfico
en su día) llegó a exportar construcciones.

Pendiente real, sin resolver aquí: decidir si este prototipo sustituye a
`vista_web.py` en producción (serverificarlo en vivo, panel de eventos con
filtro real, catálogo de comandos) o se queda como referencia de diseño;
sprite propio para `caballo` desde `inspiracion/` (pendiente de que Diego
lo genere); sprite para `salon_comun`/`cocina`; las construcciones no son
clickeables todavía (sin ficha de inspección, a diferencia de las
entidades vivas).
