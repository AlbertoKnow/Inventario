"""
Checklist de versión - Usar antes de hacer un release

Uso:
    python version_checklist.py
"""

import os
import sys
from pathlib import Path

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def check_tests():
    print_section("1. TESTS")
    print("[ ] Ejecutar: python manage.py test")
    print("[ ] Todos los tests PASAN")
    print("[ ] Coverage > 80%: coverage run -m pytest && coverage report")

def check_code_quality():
    print_section("2. CALIDAD DE CÓDIGO")
    print("[ ] Ejecutar: black .")
    print("[ ] Ejecutar: isort .")
    print("[ ] Ejecutar: flake8 . (sin errores)")
    print("[ ] No hay warnings en la terminal de Django")

def check_documentation():
    print_section("3. DOCUMENTACIÓN")
    print("[ ] README.md actualizado")
    print("[ ] DEVELOPER_GUIDE.md actualizado")
    print("[ ] SETUP.md actualizado")
    print("[ ] Comentarios y docstrings actualizados")
    print("[ ] CHANGELOG.md actualizado (si existe)")

def check_security():
    print_section("4. SEGURIDAD")
    print("[ ] No hay secretos en el código")
    print("[ ] Variables sensibles están en .env")
    print("[ ] Dependencias actualizadas: pip list --outdated")
    print("[ ] No hay credenciales en .env.example")
    print("[ ] DEBUG=False en producción")

def check_database():
    print_section("5. BASE DE DATOS")
    print("[ ] Todas las migraciones están creadas")
    print("[ ] Migraciones tienen nombres descriptivos")
    print("[ ] No hay migraciones pendientes")
    print("[ ] BD funciona en entorno limpio")

def check_git():
    print_section("6. GIT Y CONTROL DE VERSIONES")
    print("[ ] Commits están bien organizados")
    print("[ ] Mensajes de commit son descriptivos")
    print("[ ] No hay archivos sin trackear importantes")
    print("[ ] Rama está actualizada con main")
    print("[ ] Sin conflictos de merge")

def check_files():
    print_section("7. ARCHIVOS NECESARIOS")
    required_files = [
        '.python-version',
        'requirements.txt',
        '.env.example',
        '.gitignore',
        'README.md',
        'DEVELOPER_GUIDE.md',
        'SETUP.md',
        'CONTRIBUTING.md',
        'manage.py',
        'config/settings.py',
        'productos/models.py',
    ]
    
    print("Verificando archivos requeridos:\n")
    for file in required_files:
        exists = "✓" if Path(file).exists() else "✗"
        print(f"  {exists} {file}")

def check_environment():
    print_section("8. ENTORNO")
    print("[ ] check_environment.py pasa sin errores")
    print("[ ] Entorno virtual funciona: venv/bin/python --version")
    print("[ ] Todas las dependencias instaladas")
    print("[ ] Python >= 3.8")

def check_deployment():
    print_section("9. DEPLOYMENT")
    print("[ ] Archivo DEPLOYMENT.md/README con instrucciones")
    print("[ ] Guía de configuración de producción")
    print("[ ] Configuración de base de datos de producción")
    print("[ ] Variables de entorno de producción documentadas")

def check_final():
    print_section("10. VERIFICACIÓN FINAL")
    print("[ ] Todo funciona en entorno limpio")
    print("[ ] Servidor se inicia sin errores: python manage.py runserver")
    print("[ ] Admin es accesible: /admin/")
    print("[ ] Funcionalidad principal funciona correctamente")

def main():
    print("\n" + "="*60)
    print("  CHECKLIST DE VERSIÓN - SISTEMA DE INVENTARIO")
    print("  Completar antes de hacer un release")
    print("="*60)
    
    check_tests()
    check_code_quality()
    check_documentation()
    check_security()
    check_database()
    check_git()
    check_files()
    check_environment()
    check_deployment()
    check_final()
    
    print_section("PRÓXIMOS PASOS")
    print("1. Asegúrate de que todas las casillas estén marcadas")
    print("2. Crea un tag en Git: git tag -a v1.0.0 -m 'Release v1.0.0'")
    print("3. Push del tag: git push origin v1.0.0")
    print("4. Crea un Release en GitHub")
    print("5. Actualiza documentación de cambios en el sitio web\n")

if __name__ == '__main__':
    main()
