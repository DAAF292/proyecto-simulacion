# Armas fabricadas — primer círculo del arco herramientas/utensilios/armas

Fecha: 2026-09-01
Estado: aprobado por Diego (2026-09-01), pendiente de implementación

## Contexto y alcance

Cimiento de "capacidad de sostener/usar objetos" (`componentes/agarre.py`,
2026-08-31) ya está construido, y su primer consumidor real (fuego
controlado, `componentes/fogata.py`) ya está implementado y verificado.
Diego pidió retomar el arco original ("la base es usar herramientas... un
palo para defenderse, o una roca, después de eso usar dos rocas para hacer
un fuego, herramientas básicas, hachas utensilios") planteando ahora
herramientas/utensilios/armas.

**Decisión de alcance (conversación de brainstorming, 2026-09-01):**
"herramientas, utensilios y armas" son 2-3 subsistemas independientes, no
uno solo — armas simples fabricadas, herramientas de trabajo (aceleran
recolección/construcción), utensilios de cocina (dependen de comida
elaborada, que no existe). Este documento cubre **solo el primero: armas
simples fabricadas**, elegido por no depender de nada que falte todavía y
por tener ya un punto de enganche real en el motor
(`reduccion_prob_captura_por_agarre`, `config/combate.yaml`).

Herramientas de trabajo y utensilios de cocina quedan fuera de este
círculo, a la espera de su propio ciclo de diseño.

## Decisiones de diseño cerradas con Diego

1. **Fabricar es un acto consciente distinto de sujetar un objeto en
   crudo.** Hoy cualquier objeto en `Agarre.objetos` (recogido gratis y
   sin causa al RECOLECTAR) ya da un bono de defensa binario, igual para
   cualquier especie. Fabricar un arma real es un paso adicional,
   exclusivo de especies con agencia consciente (gnomo, mismo umbral
   `decision.umbral_consciencia_agencia` que ya usan `CONSTRUIR`/
   `ENCENDER_FUEGO`). Lobo/ardilla siguen exactamente igual que hoy — el
   bono binario por sujetar en crudo, sin cambios.
2. **Alcance del efecto: solo defensa, reforzada.** Este círculo no toca
   la mitad ofensiva de `_resolver_ataque` (un cazador armado no gana
   bono de caza) ni el resolutor de conflicto social
   (`nucleo/conflicto.py`). Un arma fabricada solo mejora la probabilidad
   de NO ser capturado cuando el portador es la presa.
3. **Causalidad: la utilidad de fabricar responde a una necesidad real
   (`Necesidades.seguridad`), no a una regla universal.** Mismo principio
   que la corrección de piedra suelta para el fuego ("un ser consciente
   que jamás ha experimentado el frío... no debería necesitar piedras")
   — aquí, un individuo que nunca ha sentido inseguridad real no debe
   desarrollar interés en fabricar un arma. A diferencia del fuego, **no
   hace falta una segunda cadena causal en RECOLECTAR**: el material
   crudo (madera/piedra) ya se agarra de forma oportunista y sin causa
   por el mecanismo genérico existente (diseño original de Agarre, "un
   palo para defenderse, o una roca") — fabricar solo actúa sobre
   material que YA está sujeto.
4. **Nombre diferenciado por material, no un marcador genérico.** Aunque
   el efecto es idéntico en este círculo sea cual sea el material de
   origen, el nombre queda listo para cuando un círculo futuro quiera
   diferenciar el efecto por tipo de arma, y da más riqueza a
   eventos/crónica desde ya: `madera → lanza`, `piedra → hacha_mano`.

## Diseño técnico

### 1. Catálogo de materiales — `config/materiales.yaml`

Nueva propiedad `apto_arma: bool` por material, mismo patrón que
`apto_construccion`. Para este círculo: `madera` y `piedra` (sustrato)
pasan a `apto_arma: true`. El resto del catálogo (arcilla, arena, tierra,
fibra, hierba_seca, hueso, tejido_blando) queda sin la propiedad
(default `False` vía `.get()`, mismo criterio que el resto del catálogo).
`hierro`/`cobre` quedan fuera a propósito — candidatos de un círculo
futuro de armas metálicas, no de este.

Nuevo mapa `nombre_arma_por_material` (mismo fichero, sección
`construccion` o una sección `armas` nueva — a decidir en la
implementación, sin impacto en el diseño): `{madera: lanza, piedra:
hacha_mano}`.

### 2. `Accion.FABRICAR_ARMA` — nueva, `componentes/intencion.py` +
   `sistemas/sistema_decision.py`

Mismo patrón que `Accion.ENCENDER_FUEGO`:

- Gate: `cap_mental.consciencia >= umbral_consciencia_agencia`.
- Utilidad: `1.0 - necesidades.seguridad`.
- Se fuerza a `0.0` si:
  - el individuo ya tiene un arma fabricada en `Agarre.objetos`
    (`"lanza"` o `"hacha_mano"` presentes), o
  - no tiene ningún objeto `apto_arma` sujeto todavía (ni madera ni
    piedra en crudo).
- **Sin rama causal nueva en RECOLECTAR** (ver decisión 3 arriba) — a
  diferencia de `ENCENDER_FUEGO`, que sí empuja `utilidad_recolectar`
  hacia arriba cuando faltan piedras.

### 3. Resolución — nuevo `_resolver_fabricar_arma` en
   `sistemas/sistema_recursos.py`

Un solo tick, determinista (sin tirada de éxito — a diferencia de
encender fuego, tallar un palo no es un evento de azar equivalente a que
prenda una chispa): busca el primer objeto en `Agarre.objetos` cuyo
material sea `apto_arma`, lo sustituye in situ por su nombre de arma
(`nombre_arma_por_material`). Mismo slot de la lista, no consume espacio
nuevo ni toca `Inventario`/capacidad de carga. Emite un Evento
(`ArmaFabricada`, severidad NOTABLE, mismo criterio que `FuegoEncendido`)
con `{x, y, zona_idx, arma}`.

Despacho: `sistema_recursos.py:ejecutar()` gana una rama
`elif intencion.accion == Accion.FABRICAR_ARMA:` junto a las de
`CONSTRUIR`/`RECOLECTAR`/`ENCENDER_FUEGO`, mismo patrón.

### 4. Efecto — `sistemas/sistema_depredacion.py:_resolver_ataque`

Nueva constante `reduccion_prob_captura_por_arma_fabricada`
(`config/combate.yaml`, sección `depredacion`, PROVISIONAL — valor de
partida 0.2, mayor que la actual `reduccion_prob_captura_por_agarre=0.1`).

Lógica (sustituye el bloque binario actual):
```
if agarre_presa tiene "lanza" o "hacha_mano":
    prob_exito -= reduccion_prob_captura_por_arma_fabricada
elif agarre_presa tiene algún objeto:
    prob_exito -= reduccion_prob_captura_por_agarre
```
No aditivo — un arma fabricada no suma su reducción a la del objeto
crudo, la sustituye.

### 5. Persistencia

Sin cambios de esquema. `Agarre.objetos` ya se persiste como lista de
strings (`VERSION_ESQUEMA 0.29-fase0`) — el marcador de arma
(`"lanza"`/`"hacha_mano"`) cabe sin tocar `nucleo/persistencia.py` ni
subir la versión.

## Fuera de alcance (explícito)

- Bono ofensivo en caza para un portador de arma.
- Integración con `nucleo/conflicto.py` (disputa por refugio u otro
  agravio).
- Diferenciar el efecto numérico por tipo de arma (lanza vs. hacha_mano)
  — mismo valor de reducción para ambas en este círculo, pese al nombre
  distinto.
- Herramientas de trabajo (aceleran recolección/construcción/minería).
- Utensilios de cocina (dependen de comida elaborada, inexistente hoy).
- Soltar/gastar/perder un arma fabricada — mismo límite conocido ya
  documentado en `componentes/agarre.py` para cualquier objeto sujeto.
- Fabricar arma con hierro/cobre.

## Verificación planeada

1. Arnés dirigido: gate causal (sin inseguridad nunca fabrica; con
   inseguridad real y material crudo sujeto, fabrica; ya con arma
   fabricada, utilidad cae a 0); resolución determinista reemplaza el
   objeto correcto según el material; efecto medido estadísticamente
   (misma metodología que Agarre — N ataques con presa armada con
   `lanza`/`hacha_mano` vs. con objeto crudo vs. desarmada, confirmando
   que la reducción observada coincide con la configurada).
2. Varias semillas × varios miles de ticks de motor real sin
   intervención (`BOSQUE_AUTO_TICKS` + pipeline completo), confirmando
   que se fabrican armas de verdad en juego normal, no solo en el
   arnés dirigido.
3. Suite de 22 tests existentes en verde.

## Pendiente explícito tras este círculo (a documentar en CLAUDE.md una
## vez implementado y verificado)

- `reduccion_prob_captura_por_arma_fabricada` PROVISIONAL, sin calibrar
  contra el harness completo (15 semillas × 12000 ticks).
- Bono ofensivo, integración con conflicto, diferenciación por tipo de
  arma, herramientas de trabajo, utensilios de cocina: todos señalados
  como próximos círculos posibles, ninguno decidido todavía.
