#!/usr/bin/env python
"""Script para crear superusuario automáticamente."""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User

if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print("✓ Superusuario 'admin' creado exitosamente")
    print("  Usuario: admin")
    print("  Contraseña: admin123")
else:
    print("✓ Superusuario 'admin' ya existe")
