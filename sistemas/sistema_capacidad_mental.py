"""SistemaCapacidadMental (Bloque F1 del plan de adaptacion a
criatura.docx, seccion 4.2): regeneracion pasiva del pool de estabilidad
mental. Paralelo exacto de SistemaCapacidadFisica para vitalidad --
mismo patron, mismo vinculo cruzado con energia.

estabilidad se repone con CapacidadMental.resiliencia, mas lenta cuanto
mas baja este Necesidades.energia -- criatura.docx (seccion 4.2) dice
literalmente "se repone con resiliencia, mas lenta en las mismas
condiciones que ralentizan curacion"; el unico condicionante documentado
para curacion es la energia baja (seccion 6), asi que se reutiliza la
misma condicion aqui en vez de inventar una nueva.

Bloque F2 (estres -- discutido y confirmado con Diego antes de escribir
esto, mismo criterio que ya se aplico en C2): dos fuentes de consumo.

- Amenaza sostenida: en vez de un umbral + contador de "N ticks
  consecutivos" (lo que se propuso originalmente), el drenaje es
  CONTINUO y proporcional a (1 - Necesidades.seguridad) cada tick --
  mismo patron "urgencia = 1 - necesidad" que ya usa sistema_decision.py
  en todas partes. Consecuencia: una amenaza de un solo tick apenas
  aporta, una sostenida se acumula sola por repetirse, sin necesitar
  ningun estado nuevo (un contador por entidad). Simplificacion mia
  respecto a la propuesta original, senalada aqui explicitamente -- el
  resultado que se queria (que lo sostenido pese mas que lo momentaneo)
  sale igual, sin inventar una pieza de estado que nadie mas necesita.

- Presenciar una muerte: penalizacion puntual, como mucho una vez por
  tick (varias muertes el mismo tick dentro del radio no se acumulan en
  esta primera pasada -- provisional), si algun Evento tipo "Muerte" de
  ESTE tick cayo dentro del radio de percepcion del individuo. Cualquier
  especie cuenta por igual -- distinguir "conspecifico" de "cualquiera"
  es un refinamiento real pero se deja fuera a proposito, mismo criterio
  que "parecido a el" en sociabilidad (bloque de sesgo gregario,
  sistema_movimiento.py): no inventar una nocion de similitud que nadie
  ha pedido todavia.

  Requiere leer el bus de eventos DENTRO de este sistema -- primera vez
  que un sistema de "estado interno" reacciona al bus en vez de solo al
  estado de componentes del tick actual (antes, solo narrador.py y
  persistencia.py lo hacian, y ninguno de los dos muta Necesidades ni
  pools). Por esto SistemaCapacidadMental se movio al final del bucle de
  tick en main.py, DESPUES de SistemaDepredacion (que es quien emite la
  mayoria de los Muerte) -- antes corria en tercer lugar y nunca podria
  haber visto el evento del mismo tick. Los eventos Muerte llevan x/y
  desde este bloque (sistema_necesidades.py y sistema_depredacion.py,
  antes no lo llevaban -- no hacia falta hasta ahora).

La consecuencia de llegar a estabilidad=0.0 ya esta resuelta -- Bloque F3
(sistema_decision.py): anula la Utility AI y dispara una tipologia de
crisis mental. No vive aqui porque este sistema solo gestiona el pool en
si, no las decisiones que dependen de el.

Escalares de techo (correccion posterior, discutida y confirmada con
Diego -- estabilidad_mental_maxima llevaba desde el Bloque F1 sin ningun
consumidor real, mismo hueco que vitalidad_maxima/resistencia_maxima):
ambas fuentes de drenaje (amenaza sostenida y presenciar muerte) se
dividen por CapacidadMental.estabilidad_mental_maxima antes de restarse
-- mismo criterio que los pools fisicos. La reposicion (resiliencia) NO
se toca, mismo motivo que curacion/recuperacion en capacidad fisica.

Radio de percepcion (deuda saldada, ver nucleo/percepcion.py): el chequeo
de "presenciar una muerte dentro del radio" ya no usa el unico entero
uniforme de config.percepcion.radio_celdas -- se deriva de
DimensionesFisicas.agudeza_sensorial de cada individuo, calculado solo
cuando hace falta (hay algun evento Muerte este tick) para no pagar el
coste en el caso comun de que no haya ninguno.
"""
from componentes.capacidad_mental import CapacidadMental
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.necesidades import Necesidades
from componentes.pool_mental import PoolMental
from componentes.posicion import Posicion
from nucleo.eventos import BusEventos
from nucleo.percepcion import radio_individual


def actualizar(gestor, config: dict, bus: BusEventos) -> None:
    tasa_perdida_amenaza = config["capacidad_mental"]["tasa_perdida_estabilidad_por_amenaza"]
    penalizacion_muerte = config["capacidad_mental"]["penalizacion_estabilidad_presenciar_muerte"]

    eventos_muerte = [
        e for e in bus.eventos_del_tick
        if e.tipo == "Muerte" and "x" in e.datos and "y" in e.datos
    ]

    for id_entidad in gestor.entidades_con(PoolMental, CapacidadMental, Necesidades):
        pool = gestor.obtener_componente(id_entidad, PoolMental)
        capacidad = gestor.obtener_componente(id_entidad, CapacidadMental)
        necesidades = gestor.obtener_componente(id_entidad, Necesidades)

        factor_energia = necesidades.energia
        pool.estabilidad = min(1.0, pool.estabilidad + capacidad.resiliencia * factor_energia)

        perdida_amenaza_fraccional = (
            tasa_perdida_amenaza * (1.0 - necesidades.seguridad) / capacidad.estabilidad_mental_maxima
        )
        pool.estabilidad = max(0.0, pool.estabilidad - perdida_amenaza_fraccional)

        if eventos_muerte:
            posicion = gestor.obtener_componente(id_entidad, Posicion)
            dimensiones = gestor.obtener_componente(id_entidad, DimensionesFisicas)
            if posicion is not None and dimensiones is not None:
                radio = radio_individual(dimensiones.agudeza_sensorial, config["percepcion"])
                for evento in eventos_muerte:
                    dist = abs(evento.datos["x"] - posicion.x) + abs(evento.datos["y"] - posicion.y)
                    if dist <= radio:
                        perdida_muerte_fraccional = penalizacion_muerte / capacidad.estabilidad_mental_maxima
                        pool.estabilidad = max(0.0, pool.estabilidad - perdida_muerte_fraccional)
                        break
