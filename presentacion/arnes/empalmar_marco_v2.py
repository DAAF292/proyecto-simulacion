from pathlib import Path

RUTA = Path(r'C:\Users\diego\Desktop\simulación mundo\bosque\presentacion\vista_web.py')
FRAGMENTO = Path(r'C:\Users\diego\AppData\Local\Temp\opencode\recorte_assets\marco_nuevo.txt')

texto = RUTA.read_text(encoding='utf-8')
nuevo = FRAGMENTO.read_text(encoding='utf-8').rstrip() + '\n'

# Bloque v1 a sustituir: desde su comentario unico hasta el PRIMER cierre
# de bloque '    }' que aparece despues del inicio (el cierre de la propia
# funcion). Nunca cruza hacia otras funciones: el limite es local.
inicio = texto.find('    // Circulo 4 (2026-08-27): marco de CODICE')
assert inicio > 0, 'comentario v1 no encontrado'
fin = texto.find('\n    }\n', inicio)
assert fin > inicio, 'cierre de la funcion v1 no encontrado'
fin += len('\n    }\n')

RUTA.write_text(texto[:inicio] + nuevo + texto[fin:], encoding='utf-8')

# Verificacion inmediata: las funciones criticas siguen presentes.
comprobaciones = [
    'function dibujarFormacionesMacro',
    'function colorLavadoContinuo',
    'function componentesPorBioma',
    'function setModoMapa',
    'function dibujarMarcoCodice(ancho, alto, celdaPantalla',
]
for c in comprobaciones:
    assert c in RUTA.read_text(encoding='utf-8'), f'FALTA: {c}'
print('empalme v2 aplicado y funciones intactas')
