#!/bin/bash
# ==============================================================================
# SCRIPT DE DESPLIEGUE - INVENTARIO UTP
# Ejecutar en el servidor Digital Ocean después de clonar el repositorio
# ==============================================================================

set -e  # Salir si hay error

echo "=========================================="
echo "  DESPLIEGUE INVENTARIO UTP"
echo "=========================================="

# Variables (ajustar según sea necesario)
PROJECT_DIR="/var/www/inventario"
VENV_DIR="$PROJECT_DIR/venv"
USER="www-data"

# 1. Actualizar sistema
echo ">>> Actualizando sistema..."
sudo apt update && sudo apt upgrade -y

# 2. Instalar dependencias del sistema
echo ">>> Instalando dependencias..."
sudo apt install -y python3 python3-pip python3-venv python3-dev \
    postgresql postgresql-contrib libpq-dev \
    nginx certbot python3-certbot-nginx \
    git curl

# 3. Crear directorio del proyecto
echo ">>> Creando directorio del proyecto..."
sudo mkdir -p $PROJECT_DIR
sudo chown $USER:$USER $PROJECT_DIR

# 4. Clonar repositorio (si no existe)
if [ ! -d "$PROJECT_DIR/.git" ]; then
    echo ">>> Clonando repositorio..."
    sudo -u $USER git clone https://github.com/AlbertoKnow/Inventario.git $PROJECT_DIR
fi

# 5. Crear entorno virtual
echo ">>> Creando entorno virtual..."
cd $PROJECT_DIR
python3 -m venv $VENV_DIR

# 6. Instalar dependencias Python
echo ">>> Instalando dependencias Python..."
source $VENV_DIR/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 7. Configurar PostgreSQL
echo ">>> Configurando PostgreSQL..."
sudo -u postgres psql -c "CREATE DATABASE inventario_db;" 2>/dev/null || echo "Base de datos ya existe"
sudo -u postgres psql -c "CREATE USER inventario_user WITH PASSWORD 'CAMBIAR_PASSWORD';" 2>/dev/null || echo "Usuario ya existe"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE inventario_db TO inventario_user;"
sudo -u postgres psql -c "ALTER USER inventario_user CREATEDB;"

# 8. Copiar archivo de entorno
echo ">>> Configurando variables de entorno..."
if [ ! -f "$PROJECT_DIR/.env" ]; then
    cp $PROJECT_DIR/.env.production.example $PROJECT_DIR/.env
    echo "⚠️  IMPORTANTE: Editar $PROJECT_DIR/.env con los valores correctos"
fi

# 9. Recopilar archivos estáticos
echo ">>> Recopilando archivos estáticos..."
python manage.py collectstatic --noinput

# 10. Ejecutar migraciones
echo ">>> Ejecutando migraciones..."
python manage.py migrate

# 11. Crear superusuario (opcional)
echo ">>> ¿Deseas crear un superusuario? (s/n)"
read -r respuesta
if [ "$respuesta" = "s" ]; then
    python manage.py createsuperuser
fi

echo "=========================================="
echo "  ✅ DESPLIEGUE BASE COMPLETADO"
echo "=========================================="
echo ""
echo "Próximos pasos:"
echo "1. Editar /var/www/inventario/.env con los valores correctos"
echo "2. Configurar Gunicorn (ver gunicorn.service)"
echo "3. Configurar Nginx (ver nginx.conf)"
echo "4. Configurar SSL con Certbot"
echo ""
