"""
componentes/construccion.py

Componente de datos puros para una construcción física en el mundo --
refugio individual o almacén de asentamiento. FUNDAMENTO de la pieza
"refugio construido" (2026-08-30, ver conversación de diseño con Diego y
CLAUDE.md): antes de esto, "refugio" era solo una coordenada en la
memoria individual (componentes/memoria_espacial.py, tipo "refugio"), sin
ningún objeto real en el mundo. Este componente es ese objeto.

Mismo molde que Necromasa (componentes/necromasa.py): entidad física
inerte con Posicion + este componente, sin Identidad, sin Intencion, sin
hilo individual propio -- una construcción no decide nada, no envejece
como criatura, es un objeto que otros sistemas leen y modifican.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Construccion:
    """
    Atributos:
        tipo: "refugio" | "almacen" -- catálogo abierto a propósito
            (string libre, no Enum), mismo criterio que Necromasa.
            origen_especie o el tipo de evento del bus: la lista de
            construcciones posibles crecerá (herrería, cerca...) y no
            tiene sentido cerrar un Enum para dos entradas.
        materiales: {clave_material: cantidad_kg} -- mismo patrón que
            Necromasa.masas/Inventario.contenidos/Celda.recursos. Vacío al
            crearse (progreso 0.0): la construcción empieza como un sitio
            marcado, no como una estructura ya materializada, y se llena
            con lo que Accion.CONSTRUIR transfiere desde el Inventario de
            quien construye.
        propietario_id: entidad_id del gnomo dueño (tipo "refugio"), o
            None para "almacen" -- un almacén pertenece al asentamiento,
            no a un individuo (ver conversación de diseño: "el almacén
            debe ser un objeto físico... no es una entidad nueva de
            propiedad compartida [a nivel de refugio], pero el almacén sí
            es del asentamiento"). Qué asentamiento es dueño de qué
            almacén vive en el registro de Asentamiento, no aquí --
            mismo principio que tick_nacimiento vive en Identidad y no se
            duplica en otro sitio.
        progreso: fracción [0.0, 1.0] de la masa mínima de materiales
            aptos ya aportada AHORA MISMO. 1.0 = totalmente aprovisionada
            en este instante; por debajo, sigue habiendo trabajo
            pendiente (construcción inicial O reparación tras deterioro
            -- objetivo_construccion_actual no distingue una de otra, es
            el mismo camino). Derivado en la práctica de materiales
            (suma de masa apta / umbral del tipo), pero se guarda
            explícito en vez de recalcularse cada lectura -- mismo
            criterio que otros campos de progreso acumulado del motor
            (Planta.etapa), más barato de leer que de recomputar en cada
            consumidor. FLUCTÚA: el deterioro (sistema_descomposicion.py,
            sistema_desastres.py) puede hacerlo caer de nuevo por debajo
            de 1.0 tras haberlo alcanzado.
        completado_alguna_vez: True desde la primera vez que progreso
            alcanzó 1.0, y se queda True aunque progreso decaiga después
            -- NUNCA se pone a False salvo que la propia entidad colapse
            y se elimine (una construcción nueva, si se reconstruye desde
            cero, empieza en False otra vez). Corrección de diseño
            (2026-08-30, Diego, tras ver que SistemaAsentamiento filtraba
            por progreso>=1.0 exacto: "no debería salir del asentamiento
            a la mínima degradación, una casa dañada sigue perteneciendo
            a un pueblo"): pertenencia social (¿esto llegó a ser una casa
            de verdad?) y estado de mantenimiento (¿hace falta trabajo
            aquí ahora?) son preguntas DISTINTAS que antes compartían el
            mismo campo (progreso) sin necesidad -- SistemaAsentamiento
            usa completado_alguna_vez para pertenencia,
            objetivo_construccion_actual sigue usando progreso para
            decidir si hay que aportar más material.
    """

    tipo: str
    materiales: dict[str, float] = field(default_factory=dict)
    propietario_id: int | None = None
    progreso: float = 0.0
    completado_alguna_vez: bool = False
