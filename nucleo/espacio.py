"""
nucleo/espacio.py

Cupo de espacio f\u00edsico COMPARTIDO de una celda (m\u00b2), neutral respecto a
qu\u00e9 lo ocupa. Generaliza lo que hasta hoy hac\u00eda solo construcci\u00f3n
(nucleo/construccion.py:espacio_disponible_para_construir) para que
tambi\u00e9n cuente la flora competidora: una Planta con
compite_espacio_fisico=true (p.ej. manzano, cactus) ocupa huella_m2 del
mismo presupuesto (config/materiales.yaml:construccion.
capacidad_construccion_celda_m2) que una Construccion.

La pista no-competidora (Celda.tiene_recurso/tipo_recurso) NO entra en
este c\u00e1lculo: hierba/liquen/musgo son cobertura de suelo sin obst\u00e1culo
f\u00edsico (ver spec 2026-09-03-cupo-espacio-celda-design.md).

Aislamiento por zona_idx: dos celdas en zonas distintas con coordenadas
num\u00e9ricamente coincidentes NO comparten cupo -- mismo patr\u00f3n de
verificaci\u00f3n que construcci\u00f3n/asentamiento ya aplican.
"""
from __future__ import annotations

from typing import Any


def huella_m2_para(tipo: str, config_construccion: dict[str, Any]) -> float:
    """\u00c1rea en m\u00b2 que ocupa una Construccion de este tipo -- config/
    materiales.yaml secci\u00f3n construccion. Mismo criterio permisivo que
    masa_minima_para: cualquier tipo no reconocido usa huella_m2_refugio
    como base razonable en vez de fallar (cat\u00e1logo abierto, ver
    Construccion.tipo). Vive aqu\u00ed (no en nucleo/construccion.py) para que
    el c\u00e1lculo de cupo compartido no dependa de la direcci\u00f3n del import
    entre los dos m\u00f3dulos."""
    clave = f"huella_m2_{tipo}"
    return float(
        config_construccion.get(clave, config_construccion.get("huella_m2_refugio", 15.0))
    )


def huella_m2_flora(especie_cfg: dict[str, Any]) -> float:
    """m\u00b2 que ocupa una Planta de esta especie -- solo las especies con
    compite_espacio_fisico=true declaran huella_m2 (config/flora.yaml);
    las no-competidoras no tienen clave y devuelven 0.0 (no ocupan cupo)."""
    return float(especie_cfg.get("huella_m2", 0.0))


def plantas_competidoras_en(
    gestor: Any,
    pos_x: int,
    pos_y: int,
    zona_idx: int,
    especies_cfg: dict[str, Any],
) -> list[int]:
    """Ids de las entidades Planta con compite_espacio_fisico=true en la
    celda exacta (pos_x, pos_y, zona_idx) -- consulta real de entidades
    ECS, mismo patr\u00f3n que disposicion.py/sistema_depredacion.py ya usan
    para buscar por posici\u00f3n (sin filtro espacial optimizado, aceptable a
    esta escala, mismo criterio ya asumido en el resto del motor)."""
    from componentes.planta import Planta
    from componentes.posicion import Posicion

    resultado: list[int] = []
    for pid in gestor.entidades_con(Planta, Posicion):
        pos = gestor.obtener_componente(pid, Posicion)
        if pos.x != pos_x or pos.y != pos_y or pos.zona_idx != zona_idx:
            continue
        planta = gestor.obtener_componente(pid, Planta)
        if planta is None:
            continue
        cfg_esp = especies_cfg.get(planta.especie, {})
        if cfg_esp.get("compite_espacio_fisico", False):
            resultado.append(pid)
    return resultado


def espacio_disponible(
    gestor: Any,
    pos_x: int,
    pos_y: int,
    zona_idx: int,
    config: dict[str, Any],
) -> float:
    """m\u00b2 todav\u00eda libres en (pos_x, pos_y, zona_idx) para algo que ocupe
    cupo f\u00edsico -- config['construccion'].capacidad_construccion_celda_m2
    menos la suma de:
      - la huella_m2 de cada Construccion YA presente en esa celda exacta
        (comportamiento hist\u00f3rico de espacio_disponible_para_construir, sin
        cambios);
      - la huella_m2 de cada Planta con compite_espacio_fisico=true en esa
        misma posici\u00f3n+zona.

    B\u00fasqueda lineal O(N) sobre construcciones y plantas del mundo, mismo
    l\u00edmite ya aceptado en construccion_propia/plantas_competidoras_en."""
    from componentes.construccion import Construccion
    from componentes.planta import Planta
    from componentes.posicion import Posicion

    config_construccion = config.get("construccion", {})
    especies_cfg = config.get("flora", {}).get("especies", {})

    capacidad = float(config_construccion.get("capacidad_construccion_celda_m2", 80.0))
    ocupado = 0.0

    for cid in gestor.entidades_con(Construccion, Posicion):
        pos = gestor.obtener_componente(cid, Posicion)
        if pos.x != pos_x or pos.y != pos_y or pos.zona_idx != zona_idx:
            continue
        construccion = gestor.obtener_componente(cid, Construccion)
        if construccion is not None:
            ocupado += huella_m2_para(construccion.tipo, config_construccion)

    for pid in gestor.entidades_con(Planta, Posicion):
        pos = gestor.obtener_componente(pid, Posicion)
        if pos.x != pos_x or pos.y != pos_y or pos.zona_idx != zona_idx:
            continue
        planta = gestor.obtener_componente(pid, Planta)
        if planta is None:
            continue
        cfg_esp = especies_cfg.get(planta.especie, {})
        if cfg_esp.get("compite_espacio_fisico", False):
            ocupado += huella_m2_flora(cfg_esp)

    return capacidad - ocupado
