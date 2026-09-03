"""
nucleo/armas.py

Funciones puras del circulo 1 de armas primitivas (2026-09-03, ver
docs/superpowers/specs/2026-09-03-armas-primitivas-v2-design.md) -- mismo
patron que nucleo/inventario.py y nucleo/construccion.py: funciones sin
estado, cada sistema que las consume decide cuando llamarlas.

"Todo es un arma": un material crudo apto_arma empunado ya tiene algun
efecto (nivel 1). Fabricar combina uno o mas materiales segun receta del
catalogo (config/armas.yaml) para producir algo mejor (niveles 2 y 3) --
sin nombres de arma hardcodeados aqui, todo via config.
"""

from __future__ import annotations

from typing import Any


def nivel_arma(objeto: str, catalogo_materiales: dict[str, Any], recetas: list[dict[str, Any]]) -> int:
    """Nivel de arma de un objeto -- 0 si no es arma (nada en la mano),
    1 si es material crudo apto_arma (un palo o una piedra sueltos), o el
    nivel de su receta si es un arma fabricada (lanza/hacha_mano=2,
    hacha_primitiva=3).

    Deliberadamente NO reconoce piedra_suelta: es la piedra de percusion
    del fuego, herramienta que vive en Agarre mientras se necesita, no un
    arma -- ver componentes/agarre.py para el porque causal."""
    if catalogo_materiales.get(objeto, {}).get("apto_arma", False):
        return 1
    for receta in recetas:
        if receta.get("nombre") == objeto:
            return int(receta.get("nivel", 0))
    return 0


def mayor_nivel_arma(
    objetos: list[str], catalogo_materiales: dict[str, Any], recetas: list[dict[str, Any]]
) -> int:
    """Nivel del mejor arma en una lista de objetos -- 0 si no hay ninguna."""
    mayor = 0
    for obj in objetos:
        nivel = nivel_arma(obj, catalogo_materiales, recetas)
        if nivel > mayor:
            mayor = nivel
    return mayor


def tiene_arma_nivel2_o_mas(
    objetos: list[str], catalogo_materiales: dict[str, Any], recetas: list[dict[str, Any]]
) -> bool:
    """True si la coleccion contiene ya un arma fabricada (nivel >= 2) --
    el gate que cierra para siempre la recoleccion/fabricacion de este
    circulo (no se persigue mejorar a nivel 3 automaticamente)."""
    return mayor_nivel_arma(objetos, catalogo_materiales, recetas) >= 2


def objetos_arma(
    objetos: list[str], catalogo_materiales: dict[str, Any], recetas: list[dict[str, Any]]
) -> list[str]:
    """Subconjunto de objetos que son armas (crudo apto_arma o fabricadas)."""
    return [obj for obj in objetos if nivel_arma(obj, catalogo_materiales, recetas) > 0]


def mejor_objeto_para_empunar(
    objetos: list[str], catalogo_materiales: dict[str, Any], recetas: list[dict[str, Any]]
) -> str | None:
    """El mejor objeto para empunar de una coleccion: el arma fabricada
    (nivel >= 2) si existe -- la spec: "el arma fabricada si existe, o si
    no el mejor material crudo apto_arma disponible". Max por nivel; en
    empate se queda con el primero (sin criterio adicional relevante)."""
    candidatos = objetos_arma(objetos, catalogo_materiales, recetas)
    if not candidatos:
        return None
    return max(candidatos, key=lambda obj: nivel_arma(obj, catalogo_materiales, recetas))


def mejor_receta_completable(
    objetos: list[str], recetas: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """La receta de mayor nivel completable AHORA con lo que ya se porta
    (prioriza nivel mas alto alcanzable con el material disponible en este
    instante -- no espera a conseguir un material mejor, reacciona al
    presente, coherente con que el resto de la Utility AI no planifica a
    futuro). None si ninguna receta es completable."""
    disponibles = set(objetos)
    completables = [
        r for r in recetas if all(m in disponibles for m in r.get("materiales", []))
    ]
    if not completables:
        return None
    return max(completables, key=lambda r: int(r.get("nivel", 0)))


def celda_ofrece_material_arma(celda: Any, catalogo_materiales: dict[str, Any]) -> bool:
    """True si la celda actual ofrece un recurso apto_arma: madera via el
    recurso que sistema_flora.py deposita bajo el manzano, o piedra via
    piedra_suelta (el recurso de piedras sueltas del fuego, que es la misma
    senal fisica de una piedra empunable). Ambos recursos ya existen, sin
    crear ninguno nuevo."""
    for nombre in celda.recursos:
        if celda.recursos[nombre] <= 0.0:
            continue
        if nombre == "piedra_suelta":
            return True
        if catalogo_materiales.get(nombre, {}).get("apto_arma", False):
            return True
    return False


def recolectar_material_arma_de_celda(
    celda: Any, catalogo_materiales: dict[str, Any]
) -> str | None:
    """Nombre del material apto_arma que la celda ofrece para recoger ahora
    (piedra_suelta -> material 'piedra', porque las recetas hablan de
    'piedra' no de 'piedra_suelta'). None si no ofrece ninguno."""
    for nombre in celda.recursos:
        if celda.recursos[nombre] <= 0.0:
            continue
        if nombre == "piedra_suelta":
            return "piedra"
        if catalogo_materiales.get(nombre, {}).get("apto_arma", False):
            return nombre
    return None


def bono_defensivo_arma(nivel: int, agresividad: float, config_armas: dict[str, Any]) -> float:
    """Reduccion de probabilidad de captura que da tener empunado un arma
    de este nivel -- efecto_base_por_nivel[nivel] (el obstaculo fisico,
    igual para cualquiera) + efecto_ofensivo_por_nivel[nivel] *
    agresividad (cuanto mas agresivo el portador, mayor el salto)."""
    if nivel <= 0:
        return 0.0
    base = float(config_armas.get("efecto_base_por_nivel", {}).get(str(nivel), 0.0))
    ofensivo = float(config_armas.get("efecto_ofensivo_por_nivel", {}).get(str(nivel), 0.0))
    return base + ofensivo * agresividad
