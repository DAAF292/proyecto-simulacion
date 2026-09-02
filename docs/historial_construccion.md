# Historial de diseño — `nucleo/construccion.py`

Extraído de los comentarios en línea el 2026-09-02 (ver CLAUDE.md,
sección "Comentarios técnicos vs narrativa histórica").

**Módulo, en general**: fundamento de la pieza "refugio construido"
(2026-08-30, ver componentes/construccion.py y la conversación de
diseño con Diego que dio origen al sistema de refugio/almacén).

**`material_suficiente_para`**: nació en el Círculo C (2026-08-30,
RECOLECTAR) limitado a "el refugio propio", generalizado en el Círculo
E (2026-08-30, almacén) a "cualquier Construccion objetivo, con id
explícito" para servir igual a refugio que a almacén compartido.

**`espacio_disponible_para_construir`** (2026-08-31): antes de esta
pieza, ninguna Construccion tenía noción de área — solo de masa de
materiales. Ver docstring de config/materiales.yaml, sección
construccion, para el razonamiento completo de por qué hacía falta un
límite de espacio por celda ("¿una hoguera ocupa lo mismo que una
casa?").

**`objetivo_construccion_actual`**: Círculo E (2026-08-30, almacén de
asentamiento) — el punto único que unifica la prioridad refugio-antes-
que-almacén en un solo lugar, consumido igual por decisión, movimiento
y recursos.
