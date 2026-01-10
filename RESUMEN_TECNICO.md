# RESUMEN TÉCNICO - SISTEMA DE INVENTARIO UTP

**Fecha**: 10 de enero de 2026  
**Repositorio**: https://github.com/AlbertoKnow/Inventario  
**Producción**: https://inventario.albertoknow.com

---

## 1. ARQUITECTURA DEL PROYECTO

### Stack Tecnológico

| Componente | Tecnología | Versión |
|------------|------------|---------|
| Backend | Django | 4.2.x |
| Base de Datos (Dev) | SQLite | 3.x |
| Base de Datos (Prod) | PostgreSQL | 15+ |
| Servidor WSGI | Gunicorn | 21.2.0 |
| Proxy Reverso | Nginx | - |
| SSL/HTTPS | Cloudflare | Flexible |
| Archivos Estáticos | WhiteNoise | 6.6.0 |
| Frontend | Bootstrap 5.3 + Font Awesome 6.4 | - |
| Fuentes | Inter (Google Fonts) | - |

### Despliegue Actual

- **Servidor**: Digital Ocean Droplet ($6/mes, Ubuntu 22.04)
- **IP**: 134.209.124.220
- **Dominio**: https://inventario.albertoknow.com
- **Repositorio**: https://github.com/AlbertoKnow/Inventario

### Estructura de Carpetas

```
Inventario/
├── config/                 # Configuración Django (settings.py, urls.py, wsgi.py)
├── productos/              # App principal
│   ├── models.py           # 15+ modelos
│   ├── views.py            # 40+ vistas (CBV)
│   ├── forms.py            # Formularios
│   ├── urls.py             # Rutas
│   ├── context_processors.py  # Perfil global
│   ├── signals.py          # Señales (notificaciones)
│   └── templatetags/       # Filtros personalizados
├── templates/
│   ├── base.html           # Template base con navbar
│   └── productos/          # Templates de la app
├── static/
│   └── favicon.svg         # Favicon UTP
├── deploy/                 # Archivos de deployment
│   ├── DEPLOYMENT_GUIDE.md
│   ├── gunicorn.service
│   └── nginx.conf
└── .env.production.example
```

---

## 2. MODELOS DE DATOS

### Jerarquía de Ubicaciones

```
Campus → Sede → Pabellón → Ambiente
```

### Modelos Principales

| Modelo | Descripción |
|--------|-------------|
| Area | Sistemas, Operaciones, Laboratorio |
| Campus | Campus universitarios |
| Sede | Sedes dentro de campus |
| Pabellon | Edificios/Pabellones |
| Ambiente | Aulas, Labs, Oficinas (código autogenerado) |
| TipoItem | Categorías por área (Laptop, Silla, etc.) |
| Item | Ítem de inventario (código UTP autogenerado) |
| Proveedor | Proveedores de bienes |
| Contrato | Contratos de adquisición |
| Lote | Lotes de compra (código autogenerado LOT-YYYY-XXXX) |
| Movimiento | Traslados, entradas, bajas, etc. |
| PerfilUsuario | Extensión de User (rol + área) |
| Notificacion | Sistema de notificaciones |
| HistorialCambio | Auditoría de cambios |
| EspecificacionesSistemas | Specs técnicas (RAM, disco, etc.) |

### Roles de Usuario

| Rol | Permisos |
|-----|----------|
| admin | Todo el sistema, todas las áreas |
| supervisor | Su área + aprobar movimientos + crear lotes |
| operador | Solo ver/crear ítems de su área |
| externo | Solo para asignación (sin login) |

---

## 3. FUNCIONALIDADES - ESTADO ACTUAL

### COMPLETADO

| Módulo | Funcionalidad | Estado |
|--------|---------------|--------|
| Autenticación | Login/Logout | ✅ |
| Dashboard | Estadísticas por área | ✅ |
| Ítems | CRUD completo | ✅ |
| Ítems | URLs amigables (/items/SIS-2026-0001/) | ✅ |
| Ítems | Restricción por área (operador solo ve su área) | ✅ |
| Ítems | Código UTP autogenerado | ✅ |
| Ubicaciones | CRUD Campus/Sede/Pabellón/Ambiente | ✅ |
| Movimientos | Solicitud con flujo de aprobación | ✅ |
| Movimientos | Aprobación/Rechazo por supervisor | ✅ |
| Movimientos | Modo emergencia | ✅ |
| Proveedores | CRUD (solo supervisor/admin) | ✅ |
| Contratos | CRUD + Anexos | ✅ |
| Lotes | CRUD (solo supervisor/admin) | ✅ |
| Notificaciones | Creación automática | ✅ |
| Notificaciones | Ícono en navbar | ✅ |
| UI | Paleta de colores UTP (negro, rojo, gris) | ✅ |
| UI | Favicon UTP | ✅ |
| UI | Diseño responsive | ✅ |
| Deployment | Digital Ocean + Cloudflare SSL | ✅ |

### PENDIENTE / EN DISCUSIÓN

| Funcionalidad | Prioridad | Notas |
|---------------|-----------|-------|
| Importación masiva Excel | Alta | Discutido, no implementado |
| Duplicar ítem | Media | Para lotes similares |
| Exportar a Excel/PDF | Media | Reportes |
| Búsqueda avanzada | Baja | Filtros ya existen |
| Especificaciones Sistemas | Media | Modelo existe, falta formulario dinámico |

---

## 4. DECISIONES TÉCNICAS CLAVE

### Autenticación y Permisos

- **Mixins personalizados**: PerfilRequeridoMixin, SupervisorRequeridoMixin, AdminRequeridoMixin
- **Restricción por área**: Operadores/Supervisores solo ven ítems de su área asignada
- **Context Processor**: perfil_usuario disponible globalmente en templates

### URLs Amigables

- Ítems usan codigo_utp como slug en URLs
- Ejemplo: /productos/items/SIS-2026-0001/
- No requirió migración (usa campo existente)

### Códigos Autogenerados

| Entidad | Formato | Ejemplo |
|---------|---------|---------|
| Item.codigo_utp | {AREA}-{AÑO}-{####} | SIS-2026-0001 |
| Lote.codigo_interno | LOT-{AÑO}-{####} | LOT-2026-0001 |
| Ambiente.codigo | {CAMPUS}-{SEDE}-{PAB}-{PISO}-{TIPO}-{###} | CLN-SP-A-P1-LC-001 |

### Paleta de Colores UTP

```css
--primary: #1a1a1a;      /* Negro */
--accent: #C8102E;       /* Rojo UTP */
--gray-50 a --gray-900;  /* Escala de grises */
```

### Menú Adaptativo

- **Admin**: Ve todas las áreas en dropdown
- **Operador/Supervisor**: Solo ve "Ítems de {su área}"

---

## 5. PRÓXIMO PASO INMEDIATO

### Importación Masiva desde Excel

**Plantilla Excel descargable con columnas:**

- serie* (único)
- nombre*
- area* (sistemas/operaciones/laboratorio)
- tipo_item*
- ambiente (opcional, código del ambiente)
- precio*
- fecha_adquisicion*
- garantia_hasta (opcional)
- observaciones (opcional)

**Flujo propuesto:**

1. Descargar plantilla
2. Llenar offline
3. Subir archivo
4. Preview con validación
5. Confirmar importación

**Validaciones necesarias:**

- Serie única (no duplicada en BD)
- Área válida
- Tipo de ítem existe para esa área
- Formato de fechas correcto
- Precio numérico positivo

**Librería sugerida**: openpyxl para leer Excel

---

## 6. ARCHIVOS CLAVE PARA REFERENCIA

| Archivo | Contenido |
|---------|-----------|
| productos/models.py | 15+ modelos, 908 líneas |
| productos/views.py | 40+ vistas CBV, 1540 líneas |
| productos/urls.py | Todas las rutas |
| templates/base.html | Template base + navbar + estilos |
| config/settings.py | Configuración dual dev/prod |
| .env.production.example | Variables de entorno requeridas |

---

## 7. CREDENCIALES Y ACCESOS

### Servidor Producción

- **IP**: 134.209.124.220
- **Usuario**: root
- **Ruta app**: /var/www/inventario
- **Gunicorn socket**: /var/www/inventario/inventario.sock

### Base de Datos Producción

- **Motor**: PostgreSQL
- **DB**: inventario_db
- **Usuario**: inventario_user
- **Password**: Inventario2026Seguro

### Cloudflare

- **Dominio**: inventario.albertoknow.com
- **SSL**: Flexible
- **Registro A**: Apunta a 134.209.124.220

---

## 8. COMANDOS ÚTILES

### Actualizar servidor

```bash
cd /var/www/inventario
git pull
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart inventario
```

### Ver logs

```bash
sudo journalctl -u inventario -f
```

---

## 9. HISTORIAL DE COMMITS RECIENTES

```
3a4e19e Remover link a ubicacion-delete que no existe
0902282 Corregir load static en base.html
ca5a8cc Agregar favicon UTP y estilizar iconos del flujo de aprobación
cec55ba Restringir visibilidad por área y URLs amigables con codigo_utp
937df9d Cambiar container-fluid a container para diseño más compacto
6c6d4ae Actualizar paleta de colores a UTP (negro, rojo, blanco, gris)
177ce83 feat: Sistema de Inventario UTP completo
098f1a4 Initial commit
```

---

**Fin del resumen técnico**
