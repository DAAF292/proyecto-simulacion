from pathlib import Path

p = Path(r'presentacion/vista_web.py')
raw = p.read_bytes()
lineas = raw.split(b'\n')

# Linea 346 (indice 345): la linea RUNAS quedo con mojibake triple por los
# pases de PowerShell; se sustituye por los runas correctos en UTF-8 limpio.
correcta = "    const RUNAS = { 'gnomo': '\u16b7', 'lobo': '\u16da', 'conejo': '\u16b2', 'ardilla': '\u16a8', 'necromasa': '\U0001f9b4' };"
lineas[345] = correcta.encode('utf-8')

# Linea 1404 (indice 1403) y 2184 (indice 2183): montana y librerias.
lineas[1403] = lineas[1403].replace(b'monta\xc3\x83\xc2\xb1a', b'monta\xc3\xb1a')
lineas[2183] = lineas[2183].replace(b'librer\xc3\x83\xc2\xadas', b'librer\xc3\xadas')

raw = b'\n'.join(lineas)
p.write_bytes(raw)
print('runas y comentarios restaurados')
