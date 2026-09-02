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

# test_ley_sustrato_por_bioma_no_cambia_de_forma_todavia (2026-09-01,
# pieza 1/5) retirado el 2026-09-02: documentaba una restricción
# deliberada de ESE plan concreto ("esta pieza no toca sustrato_por_
# bioma"), no una ley permanente del motor -- la pieza 4/5 cambia esa
# forma a lista por diseño (ver tests/test_zona_bioma_fertilidad.py),
# así que la aserción quedó obsoleta y contradicha a propósito, no rota
# por error. Hallazgo real de revisión de plan, no del pipeline: la
# pieza 4 nunca instruyó actualizar/retirar este test heredado de la
# pieza 1.
