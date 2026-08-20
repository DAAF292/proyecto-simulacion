"""SistemaFlora (fase terreno 4, informe tecnico -- ultima de las cuatro
fases de terreno, flora como entidad con crecimiento; corregida despues,
ver nucleo/flora.py y componentes/planta.py para el detalle de la
correccion biomas/especies y multi-recurso).

Sustituye la vieja _regenerar() de sistema_recursos.py (regeneracion
uniforme de cualquier celda con tiene_recurso=True) por una produccion
DERIVADA de plantas concretas: Celda.recursos solo sube donde hay una
Planta madura (componentes/planta.py) presente, no solo porque la celda
"pertenezca a una mancha" declarada en la generacion del mapa. El resto
del ciclo de recurso no cambia: _consumir/_beber/_fertilizar/
_decaer_fertilidad (sistema_recursos.py) siguen intactos -- comer sigue
gastando Celda.recursos igual que siempre, fertilidad sigue siendo un
bono sobre la produccion (ahora sobre el APORTE de la planta, no sobre
una tasa de celda abstracta).

Tres cadencias de dia, mismo archivo (igual criterio que
sistema_recursos.py/sistema_clima.py: un dominio, un sitio):

- Crecimiento: una planta inmadura avanza etapa hacia 1.0, a la
  tasa_crecimiento_por_dia de SU PROPIA especie (config/constantes.yaml,
  flora.especies) -- ya no un unico valor global para toda planta (ver
  nucleo/flora.py).
- Produccion: una planta madura (etapa=1.0) aporta, a CADA recurso de
  categoria 'alimento' de su especie (puede ser mas de uno -- hierba
  silvestre da raices Y hierba, ver nucleo/flora.py), hasta el techo
  capacidad_maxima de ESE recurso concreto. El aporte diario reutiliza
  tasa_regeneracion del recurso, multiplicado por tres factores: (1+
  fertilidad de la celda) igual que siempre, el modificador de
  estacion+clima (nucleo/clima.py, mismo consumidor que
  sistema_necesidades.py para confort_termico) y AHORA TAMBIEN
  factor_produccion (nucleo/flora.py) -- idoneidad de lluvia y
  temperatura de la celda frente a la preferencia de la especie, pieza
  nueva de esta correccion, antes esos dos campos se descartaban tras
  clasificar el bioma. Un cuarto factor, factor_ribera (nucleo/flora.py,
  correccion posterior tras rediseñar la generacion de agua -- ver
  nucleo/agua.py): bono si la celda tiene agua superficial (rio/lago/
  poza), antes Celda.tiene_agua no influia en nada de esto.
- Propagacion: una planta madura tiene una probabilidad diaria (propia
  de su especie, prob_propagacion_por_dia) de colonizar una celda vecina
  VACIA (sin otra Planta ya presente) cuyo BIOMA este en la lista de
  biomas compatibles de la especie -- ya no "mismo tipo_terreno exacto"
  (una especie de Bosque puede propagarse a cualquier celda de Bosque
  vecina, no solo a las que compartian el mismo sub-tipo) -- ni a una
  celda en llamas. Al colonizar, marca Celda.tiene_recurso=True Y
  Celda.tipo_recurso=<especie> en la celda nueva -- redefinicion
  deliberada de tiene_recurso (ver nucleo/celda.py): antes era un dato
  ESTATICO fijado en la generacion del mapa ("esta celda pertenece a una
  mancha"), ahora es DINAMICO ("esta celda tiene una planta ahora
  mismo"), fiel reflejo de que la vegetacion puede crecer y morir en
  juego, no solo al generar el mundo. Sin limite EXPLICITO de manchas ni
  de superficie total -- ninguna cuota artificial en el codigo (ver
  docstring anterior de este modulo, mismo razonamiento, no repetido
  aqui: la geometria de "vecina vacia" ya autolimita la poblacion).
"""
from componentes.planta import Planta
from componentes.posicion import Posicion
from nucleo.celda import TipoTerreno
from nucleo.clima import estacion_actual, modificador_regeneracion
from nucleo.entidad import crear_planta
from nucleo.flora import factor_produccion, factor_ribera, recursos_alimento
from nucleo.reloj import Reloj
from nucleo.zona_bioma import vecinos


def _crecer(gestor, config_flora: dict) -> None:
    for id_planta in gestor.entidades_con(Posicion, Planta):
        planta = gestor.obtener_componente(id_planta, Planta)
        if planta.etapa < 1.0:
            tasa = config_flora["especies"][planta.especie]["tasa_crecimiento_por_dia"]
            planta.etapa = min(1.0, planta.etapa + tasa)


def _producir(gestor, zona, reloj: Reloj, config: dict) -> None:
    estacion_hoy = estacion_actual(reloj.estacion)
    mult_estacional = modificador_regeneracion(estacion_hoy, zona.clima_actual, config["estaciones"], config["clima"])
    config_especies = config["flora"]["especies"]

    for id_planta in gestor.entidades_con(Posicion, Planta):
        planta = gestor.obtener_componente(id_planta, Planta)
        if planta.etapa < 1.0:
            continue
        pos = gestor.obtener_componente(id_planta, Posicion)
        celda = zona.celda(pos.x, pos.y)
        especie_cfg = config_especies[planta.especie]
        mult_idoneidad = factor_produccion(celda.lluvia, celda.temperatura, especie_cfg)
        mult_ribera = factor_ribera(celda.tiene_agua, config["flora"]["bono_produccion_ribera"])

        for recurso in recursos_alimento(especie_cfg):
            nombre = recurso["nombre"]
            aporte = (
                recurso["tasa_regeneracion"] * (1.0 + celda.fertilidad)
                * mult_estacional * mult_idoneidad * mult_ribera
            )
            actual = celda.recursos.get(nombre, 0.0)
            celda.recursos[nombre] = min(recurso["capacidad_maxima"], actual + aporte)


def _propagar(gestor, zona, config_flora: dict, rng) -> None:
    ocupadas = set()
    for id_planta in gestor.entidades_con(Posicion, Planta):
        pos = gestor.obtener_componente(id_planta, Posicion)
        ocupadas.add((pos.x, pos.y))

    # list(...) porque se anaden entidades nuevas dentro del bucle
    # (crear_planta) -- mismo motivo que list(...) en sistemas que
    # eliminan entidades, aqui es el caso simetrico (se crean).
    for id_planta in list(gestor.entidades_con(Posicion, Planta)):
        planta = gestor.obtener_componente(id_planta, Planta)
        especie_cfg = config_flora["especies"][planta.especie]
        prob = especie_cfg["prob_propagacion_por_dia"]
        if planta.etapa < 1.0 or rng.random() >= prob:
            continue

        biomas_compatibles = {TipoTerreno(b) for b in especie_cfg["biomas"]}
        pos = gestor.obtener_componente(id_planta, Posicion)
        candidatas = [
            (nx, ny) for nx, ny in vecinos(pos.x, pos.y, zona.ancho, zona.alto)
            if (nx, ny) not in ocupadas
            and zona.celda(nx, ny).tipo_terreno in biomas_compatibles
            and not zona.celda(nx, ny).en_llamas
        ]
        if not candidatas:
            continue

        nx, ny = rng.choice(candidatas)
        crear_planta(gestor, nx, ny, planta.especie, etapa=0.0)
        ocupadas.add((nx, ny))
        celda_nueva = zona.celda(nx, ny)
        celda_nueva.tiene_recurso = True
        celda_nueva.tipo_recurso = planta.especie


def actualizar(gestor, zona, reloj: Reloj, config: dict, rng, tick_actual: int) -> None:
    if tick_actual % Reloj.TICKS_POR_DIA != 0:
        return
    _crecer(gestor, config["flora"])
    _producir(gestor, zona, reloj, config)
    _propagar(gestor, zona, config["flora"], rng)
