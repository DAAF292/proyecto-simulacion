# Comandos — prototipo del bosque

Referencia rápida de terminal (PowerShell, Windows). Todo se ejecuta desde la
carpeta del proyecto: `C:\Users\diego\Desktop\simulación mundo\bosque`.

## Configuración inicial (una sola vez por máquina)

Permite ejecutar scripts `.ps1` (como `Activate.ps1`) sin tener que repetirlo
en cada sesión. `RemoteSigned` exige firma solo a scripts descargados de
internet, no a los que crees tú mismo — más seguro que `Bypass` a nivel
global.

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Crear el entorno virtual e instalar dependencias (solo si `.venv` no existe
todavía):

```powershell
cd "C:\Users\diego\Desktop\simulación mundo\bosque"
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Arrancar el prototipo (modo interactivo)

Avanza tick a tick pulsando Enter, mostrando el mapa y el estado de cada
gnomo.

```powershell
cd "C:\Users\diego\Desktop\simulación mundo\bosque"
.venv\Scripts\Activate.ps1
python main.py
```

Si ya existe una partida guardada en `datos/bosque.db`, la continúa donde se
quedó (misma semilla, mismo estado del RNG). Si no existe, arranca una nueva.

## Modo automático (para pruebas largas, sin interacción)

Corre N ticks seguidos sin esperar a pulsar Enter. Pensado solo para
verificar comportamiento, no es el modo de juego real.

```powershell
$env:BOSQUE_AUTO_TICKS=500
python main.py
```

Cambia `500` por el número de ticks que quieras (p. ej. `5000` para pruebas
de calibración más largas).

## Empezar una partida nueva desde cero

Borra la partida guardada. La próxima ejecución generará un mundo nuevo con
la misma semilla por defecto (o la que se indique en `config/constantes.yaml`).

```powershell
Remove-Item "datos\bosque.db"
python main.py
```

## Git (control de versiones)

El repositorio se gestiona en local, en esta misma carpeta.

```powershell
git status
git add -A
git commit -m "mensaje descriptivo del cambio"
```

## Notas

- `.venv\Scripts\Activate.ps1` debe ejecutarse en **cada terminal nueva**
  antes de `python main.py` (la política de ejecución de arriba solo evita
  que PowerShell lo bloquee, no lo activa automáticamente).
- Salir del modo interactivo con `Ctrl+C` guarda la partida igualmente antes
  de cerrar.
