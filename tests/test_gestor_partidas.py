"""Ciclo de vida de una partida controlada por web (2026-09-16, ver
docs/superpowers/specs/2026-09-16-servidor-control-remoto-design.md):
nueva/pausar/reanudar/velocidad/finalizar.

Sustituye `main.ejecutar_partida_controlada` por una versión falsa (sin
motor real, sin config real) para probar el CICLO DE VIDA DEL HILO -- que
pausar detiene el avance real, que finalizar deja el hilo anterior
realmente muerto antes de arrancar el siguiente -- sin pagar el coste de
levantar un Mundo real en cada test. Cada test es una "ley física" del
comportamiento real que se valida, misma convención que el resto del
proyecto.
"""
import time

import main
from presentacion.gestor_partidas import GestorPartidas
from presentacion.vista_web import ServidorWeb


def _partida_falsa(semilla, control, servidor_web, config, ruta_base):
    """Bucle mínimo que solo ejerce el mecanismo de control (pausa/
    detener/velocidad), incrementando un contador de ticks en vez de
    correr el motor real."""
    ticks = 0
    while not control.detener.is_set():
        control.esperar_si_pausado()
        if control.detener.is_set():
            break
        ticks += 1
        servidor_web.actualizar_instantanea({"ticks": ticks, "semilla": semilla})
        time.sleep(0.02)


def _servidor() -> ServidorWeb:
    servidor_web = ServidorWeb(puerto=0)
    servidor_web.iniciar()
    return servidor_web


def test_ley_sin_partida_activa_al_construir(monkeypatch):
    servidor_web = _servidor()
    try:
        gestor = GestorPartidas(servidor_web, {}, None)
        assert gestor.estado()["activa"] is False
    finally:
        servidor_web.detener()


def test_ley_nueva_partida_arranca_el_hilo_y_avanza(monkeypatch):
    monkeypatch.setattr(main, "ejecutar_partida_controlada", _partida_falsa)
    servidor_web = _servidor()
    try:
        gestor = GestorPartidas(servidor_web, {}, None)
        gestor.nueva(semilla=42)
        time.sleep(0.2)
        estado = gestor.estado()
        assert estado["activa"] is True
        assert estado["semilla"] == 42
        assert servidor_web.instantanea_json != "{}"
    finally:
        gestor.finalizar()
        servidor_web.detener()


def test_ley_nueva_sin_semilla_es_aleatoria(monkeypatch):
    monkeypatch.setattr(main, "ejecutar_partida_controlada", _partida_falsa)
    servidor_web = _servidor()
    try:
        gestor = GestorPartidas(servidor_web, {}, None)
        semilla_1 = gestor.nueva()
        gestor.finalizar()
        semilla_2 = gestor.nueva()
        # No es una ley matemática (dos semillas aleatorias PODRIAN
        # coincidir), pero con un rango de 2**31 la probabilidad real es
        # despreciable -- si esto falla alguna vez, es señal real de que
        # random.randint dejo de variar entre llamadas, no un flake a
        # ignorar.
        assert semilla_1 != semilla_2
    finally:
        gestor.finalizar()
        servidor_web.detener()


def test_ley_pausar_detiene_el_avance_real(monkeypatch):
    monkeypatch.setattr(main, "ejecutar_partida_controlada", _partida_falsa)
    servidor_web = _servidor()
    try:
        gestor = GestorPartidas(servidor_web, {}, None)
        gestor.nueva(semilla=1)
        time.sleep(0.15)
        assert gestor.pausar() is True
        assert gestor.estado()["pausada"] is True
        tras_pausar = servidor_web.instantanea_json
        time.sleep(0.2)
        assert servidor_web.instantanea_json == tras_pausar  # no avanzo mientras pausado
    finally:
        gestor.finalizar()
        servidor_web.detener()


def test_ley_reanudar_retoma_el_avance(monkeypatch):
    monkeypatch.setattr(main, "ejecutar_partida_controlada", _partida_falsa)
    servidor_web = _servidor()
    try:
        gestor = GestorPartidas(servidor_web, {}, None)
        gestor.nueva(semilla=1)
        gestor.pausar()
        congelado = servidor_web.instantanea_json
        time.sleep(0.1)
        assert servidor_web.instantanea_json == congelado

        assert gestor.reanudar() is True
        assert gestor.estado()["pausada"] is False
        time.sleep(0.15)
        assert servidor_web.instantanea_json != congelado
    finally:
        gestor.finalizar()
        servidor_web.detener()


def test_ley_pausar_sin_partida_activa_devuelve_false():
    servidor_web = _servidor()
    try:
        gestor = GestorPartidas(servidor_web, {}, None)
        assert gestor.pausar() is False
        assert gestor.reanudar() is False
        assert gestor.velocidad(2.0) is None
    finally:
        servidor_web.detener()


def test_ley_velocidad_se_refleja_en_el_control(monkeypatch):
    monkeypatch.setattr(main, "ejecutar_partida_controlada", _partida_falsa)
    servidor_web = _servidor()
    try:
        gestor = GestorPartidas(servidor_web, {}, None)
        gestor.nueva(semilla=1)
        resultado = gestor.velocidad(4.0)
        assert resultado == 4.0
        assert gestor.estado()["velocidad"] == 4.0
    finally:
        gestor.finalizar()
        servidor_web.detener()


def test_ley_finalizar_deja_el_hilo_realmente_muerto(monkeypatch):
    monkeypatch.setattr(main, "ejecutar_partida_controlada", _partida_falsa)
    servidor_web = _servidor()
    try:
        gestor = GestorPartidas(servidor_web, {}, None)
        gestor.nueva(semilla=1)
        hilo_anterior = gestor._hilo
        time.sleep(0.1)
        assert hilo_anterior.is_alive()

        gestor.finalizar()
        assert not hilo_anterior.is_alive()
        assert gestor.estado()["activa"] is False
    finally:
        servidor_web.detener()


def test_ley_nueva_partida_sustituye_la_anterior_sin_dejarla_corriendo(monkeypatch):
    monkeypatch.setattr(main, "ejecutar_partida_controlada", _partida_falsa)
    servidor_web = _servidor()
    try:
        gestor = GestorPartidas(servidor_web, {}, None)
        gestor.nueva(semilla=1)
        hilo_1 = gestor._hilo
        time.sleep(0.1)

        gestor.nueva(semilla=2)
        assert not hilo_1.is_alive()  # el primer hilo murio de verdad
        assert gestor.estado()["semilla"] == 2
        assert gestor._hilo is not hilo_1
    finally:
        gestor.finalizar()
        servidor_web.detener()


def test_ley_finalizar_sin_partida_activa_no_falla():
    servidor_web = _servidor()
    try:
        gestor = GestorPartidas(servidor_web, {}, None)
        assert gestor.finalizar() is False  # idempotente, no hay nada que parar
    finally:
        servidor_web.detener()
