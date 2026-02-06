"""
Capa de servicios (lógica de negocio).

Este paquete contiene la lógica de negocio compleja separada de las vistas:
- movimiento_service: Flujo de trabajo de movimientos
- acta_service: Generación de actas, PDF, email
- importacion_service: Importación desde Excel
- exportacion_service: Exportación de reportes

Los services encapsulan operaciones complejas que involucran múltiples modelos
y/o integraciones externas (email, PDF, Excel).
"""

# Services se irán agregando conforme se extraigan de las views
