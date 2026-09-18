"""Test de la ley de madurez reproductiva (2026-09-02, ver CLAUDE.md).

nucleo/ciclo_vital.py:es_adulto decide si un individuo puede reproducirse
-- reutiliza la longevidad INDIVIDUAL ya sorteada de ese individuo
(dims.longevidad) como ancla, escalado por fraccion_madurez, la misma
fraccion que sistemas/sistema_reproduccion.py ya lee por especie desde
config/poblacion.yaml. Estos tests fijan el umbral exacto en ticks para
dos longevidades reales (gnomo, lobo) y confirman que dos individuos de
la MISMA especie con longevidades individuales distintas maduran en
ticks distintos -- corregido 2026-09-18 (ver docs/superpowers/specs/
2026-09-18-madurez-por-longevidad-individual-design.md): antes usaba el
minimo racial fijo, sincronizando la madurez de toda una camada en el
mismo instante con independencia de la longevidad de cada uno,
verificado como un amplificador real del ciclo boom-and-bust de
ardilla."""
from nucleo.ciclo_vital import TICKS_POR_ANIO, es_adulto


def test_gnomo_es_adulto_justo_en_el_umbral_no_antes():
    """Ley: con fraccion_madurez=0.1 (config real de gnomo) y longevidad
    individual=45 anios (minimo del rango racial), el umbral de madurez
    es exactamente 0.1 * 45 * TICKS_POR_ANIO = 2160 ticks -- un tick
    antes NO es adulto, en el umbral exacto SI lo es."""
    umbral = int(0.1 * 45 * TICKS_POR_ANIO)
    assert umbral == 2160

    assert es_adulto(umbral - 1, 45, 0.1) is False
    assert es_adulto(umbral, 45, 0.1) is True


def test_lobo_es_adulto_justo_en_el_umbral_no_antes():
    """Ley: con fraccion_madurez=0.2 (config real de lobo) y longevidad
    individual=8 anios (minimo del rango racial), el umbral de madurez
    es exactamente 0.2 * 8 * TICKS_POR_ANIO = 768 ticks -- un tick antes
    NO es adulto, en el umbral exacto SI lo es."""
    umbral = int(0.2 * 8 * TICKS_POR_ANIO)
    assert umbral == 768

    assert es_adulto(umbral - 1, 8, 0.2) is False
    assert es_adulto(umbral, 8, 0.2) is True


def test_fraccion_madurez_se_aplica_por_especie_no_como_valor_global():
    """Ley: la MISMA edad en ticks puede ser adulta para una especie y
    no adulta para otra -- fraccion_madurez y la longevidad individual
    son propias de cada especie/individuo, es_adulto no comparte ningun
    umbral entre especies."""
    edad = 1000  # adulto para lobo (umbral 768 con longevidad=8), no para gnomo (umbral 2160 con longevidad=45)

    assert es_adulto(edad, 8, 0.2) is True
    assert es_adulto(edad, 45, 0.1) is False


def test_ley_central_dos_individuos_de_la_misma_especie_maduran_en_ticks_distintos():
    """Ley central de la correccion de 2026-09-18: dos lobos de la MISMA
    camada (nacidos el mismo tick), con longevidades individuales
    distintas dentro del rango racial (8 y 14 anios), maduran en ticks
    DISTINTOS -- antes de la correccion, ambos maduraban exactamente en
    el mismo tick (768, calculado sobre el minimo racial fijo de 8
    anios) con independencia de su propia longevidad sorteada."""
    fraccion_madurez = 0.2
    edad_umbral_longevidad_minima = int(fraccion_madurez * 8 * TICKS_POR_ANIO)  # 768
    edad_umbral_longevidad_maxima = int(fraccion_madurez * 14 * TICKS_POR_ANIO)  # 1344

    assert edad_umbral_longevidad_minima != edad_umbral_longevidad_maxima

    # A esta edad, el lobo de longevidad corta ya es adulto; el de
    # longevidad larga todavia no -- la madurez de la camada se dispersa.
    edad_intermedia = (edad_umbral_longevidad_minima + edad_umbral_longevidad_maxima) // 2
    assert es_adulto(edad_intermedia, 8, fraccion_madurez) is True
    assert es_adulto(edad_intermedia, 14, fraccion_madurez) is False
