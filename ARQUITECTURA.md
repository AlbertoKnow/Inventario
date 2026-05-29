# Diagrama de Arquitectura — Sistema de Inventario

> Stack: Python 3.11 · Django 4.2 · PostgreSQL 16 · Docker · DigitalOcean

---

## 1. Contexto del Sistema

```mermaid
C4Context
    title Diagrama de Contexto

    Person(usuario, "Usuario", "Personal administrativo que gestiona el inventario desde el navegador")

    System(inventario, "Sistema de Inventario", "Gestión de ítems, movimientos, mantenimientos, garantías y actas de entrega")

    System_Ext(resend, "Resend API", "Envío de correos electrónicos con actas adjuntas")
    System_Ext(github, "GitHub", "Control de versiones y origen del código en producción")

    Rel(usuario, inventario, "Usa", "HTTPS")
    Rel(inventario, resend, "Envía correos", "HTTPS / REST")
    Rel(inventario, github, "Pull de código", "Git")
```

---

## 2. Contenedores (Infraestructura Docker)

```mermaid
C4Container
    title Diagrama de Contenedores

    Person(usuario, "Usuario", "Accede desde el navegador")

    System_Boundary(do, "DigitalOcean VPS — Ubuntu 22.04") {
        Container(npm, "Nginx Proxy Manager", "Docker / Nginx", "Terminación SSL/TLS, certificados Let's Encrypt, redirección HTTP a HTTPS")
        Container(app, "inventario", "Docker / Python 3.11", "Aplicación Django 4.2 servida con Gunicorn (2 workers)")
        ContainerDb(db, "inventario-db", "Docker / PostgreSQL 16", "Base de datos principal")
        ContainerDb(vol_media, "Volumen: data/media", "Volumen Docker", "Fotos e imágenes subidas por usuarios")
        ContainerDb(vol_db, "Volumen: data/postgres", "Volumen Docker", "Datos persistentes de PostgreSQL")
        Container(portainer, "Portainer", "Docker", "Gestión visual de contenedores")
        Container(kuma, "Uptime Kuma", "Docker", "Monitoreo de disponibilidad 24/7")
        Container(watchtower, "Watchtower", "Docker", "Actualización automática de imágenes Docker")
    }

    System_Ext(resend, "Resend API", "Servicio externo de envío de correos")

    Rel(usuario, npm, "HTTPS", "puerto 443")
    Rel(npm, app, "HTTP proxy", "puerto 8000 / red interna")
    Rel(app, db, "Consultas SQL", "psycopg2 / puerto 5432")
    Rel(app, resend, "Envía correos con actas", "HTTPS")
    Rel(app, vol_media, "Lee y escribe archivos")
    Rel(db, vol_db, "Persiste datos")
```

---

## 3. Componentes (Aplicación Django)

```mermaid
C4Component
    title Diagrama de Componentes

    Container_Boundary(app, "Contenedor: inventario") {
        Component(middleware, "Middleware Stack", "Django Middleware", "Security, WhiteNoise, Session, CSRF, Auth, CurrentUser (en orden)")
        Component(router, "URL Router", "Django URLs", "config/urls.py enruta a productos/urls_legacy.py")
        Component(views, "Vistas", "Django CBV", "Dashboard, Items, Movimientos, Actas, Mantenimientos, Garantías, Reportes, API AJAX")
        Component(mixins, "Mixins de Permisos", "Python", "LoginRequired, RolRequerido, AreaPermiss — RBAC con 5 roles por campus")
        Component(forms, "Formularios", "Django Forms", "Validación MIME real con python-magic, sanitización y lógica de negocio")
        Component(models, "Modelos", "Django ORM", "Item, Movimiento, ActaEntrega, Mantenimiento, GarantiaRegistro, PerfilUsuario...")
        Component(signals, "Señales", "Django Signals", "Genera HistorialCambio y Notificaciones automáticamente en pre/post_save")
        Component(utils, "Utilidades", "Python", "acta_pdf → ReportLab, acta_email → Resend, export_utils → openpyxl")
    }

    ContainerDb(db, "inventario-db", "PostgreSQL 16", "")
    System_Ext(resend, "Resend API", "")

    Rel(middleware, router, "Pasa la request procesada")
    Rel(router, views, "Enruta según URL")
    Rel(views, mixins, "Verifica permisos antes de ejecutar")
    Rel(views, forms, "Valida datos de entrada")
    Rel(views, utils, "Genera PDF, correo o Excel")
    Rel(forms, models, "Persiste datos validados")
    Rel(models, signals, "Dispara eventos automáticos")
    Rel(models, db, "ORM", "psycopg2")
    Rel(utils, resend, "Envía correos con actas adjuntas", "HTTPS")
```

---

## 4. Modelo de Dominio

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

## 5. Seguridad Implementada

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

## 6. Flujo de Despliegue

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
    APP-->>DO: Contenedor activo en red interna
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
| Monitoreo | Uptime Kuma | Alertas de disponibilidad 24/7 |
