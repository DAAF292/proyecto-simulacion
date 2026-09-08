# Cómo cocinar — Accion.COCINAR, comida elaborada y toxicidad real — diseño

Fecha: 2026-09-08. Cierra el círculo abierto por
`docs/superpowers/specs/2026-09-08-sistema-comidas-design.md` (dieta
real de gnomo + catálogo `toxico_crudo`, sin ningún consumidor
todavía). Este círculo activa el mecanismo real y completo: cocinar,
comida elaborada, y la toxicidad de crudo con su cura -- las cocinas
comunes (edificio) quedan para el círculo siguiente del arco
"dinámicas internas de asentamiento".

## Decisiones cerradas con Diego, en orden

1. **`Accion.COCINAR` dedicada**, no un efecto pasivo -- Diego, contra
   la recomendación inicial de Claude (que prefería un efecto pasivo en
   la Fogata para no inventar una curva de utilidad nueva, dado el
   historial de este proyecto con curvas nuevas casi inalcanzables --
   ver `ENCENDER_FUEGO`/"piedra suelta"). Se acepta el riesgo,
   mitigado con una utilidad BASE FIJA (mismo patrón que
   `CONSTRUIR`/`RECOLECTAR`, no una fórmula derivada de una necesidad
   real) en vez de inventar una fórmula compleja.
2. **Intoxicación = muerte probabilística**, mismo molde exacto que
   `probabilidad_muerte_saciedad_critica`/`_deshidratacion`/
   `_ahogamiento` ya existentes -- Diego, tras plantearle explícitamente
   el riesgo (gnomo es la especie más frágil de todo el catálogo, con
   el peor perfil reproductivo, y esto introduce un vector de muerte
   nuevo). Mitigado con una probabilidad base deliberadamente muy baja
   y verificación obligatoria contra el motor real antes de confiar en
   ella.
3. **Comida elaborada = clave con sufijo `_elaborada`** dentro del
   mismo `Inventario.provisiones`, con un multiplicador ÚNICO y
   universal sobre `valor_nutricional`/`valor_hidratacion` -- decisión
   ya cerrada en el círculo anterior, sin tabla de recetas por
   alimento.
4. **La toxicidad se elimina POR COMPLETO al cocinar, no se reduce**:
   la versión `_elaborada` nunca tira la probabilidad de intoxicación,
   sin importar si el recurso base es `toxico_crudo`. Binario, no
   gradual -- coherente con "cocinar es la cura", no "cocinar mejora
   las probabilidades".
5. **Se prefiere comer lo elaborado sobre lo crudo** cuando ambas
   versiones del mismo recurso existen guardadas -- decisión racional
   simple y universal, no autoría por individuo.
6. **Hallazgo real de diseño, mejora dirigida incluida**: la lógica de
   morir (instanciar `Necromasa`, emitir el evento `Muerte`, purgar la
   entidad) vive hoy solo dentro de
   `sistema_necesidades.py:_resolver_deceso`, sin ser invocable desde
   otro sistema. Se extrae a `nucleo/entidad.py:procesar_deceso(...)`
   para que `sistema_recursos.py` pueda matar por intoxicación sin
   duplicar esa lógica -- `_resolver_deceso` pasa a ser un wrapper de
   una línea, comportamiento idéntico (regresión explícita en tests).

## Alcance

**Dentro:**

1. `nucleo/entidad.py`: extracción de `procesar_deceso`:
   ```python
   def procesar_deceso(
       gestor: GestorEntidades,
       bus_eventos: BusEventos,
       tick_actual: int,
       entidad_id: int,
       pos_x: int,
       pos_y: int,
       dims: DimensionesFisicas,
       ident: Identidad,
       causa: str,
       zona_idx: int = 0,
       fraccion_masa_seca: float = 0.35,
       fraccion_hueso: float = 0.15,
       fraccion_agua_tisular: float = 0.65,
       tasa_putrefaccion: float = 0.05,
   ) -> None:
   ```
   Cuerpo idéntico al de `_resolver_deceso` actual (mismas llamadas a
   `componer_necromasa`/`crear_necromasa`, mismo `Evento` `"Muerte"`,
   mismo `gestor.eliminar_entidad`). Requiere importar
   `BusEventos, Evento, Severidad` de `nucleo.eventos` en
   `nucleo/entidad.py` (sin ciclo -- `nucleo/eventos.py` no importa
   nada de `nucleo/entidad.py`). `sistema_necesidades.py:_resolver_deceso`
   pasa a llamar a esta función con sus propios
   `self.fraccion_masa_seca`/`self.fraccion_hueso`/
   `self.fraccion_agua_tisular` ya cacheados -- sin cambio de
   comportamiento.
2. `componentes/flora` / catálogo: sin cambios (ya cerrado en el
   círculo anterior).
3. `componentes/intencion.py`: `Accion.COCINAR` nuevo.
4. `sistemas/sistema_decision.py`: bloque nuevo, mismo molde que
   `ENCENDER_FUEGO` (búscalo como referencia exacta de dónde insertar,
   justo después):
   ```python
   utilidad_cocinar = 0.0
   if cap_mental.consciencia >= umbral_consciencia_agencia:
       if fogata_en(gestor, pos.x, pos.y, pos.zona_idx) is not None:
           provisiones = inventario.provisiones if inventario is not None else {}
           tiene_crudo = any(
               not r.endswith("_elaborada") and c > 0.0 for r, c in provisiones.items()
           )
           if tiene_crudo:
               utilidad_cocinar = utilidad_cocinar_base
   ```
   Añadido a la tupla `candidatas`, junto a `(utilidad_encender_fuego,
   Accion.ENCENDER_FUEGO)`: `(utilidad_cocinar, Accion.COCINAR)`. Sin
   desplazamiento -- se resuelve donde ya se está, mismo criterio que
   `ENCENDER_FUEGO`/`RECOLECTAR`.
5. `nucleo/comida.py` (nuevo, funciones puras, mismo patrón que
   `nucleo/intercambio.py`):
   ```python
   def elaborar_recurso(provisiones: dict[str, float], recurso: str, cantidad_max: float) -> float:
       """Mueve hasta cantidad_max kg de `recurso` (crudo) a
       "<recurso>_elaborada" DENTRO del mismo dict -- no es una
       transferencia entre dos entidades (ver nucleo/intercambio.py),
       es una transformación del propio recurso. Devuelve la cantidad
       real transformada."""

   def es_elaborado(recurso: str) -> bool:
       return recurso.endswith("_elaborada")

   def recurso_base(recurso: str) -> str:
       """"manzanas_elaborada" -> "manzanas"; si no tiene el sufijo,
       devuelve tal cual."""
   ```
6. `sistemas/sistema_recursos.py`:
   - `ejecutar()` gana una rama nueva, mismo molde que
     `elif intencion.accion == Accion.ENCENDER_FUEGO:` (buscar esa rama
     como referencia exacta de dónde insertar): `elif intencion.accion
     == Accion.COCINAR: self._resolver_cocinar(gestor, eid, pos.zona_idx)`
     (usa `celda`/`pos.x`/`pos.y` ya resueltos en el cuerpo del bucle,
     igual que las demás ramas).
   - `_resolver_cocinar(gestor, entidad_id, celda, pos_x, pos_y, zona_idx)`
     (nuevo): obtiene `Inventario`, si no hay Fogata activa o no hay
     nada crudo, no hace nada (defensivo, la compuerta ya lo filtra en
     decisión); si hay, `elaborar_recurso` sobre el primer recurso crudo
     no vacío (orden determinista, mismo criterio que robo/compartir),
     topado por `tasa_cocinar_kg_tick`.
   - `_resolver_comer`: los lookups `self.nutricion_flora.get(nombre, 0.2)`/
     `self.hidratacion_flora.get(nombre, 0.05)` (hay TRES puntos: forraje
     de celda, salida de provisiones -- ver círculo anterior) se
     envuelven en un helper `_valor_nutricional_efectivo`/
     `_valor_hidratacion_efectivo` que, si `es_elaborado(nombre)`,
     multiplican el valor del `recurso_base(nombre)` por
     `factor_mejora_elaboracion`.
   - Toxicidad: `_cachear_configuracion` gana un diccionario nuevo,
     extendiendo EL MISMO bucle que ya rellena `self.nutricion_flora`/
     `self.hidratacion_flora` (`for esp_data in self.especies_flora.values():
     for rec in esp_data.get("recursos", []): ...`) -- no un bucle
     aparte: `self.toxico_crudo_flora[nom] = bool(rec.get("toxico_crudo", False))`.
     Nuevo chequeo en los DOS puntos donde hoy se come algo crudo
     (forraje de celda y salida de provisiones -- NUNCA en la
     entrada/guardado, comer y guardar son momentos distintos), **gateado
     a consciente** (`cap_mental is not None and cap_mental.consciencia
     >= self.umbral_consciencia_agencia`, mismo umbral que ya usan
     `RECOLECTAR`/la entrada de provisiones -- SIN este gate, conejo y
     caballo (que también comen `raices`/`bayas_espinosas` en su dieta,
     ver `config/poblacion.yaml`) quedarían expuestos a un vector de
     muerte nuevo sin ninguna forma de cocinar jamás -- fauna queda
     aplazada, no descartada, mismo criterio que el resto de este arco):
     si el consciente cumple el gate, `not es_elaborado(nombre)`, y
     `self.toxico_crudo_flora.get(recurso_base(nombre), False)`,
     tirada `self.rng.random() < self.probabilidad_muerte_intoxicacion_base
     * (1.0 - dims.resistencia_enfermedad)` -- si dispara, llama a
     `procesar_deceso(..., causa="intoxicacion")` y **retorna
     inmediatamente** (la entidad ya no existe, nada más que hacer en
     este método). Necesita `DimensionesFisicas` de la entidad (ya se
     importa en este fichero, hoy no se obtenía en `_resolver_comer` --
     se añade el fetch).
   - Salida de provisiones (círculo anterior): orden de búsqueda
     explícito para evitar ambigüedad -- para CADA `r` de la dieta, en
     su orden ya establecido, se prueba primero `f"{r}_elaborada"` y
     luego `r` crudo, antes de pasar al siguiente `r` de la dieta. No
     es una búsqueda global de "cualquier elaborada en todo el
     inventario" -- se prefiere lo elaborado del PRIMER alimento de la
     dieta que tenga algo guardado (crudo o elaborado), no lo elaborado
     de un alimento más abajo en la dieta por encima de lo crudo de uno
     más arriba.
7. Config nueva (PROVISIONAL, sin calibrar):
   - `config/fisiologia.yaml`, sección `decision:` (junto a
     `utilidad_construir_base`): `utilidad_cocinar_base: 0.25` (por
     debajo de `utilidad_construir_base`=0.3 -- cocinar es preparación
     para más tarde, ligeramente menos prioritario que terminar el
     refugio propio).
   - `config/fisiologia.yaml`, sección `consumo:` (junto a
     `tasa_consumo_al_comer`): `tasa_cocinar_kg_tick: 0.5` (mismo orden
     de magnitud que `tasa_consumo_al_comer`).
   - `config/fisiologia.yaml`, sección `necesidades.defecto` (junto a
     las otras `probabilidad_muerte_*`): `probabilidad_muerte_intoxicacion_base:
     0.001` -- deliberadamente MUY por debajo de
     `probabilidad_muerte_saciedad_critica`/`_deshidratacion` (0.005 en
     el catálogo por defecto, algunas especies ya bajadas a 0.0004) --
     un vector de muerte nuevo para la especie más frágil exige empezar
     conservador, no igualar a las tasas ya calibradas de otras causas.
   - `config/flora.yaml` (nueva sección `elaboracion:`, junto a
     `descomposicion:`): `factor_mejora_elaboracion: 1.5`.
8. Tests dirigidos + verificación obligatoria contra el motor real, con
   énfasis explícito en medir el impacto real de la intoxicación sobre
   la supervivencia de gnomo, no solo confirmar que el mecanismo
   dispara.

**Fuera de alcance, explícito:**

- Cocinas comunes (edificio) -- círculo siguiente del mismo arco.
- Cualquier reducción PARCIAL de toxicidad -- binario, ya decidido.
- Alquimia, refinamiento de metales, magia -- visión a futuro, sin
  diseñar.
- Toxicidad para fauna -- ninguna especie fauna tiene provisiones ni
  cocina (gateado a consciente, igual que el resto del arco); si comen
  algo `toxico_crudo` de la celda directamente, HOY no se les aplica el
  chequeo -- confirmar explícitamente este alcance en testing (mismo
  criterio que el resto del arco: mecanismo pensado para consciente,
  fauna queda aplazada, no descartada).

## Testing

- `procesar_deceso`: mismo comportamiento observable que
  `_resolver_deceso` antes de la extracción (regresión: necromasa
  creada, evento `Muerte` con los mismos campos, entidad purgada).
- `elaborar_recurso`/`es_elaborado`/`recurso_base`: transforma la
  cantidad correcta, topada por lo disponible y por `cantidad_max`;
  purga la clave cruda al vaciarse; el sufijo se detecta y se separa
  correctamente.
- `Accion.COCINAR`: utilidad 0.0 sin Fogata, sin consciencia, o sin
  nada crudo en provisiones; `utilidad_cocinar_base` cuando las tres
  condiciones se cumplen.
- `_resolver_cocinar`: transforma hasta la tasa configurada del primer
  recurso crudo; dos llamadas sucesivas siguen transformando el mismo
  recurso hasta agotarlo antes de pasar al siguiente.
- Nutrición/hidratación efectiva: un recurso `_elaborada` da
  `factor_mejora_elaboracion` veces el valor del recurso crudo
  correspondiente, en ambos puntos de consumo (celda y provisiones).
- Toxicidad: comer un recurso crudo `toxico_crudo` con la tirada
  forzada a disparar mata a la entidad (verificar `procesar_deceso`
  invocado con causa "intoxicacion", vía el evento emitido); la MISMA
  situación con la versión `_elaborada` del mismo recurso NUNCA mata,
  con cualquier tirada; `resistencia_enfermedad` alta reduce la
  probabilidad efectiva medible.
- Preferencia por lo elaborado: con ambas versiones guardadas, se
  consume primero la `_elaborada`.
- **Fauna exenta**: conejo o caballo comiendo `raices`/`bayas_espinosas`
  crudas de la celda, con la tirada forzada a disparar, NUNCA muere por
  intoxicación -- el gate de consciencia lo evita por completo
  (regresión explícita, dado que ambas especies ya tenían estos
  recursos en su dieta antes de esta pieza).
- **Verificación obligatoria contra `BOSQUE_AUTO_TICKS` Y un arnés
  dirigido de varias semillas nuevas, no opcional**: medir la tasa de
  muertes por intoxicación real de gnomo frente al resto de causas ya
  conocidas, y si la población de gnomo se resiente de forma medible
  frente al estado actual (sin este círculo). Si el impacto resulta
  demasiado alto, la probabilidad base es el primer valor a revisar
  antes de dar la pieza por buena -- reportar con la misma honestidad
  ya aplicada al resto de esta sesión.

## Pendiente real tras esta pieza

- Las cuatro constantes nuevas (`utilidad_cocinar_base`,
  `tasa_cocinar_kg_tick`, `probabilidad_muerte_intoxicacion_base`,
  `factor_mejora_elaboracion`) PROVISIONALES, sin calibrar contra el
  harness completo.
- Cocinas comunes (edificio) es el siguiente círculo real del arco.
- Toxicidad para fauna, memoria de "sitio donde algo me hizo daño"
  (conectaría con `nucleo/memoria.py` a futuro), y cualquier variación
  de la toxicidad por atributo más allá de `resistencia_enfermedad`
  quedan fuera, sin necesidad real todavía.
