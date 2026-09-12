"""Prioridad consciente -- Vía 1 (piedra_suelta para fuego) requiere
motivo real (2026-09-12, ver CLAUDE.md sección "Prioridad consciente").

Hallazgo real: Vía 1 llevaba desde el 2026-08-31 (piedra suelta)
disparándose SIEMPRE que hubiera hueco en Agarre y faltaran piedras,
sin comprobar si fuego fue de verdad el motivo que ganó el RECOLECTAR
de este tick -- interceptando casi cualquier piedra_suelta disponible
antes de que Vía 2/3 (arma/herramienta) pudieran considerarla como
material "piedra". Retrofit del mismo patrón `recolectar_motivo_X` que
ya usan arma/herramienta desde su diseño original.

Cada test es una "ley física" del comportamiento real que se valida,
misma convención que el resto del proyecto.
"""
import random
from pathlib import Path

from componentes.agarre import Agarre
from componentes.capacidad_mental import CapacidadMental
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Especie
from componentes.intencion import Accion, Intencion
from componentes.inventario import Inventario
from componentes.necesidades import Necesidades
from componentes.pool_fisico import PoolFisico
from componentes.temperamento import Temperamento
from main import cargar_configuracion
from nucleo.celda import Celda, TipoTerreno
from nucleo.entidad import GestorEntidades, crear_criatura
from nucleo.eventos import BusEventos
from nucleo.mundo import Mundo
from sistemas.sistema_decision import actualizar
from sistemas.sistema_recursos import SistemaRecursos

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def _config() -> dict:
    return cargar_configuracion(RUTA_CONFIG)


def _dims(peso: float = 50.0) -> DimensionesFisicas:
    return DimensionesFisicas(
        peso=peso, fuerza=0.5, agilidad=0.5, vitalidad_maxima=1.0, resistencia_maxima=1.0,
        curacion=0.01, recuperacion=0.1, altura=1.3, longevidad=50.0, velocidad=0.4,
        resistencia_enfermedad=0.5, agudeza_sensorial=0.5,
    )


def _celda_con_piedra_suelta() -> Celda:
    return Celda(tipo_terreno=TipoTerreno.BOSQUE, recursos={"piedra_suelta": 1.0})


def _gnomo_neutralizado(gestor, config, rng, x=0, y=0) -> int:
    """Mismo patrón de neutralización de aptitud vocacional que
    tests/test_fabricacion_herramientas.py -- fija los 4 atributos que
    componen las 4 cubetas a 0.5 (factor_aptitud == 1.0), para que los
    empates numéricos exactos que estos tests dependen de comparar no
    queden distorsionados por el sorteo aleatorio de cada individuo."""
    eid = crear_criatura(gestor, Especie.GNOMO, x, y, config, rng)
    nec = gestor.obtener_componente(eid, Necesidades)
    nec.saciedad = nec.energia = nec.hidratacion = nec.aliviado = 1.0
    nec.seguridad = 1.0
    nec.confort_termico = 1.0
    gestor.obtener_componente(eid, PoolFisico).resistencia = 1.0
    temperamento = gestor.obtener_componente(eid, Temperamento)
    temperamento.sociabilidad = 0.0
    temperamento.curiosidad = 0.5
    dims = gestor.obtener_componente(eid, DimensionesFisicas)
    dims.agudeza_sensorial = 0.5
    dims.fuerza = 0.5
    cap_mental = gestor.obtener_componente(eid, CapacidadMental)
    cap_mental.voluntad = 0.5
    cap_mental.inteligencia = 0.5
    return eid


# ---------------------------------------------------------------------------
# sistemas/sistema_recursos.py -- Vía 1 gateada por recolectar_fuego
# ---------------------------------------------------------------------------

def test_ley_via1_fuego_requiere_motivo_real():
    """piedra_suelta NUNCA se agarra para fuego sin el motivo real
    (recolectar_fuego=True) -- ni siquiera con hueco de sobra en Agarre
    y piedras pendientes."""
    config = _config()
    sistema = SistemaRecursos(config, random.Random(1))
    celda = _celda_con_piedra_suelta()

    inv_sin_motivo = Inventario()
    sistema._resolver_recolectar(
        inv_sin_motivo, _dims(), celda, Agarre(), "gnomo", True, recolectar_fuego=False
    )
    assert "piedra_suelta" not in Agarre().objetos  # sanity: Agarre por defecto vacío

    agarre_sin_motivo = Agarre()
    sistema._resolver_recolectar(
        inv_sin_motivo, _dims(), celda, agarre_sin_motivo, "gnomo", True, recolectar_fuego=False
    )
    assert "piedra_suelta" not in agarre_sin_motivo.objetos

    agarre_con_motivo = Agarre()
    sistema._resolver_recolectar(
        Inventario(), _dims(), celda, agarre_con_motivo, "gnomo", True, recolectar_fuego=True
    )
    assert "piedra_suelta" in agarre_con_motivo.objetos


def test_ley_via1_fuego_no_intercepta_piedra_suelta_motivada_por_arma():
    """Sin motivo de fuego (recolectar_fuego=False) pero CON motivo de
    arma, la piedra_suelta de la celda ya no la agarra Vía 1 para fuego
    -- llega intacta hasta Vía 2, que la recoge como material "piedra"
    para el arma. Antes de este fix, Vía 1 (sin gate) se la quedaba
    primero siempre, bloqueando por completo esta vía."""
    config = _config()
    sistema = SistemaRecursos(config, random.Random(1))
    celda = _celda_con_piedra_suelta()

    inv = Inventario()
    agarre = Agarre()
    sistema._resolver_recolectar(
        inv, _dims(), celda, agarre, "gnomo", True,
        recolectar_arma=True, recolectar_fuego=False,
    )
    assert "piedra" in inv.objetos
    assert "piedra_suelta" not in agarre.objetos


def test_ley_via1_fuego_no_intercepta_piedra_suelta_motivada_por_herramienta():
    """Mismo caso que arriba, para la categoría herramienta (Vía 3)."""
    config = _config()
    sistema = SistemaRecursos(config, random.Random(1))
    celda = _celda_con_piedra_suelta()

    inv = Inventario()
    agarre = Agarre()
    sistema._resolver_recolectar(
        inv, _dims(), celda, agarre, "gnomo", True,
        recolectar_herramienta=True, recolectar_fuego=False,
    )
    assert "piedra" in inv.objetos
    assert "piedra_suelta" not in agarre.objetos


# ---------------------------------------------------------------------------
# sistemas/sistema_decision.py -- Intencion.recolectar_motivo_fuego
# ---------------------------------------------------------------------------

def test_ley_decision_motivo_fuego_gana_cuando_es_la_mayor_necesidad():
    """Un gnomo con frío real (confort_termico bajo), sin ninguna otra
    necesidad de trabajo pendiente (ni refugio, ni arma, ni herramienta),
    de pie sobre piedra_suelta: RECOLECTAR se motiva por fuego."""
    config = _config()
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    rng = random.Random(1)
    eid = _gnomo_neutralizado(gestor, config, rng)
    nec = gestor.obtener_componente(eid, Necesidades)
    nec.confort_termico = 0.1  # frío real
    zona = mundo.territorio.zonas[0]
    zona.obtener_celda(0, 0).recursos["piedra_suelta"] = 1.0

    actualizar(gestor, mundo, config, BusEventos(), 1)

    intencion = gestor.obtener_componente(eid, Intencion)
    assert intencion.accion == Accion.RECOLECTAR
    assert intencion.recolectar_motivo_fuego is True
    assert intencion.recolectar_motivo_arma is False
    assert intencion.recolectar_motivo_herramienta is False


def test_ley_decision_motivo_fuego_pierde_frente_a_necesidad_de_trabajo_mayor():
    """Con el confort térmico casi pleno (déficit mínimo, fuego apenas
    interesa) pero la necesidad de trabajo implícita de todo gnomo sin
    refugio propio (0.35, config/fisiologia.yaml:utilidad_recolectar_base)
    superando a fuego, RECOLECTAR se motiva por herramienta -- no por
    fuego -- aunque la celda también ofrezca piedra_suelta y todavía
    falten piedras."""
    config = _config()
    gestor = GestorEntidades()
    mundo = Mundo(10, 10, config, random.Random(1))
    rng = random.Random(1)
    eid = _gnomo_neutralizado(gestor, config, rng)
    nec = gestor.obtener_componente(eid, Necesidades)
    nec.confort_termico = 0.95  # frío casi irrelevante
    zona = mundo.territorio.zonas[0]
    zona.obtener_celda(0, 0).recursos["piedra_suelta"] = 1.0

    actualizar(gestor, mundo, config, BusEventos(), 1)

    intencion = gestor.obtener_componente(eid, Intencion)
    assert intencion.accion == Accion.RECOLECTAR
    assert intencion.recolectar_motivo_fuego is False
    assert intencion.recolectar_motivo_herramienta is True
