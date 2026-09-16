# Terminal — único sistema visual del proyecto

**Pivote completo (2026-09-16, decisión de Diego)**: se retiró por completo
el Códice Cartográfico (`presentacion/vista_web.py`, pergamino/acuarela —
ver `docs/informe_codice_cartografico.md` para su documentación íntegra) y
este visor de estética de terminal informática antigua (fondo negro, ámbar,
CRT) pasa a ser el **único** sistema visual del proyecto. El pivote anterior
(23-08 a 13-09-2026) era un híbrido ASCII+sprite; desde hoy es **mapa 100%
glifos de texto, sin ningún asset de imagen** — los ~83MB de sprites que
usaba (`sprites/`) se retiraron del repositorio (recuperables por
`git log` si algún día se decide volver a una vía gráfica).

Motivo del pivote a ASCII puro: varias sesiones sin encontrar un estilo de
arte/asset definitivo (ver `docs/historial_capa_visual.md` para toda la
saga de fuentes descartadas — PyxelSpace, Urizen, Mini Medieval, y antes de
eso el propio Códice) estaban restando foco real al desarrollo del motor de
simulación. Un mapa de glifos+color no depende de ningún pack de terceros
ni de su licencia, y es trivialmente extensible: añadir una especie o
categoría nueva es una entrada en un catálogo, no un recorte de sprite.

## Cómo verlo

Servido por el mismo servidor que la simulación real:

```
SIMULACION_MODO_VISUAL=1 python main.py
# abrir http://localhost:8765/  (o el puerto de config/visual.yaml)
```

También puede verse suelto, sin motor en marcha, con la instantánea
estática de referencia:

```
python3 -m http.server 8877 --directory presentacion/terminal_prototipo
# abrir http://localhost:8877/terminal.html
```

Para refrescar esa instantánea con otra semilla/duración:
`python presentacion/terminal_prototipo/generar_datos.py [N_TICKS]` desde
la raíz del proyecto (por defecto 2500 ticks).

## Arquitectura del mapa ASCII

Todo el mapa se dibuja con `<div>` de texto (una celda de terreno + una capa
aparte, persistente entre renders, para las criaturas — así se puede animar
su desplazamiento con una transición CSS en vez de teletransportarlas).

**Una única fuente de verdad**: el objeto `CATALOGO_GLIFOS` en
`terminal.html` — glifo + color + nombre legible por cada tipo de terreno,
agua, especie de flora/fauna, tipo de construcción y recurso en el suelo.
Tanto el renderizado del mapa como la leyenda desplegable (botón
"LEYENDA ▾" en la barra del mapa) leen de esta misma tabla; añadir algo
nuevo al mundo es una entrada aquí, nunca dos tablas que puedan
desincronizarse.

Decisiones de diseño concretas:
- **Flora por categoría, no por especie**: en vez de 15 glifos distintos
  (uno por especie del catálogo), el glifo indica la FORMA/FUNCIÓN (árbol
  `♣`, arbusto `*`, cobertura de suelo `,` — reutilizando la misma
  distinción que ya usa `config/flora.yaml` vía `compite_espacio_fisico` +
  `huella_m2`) y el COLOR diferencia la especie dentro de esa categoría.
  Evita "sopa de glifos" con 15 símbolos casi ilegibles a la vez.
- **Prioridad de una sola representación por celda**: construcción > agua >
  planta > recurso suelto en el suelo > terreno base — mismo orden que ya
  usaba el prototipo híbrido anterior.
- **Datos reales del motor modulan la presentación, no números inventados**:
  la opacidad de una planta sube con `Planta.etapa` real (brote tenue,
  madura llena de color); la de una celda de agua sube con
  `profundidad_agua`/`profundidad_charco` real; una montaña muestra pico
  (`▲`) en vez de ladera (`^`) cuando `elevacion > 0.72`; una criatura
  consciente (mismo umbral de agencia que usa el motor,
  `capacidad_mental.consciente`) recibe un resplandor de texto.
- **Zoom centrado en el cursor**: al hacer scroll, el punto de mundo bajo
  el cursor permanece fijo en pantalla (antes el zoom escalaba siempre
  desde el origen, así que el mapa "derivaba" si ya se había desplazado).
  Paneo por arrastre directo (1:1 con el ratón).

## Pendiente real, sin resolver aquí

- **Confirmación visual de Diego sobre la elección concreta de
  glifos/colores** — es una primera propuesta razonada (reutilizando el
  fallback ASCII que ya existía en el prototipo híbrido para fauna, y
  aplicando el mismo criterio de "forma=función, color=especie" a flora),
  no una calibración ya cerrada. Un glifo o color concreto que no se lea
  bien es un ajuste aislado en `CATALOGO_GLIFOS`, sin tocar el mecanismo.
- Catálogo de eventos filtrable (panel "EVENTOS://LOG") sigue siendo un
  placeholder, sin implementar — no tocado en este círculo.
- Construcciones no son clickeables todavía (sin ficha de inspección, a
  diferencia de las entidades vivas).
- `salon_comun`/`cocina`/`taller` ya tienen entrada propia en
  `CATALOGO_GLIFOS.construcciones` (glifo dedicado), pero no se ha
  verificado en juego libre con una semilla donde lleguen a construirse
  las tres a la vez.
