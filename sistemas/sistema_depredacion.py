"""SistemaDepredacion (paso 12.3): resuelve la captura cuando quien caza
(Intencion.CAZAR) ya esta en la misma celda que una presa valida --
SistemaMovimiento ya hizo el trabajo de acercarlos, este sistema solo
decide si la caza tiene exito una vez hay contacto. Mismo reparto de
responsabilidades que comer/SistemaRecursos: movimiento decide adonde ir,
un sistema aparte resuelve el consumo cuando ya se llego. Aqui la "celda
con recurso" es, literalmente, otro individuo.

"Presa valida" reutiliza el mismo criterio del paso 12.2 (peso menor +
magnitud_disposicion_por_peso por encima del umbral) -- no hay una
segunda nocion de presa en este archivo, para no arriesgarse a que las
dos definiciones diverjan con el tiempo.

Resolucion de captura: tirada de probabilidad. Base = magnitud de
disposicion por peso (nucleo/disposicion.py) entre cazador y presa;
ajuste = (agresividad del cazador - evasion de la presa) * factor de
config, acotado entre captura_prob_min y captura_prob_max para que ni el
emparejamiento mas favorable ni el mas desfavorable sea un resultado
seguro. provisional en su totalidad -- ver config/constantes.yaml.

evasion (Bloque B del plan de migracion a criatura.docx): sustituye a la
vieja Categoria.resistencia, que no representaba ningun concepto real del
modelo nuevo. Decision explicita tomada con Diego: escapar de una
captura depende de forcejear/esquivar, no de un aguante generico, asi que
evasion = (fuerza + agilidad) / 2 de la presa -- combinacion simetrica y
simple, marcada como hipotesis de partida, no calibrada contra el motor
en marcha (mismo estatus que el resto de esta formula).

Un fallo no tiene coste explicito aqui: si la presa sigue en la misma
celda el siguiente tick (porque su propia intencion no la aleja), el
cazador simplemente vuelve a intentarlo -- no hace falta cooldown ni
temporizador, sale solo del bucle normal de decision-movimiento-captura.

Herida en vez de muerte instantanea (Bloque C2 del plan de adaptacion a
criatura.docx, propuesta discutida y confirmada con Diego -- el
documento dejaba esto como pendiente explicito, sin mecanica de
aplicacion definida): un contacto con exito ya no mata directamente,
inflige dano a la vitalidad de la presa -- dano_bruto = fuerza del
cazador * factor_dano_captura (config, provisional). La muerte pasa a
ser vitalidad <= 0.0, resuelta aqui mismo tras aplicar el dano. Reutiliza
fuerza, que hasta ahora solo alimentaba la evasion, dandole un segundo
consumidor con sentido: un cazador mas fuerte hiere mas por golpe.

Escalares de techo (correccion posterior, discutida y confirmada con
Diego -- vitalidad_maxima llevaba desde el Bloque C1 sin ningun
consumidor real): dano_bruto ya no se aplica directo sobre la escala
[0,1] del pool, se divide por DimensionesFisicas.vitalidad_maxima DE LA
PRESA antes de restarlo -- dano_fraccional = dano_bruto /
vitalidad_maxima. Una presa con vitalidad_maxima alta (mas "aguante
relativo") absorbe mejor el mismo golpe bruto que una con vitalidad_maxima
baja. Como ningun individuo llega a vitalidad_maxima=1.0 (rango racial
tope 0.9), esto amplifica todo el dano respecto a antes de este cambio.

LIMITE CONOCIDO investigado en la fase de calibracion posterior a Bloque G
(ver config/constantes.yaml, seccion 'depredacion', para el detalle
completo con datos): se especulo que esta amplificacion obligaria a
recalibrar factor_dano_captura a la baja -- se probo con el motor en
marcha (5 semillas, 600 ticks, factor 0.4 vs. 0.13) y NO es asi. El
cuello de botella real de la sostenibilidad de la caza no es la letalidad
del golpe, es la frecuencia de contacto: un lobo con intencion CAZAR
percibe una presa dentro de su radio en menos del 10% de los ticks en
todas las semillas probadas, incluso llevando su agudeza_sensorial al
maximo teorico. Densidad de poblacion sobre el tamano de mapa actual, no
un numero de este archivo -- limite estructural de la fase sin
reproduccion, no un bug de esta formula.

Una presa que sobrevive herida se queda con la vitalidad reducida y sigue
en juego -- el cazador puede volver a intentarlo el siguiente tick si
sigue en contacto, exactamente igual que con un fallo de captura. Se
emite un evento Herida (NOTABLE) para que quede en la cronica igual que
una muerte, distinto de Muerte.

Satisfaccion de la saciedad (Bloque A del plan de migracion: convencion
1.0=pleno/0.0=crisis): solo una captura LETAL deja al cazador con
saciedad=1.0 -- un golpe que solo hiere no alimenta (no hay todavia
nocion de "cuanta carne" deja un cadaver concreto, pero comerse una
presa herida y viva no tiene sentido). provisional, revisar si se siente
demasiado generoso una vez observada la dinamica de poblacion de ambas
especies.
"""
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Identidad
from componentes.intencion import Accion, Intencion
from componentes.necesidades import Necesidades
from componentes.pool_fisico import PoolFisico
from componentes.posicion import Posicion
from componentes.temperamento import Temperamento
from nucleo.disposicion import id_en_contacto_por_disposicion, magnitud_disposicion_por_peso
from nucleo.eventos import BusEventos, Evento, Severidad


def actualizar(gestor, config: dict, rng, bus: BusEventos, tick_actual: int) -> None:
    umbral_disposicion = config["depredacion"]["umbral_disposicion_presa"]
    factor_ajuste = config["depredacion"]["factor_ajuste_agresividad_evasion"]
    factor_dano = config["depredacion"]["factor_dano_captura"]
    p_min = config["depredacion"]["captura_prob_min"]
    p_max = config["depredacion"]["captura_prob_max"]

    # list(...) porque eliminar_entidad() puede mutar los diccionarios
    # del gestor mientras iteramos (mismo motivo que en SistemaNecesidades).
    for id_cazador in list(gestor.entidades_con(Posicion, Intencion, DimensionesFisicas, Temperamento, Necesidades)):
        intencion = gestor.obtener_componente(id_cazador, Intencion)
        if intencion is None or intencion.accion != Accion.CAZAR:
            continue

        posicion = gestor.obtener_componente(id_cazador, Posicion)
        dimensiones_cazador = gestor.obtener_componente(id_cazador, DimensionesFisicas)
        temperamento_cazador = gestor.obtener_componente(id_cazador, Temperamento)

        id_presa = id_en_contacto_por_disposicion(
            gestor, id_cazador, posicion.x, posicion.y,
            dimensiones_cazador.peso, umbral_disposicion, buscar_mayor=False,
        )
        if id_presa is None:
            continue

        dimensiones_presa = gestor.obtener_componente(id_presa, DimensionesFisicas)
        magnitud = magnitud_disposicion_por_peso(dimensiones_cazador.peso, dimensiones_presa.peso)
        evasion_presa = (dimensiones_presa.fuerza + dimensiones_presa.agilidad) / 2
        ajuste = (temperamento_cazador.agresividad - evasion_presa) * factor_ajuste
        p_captura = max(p_min, min(p_max, magnitud + ajuste))

        if rng.random() >= p_captura:
            continue  # la presa escapa este intento, se reintenta el siguiente tick

        pool_presa = gestor.obtener_componente(id_presa, PoolFisico)
        dano_bruto = dimensiones_cazador.fuerza * factor_dano
        dano_fraccional = dano_bruto / dimensiones_presa.vitalidad_maxima
        pool_presa.vitalidad = max(0.0, pool_presa.vitalidad - dano_fraccional)

        identidad_presa = gestor.obtener_componente(id_presa, Identidad)

        if pool_presa.vitalidad > 0.0:
            # herida, no muerte -- la presa sigue en el gestor.
            datos_herida = {"causa": "depredacion", "vitalidad_restante": round(pool_presa.vitalidad, 3)}
            if identidad_presa is not None:
                datos_herida["especie"] = identidad_presa.especie.value
                if identidad_presa.nombre:
                    datos_herida["nombre"] = identidad_presa.nombre
            bus.emitir(
                Evento(
                    tipo="Herida",
                    severidad=Severidad.NOTABLE,
                    tick=tick_actual,
                    entidad_id=id_presa,
                    datos=datos_herida,
                )
            )
            continue

        # captura letal -- leer identidad ANTES de eliminar (una vez
        # fuera del gestor nadie puede volver a preguntarle su especie o
        # nombre, mismo motivo que en SistemaNecesidades).
        datos_muerte = {"causa": "depredacion"}
        if identidad_presa is not None:
            datos_muerte["especie"] = identidad_presa.especie.value
            if identidad_presa.nombre:
                datos_muerte["nombre"] = identidad_presa.nombre
        # posicion del cazador == posicion de la presa (captura es por
        # contacto, comparten celda) -- para Bloque F2 (presenciar una
        # muerte dentro del radio de percepcion).
        datos_muerte["x"] = posicion.x
        datos_muerte["y"] = posicion.y

        gestor.eliminar_entidad(id_presa)
        bus.emitir(
            Evento(
                tipo="Muerte",
                severidad=Severidad.NOTABLE,
                tick=tick_actual,
                entidad_id=id_presa,
                datos=datos_muerte,
            )
        )

        necesidades_cazador = gestor.obtener_componente(id_cazador, Necesidades)
        necesidades_cazador.saciedad = 1.0
