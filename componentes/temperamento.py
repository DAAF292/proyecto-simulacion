"""Componente Temperamento: dato puro, sin logica.

Rasgos de temperamento con rango racial (informe tecnico, seccion 8.6 /
criatura.docx seccion 4.1): sorteados al nacer dentro del rango de la
especie, fijos de por vida en fase 0 -- sin capa de expresion dinamica.
El efecto de que un individuo cansado sea menos sociable, por ejemplo,
sale gratis de la competencia de necesidades del Utility AI (una energia
critica gana la decision antes de que la sociabilidad tenga ocasion de
pesar), no de que el rasgo mismo cambie de valor con el estado del
individuo.

Bloque B del plan de migracion (sustituye a la vieja Categoria, que
mezclaba esto con dimensiones fisicas -- ver DimensionesFisicas en este
mismo paquete): valentia, sociabilidad y agresividad son los tres rasgos
que el prototipo asociaba a esta migracion. Correccion tras auditoria de
coherencia (el codigo, no la intencion original, manda): en la practica
solo agresividad tenia consumidor real en ese momento (ajuste de evasion
en sistema_depredacion.py). sociabilidad gano el suyo mas tarde, fuera de
orden alfabetico -- el sesgo gregario en deambular (sistemas/
sistema_movimiento.py, surgido de una pregunta directa de Diego, no del
plan por bloques). valentia sigue sin ninguno.

Bloque E: dominancia, empatia, lealtad, fe y curiosidad completan los
ocho rasgos de criatura.docx (4.1). Ninguno tiene sistema que lo consuma
todavia -- dominancia espera el calculo de liderazgo de un asentamiento,
empatia y lealtad esperan vinculos personales con nombre propio, fe
espera el sistema de magia (fase 7+), curiosidad espera logica de
exploracion mas alla de deambular. Se sortean igual que el resto (mismo
mecanismo de rango racial), declarados y persistidos desde ya -- a
diferencia de las necesidades sin mecanica del Bloque D3, estos SI se
fijan por individuo al nacer y deben sobrevivir a guardar/cargar, aunque
ningun sistema los lea todavia.
"""
from dataclasses import dataclass


@dataclass
class Temperamento:
    valentia: float
    sociabilidad: float
    agresividad: float
    dominancia: float
    empatia: float
    lealtad: float
    fe: float
    curiosidad: float
