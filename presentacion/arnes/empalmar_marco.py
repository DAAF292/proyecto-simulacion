from pathlib import Path

RUTA = Path(r'C:\Users\diego\Desktop\simulación mundo\bosque\presentacion\vista_web.py')
FRAGMENTO = Path(r'C:\Users\diego\AppData\Local\Temp\opencode\recorte_assets\marco_nuevo.txt')

texto = RUTA.read_text(encoding='utf-8')
nuevo = FRAGMENTO.read_text(encoding='utf-8')

inicio = texto.find('    function dibujarMarcoCodice(')
fin = texto.find('    // Un rio es un CAMINO')
assert inicio > 0 and fin > inicio, f'marcadores no encontrados ({inicio}, {fin})'

RUTA.write_text(texto[:inicio] + nuevo + texto[fin:], encoding='utf-8')
print('sustituido ok')
