# Sistema de Inventario UTP

Sistema de gestión de inventario para la **Universidad Tecnológica del Perú (UTP)**, desarrollado con Django y desplegado en producción con Docker.

**Producción:** [inventario.albertoknow.com](https://inventario.albertoknow.com)

## Stack Tecnológico

| Componente | Tecnología |
|---|---|
| Backend | Django 4.2 |
| Frontend | Django Templates + Bootstrap 5 |
| Base de Datos | PostgreSQL 16 |
| Python | 3.11 |
| Servidor | Gunicorn + Nginx Proxy Manager |
| Deploy | Docker + DigitalOcean |

## Características

- Gestión de ítems con código UTP, estado, ubicación y especificaciones técnicas
- Control de movimientos (traslados, bajas, préstamos) con flujo de aprobación
- Módulo de mantenimiento preventivo y correctivo
- Módulo de garantías con seguimiento de estados
- Generación de actas de entrega en PDF
- Importación masiva desde Excel
- Sistema de permisos por roles (operador, supervisor, admin) y campus
- Auditoría y notificaciones
- Rate limiting y validación de archivos

## Estructura del Proyecto

```
Inventario/
├── config/                 # Configuración Django (settings, urls, wsgi)
├── productos/              # Aplicación principal
│   ├── models/             # Modelos organizados por dominio
│   ├── views/              # Vistas (re-exportan desde views_legacy.py)
│   ├── forms/              # Formularios (re-exportan desde forms_legacy.py)
│   ├── urls/               # URLs (re-exportan desde urls_legacy.py)
│   ├── admin/              # Admin (re-exporta desde admin_legacy.py)
│   ├── migrations/         # Migraciones de base de datos
│   ├── management/         # Comandos de gestión
│   ├── templatetags/       # Filtros y tags personalizados
│   ├── utils/              # Utilidades (PDF, email, exportación)
│   └── tests.py            # Tests automatizados
├── templates/              # Plantillas HTML (73 templates)
├── scripts/                # Scripts de utilidad
├── deploy/                 # Guía de despliegue
├── static/                 # Archivos estáticos
└── manage.py
```

## Modelos Principales

- **Item** — equipo o mueble con código UTP, tipo, estado, ubicación y especificaciones
- **Movimiento / MovimientoItem** — traslados y bajas con flujo PENDIENTE → APROBADO → EJECUTADO
- **Mantenimiento** — mantenimientos programados, preventivos y correctivos
- **GarantiaRegistro** — seguimiento de garantías con estados y documentación
- **ActaEntrega / ActaItem** — generación de actas en PDF con firma
- **Campus / Sede / Pabellon / Ambiente** — jerarquía de ubicaciones
- **PerfilUsuario** — usuarios con roles y campus permitidos

## Inicio Rápido (Desarrollo)

```bash
# 1. Clonar repositorio
git clone https://github.com/AlbertoKnow/Inventario.git
cd Inventario

# 2. Crear entorno virtual e instalar dependencias
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows
pip install -r requirements.txt

# 3. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus valores

# 4. Aplicar migraciones y crear superusuario
python manage.py migrate
python manage.py createsuperuser

# 5. Ejecutar servidor
python manage.py runserver
```

## Tests

```bash
python manage.py test productos
```

## Variables de Entorno

Crea un `.env` basándote en `.env.example`:

```env
SECRET_KEY=tu-clave-secreta
DEBUG=True
DATABASE_URL=postgres://usuario:password@localhost:5432/inventario
ALLOWED_HOSTS=localhost,127.0.0.1
```

## Licencia

[MIT License](LICENSE)

---

Desarrollado para la **Universidad Tecnológica del Perú**
