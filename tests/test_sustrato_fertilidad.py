"""Tests del catálogo de sustrato con fertilidad base (2026-09-01, pieza
1/5 de la distribución causal de flora -- ver
docs/superpowers/specs/2026-09-01-distribucion-causal-flora-design.md).

Valida solo la FORMA del catálogo -- ningún sistema del motor consume
todavía fertilidad_base (eso llega en los planes 2-5). Carga el YAML
real, no una config de prueba recortada: es la única forma de detectar
un typo de indentación o una clave mal escrita antes de que otro plan
dependa de ella.
"""
import yaml

RUTA_MATERIALES = "config/materiales.yaml"

SUSTRATOS_EXISTENTES = {"piedra", "arcilla", "arena", "tierra"}
SUSTRATOS_NUEVOS = {"tierra_negra", "marga", "grava"}


def _cargar_materiales():
    with open(RUTA_MATERIALES, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_ley_todo_sustrato_tiene_fertilidad_base_en_0_1():
    datos = _cargar_materiales()
    catalogo = datos["materiales"]
    for nombre, propiedades in catalogo.items():
        if propiedades.get("forma_en_mundo") == "sustrato":
            assert "fertilidad_base" in propiedades, f"{nombre} sin fertilidad_base"
            assert 0.0 <= propiedades["fertilidad_base"] <= 1.0


def test_ley_los_tres_sustratos_nuevos_existen_con_esquema_completo():
    datos = _cargar_materiales()
    catalogo = datos["materiales"]
    campos_obligatorios = {
        "categoria", "forma_en_mundo", "densidad_kg_m3", "dureza",
        "tasa_infiltracion", "capacidad_retencion", "combustibilidad",
        "apto_construccion", "fertilidad_base",
    }
    for nombre in SUSTRATOS_NUEVOS:
        assert nombre in catalogo, f"falta el material nuevo {nombre}"
        assert campos_obligatorios.issubset(catalogo[nombre].keys()), (
            f"{nombre} no tiene el esquema completo de un sustrato"
        )
        assert catalogo[nombre]["forma_en_mundo"] == "sustrato"


def test_ley_sustrato_por_bioma_no_cambia_de_forma_todavia():
    """Este plan NO toca sustrato_por_bioma -- sigue siendo un mapeo
    escalar bioma->material, exactamente como antes. El cambio a lista
    llega en el plan 4, junto con su único consumidor real."""
    datos = _cargar_materiales()
    mapeo = datos["sustrato_por_bioma"]
    for bioma, material in mapeo.items():
        assert isinstance(material, str), (
            f"sustrato_por_bioma[{bioma}] ya no es un string -- este plan no debía tocar esto"
        )
