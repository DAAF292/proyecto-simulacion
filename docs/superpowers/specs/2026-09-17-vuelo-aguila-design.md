# Vuelo + águila: mecanismo de vuelo y primera especie voladora

Fecha: 2026-09-17. Quinto círculo de la sesión, tema nuevo de la lista
original de 13 (no parte del arco "vida familiar"). Origen: "me interesa
el tema de vuelos, para poder añadir fauna que vuela, insectos, etc".

## Alcance confirmado con Diego (vía AskUserQuestion)

- Mecanismo de vuelo + una especie sencilla ahora; insectos quedan
  aparcados para después (pendiente real, ver `CLAUDE.md`).
- No solo movimiento: también "posarse" y "cazar en el aire".

## Hallazgo crítico, comunicado antes de implementar

El mundo no tiene eje de altura (`Posicion` es x/y/zona_idx, sin
componente vertical) y no existe todavía ninguna especie voladora ni
insecto que sirva de presa aérea. Las dos peticiones literales
("posarse" como "estar por encima del suelo", "cazar en el aire" como
depredación de otra presa voladora) no son representables con la
arquitectura actual sin inventar una dimensión nueva -- coste de
complejidad injustificado para una primera especie.

Propuesta simplificada, aceptada explícitamente por Diego ("me vale de
momento, adelante"):

- **Vuelo (movimiento)**: rasgo racial (`vuela: bool`), no de celda ni
  componente aparte -- mismo patrón categórico que `medio_alimentacion`.
  Ignora el ahogamiento por profundidad de agua SIEMPRE. Ignora el
  chequeo de pendiente máxima transitable (y su coste de resistencia
  asociado) SOLO en superficie (`zona_idx == 0`) -- bajo tierra, las
  paredes de cueva reutilizan el mismo campo de elevación para roca
  sólida real (`nucleo/cueva.py`, "PAREDES IMPASABLES SIN CAMPO NUEVO"),
  así que un ave sigue sin poder atravesarlas: no hay excepción de
  vuelo para eso, sería contradecir esa decisión deliberada.
- **Posarse**: reinterpretado como preferencia de CELDA, no de altura --
  al `DORMIR`, un volador prioriza la celda más cercana con un árbol
  (`Planta.masa_tronco_kg > 0`) sobre el refugio recordado o el sesgo
  gregario que ya usa el resto de fauna. Sin árbol en rango, cae a las
  capas existentes sin cambios.
- **Cazar en el aire**: no exige NINGÚN cambio en
  `sistema_depredacion.py` -- ese sistema ya resuelve la depredación por
  contacto en la misma celda, agnóstico a cómo llegaron depredador y
  presa hasta ahí. Un águila con `medio_alimentacion: cazar` persigue
  presa terrestre existente (conejo/ardilla) exactamente igual que
  zorro/lobo, solo que su propio desplazamiento usa el pathfinding
  consciente de vuelo. "Cazar en el aire" en el sentido de depredar OTRA
  especie voladora queda fuera de alcance -- no existe presa aérea
  todavía (insectos aparcados).

## Diseño

### `Especie.AGUILA` (`componentes/identidad.py`)

Primera especie voladora del catálogo.

### `vuela` en `rangos_raciales` (`config/poblacion.yaml`)

Nuevo campo booleano, leído una vez por individuo por tick en
`sistema_movimiento.py::ejecutar` (`self.config["rangos_raciales"][especie]["vuela"]`,
`False` si no está presente -- el resto del catálogo no lo declara y
conserva el comportamiento actual sin cambios).

### `_aplicar_movimiento` (`sistemas/sistema_movimiento.py`)

Nuevo parámetro `vuela: bool = False`:

1. Si `vuela`: se salta el chequeo de ahogamiento (profundidad de agua
   vs. `DimensionesFisicas.altura`) incondicionalmente.
2. `ignora_relieve = vuela and pos.zona_idx == 0`: si es cierto,
   `delta_elev` queda fijo en `0.0` (sin chequeo de pendiente máxima, sin
   coste de resistencia por desnivel en el paso 3, que ya depende de
   `delta_elev`).

### `_calcular_dormir` (`sistemas/sistema_movimiento.py`)

Nuevo parámetro `vuela: bool = False`, nueva "capa 0" antes de las dos
capas existentes (refugio recordado / sesgo gregario): si `vuela`, busca
la celda con árbol más cercana (`_arbol_mas_cercano`, nuevo helper,
escaneo directo vía índice espacial si está disponible, mismo patrón que
`_buscar_conspecifico_mas_cercano`) y se mueve hacia ella (o se queda
quieta si ya está ahí). Sin árbol en rango, cae a las capas existentes
sin cambios. Sin bono numérico añadido -- puramente conductual, mismo
criterio que el resto de la función.

### `Especie.AGUILA` en `config/poblacion.yaml`

Bloque de rango racial completo, modelado sobre la plantilla de zorro
(mismo nivel de detalle) con:

- `vuela: true`
- `medio_alimentacion: cazar`
- Peso/altura fieles al águila real (~3.5-6.5kg)
- Longevidad más alta que el resto de depredadores del catálogo (rapaz
  longeva real, 12-20 frente a 4-8 de zorro) -- PROVISIONAL
- `puntos_agarre: 2` (garras)
- Sociabilidad baja (territorial/solitaria, mismo criterio que zorro)

Todo PROVISIONAL, sin calibrar contra el harness completo -- primera
especie, sin ninguna medición todavía.

### Siembra inicial (`main.py::sembrar_poblacion_inicial`)

`aguilas_iniciales` (config, PROVISIONAL: 4) nace en pool combinado
bosque + montaña (mismo criterio de pool combinado sin reparto forzado
que ya usa zorro con bosque+pradera) -- rapaz de territorio amplio, no
ligada a un único bioma.

## Qué NO se toca

- `sistema_depredacion.py` -- sin cambios, ver hallazgo crítico arriba.
- Ningún componente nuevo -- `vuela` vive en config, no en un componente
  por-entidad (no varía por individuo, es 100% racial).
- Ninguna especie existente cambia de comportamiento -- `vuela` por
  defecto es `False` para todo el catálogo previo.

## Pendiente explícito, no resuelto aquí

- Insectos (presa aérea real, "cazar en el aire" en su sentido literal)
  -- aparcado a petición de Diego.
- Eje de altura real -- si algún día se necesita "estar por encima del
  suelo" de verdad (para representación visual, por ejemplo), esto no lo
  resuelve, solo lo evita.
- Calibración numérica del bloque de águila contra el harness completo.
