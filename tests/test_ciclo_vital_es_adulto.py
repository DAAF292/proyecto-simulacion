"""Test de la ley de madurez reproductiva (2026-09-02, ver CLAUDE.md).

nucleo/ciclo_vital.py:es_adulto decide si un individuo puede reproducirse
-- reutiliza el minimo racial de longevidad (rangos_raciales[especie]
["longevidad"][0]) como ancla, escalado por fraccion_madurez, la misma
fraccion que sistemas/sistema_reproduccion.py ya lee por especie desde
config/poblacion.yaml. Estos tests fijan el umbral exacto en ticks para
dos especies reales (gnomo, lobo) y confirman que la fraccion se aplica
POR ESPECIE, no como un valor global compartido."""
from nucleo.ciclo_vital import TICKS_POR_ANIO, es_adulto

RANGOS_RACIALES = {
    "gnomo": {"longevidad": [45, 65]},
    "lobo": {"longevidad": [8, 14]},
}


def test_gnomo_es_adulto_justo_en_el_umbral_no_antes():
    """Ley: con fraccion_madurez=0.1 (config real de gnomo) y minimo
    racial de longevidad=45 anios, el umbral de madurez es exactamente
    0.1 * 45 * TICKS_POR_ANIO = 2160 ticks -- un tick antes NO es adulto,
    en el umbral exacto SI lo es."""
    umbral = int(0.1 * 45 * TICKS_POR_ANIO)
    assert umbral == 2160

    assert es_adulto(umbral - 1, "gnomo", RANGOS_RACIALES, 0.1) is False
    assert es_adulto(umbral, "gnomo", RANGOS_RACIALES, 0.1) is True


def test_lobo_es_adulto_justo_en_el_umbral_no_antes():
    """Ley: con fraccion_madurez=0.2 (config real de lobo) y minimo
    racial de longevidad=8 anios, el umbral de madurez es exactamente
    0.2 * 8 * TICKS_POR_ANIO = 768 ticks -- un tick antes NO es adulto,
    en el umbral exacto SI lo es."""
    umbral = int(0.2 * 8 * TICKS_POR_ANIO)
    assert umbral == 768

    assert es_adulto(umbral - 1, "lobo", RANGOS_RACIALES, 0.2) is False
    assert es_adulto(umbral, "lobo", RANGOS_RACIALES, 0.2) is True


def test_fraccion_madurez_se_aplica_por_especie_no_como_valor_global():
    """Ley: la MISMA edad en ticks puede ser adulta para una especie y
    no adulta para otra -- fraccion_madurez y el minimo racial de
    longevidad son propios de cada especie, es_adulto no comparte
    ningun umbral global entre especies."""
    edad = 1000  # adulto para lobo (umbral 768), no adulto para gnomo (umbral 2160)

    assert es_adulto(edad, "lobo", RANGOS_RACIALES, 0.2) is True
    assert es_adulto(edad, "gnomo", RANGOS_RACIALES, 0.1) is False
