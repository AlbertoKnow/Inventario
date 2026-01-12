#!/bin/bash
# Script de diagnóstico para el servidor de producción

echo "=========================================="
echo "DIAGNÓSTICO DEL SERVIDOR - INVENTARIO UTP"
echo "=========================================="
echo ""

echo "1. Estado del servicio inventario:"
sudo systemctl status inventario --no-pager
echo ""

echo "2. Últimos 30 logs del servicio:"
sudo journalctl -u inventario -n 30 --no-pager
echo ""

echo "3. Verificar que openpyxl esté instalado:"
cd /var/www/inventario
source venv/bin/activate
python -c "import openpyxl; print('✓ openpyxl instalado correctamente, versión:', openpyxl.__version__)" 2>&1
echo ""

echo "4. Verificar Django check:"
python manage.py check 2>&1
echo ""

echo "5. Verificar permisos:"
ls -la /var/www/inventario/*.sock 2>&1
echo ""

echo "=========================================="
echo "FIN DEL DIAGNÓSTICO"
echo "=========================================="
