#!/bin/bash
# Script para iniciar el servidor de desarrollo en macOS/Linux

echo "======================================"
echo "Sistema de Inventario - Desarrollo"
echo "======================================"
echo

# Verificar si el entorno virtual existe
if [ ! -d "venv" ]; then
    echo "Creando entorno virtual..."
    python3 -m venv venv
fi

# Activar el entorno virtual
source venv/bin/activate

# Instalar dependencias si es necesario
pip install -r requirements.txt > /dev/null 2>&1

# Realizar migraciones
echo "Ejecutando migraciones..."
python manage.py migrate

# Iniciar servidor
echo
echo "======================================"
echo "Servidor iniciado en: http://127.0.0.1:8000/"
echo "Panel Admin: http://127.0.0.1:8000/admin/"
echo "Presiona Ctrl+C para detener"
echo "======================================"
echo

python manage.py runserver
