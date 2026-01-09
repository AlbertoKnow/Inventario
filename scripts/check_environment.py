#!/usr/bin/env python
"""
Script de validación del entorno de desarrollo.

Este script verifica que el entorno esté correctamente configurado
para ejecutar el proyecto Django.

Uso:
    python check_environment.py
"""

import sys
import os
import subprocess
from pathlib import Path

# Colores para terminal
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'


def print_header(text):
    """Imprime un encabezado formateado."""
    print(f"\n{BLUE}{BOLD}{'='*60}{RESET}")
    print(f"{BLUE}{BOLD}{text}{RESET}")
    print(f"{BLUE}{BOLD}{'='*60}{RESET}\n")


def print_success(text):
    """Imprime un mensaje de éxito."""
    print(f"{GREEN}✓ {text}{RESET}")


def print_error(text):
    """Imprime un mensaje de error."""
    print(f"{RED}✗ {text}{RESET}")


def print_warning(text):
    """Imprime un mensaje de advertencia."""
    print(f"{YELLOW}⚠ {text}{RESET}")


def print_info(text):
    """Imprime un mensaje informativo."""
    print(f"{BLUE}ℹ {text}{RESET}")


def check_python_version():
    """Verifica que la versión de Python sea 3.8+"""
    print_header("1. Verificando Versión de Python")
    
    version = sys.version_info
    version_string = f"{version.major}.{version.minor}.{version.micro}"
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print_error(f"Python {version_string} - Requiere 3.8+")
        return False
    
    print_success(f"Python {version_string}")
    return True


def check_virtual_environment():
    """Verifica que estemos en un entorno virtual."""
    print_header("2. Verificando Entorno Virtual")
    
    in_venv = (
        hasattr(sys, 'real_prefix') or
        (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    )
    
    venv_path = sys.prefix
    
    if not in_venv:
        print_warning("No estás en un entorno virtual")
        print_info("Ejecuta: python -m venv venv")
        print_info("Luego activa: venv\\Scripts\\activate (Windows)")
        print_info("O: source venv/bin/activate (macOS/Linux)")
        return False
    
    print_success(f"Entorno virtual activo: {venv_path}")
    return True


def check_required_packages():
    """Verifica que las dependencias requeridas estén instaladas."""
    print_header("3. Verificando Paquetes Requeridos")
    
    required_packages = {
        'django': 'Django',
        'decouple': 'python-decouple',
    }
    
    all_ok = True
    
    for package, display_name in required_packages.items():
        try:
            module = __import__(package)
            version = getattr(module, '__version__', 'versión desconocida')
            print_success(f"{display_name} instalado ({version})")
        except ImportError:
            print_error(f"{display_name} NO instalado")
            all_ok = False
    
    if not all_ok:
        print_info("\nExecuta: pip install -r requirements.txt")
    
    return all_ok


def check_django_configuration():
    """Verifica que Django esté correctamente configurado."""
    print_header("4. Verificando Configuración de Django")
    
    try:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
        import django
        django.setup()
        
        from django.conf import settings
        
        print_success("Configuración de Django cargada correctamente")
        print_info(f"Zona horaria: {settings.TIME_ZONE}")
        print_info(f"Idioma: {settings.LANGUAGE_CODE}")
        
        return True
    except Exception as e:
        print_error(f"Error al cargar Django: {str(e)}")
        return False


def check_database():
    """Verifica que la base de datos esté configurada."""
    print_header("5. Verificando Base de Datos")
    
    try:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
        import django
        django.setup()
        
        from django.core.management import call_command
        from django.db import connection
        
        # Verificar conexión a BD
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        print_success("Conexión a base de datos establecida")
        
        # Verificar migraciones
        print_info("Verificando estado de migraciones...")
        try:
            from django.core.management import call_command
            import io
            from contextlib import redirect_stdout
            
            f = io.StringIO()
            call_command('showmigrations', '--plan', stdout=f)
            output = f.getvalue()
            
            if '[X]' in output:
                print_success("Migraciones aplicadas correctamente")
            else:
                print_warning("Hay migraciones pendientes")
                print_info("Ejecuta: python manage.py migrate")
        except:
            pass
        
        return True
    except Exception as e:
        print_error(f"Error con la base de datos: {str(e)}")
        print_info("Ejecuta: python manage.py migrate")
        return False


def check_directories():
    """Verifica que los directorios necesarios existan."""
    print_header("6. Verificando Estructura de Directorios")
    
    required_dirs = [
        'config',
        'productos',
        'templates',
        'static',
        'media',
    ]
    
    all_ok = True
    
    for directory in required_dirs:
        if Path(directory).exists():
            print_success(f"Carpeta '{directory}' existe")
        else:
            print_error(f"Carpeta '{directory}' NO existe")
            all_ok = False
    
    return all_ok


def check_env_file():
    """Verifica que el archivo .env esté configurado."""
    print_header("7. Verificando Archivo de Configuración")
    
    if Path('.env').exists():
        print_success("Archivo '.env' encontrado")
        
        # Verificar variables importantes
        try:
            from decouple import config
            secret_key = config('SECRET_KEY', default='')
            debug = config('DEBUG', default='True')
            
            if secret_key and secret_key != 'django-insecure-your-secret-key-change-in-production':
                print_success("SECRET_KEY configurada")
            else:
                print_warning("SECRET_KEY no está personificada (OK para desarrollo)")
            
            print_info(f"DEBUG: {debug}")
        except:
            pass
        
        return True
    else:
        print_warning("Archivo '.env' no encontrado")
        print_info("Crea uno basado en: cp .env.example .env")
        return False


def check_permissions():
    """Verifica permisos de escritura en directorios críticos."""
    print_header("8. Verificando Permisos")
    
    critical_dirs = [
        '.',
        'media',
        'static',
    ]
    
    all_ok = True
    
    for directory in critical_dirs:
        path = Path(directory)
        if path.exists() and os.access(path, os.W_OK):
            print_success(f"Escritura permitida en '{directory}'")
        else:
            print_warning(f"Posible problema de permisos en '{directory}'")
            all_ok = False
    
    return all_ok


def print_summary(results):
    """Imprime un resumen de los resultados."""
    print_header("Resumen de Validación")
    
    total = len(results)
    passed = sum(results)
    failed = total - passed
    
    print(f"Total de verificaciones: {total}")
    print_success(f"{passed} pasadas")
    if failed > 0:
        print_error(f"{failed} fallidas")
    
    if passed == total:
        print(f"\n{GREEN}{BOLD}¡Todo está configurado correctamente! 🎉{RESET}")
        print(f"{GREEN}Puedes comenzar el desarrollo con:{RESET}")
        print(f"{BOLD}  python manage.py runserver{RESET}\n")
        return True
    else:
        print(f"\n{YELLOW}{BOLD}Revisa los errores arriba para continuar.{RESET}\n")
        return False


def main():
    """Función principal."""
    print(f"\n{BOLD}{BLUE}Sistema de Inventario - Validación de Entorno{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    results = [
        check_python_version(),
        check_virtual_environment(),
        check_required_packages(),
        check_directories(),
        check_env_file(),
        check_permissions(),
        check_django_configuration(),
        check_database(),
    ]
    
    success = print_summary(results)
    
    return 0 if success else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Validación cancelada por el usuario.{RESET}\n")
        sys.exit(130)
    except Exception as e:
        print_error(f"Error inesperado: {str(e)}")
        sys.exit(1)
