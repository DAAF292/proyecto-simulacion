"""Bucle minimo de fase 0 (paso 6 del orden de construccion + regla de
muerte por inanicion, calibrada tras observar el paso 6 corriendo).

Genera y muestra el mapa (Mundo -> Territorio -> ZonaBioma -> Celda), crea
un unico gnomo, avanza por Enter, sin narrador todavia -- solo imprime
hambre/energia por consola y cualquier evento del bus (por ahora, solo
Muerte por inanicion puede ocurrir).

Ejecutar: python main.py
Variable de entorno BOSQUE_AUTO_TICKS=N ejecuta N ticks automaticos sin
esperar Enter -- solo para pruebas, no es el modo de juego real.
"""
import os
import random

import yaml

from componentes.intencion import Intencion
from componentes.necesidades import Necesidades
from nucleo.celda import TipoTerreno
from nucleo.entidad import GestorEntidades, crear_gnomo
from nucleo.eventos import BusEventos
from nucleo.mundo import Mundo
from nucleo.reloj import Reloj
from nucleo.territorio import Territorio
from nucleo.zona_bioma import generar_zona_bioma
from sistemas import sistema_decision, sistema_necesidades

SIMBOLO_TERRENO = {
    TipoTerreno.CLARO: ".",
    TipoTerreno.ESPESURA: "#",
    TipoTerreno.RIBERA: "~",
}


def cargar_config(ruta: str = "config/constantes.yaml") -> dict:
    with open(ruta, encoding="utf-8") as f:
        return yaml.safe_load(f)


def imprimir_mapa(zona) -> None:
    conteo = {t: 0 for t in TipoTerreno}
    for y in range(zona.alto):
        fila = []
        for x in range(zona.ancho):
            celda = zona.celda(x, y)
            fila.append(SIMBOLO_TERRENO[celda.tipo_terreno])
            conteo[celda.tipo_terreno] += 1
        print("  " + "".join(fila))
    total = zona.ancho * zona.alto
    resumen = "  ".join(
        f"{t.value}={n} ({100 * n / total:.0f}%)" for t, n in conteo.items()
    )
    print(f"  {resumen}\n")


def main() -> None:
    config = cargar_config()
    semilla = config["semilla_por_defecto"]
    rng = random.Random(semilla)

    ancho = config["mundo"]["grid_ancho"]
    alto = config["mundo"]["grid_alto"]
    zona = generar_zona_bioma(
        rng, config["generacion_mapa"], config["recursos_por_terreno"], ancho, alto
    )
    territorio = Territorio(nombre="El Bosque", zonas_bioma=[zona])
    mundo = Mundo(semilla=semilla, territorios=[territorio])  # noqa: F841 (aun sin uso fuera de esta creacion)

    print(f"Mundo generado con semilla={semilla}. Mapa de '{territorio.nombre}':\n")
    imprimir_mapa(zona)

    gestor = GestorEntidades()
    reloj = Reloj()
    bus = BusEventos()

    centro_x, centro_y = ancho // 2, alto // 2
    id_gnomo = crear_gnomo(
        gestor, rng, x=centro_x, y=centro_y, rangos_raciales=config["rangos_raciales"]
    )

    print(f"Gnomo creado con id={id_gnomo} en ({centro_x}, {centro_y}).")
    print("Pulsa Enter para avanzar un tick (Ctrl+C para salir).\n")

    auto_ticks = int(os.environ.get("BOSQUE_AUTO_TICKS", "0"))
    tick_n = 0

    while True:
        if auto_ticks:
            if tick_n >= auto_ticks:
                break
        else:
            input()

        reloj.avanzar()
        tick_n += 1
        sistema_necesidades.actualizar(gestor, config, rng, bus, reloj.tick_actual)
        sistema_decision.actualizar(gestor, config)

        for evento in bus.eventos_del_tick:
            print(
                f"  [EVENTO] tick={evento.tick} tipo={evento.tipo} "
                f"severidad={evento.severidad.value} entidad={evento.entidad_id} "
                f"datos={evento.datos}"
            )
        bus.limpiar()

        necesidades = gestor.obtener_componente(id_gnomo, Necesidades)
        if necesidades is None:
            print(f"tick={reloj.tick_actual:4d}  dia={reloj.dia:3d}  el gnomo {id_gnomo} ha muerto.")
            break

        intencion = gestor.obtener_componente(id_gnomo, Intencion)
        print(
            f"tick={reloj.tick_actual:4d}  dia={reloj.dia:3d}  "
            f"hambre={necesidades.hambre:.3f}  energia={necesidades.energia:.3f}  "
            f"intencion={intencion.accion.value}"
        )


if __name__ == "__main__":
    main()
