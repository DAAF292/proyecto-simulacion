# Convivencia familiar: bono de parentesco en la afinidad diaria

Fecha: 2026-09-17. Cuarto círculo de la sesión, continuación del arco
"vida familiar" tras "emancipación gateada por adultez + parto dirigido
a refugio" (mismo día, ya en master). Diseñado en conversación con
Diego: "los lazos de sangre inciten a los conscientes a hacer una vida
común más estrecha... es más probable que vayas a comer con tu hijo o
tu abuela que con un vecino del pueblo".

## Hallazgo que motiva este círculo

`_acrecion_amistad_convivencia` (`sistema_asentamiento.py:257-297`) daba
el MISMO delta diario de afinidad (`delta_amistad_convivencia_dia`,
0.05) a cualquier par de miembros conscientes del mismo asentamiento —
un hijo y un vecino cualquiera generaban exactamente el mismo vínculo
por "convivir". Sin ningún sesgo de parentesco.

## Nota sobre "abuela" (límite real, ya documentado, no resuelto aquí)

`nucleo/parentesco.py` deriva todo de `Identidad.id_madre/id_padre` EN
VIVO. "Abuela" es derivable hoy de forma transitoria -- mientras el
progenitor intermedio siga vivo, "mi madre → su madre" es una cadena de
dos saltos consultable -- pero `GestorEntidades.eliminar_entidad` purga
TODA la `Identidad` al morir, así que el vínculo con la abuela se pierde
para siempre en el instante en que el intermedio muere, aunque la abuela
siga viva. Limitación técnica real, ya documentada en el propio módulo y
en `CLAUDE.md` ("abuelos/tíos en parentesco, bloqueados por la purga de
Identidad al morir") -- fuera de alcance de este círculo.

## Alcance: Círculo A de dos (decisión explícita de Diego, trocear)

- **Círculo A (este)**: bono de afinidad -- la convivencia genera más
  vínculo entre familia directa que entre el resto. Cierra ahora.
- **Círculo B (pendiente, próximo)**: comportamiento real de "hacer vida
  en común" -- agruparse preferentemente con familiares al deambular/
  socializar, o algo más ambicioso (p.ej. una noción de "comer juntos").
  Mucho más grande que A, toca el sesgo gregario de movimiento
  (`sistema_movimiento.py`). Sin diseñar todavía, deliberadamente.

## Diseño (Círculo A)

`_acrecion_amistad_convivencia` gana un multiplicador
`factor_amistad_convivencia_familia` (PROVISIONAL 2.0, hipótesis de
partida sin calibrar) aplicado al delta diario cuando el par es
`es_familia_directa()` (hermanos, o padre/madre-hijo -- reutiliza
`nucleo/parentesco.py` sin ningún componente nuevo). El resto del
mecanismo (gate de consciencia, escritura bidireccional, purga FIFO de
`Relaciones.vinculos`) no cambia.

## Config nueva (`config/relaciones.yaml`, PROVISIONAL)

- `factor_amistad_convivencia_familia: 2.0`
