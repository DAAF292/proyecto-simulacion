# Evasión por vuelo frente a depredador terrestre

Fecha: 2026-09-17. Origen: hallazgo del harness completo (15×10000
ticks) -- águila (especie nueva de esta misma sesión) no aparece viva
en NINGUNA de las 15 semillas al cierre. Verificado el mecanismo real:
`lobo caza aguila` es presa válida GARANTIZADA por ratio de peso (peor
caso de disposición 0.690, muy por encima del umbral 0.5) -- el mismo
mecanismo de ratio de peso sin lista de dieta que ya usa el motor para
cualquier par depredador/presa, aplicado sin ningún ajuste por que la
presa vuele.

Diego señaló el problema de física real: un lobo no puede perseguir
algo que remonta el vuelo -- el círculo de vuelo (mismo día, antes de
este) tocó movimiento (`_aplicar_movimiento`, ignora agua/relieve en
superficie) y "posarse" al dormir, pero nunca depredación. Un ave
debería ser mecánicamente más difícil de atrapar para un depredador que
no vuela, sin que ningún bono (agresividad, manada, arma) lo compense --
el cuello de botella es físico, no de fuerza.

## Diseño

### Qué NO se toca

- `_es_presa_valida` (`sistema_depredacion.py`) -- una presa que vuela
  sigue siendo un candidato válido para el chequeo de contacto y para
  `sistema_movimiento.py::_calcular_caza` (el depredador sigue
  persiguiéndola, físicamente correcto: un lobo sí intenta cazar un
  ave, solo que casi nunca lo consigue). No se gatea aquí a propósito --
  cambiar esto también apagaría la persecución, que es un
  comportamiento razonable de por sí (un depredador no "sabe" de
  antemano que va a fallar).
- Ningún bono nuevo para el sentido contrario (depredador que SÍ vuela,
  como águila, contra presa terrestre) -- su caza normal ya cubre eso
  sin cambios, el círculo de vuelo de hoy ya lo dejó funcionando vía
  reutilización de `sistema_depredacion.py` sin modificar nada.

### Qué cambia

En `_resolver_ataque` (paso 1, cálculo de `prob_exito`), justo antes del
clamp final a `[captura_prob_min, captura_prob_max]`: si la presa vuela
y el cazador NO vuela, `prob_exito` se fuerza directamente al SUELO ya
existente (`self.captura_prob_min`, típicamente 0.05) -- se descarta
cualquier bono acumulado hasta ese punto (disposición por peso,
agresividad/valentía, bono de manada, penalización por arma empuñada de
la presa).

Se reutiliza el suelo YA EXISTENTE en vez de inventar una segunda
constante ("evasión total" vs. "suelo normal de captura") -- modela
"rara vez, por oportunismo" (la presa está en tierra comiendo,
durmiendo, herida) sin duplicar el concepto. Forzar el valor entero
(no restar una penalización) es deliberado: ningún acumulado de bonos
(por fuerte, numeroso o armado que sea el grupo cazador) debería poder
compensar la ventaja física de volar -- si en cambio se restara una
penalización fija, un cazador con suficientes bonos acumulados podría
seguir superando el umbral, lo que contradice la física que motiva este
círculo.

Nuevo helper `_vuela(especie: str) -> bool` en `SistemaDepredacion`,
mismo patrón de lectura de `rangos_raciales` que ya usa
`sistema_movimiento.py`.

## Qué deja abierto, sin resolver aquí

- La otra tensión señalada por Diego en la misma conversación (¿es
  realista que lobo trate a zorro como presa garantizada?) es un
  círculo aparte -- no es un problema de vuelo, es una tensión general
  entre "leyes neutras por peso" y "frecuencia ecológica real" que
  afecta a cualquier par de especies, no solo a voladores.
- Si algún día existe un depredador terrestre que además ataque desde
  emboscada o sorpresa, el suelo de 0.05 seguiría aplicando sin
  distinción -- no se modela "presa distraída/dormida" como un estado
  aparte, mismo nivel de abstracción que el resto del sistema.
