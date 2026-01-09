# ==============================================================================
# GUÍA DE DESPLIEGUE EN DIGITAL OCEAN - INVENTARIO UTP
# ==============================================================================

## Requisitos Previos

- Cuenta en Digital Ocean
- Dominio (opcional, pero recomendado para SSL)
- Repositorio en GitHub actualizado

---

## PASO 1: Crear el Droplet

1. Ir a [Digital Ocean](https://cloud.digitalocean.com/)
2. Crear nuevo Droplet:
   - **Región:** New York o la más cercana a tus usuarios
   - **Imagen:** Ubuntu 22.04 LTS
   - **Plan:** Basic $6/mes (1GB RAM, 25GB SSD)
   - **Autenticación:** SSH Key (recomendado) o Password
   - **Hostname:** inventario-utp

3. Anotar la IP del servidor

---

## PASO 2: Conectar al Servidor

```bash
ssh root@TU_IP_DEL_SERVIDOR
```

---

## PASO 3: Configuración Inicial del Servidor

```bash
# Actualizar sistema
apt update && apt upgrade -y

# Instalar dependencias
apt install -y python3 python3-pip python3-venv python3-dev \
    postgresql postgresql-contrib libpq-dev \
    nginx certbot python3-certbot-nginx \
    git curl ufw

# Configurar firewall
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw enable
```

---

## PASO 4: Configurar PostgreSQL

```bash
# Acceder a PostgreSQL
sudo -u postgres psql

# En la consola de PostgreSQL:
CREATE DATABASE inventario_db;
CREATE USER inventario_user WITH PASSWORD 'TU_PASSWORD_SEGURO';
ALTER ROLE inventario_user SET client_encoding TO 'utf8';
ALTER ROLE inventario_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE inventario_user SET timezone TO 'America/Lima';
GRANT ALL PRIVILEGES ON DATABASE inventario_db TO inventario_user;
\q
```

---

## PASO 5: Clonar y Configurar el Proyecto

```bash
# Crear directorio
mkdir -p /var/www
cd /var/www

# Clonar repositorio
git clone https://github.com/AlbertoKnow/Inventario.git inventario
cd inventario

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt

# Crear archivo .env
cp .env.production.example .env
nano .env  # Editar con los valores correctos
```

### Contenido del archivo .env:

```env
SECRET_KEY=genera-una-clave-larga-y-segura
DEBUG=False
ALLOWED_HOSTS=tu-ip,tu-dominio.com
DB_NAME=inventario_db
DB_USER=inventario_user
DB_PASSWORD=TU_PASSWORD_SEGURO
DB_HOST=localhost
DB_PORT=5432
TIME_ZONE=America/Lima
SECURE_SSL_REDIRECT=False
CSRF_TRUSTED_ORIGINS=https://tu-dominio.com
```

Para generar SECRET_KEY:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## PASO 6: Preparar Django

```bash
# Asegurarse que el entorno virtual está activo
source /var/www/inventario/venv/bin/activate
cd /var/www/inventario

# Crear directorio de logs
mkdir -p logs

# Recopilar archivos estáticos
python manage.py collectstatic --noinput

# Ejecutar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser
```

---

## PASO 7: Configurar Gunicorn (Servicio)

```bash
# Copiar archivo de servicio
sudo cp deploy/gunicorn.service /etc/systemd/system/inventario.service

# Crear usuario www-data si no existe
sudo useradd -r -s /bin/false www-data 2>/dev/null || true

# Dar permisos
sudo chown -R www-data:www-data /var/www/inventario

# Habilitar e iniciar el servicio
sudo systemctl daemon-reload
sudo systemctl enable inventario
sudo systemctl start inventario

# Verificar estado
sudo systemctl status inventario
```

---

## PASO 8: Configurar Nginx

```bash
# Copiar configuración
sudo cp deploy/nginx.conf /etc/nginx/sites-available/inventario

# Editar el archivo (cambiar dominio/IP)
sudo nano /etc/nginx/sites-available/inventario

# Habilitar sitio
sudo ln -s /etc/nginx/sites-available/inventario /etc/nginx/sites-enabled/

# Deshabilitar sitio por defecto
sudo rm /etc/nginx/sites-enabled/default 2>/dev/null || true

# Verificar configuración
sudo nginx -t

# Reiniciar Nginx
sudo systemctl restart nginx
```

---

## PASO 9: Configurar SSL (HTTPS) - Opcional pero Recomendado

Si tienes un dominio apuntando al servidor:

```bash
sudo certbot --nginx -d tu-dominio.com -d www.tu-dominio.com
```

Después de configurar SSL, editar `.env`:
```
SECURE_SSL_REDIRECT=True
CSRF_TRUSTED_ORIGINS=https://tu-dominio.com,https://www.tu-dominio.com
```

Y reiniciar:
```bash
sudo systemctl restart inventario
```

---

## PASO 10: Verificar

1. Abrir en navegador: `http://TU_IP` o `https://tu-dominio.com`
2. Iniciar sesión con el superusuario creado
3. Verificar que todo funcione correctamente

---

## Comandos Útiles

```bash
# Ver logs de la aplicación
sudo journalctl -u inventario -f

# Ver logs de Nginx
sudo tail -f /var/log/nginx/error.log

# Reiniciar aplicación después de cambios
sudo systemctl restart inventario

# Actualizar código desde GitHub
cd /var/www/inventario
git pull
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart inventario
```

---

## Troubleshooting

### Error 502 Bad Gateway
- Verificar que Gunicorn esté corriendo: `sudo systemctl status inventario`
- Ver logs: `sudo journalctl -u inventario -n 50`

### Error de permisos
```bash
sudo chown -R www-data:www-data /var/www/inventario
sudo chmod -R 755 /var/www/inventario
```

### Reiniciar todo
```bash
sudo systemctl restart inventario
sudo systemctl restart nginx
```

---

## Costos Estimados

| Servicio | Costo Mensual |
|----------|---------------|
| Droplet Basic | $6 |
| Dominio (opcional) | $1/mes aprox |
| **Total** | **$6-7/mes** |

---

## Próximos Pasos (Mejoras Opcionales)

1. **Backups automáticos** - Digital Ocean ofrece por $1/mes extra
2. **Monitoreo** - Configurar alertas en Digital Ocean
3. **CDN** - Cloudflare (gratis) para mejor rendimiento
4. **CI/CD** - GitHub Actions para despliegue automático
