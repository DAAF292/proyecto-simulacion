# Lealtad y liderazgo con inercia real (5b) — diseño

Fecha: 2026-09-06. Círculo 5b, cierre de la quinta y última pieza del
informe de "capa de comunicación" — ver
`docs/superpowers/specs/2026-09-06-rumor-social-design.md` (círculo 5a,
el primitivo de rumor/confianza) para el contexto completo.

**Dependencia dura**: exige que 5a esté YA MERGEADO — no por reutilizar
código de 5a directamente (este círculo no llama a `_compartir_rumor`
en absoluto), sino porque su consumidor real es la MISMA estructura de
datos (`Relaciones.vinculos`) que 5a empieza a poblar con opiniones de
terceros. Sin 5a, este círculo seguiría funcionando (lee cualquier
`Relaciones` existente, venga de rencor/amistad/concepción/socializar
o de rumor), pero el propio informe pedía la conexión explícita
rumor→liderazgo, así que se secuencian igualmente.

## Motivación

El informe original pedía que la reputación "impacte directamente" en
`calcular_liderazgo`. Primera propuesta (reputación solo como
desempate marginal) fue cuestionada por Diego: *"es raro que un líder
cambie de un día a otro directamente... tendría que haber un proceso o
que alguien que lleve mucho en el poder tenga adeptos o seguidores"*.

**Hallazgo real que resolvió el diseño**: `Asentamiento.id` se
reasigna desde 1 cada día (`sistema_asentamiento.py`, `siguiente_id`,
sin relación con el id del día anterior) — no hay identidad estable de
"el mismo asentamiento" entre días para colgar ahí un contador de
"días en el poder". Pero `Relaciones` SÍ persiste en cada individuo,
con independencia de cómo se recalculen los clústeres. La solución:
**"tener seguidores" no es un contador nuevo, es literalmente
reputación acumulada** — un líder que gobierna genera lealtad real
(afinidad positiva) en quienes lidera, día a día, y esa lealtad
YA ES lo que hace falta consultar para dar inercia real al liderazgo,
sin inventar ningún estado nuevo que persistir.

## Decisiones ya cerradas con Diego

- **Acumulación diaria de lealtad**: cada miembro NO-líder de un
  asentamiento gana una pequeña afinidad POSITIVA hacia su(s) líder(es)
  actual(es), cada día — mismo patrón exacto que "amistad por
  convivencia" (`ajustar_afinidad`, sin componente nuevo), dirigido
  específicamente miembro→líder (los seguidores admiran al líder, no
  necesariamente al revés — no se autora reciprocidad).
- **`calcular_liderazgo` lee reputación**: para cada candidato por
  dominancia, la afinidad MEDIA que el resto del grupo le tiene —
  calculada solo sobre quienes YA tienen una opinión formada (sin
  datos, reputación neutra 0.0, comportamiento idéntico a antes de esta
  pieza). Cero parámetros nuevos en la firma de la función: ya recibe
  `gestor`, así que consulta `Relaciones` directamente.
- **Dos efectos de la reputación, ambos sobre los candidatos YA
  filtrados por dominancia** (no se toca el filtro de dominancia en
  sí):
  1. **Descalificación**: reputación por debajo de
     `umbral_reputacion_descalificante` (PROVISIONAL, negativo) saca al
     candidato de la lista aunque sea el más dominante. Si TODOS los
     candidatos quedan descalificados, el asentamiento se queda sin
     líder ese día — resultado legítimo, no un caso especial que
     evitar con una regla de respaldo.
  2. **Desempate del líder único**: entre los candidatos restantes
     dentro del margen de dominancia, la reputación entra en el
     desempate ANTES que valentía (orden nuevo:
     `(dominancia, reputacion, valentia)`) — un aspirante igual de
     dominante no desplaza a un incumbente con reputación ya
     construida, porque esa reputación tardó días reales de partida en
     formarse, no se puede igualar de golpe.
- **El consejo (vs. líder único) no se toca** — la decisión de
  consejo-vs-único sigue siendo solo cohesión social menos agresividad
  media de los candidatos YA filtrados por dominancia+reputación; no se
  añade reputación a esa fórmula en este círculo.

## Alcance

**Dentro:**

1. `sistemas/sistema_asentamiento.py`: nuevo método
   `_acrecion_lealtad_liderazgo(gestor, mundo, reloj)`, llamado desde
   `ejecutar()` junto a `_acrecion_amistad_convivencia` (misma
   cadencia diaria). Para cada `Asentamiento` con `lideres` no vacío,
   cada miembro no-líder aporta `delta_lealtad_liderazgo` (nuevo,
   PROVISIONAL) de afinidad hacia cada líder, gateado a que el miembro
   sea consciente (mismo criterio que `_ajustar_amistad`).
2. `nucleo/asentamiento.py:calcular_liderazgo`: tras filtrar candidatos
   por dominancia (sin tocar ese filtro), calcular la reputación de
   cada uno y aplicar descalificación + reordenar el desempate final
   como se describe arriba.
3. `config/comportamiento.yaml`, sección `asentamiento:`:
   `umbral_reputacion_descalificante` nueva (PROVISIONAL).
4. `config/relaciones.yaml`: `delta_lealtad_liderazgo` nueva
   (PROVISIONAL).
5. Tests dirigidos + verificación obligatoria contra el motor real.

**Fuera de alcance, explícito:**

- Cualquier cambio a la decisión consejo-vs-líder-único — sigue
  exactamente igual.
- Cualquier cambio al filtro de candidatos por dominancia
  (`margen_dominancia_elite`) — la reputación actúa DESPUÉS de ese
  filtro, no lo sustituye ni lo amplía.
- Cualquier mecánica explícita de "golpe de estado" o proceso de
  transición — la inercia emerge de que la reputación tarda en
  construirse, no de un estado de transición nuevo que modelar.
- Lealtad reciente hacia miembros del consejo cuando hay varios
  líderes — se aplica a TODOS los líderes actuales por igual, sin
  repartir ni ponderar por quién "manda más" dentro del consejo (el
  propio concepto de consejo ya implica poder repartido).
- Persistencia de ningún estado nuevo — la lealtad vive enteramente en
  `Relaciones`, ya persistido; no se guarda ningún historial de
  liderazgo aparte.

## Arquitectura

### Acumulación diaria (`sistema_asentamiento.py`)

```python
def _acrecion_lealtad_liderazgo(self, gestor, mundo, reloj) -> None:
    """Lealtad diaria de seguidor hacia lider (2026-09-06, circulo 5b --
    ver docs/superpowers/specs/2026-09-06-lealtad-liderazgo-design.md):
    mismo patron que _acrecion_amistad_convivencia, dirigido
    especificamente miembro->lider. Es literalmente como se construyen
    "seguidores" -- sin contador de dias en el poder, la propia
    Relaciones acumulada hace ese papel."""
    delta = float(self.config.get("relaciones", {}).get("delta_lealtad_liderazgo", 0.0))
    if delta <= 0.0:
        return
    for asentamiento in mundo.asentamientos.values():
        if not asentamiento.lideres:
            continue
        for miembro_id in asentamiento.miembros:
            if miembro_id in asentamiento.lideres:
                continue
            for lider_id in asentamiento.lideres:
                self._ajustar_amistad(  # reutilizado tal cual -- ya gatea consciencia
                    gestor, miembro_id, lider_id, delta, reloj.tick_actual,
                )
```

Reutiliza `_ajustar_amistad` (ya existente, ya gatea por consciencia
del autor) sin cambiarlo — mismo mecanismo, dirección distinta.

### Reputación en `calcular_liderazgo` (`nucleo/asentamiento.py`)

```python
def calcular_liderazgo(gestor, miembros, config_asentamiento):
    ...  # calculo de temperamentos y candidatos por dominancia, sin cambios

    umbral_descalifica = float(
        config_asentamiento.get("umbral_reputacion_descalificante", -0.4)
    )

    def _reputacion(candidato_id: int) -> float:
        opiniones = []
        for otro_id in miembros:
            if otro_id == candidato_id:
                continue
            rel = gestor.obtener_componente(otro_id, Relaciones)
            if rel is not None and candidato_id in rel.vinculos:
                opiniones.append(rel.vinculos[candidato_id].afinidad)
        return sum(opiniones) / len(opiniones) if opiniones else 0.0

    reputaciones = {c: _reputacion(c) for c in candidatos}
    candidatos = [c for c in candidatos if reputaciones[c] >= umbral_descalifica]
    if not candidatos:
        return set()

    if len(candidatos) == 1:
        return set(candidatos)

    cohesion_social = ...  # sin cambios, sobre los candidatos YA filtrados
    ...
    if (cohesion_social - agresividad_media) > umbral_ajustado:
        return set(candidatos)

    ganador = max(
        candidatos,
        key=lambda mid: (temperamentos[mid].dominancia, reputaciones[mid], temperamentos[mid].valentia),
    )
    return {ganador}
```

Requiere `from componentes.relaciones import Relaciones` en
`nucleo/asentamiento.py` (no importado hoy).

## Config nueva (PROVISIONAL, sin calibrar)

```yaml
# config/relaciones.yaml
relaciones:
  delta_lealtad_liderazgo: 0.03  # PROVISIONAL -- algo menor que
    # delta_amistad_convivencia_dia (0.05/dia): admirar a un lider es
    # mas especifico que la convivencia general del grupo.

# config/comportamiento.yaml, seccion asentamiento:
asentamiento:
  umbral_reputacion_descalificante: -0.4  # PROVISIONAL -- por debajo de
    # esto, un candidato dominante queda descalificado pese a serlo.
```

## Testing

- `_acrecion_lealtad_liderazgo`: aplica lealtad correctamente miembro→
  líder para cada líder de un consejo; no se aplica al propio líder
  hacia sí mismo; no se aplica si `lideres` está vacío; respeta el gate
  de consciencia ya existente en `_ajustar_amistad`.
- `calcular_liderazgo` — descalificación: un candidato con reputación
  por debajo del umbral queda excluido aunque tenga la dominancia más
  alta; si todos los candidatos quedan descalificados, devuelve
  `set()` (sin líder ese día).
- `calcular_liderazgo` — desempate: dos candidatos con dominancia
  empatada, distinta reputación → gana el de mejor reputación
  (verificar que ni siquiera se llega a comparar valentía).
- `calcular_liderazgo` — sin datos de reputación (candidato nuevo, sin
  vínculos formados en el grupo): reputación 0.0, comportamiento
  idéntico a antes de esta pieza (ni descalifica ni desempata contra un
  candidato en verdad mal valorado).
- **Verificación obligatoria contra `BOSQUE_AUTO_TICKS`, no opcional**:
  medir cuántas veces se aplicó lealtad diaria, cuántas veces la
  reputación descalificó a un candidato dominante, y cuántas veces
  cambió el desenlace del desempate final respecto a la fórmula
  anterior (dominancia+valentía sin reputación) — reportar con
  honestidad, incluido si el resultado es bajo o nulo (dado el
  historial ya documentado de asentamiento/pareja/parentesco siendo
  correctos pero casi invisibles en juego libre).

## Pendiente real tras esta pieza

- `delta_lealtad_liderazgo`/`umbral_reputacion_descalificante`
  PROVISIONALES, sin calibrar contra el harness completo.
- Con esto, **las 5 piezas del informe de "capa de comunicación"
  quedarían cerradas** (conflicto verbal, memoria espacial compartida,
  ocio consciente, sonido físico 4a+4b, rumor+liderazgo 5a+5b).
- Mercadería, encargos, confianza para pedir/contar algo — ideas de
  Diego para el futuro, ninguna diseñada, candidatas naturales a
  reutilizar el mismo primitivo de `Relaciones`/rumor sin mecanismo
  nuevo de fondo.
- Sigue sin resolver el hallazgo de fondo, ya documentado varias veces
  en este proyecto: los asentamientos rara vez se forman en juego
  libre por la fragilidad de población — este círculo puede quedar tan
  invisible como amistad/pareja/parentesco hasta que esa investigación
  se retome.
