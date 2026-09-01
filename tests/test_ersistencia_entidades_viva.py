"""Test de la ley de persistencia histórica de entidades (2026-09-02,
fix aislado -- ver CLAUDE.md).

La tabla `entidades` es el registro histórica PERMANENTE de toda
entidad que ha existido en la partida (vivo o muerto), distinto del
snapshot en vivo `componentes_estado` (que sí se sobrescribe en cada
guardado y solo contiene quién sigue vivo ahora). La columna `viva` de
`entidades` debía reflejar el estado real -- este test verifica el
ciclo completo: nace viva, muere y deja de estarlo, sin que la fila se
borre ni se duplique.
"""
import sqlite3
from pathlib import Path

from nucleo.persistencia import Persistencia


def _leer_viva(ruta_db: Path, entidad_id: int) -> bool:
    con = sqlite3.connect(ruta_db)
    try:
        cur = con.cursor()
        cur.execute("SELECT viva FROM entidades WHERE id = ?", (entidad_id,))
        fila = cur.fetchone()
        assert fila is not None, f"no existe fila para entidad_id={entidad_id}"
        return bool(fila[0])
    finally:
        con.close()


def test_entidad_nace_viva_y_muere_no_viva(tmp_path):
    """Ley: registar_entidad_nueva deja viva=True; marcar_entidad_muerta
    la pasa a viva=False sobre la MISMA fila, sin crear una fila nueva
    ni borrar la existente."""
    ruta_db = tmp_path / "test_entidades_viva.db"
    persistencia = Persistencia(ruta_db)

    persistencia.registar_entidad_nueva(
        entidad_id=7,
        datos={"especie": "gnomo", "nombre": "Test", "tick_nacimiento": 0},
    )
    assert _leer_viva(ruta_db, 7) is True

    persistencia.marcar_entidad_muerta(7)
    assert _leer_viva(ruta_db, 7) is False


def test_maracr_muerta_no_afecta_a_otras_entidades(tmp_path):
    """Ley: marcar_entidad_muerta solo toca la fila de su propio
    entidad_id -- una entidad distinta que sigue viva no se ve afactada."""
    ruta_db = tmp_path / "test_entidades_viva_multi.db"
    persistencia = Persistencia(ruta_db)

    persistencia.registar_entidad_nueva(
        entidad_id=1, datos={"especie": "gnomo", "tick_nacimiento": 0}
    )
    persistencia.registar_entidad_nueva(
        entidad_id=2, datos={"especie": "lobo", "tick_nacimiento": 0}
    )

    persistencia.marcar_entidad_muerta(1)

    assert _leer_viva(ruta_db, 1) is False
    assert _leer_viva(ruta_db, 2) is True
