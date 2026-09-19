# Idiomas: catálogo de lenguas y matriz de comprensión

Fecha: 2026-09-18. Origen: tras cerrar el círculo de desastres
naturales, Diego pidió explorar "lenguaje" -- hoy el motor tiene una
capa de comunicación completa (conflicto verbal, memoria espacial
compartida, ocio consciente, sonido físico, rumor + liderazgo, ver
`docs/historial_capa_comunicacion.md`) pero ninguno de sus cuatro
consumidores reales (roce social/conflicto verbal, memoria compartida,
rumor, liderazgo vía `Relaciones`) consulta `Identidad.especie` como
condición de entendimiento -- confirmado leyendo el código, no supuesto:
hay un comentario explícito en `sistema_movimiento.py` (bloque de
`_agrupar_conscientes_por_celda`) que ya avisaba de este hueco. Hoy es
invisible porque solo gnomo es consciente.

Diego planteó tres familias de razas con solapamiento parcial de lengua:
- **Feéricas** (elfo, hada, gnomo) hablan **feérica**.
- **Comunes** (humano, enano) hablan **común**, que comparte un 33% con
  feérica.
- **Brutas** (orco, trasgo, ogro) hablan **bruta**, que comparte un 33%
  con común y un 0% con feérica (no transitivo -- deliberado, ver abajo).

De las ocho razas nombradas, hoy solo **gnomo** existe como especie
consciente real en el motor. El resto son declaración de intención a
futuro, sin ningún dato ni implementación asociada más allá de la
entrada de `lengua_por_especie` que se les reserva en este círculo.

## Decisión de modelado: lengua, no raza

Modelar la comprensión como una relación directa raza↔raza (matriz N×N
que crece cuadráticamente con cada raza nueva, y que además duplicaría
información -- todas las razas feéricas entre sí valdrían 1.0 por
definición) viola el principio de "reglas, no guiones": codificaría
resultados concretos en vez de la ley que los genera.

Modelo de dos capas en su lugar:
- **Catálogo de lenguas**, con una matriz de comprensión SIMÉTRICA entre
  ellas (3×3 hoy: feérica/común/bruta).
- **Cada raza consciente declara UNA lengua nativa**, dato categórico
  fijo -- mismo espíritu que `Identidad.especie` en sí (no es un rango
  racial sorteado al nacer, se hereda entero de la raza, ninguna
  variación individual).

Añadir una raza nueva es una línea de config (asignarle su lengua), no
tocar la matriz. La asimetría feérica-bruta=0% frente a
feérica-común=común-bruta=33% se declara explícita en la matriz, no se
deriva de ninguna fórmula de distancia (una fórmula de distancia sumada
dejaría feérica-bruta en algo mayor que 0 vía el nodo intermedio común,
que es exactamente el resultado que Diego no quiere).

## Config nueva: `config/idiomas.yaml`

```yaml
idiomas:
  matriz_comprension:
    feerica: {feerica: 1.0, comun: 0.33, bruta: 0.0}
    comun:   {feerica: 0.33, comun: 1.0, bruta: 0.33}
    bruta:   {feerica: 0.0, comun: 0.33, bruta: 1.0}

  lengua_por_especie:
    gnomo: feerica
    # elfo, hada, humano, enano, orco, trasgo, ogro: se añaden cuando
    # existan como Especie real en el motor -- reservar aquí su entrada
    # no las crea.
```

Sección de nivel superior `idiomas` (mismo patrón de fusión que
`main.py:cargar_configuracion` ya aplica a cualquier fichero nuevo de
`config/*.yaml`, sin registro adicional en ningún sitio).

**PROVISIONAL, con un matiz distinto al resto de constantes del
proyecto**: los valores 1.0/0.33/0.0 son de partida narrativa, no
calibrados contra el motor -- y a diferencia de otras PROVISIONAL, no
hay ninguna corrida de harness que pueda corregirlos pronto, porque hoy
no existe una segunda raza consciente real con la que observar el
efecto. Quedan así hasta que Diego decida ajustarlos por criterio propio
o hasta que una segunda raza consciente permita observarlos en juego
libre.

## `nucleo/idioma.py` (nuevo)

Dos funciones puras, mismo molde que `nucleo/disposicion.py:
magnitud_disposicion_por_peso` (sin estado, config como única fuente de
verdad):

```python
def lengua_de_especie(especie: str, config: dict) -> str | None:
    """None si la especie no tiene lengua declarada (toda la fauna no
    consciente hoy, y cualquier especie consciente futura que aún no se
    haya añadido a lengua_por_especie)."""
    return config.get("idiomas", {}).get("lengua_por_especie", {}).get(especie)


def comprension(especie_a: str, especie_b: str, config: dict) -> float:
    """Grado de comprensión mutua [0, 1] entre dos especies, vía sus
    lenguas nativas. 0.0 si cualquiera de las dos no tiene lengua
    declarada (no hay "conversación" posible sin lengua) -- no una
    excepción, un resultado válido y neutral."""
    lengua_a = lengua_de_especie(especie_a, config)
    lengua_b = lengua_de_especie(especie_b, config)
    if lengua_a is None or lengua_b is None:
        return 0.0
    matriz = config.get("idiomas", {}).get("matriz_comprension", {})
    return float(matriz.get(lengua_a, {}).get(lengua_b, 0.0))
```

`especie_a`/`especie_b` son el valor string de `Especie` (`.value`), no
el Enum -- mismo criterio ya usado para leer `rangos_raciales` por
especie en el resto del motor (p.ej. la lectura de `vuela` en
`sistema_movimiento.py`).

## Alcance de este círculo

Ningún consumidor se toca aquí. `comprension()` no tiene ningún efecto
observable todavía -- con una sola especie consciente,
`comprension("gnomo", "gnomo")` siempre vale 1.0. Su único propósito es
dejar la ley lista para el primer consumidor real, que es la Pieza 2
(leyendas / memoria oral, spec aparte:
`2026-09-18-leyendas-memoria-oral-design.md`).

## Verificación

Tests dirigidos puros sobre `nucleo/idioma.py` (sin motor, sin
integración): matriz simétrica leída correctamente en ambas direcciones,
`comprension("feerica-especie", "bruta-especie") == 0.0`,
`lengua_de_especie` de una especie sin entrada devuelve `None`, y
`comprension` con cualquiera de las dos especies sin lengua devuelve
0.0. No se corre ningún smoke test de motor para esta pieza -- no hay
comportamiento emergente que observar todavía, coherente con "alcance de
este círculo" arriba.
