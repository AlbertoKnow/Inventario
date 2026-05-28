# Diagrama de Arquitectura — Sistema de Inventario UTP

> Stack: Python 3.11 · Django 4.2 · PostgreSQL 16 · Docker · DigitalOcean

---

## 1. Arquitectura de Infraestructura

```mermaid
graph TD
    USER["🌐 Usuario\n(Navegador)"]

    subgraph DO["☁️ DigitalOcean VPS — Ubuntu 22.04"]
        direction TB

        subgraph PROXY_LAYER["Capa de Entrada"]
            NPM["Nginx Proxy Manager\n• Terminación SSL/TLS\n• Certificados Let's Encrypt\n• Redirección HTTP → HTTPS\npuertos: 80, 443"]
        end

        subgraph NET["Red Docker Interna: docker-server-network"]
            direction TB

            subgraph APP_CONTAINER["Contenedor: inventario"]
                GUNICORN["Gunicorn\n(2 workers WSGI)\npuerto interno: 8000"]
                DJANGO["Django 4.2\nAplicación"]
                WHITENOISE["WhiteNoise\nArchivos estáticos"]
                GUNICORN --> DJANGO
                WHITENOISE --> DJANGO
            end

            subgraph DB_CONTAINER["Contenedor: inventario-db"]
                PG["PostgreSQL 16\npuerto interno: 5432"]
            end

            APP_CONTAINER -->|"psycopg2\nred interna"| DB_CONTAINER
        end

        subgraph OPS["Operaciones"]
            PORTAINER["Portainer\nGestión de contenedores\npuerto: 9000"]
            KUMA["Uptime Kuma\nMonitoreo de disponibilidad\npuerto: 3001"]
            WATCHTOWER["Watchtower\nActualización automática\nde imágenes Docker"]
        end

        subgraph VOLUMES["Volúmenes Persistentes"]
            VOL_MEDIA["./data/media\nFotos e imágenes\nde ítems"]
            VOL_DB["./data/postgres\nDatos de PostgreSQL"]
        end
    end

    subgraph EXT["Servicios Externos"]
        RESEND["Resend API\nEnvío de correos\n(actas, notificaciones)"]
        GIT["GitHub\nControl de versiones\nCI/CD manual"]
    end

    USER -->|"HTTPS"| NPM
    NPM -->|"HTTP proxy\nred interna"| APP_CONTAINER
    APP_CONTAINER -.->|"API REST"| RESEND
    APP_CONTAINER --- VOL_MEDIA
    DB_CONTAINER --- VOL_DB

    style DO fill:#0069ff,color:#fff,stroke:#0050cc
    style NET fill:#e8f4fd,stroke:#0069ff
    style APP_CONTAINER fill:#c8e6c9,stroke:#388e3c
    style DB_CONTAINER fill:#fff9c4,stroke:#f9a825
    style OPS fill:#f3e5f5,stroke:#7b1fa2
    style VOLUMES fill:#fce4ec,stroke:#c62828
    style EXT fill:#e0f2f1,stroke:#00695c
```

---

## 2. Arquitectura de la Aplicación Django

```mermaid
graph LR
    subgraph REQUEST["Ciclo de una Petición HTTP"]
        direction TB

        CLIENT["Cliente HTTP"]

        subgraph MW["Middleware Stack (ordenado)"]
            MW1["SecurityMiddleware\nHeaders de seguridad"]
            MW2["WhiteNoiseMiddleware\nArchivos estáticos"]
            MW3["SessionMiddleware\nSesiones (24h)"]
            MW4["CsrfViewMiddleware\nProtección CSRF"]
            MW5["AuthenticationMiddleware\nIdentidad del usuario"]
            MW6["CurrentUserMiddleware\nCaptura usuario p/auditoría"]
        end

        subgraph ROUTER["Enrutamiento"]
            URL["urls.py\nconfig/urls.py\n+ productos/urls_legacy.py"]
        end

        subgraph VIEWS["Vistas (views_legacy.py)"]
            V_AUTH["Autenticación\nlogin / logout"]
            V_ITEMS["Gestión de Ítems\nCRUD + búsqueda + filtros"]
            V_ACTAS["Actas de Entrega\n+ envío por email + PDF"]
            V_MOV["Movimientos\n+ flujo aprobación"]
            V_MANT["Mantenimientos\n+ lotes"]
            V_GAR["Garantías\n+ alertas"]
            V_REPORT["Reportes\n+ exportación Excel"]
            V_DASH["Dashboard\nEstadísticas en tiempo real"]
        end

        subgraph MIXINS["Mixins de Permisos"]
            MIX1["LoginRequiredMixin"]
            MIX2["RolRequeridoMixin\n(admin/gerente/supervisor...)"]
            MIX3["AreaPermissMixin\n(filtro por área/campus)"]
        end

        subgraph FORMS["Formularios (forms_legacy.py)"]
            F1["ItemForm\n+ validación MIME\n+ sanitización"]
            F2["ActaForm / MovimientoForm"]
            F3["ColaboradorForm"]
        end

        subgraph UTILS["Utilidades"]
            U1["acta_pdf.py\nReportLab → PDF"]
            U2["acta_email.py\nResend → Email con adjuntos"]
            U3["export_utils.py\nopenpyxl → Excel"]
        end

        subgraph SIGNALS["Señales Django"]
            S1["pre_save / post_save\nen Item"]
            S2["post_save\nen Movimiento"]
            S3["HistorialCambio\nauditoría de campos"]
            S4["Notificacion\nalertas en tiempo real"]
        end

        subgraph MODELS["Modelos (models_legacy.py)"]
            direction TB
            M_LOCATION["📍 Ubicación\nCampus→Sede→Pabellón→Ambiente"]
            M_ITEM["📦 Item\nentidad central"]
            M_COLLAB["👤 Colaborador\nreceptor de equipos"]
            M_ACTA["📄 Acta de Entrega"]
            M_PROV["🏢 Proveedor→Contrato→Lote"]
            M_USER["🔐 PerfilUsuario\n5 roles RBAC"]
        end

        DB[("PostgreSQL 16")]
    end

    CLIENT --> MW1 --> MW2 --> MW3 --> MW4 --> MW5 --> MW6
    MW6 --> URL --> VIEWS
    VIEWS --> MIXINS
    VIEWS --> FORMS --> MODELS
    VIEWS --> UTILS
    MODELS --> S1 --> S3
    S1 --> S4
    MODELS --> S2 --> S4
    MODELS <--> DB
```

---

## 3. Modelo de Dominio (Entidades Clave)

```mermaid
erDiagram
    Campus {
        int id PK
        string nombre
        string codigo
    }
    Sede {
        int id PK
        int codigo_sede
        string nombre
    }
    Pabellon {
        int id PK
        char letra
    }
    Ambiente {
        int id PK
        string codigo "autogenerado: 77C201"
        string tipo
        int piso
        int numero
    }
    Area {
        int id PK
        string codigo "sistemas/operaciones/laboratorio"
    }
    TipoItem {
        int id PK
        string nombre
    }
    Proveedor {
        int id PK
        string ruc
        string razon_social
    }
    Contrato {
        int id PK
        string numero_contrato
        decimal monto_total
        string estado
    }
    Lote {
        int id PK
        string codigo_interno "LOT-YYYY-XXXX"
        date fecha_adquisicion
    }
    Item {
        int id PK
        string codigo_utp "autogenerado"
        string codigo_interno
        string serie
        string estado
        decimal precio
        date garantia_hasta
        bool es_leasing
    }
    PerfilUsuario {
        int id PK
        string rol "admin/gerente/supervisor/auxiliar/almacen"
    }
    Colaborador {
        int id PK
        string nombre
        string cargo
        string dni
    }
    Acta {
        int id PK
        string numero_acta
        date fecha
        string tipo
    }
    Movimiento {
        int id PK
        string tipo "traslado/prestamo/baja"
        string estado "pendiente/aprobado/rechazado"
    }
    Mantenimiento {
        int id PK
        string tipo
        string estado
        date fecha_inicio
    }
    GarantiaRegistro {
        int id PK
        date fecha_envio
        string estado
    }
    HistorialCambio {
        int id PK
        string campo
        string valor_anterior
        string valor_nuevo
        datetime fecha
    }
    Notificacion {
        int id PK
        string tipo
        string titulo
        bool urgente
        bool leida
    }

    Campus ||--o{ Sede : contiene
    Sede ||--o{ Pabellon : contiene
    Pabellon ||--o{ Ambiente : contiene
    Area ||--o{ TipoItem : clasifica
    TipoItem ||--o{ Item : tipifica
    Ambiente ||--o{ Item : ubica
    Proveedor ||--o{ Contrato : firma
    Contrato ||--o{ Lote : agrupa
    Lote ||--o{ Item : incluye
    Item ||--o{ HistorialCambio : registra
    Item ||--o{ Movimiento : genera
    Item ||--o{ Mantenimiento : recibe
    Item ||--o{ GarantiaRegistro : tiene
    Colaborador ||--o{ Acta : recibe
    Acta }o--o{ Item : incluye
    PerfilUsuario ||--|| Area : pertenece
```

---

## 4. Seguridad Implementada

```mermaid
mindmap
  root((Seguridad))
    Transporte
      HTTPS obligatorio en producción
      HSTS 1 año + preload + subdomains
      Certificados Let's Encrypt via NPM
      SECURE_PROXY_SSL_HEADER configurado
    Autenticación y Sesiones
      Django Auth nativo
      Sesiones de 24 horas
      SESSION_COOKIE_SECURE
      CSRF_COOKIE_SECURE
      Validadores de contraseña robustos
    Autorización
      RBAC con 5 roles
      Mixins de permisos por vista
      Filtrado por área y campus
    Entradas de Usuario
      CSRF en todos los formularios
      Validación MIME real con python-magic
      Límite de tamaño de archivos 10MB
      Rate limiting con django-ratelimit
      Validadores personalizados
    Headers HTTP
      X-Frame-Options DENY
      SECURE_CONTENT_TYPE_NOSNIFF
      SECURE_BROWSER_XSS_FILTER
    Configuración
      Secretos vía variables de entorno python-decouple
      DEBUG=False en producción
      Sin credenciales en código fuente
      .env excluido de git
    Auditoría y Trazabilidad
      HistorialCambio por señales Django
      Thread-local para capturar usuario activo
      Logs rotativos 10MB x5 backups
      Log de errores separado del log de auditoría
    Contenedores
      Imágenes slim minimizando superficie de ataque
      Red Docker interna sin exposición directa del app
      Restart unless-stopped
      Volúmenes separados para datos
```

---

## 5. Flujo de Despliegue

```mermaid
sequenceDiagram
    participant DEV as Desarrollador (local)
    participant GIT as GitHub (master)
    participant DO as Servidor DO
    participant DC as Docker Compose
    participant APP as Contenedor inventario

    DEV->>GIT: git push origin master
    DEV->>DO: ssh root@204.48.27.5
    DO->>GIT: git pull origin master
    DO->>DC: docker compose build
    DC->>DC: FROM python:3.11-slim
    DC->>DC: pip install requirements.txt
    DC->>DC: COPY app/
    DO->>DC: docker compose up -d
    DC->>APP: python manage.py migrate --noinput
    DC->>APP: python manage.py collectstatic --noinput
    DC->>APP: gunicorn config.wsgi --bind 0.0.0.0:8000 --workers 2
    APP-->>DO: ✅ Contenedor activo en red interna
```

---

## Resumen Técnico

| Componente | Tecnología | Justificación |
|---|---|---|
| Lenguaje | Python 3.11 | Versión LTS estable, tipado mejorado |
| Framework | Django 4.2 LTS | Baterías incluidas, ORM robusto, admin |
| Base de datos | PostgreSQL 16 | ACID compliant, escalable |
| WSGI | Gunicorn 2 workers | Concurrencia en producción |
| Archivos estáticos | WhiteNoise | Sin dependencia de Nginx para estáticos |
| Contenedores | Docker + Compose | Reproducibilidad, aislamiento |
| Proxy/SSL | Nginx Proxy Manager | Terminación SSL centralizada, multi-proyecto |
| Email | Resend API | Entregabilidad alta, SPF/DKIM incluido |
| PDF | ReportLab | Generación de actas sin dependencias externas |
| Excel | openpyxl | Importación masiva de inventario |
| Seguridad archivos | python-magic | Validación MIME real (no solo extensión) |
| Rate limiting | django-ratelimit | Protección contra ataques de fuerza bruta |
| Variables de entorno | python-decouple | Separación config/código (12-factor app) |
| Auditoría | Django Signals | Historial automático sin modificar modelos |
| Control de versiones | Git + GitHub | Historial completo, 15+ commits documentados |
| Monitoreo | Uptime Kuma | Alertas de disponibilidad 24/7 |
