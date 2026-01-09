@echo off
REM Script para iniciar el servidor de desarrollo en Windows

echo ======================================
echo Sistema de Inventario - Desarrollo
echo ======================================
echo.

REM Verificar si el entorno virtual existe
if not exist "venv" (
    echo Creando entorno virtual...
    python -m venv venv
)

REM Activar el entorno virtual
call venv\Scripts\activate.bat

REM Instalar dependencias si es necesario
pip install -r requirements.txt > nul 2>&1

REM Realizar migraciones
echo Ejecutando migraciones...
python manage.py migrate

REM Iniciar servidor
echo.
echo ======================================
echo Servidor iniciado en: http://127.0.0.1:8000/
echo Panel Admin: http://127.0.0.1:8000/admin/
echo Presiona Ctrl+C para detener
echo ======================================
echo.

python manage.py runserver
