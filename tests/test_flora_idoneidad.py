from nucleo.celda import Celda, TipoTerreno
from nucleo.clima import Clima, Estacion
from nucleo.flora import _idoneidad_por_rango, factor_humedad_subsuelo, idoneidad_colonizacion


def test_idoneidad_por_rango_dentro():
    assert _idoneidad_por_rango(0.5, [0.0, 1.0]) == 1.0


def test_idoneidad_por_rango_fuera():
    assert _idoneidad_por_rango(1.5, [0.0, 1.0]) == 0.0


def test_idoneidad_por_rango_suelo():
    assert _idoneidad_por_rango(2.0, [0.0, 1.0]) == 0.1


def test_idoneidad_colonizacion_ideal():
    celda = Celda(
        tipo_terreno=TipoTerreno.BOSQUE,
        lluvia=0.5,
        temperatura=0.5,
        fertilidad=0.5,
        humedad_subsuelo=0.5,
    )
    especie_cfg = {
        "preferencia_lluvia": [0.0, 1.0],
        "preferencia_temperatura": [0.0, 1.0],
        "preferencia_fertilidad": [0.0, 1.0],
    }
    assert idoneidad_colonizacion(especie_cfg, celda, 1.0) == 1.0


def test_idoneidad_colonizacion_cero():
    celda = Celda(
        tipo_terreno=TipoTerreno.DESIERTO,
        lluvia=0.0,
        temperatura=0.0,
        fertilidad=0.0,
        humedad_subsuelo=0.0,
    )
    especie_cfg = {
        "preferencia_lluvia": [0.5, 1.0],
        "preferencia_temperatura": [0.5, 1.0],
        "preferencia_fertilidad": [0.5, 1.0],
    }
    assert idoneidad_colonizacion(especie_cfg, celda, 1.0) == 0.0


def test_factor_humedad_subsuelo_saturado():
    celda = Celda(
        tipo_terreno=TipoTerreno.BOSQUE,
        lluvia=0.5,
        temperatura=0.5,
        fertilidad=0.5,
        humedad_subsuelo=1.0,
    )
    assert factor_humedad_subsuelo(celda, 1.0) == 1.2


def test_factor_humedad_subsuelo_seco():
    celda = Celda(
        tipo_terreno=TipoTerreno.DESIERTO,
        lluvia=0.0,
        temperatura=0.0,
        fertilidad=0.0,
        humedad_subsuelo=0.0,
    )
    assert factor_humedad_subsuelo(celda, 1.0) == 1.0
