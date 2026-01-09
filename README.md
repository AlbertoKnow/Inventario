# 📦 Sistema de Inventario UTP

Sistema de gestión de inventario para la **Universidad Tecnológica del Perú (UTP)** desarrollado con Django.

## 🚀 Características

- ✅ **Herencia Multi-tabla**: Productos base con especialización (Equipos Electrónicos, Muebles)
- ✅ **Gestión completa**: CRUD para todos los tipos de productos
- ✅ **Control de inventario**: Alertas de stock bajo y movimientos registrados
- ✅ **Auditoría**: Registro de movimientos y mantenimientos
- ✅ **Dashboard**: Panel con métricas y gráficos
- ✅ **Responsive**: Bootstrap 5 + Font Awesome 6
- ✅ **Pruebas automatizadas**: 44 tests unitarios y de integración

## 🛠️ Stack Tecnológico

| Componente | Tecnología |
|------------|------------|
| Backend | Django 6.0.1 |
| Frontend | Django Templates + Bootstrap 5 |
| Base de Datos | SQLite (desarrollo) |
| Python | 3.14+ |
| Testing | Django TestCase (44 tests) |

## ⚡ Inicio Rápido

```bash
# 1. Clonar repositorio
git clone https://github.com/AlbertoKnow/Inventario.git
cd Inventario

# 2. Crear y activar entorno virtual
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows PowerShell
# source venv/bin/activate   # Linux/Mac

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Aplicar migraciones
python manage.py migrate

# 5. Crear superusuario
python manage.py createsuperuser

# 6. Ejecutar servidor
python manage.py runserver
```

Accede a: **http://127.0.0.1:8000/**

## 🧪 Ejecutar Pruebas

```bash
python manage.py test productos
```

## 📁 Estructura del Proyecto

```
Inventario/
├── config/                 # Configuración Django
│   ├── settings.py         # Configuración principal
│   ├── urls.py             # URLs raíz
│   └── wsgi.py             # Servidor WSGI
├── productos/              # Aplicación principal
│   ├── models.py           # Modelos (Producto, Equipo, Mueble, etc.)
│   ├── views.py            # Vistas basadas en clases
│   ├── forms.py            # Formularios
│   ├── admin.py            # Admin personalizado
│   ├── urls.py             # URLs de productos
│   └── tests.py            # 44 pruebas automatizadas
├── templates/              # Plantillas HTML
│   ├── base.html           # Template base
│   ├── index.html          # Página de inicio
│   └── productos/          # Templates de productos
├── scripts/                # Scripts de utilidad
│   ├── crear_datos_prueba.py
│   ├── check_environment.py
│   └── run.bat / run.sh
├── requirements.txt        # Dependencias
└── manage.py               # CLI Django
```

## 📊 Modelos de Datos

```
Producto (Base)
├── EquipoElectronico (marca, modelo, número de serie...)
└── Mueble (material, color, dimensiones...)

Modelos de soporte:
├── Categoria
├── TipoProducto
├── Ubicacion
├── Condicion
├── Movimiento (auditoría de inventario)
└── Mantenimiento (historial de equipos)
```

## 🔧 Configuración

Crea un archivo `.env` basándote en `.env.example`:

```env
SECRET_KEY=tu-clave-secreta
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

## 📝 Licencia

[MIT License](LICENSE)

---

Desarrollado para la **Universidad Tecnológica del Perú** 🇵🇪
