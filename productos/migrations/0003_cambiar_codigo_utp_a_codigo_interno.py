# Generated manually to handle codigo_utp -> codigo_interno change

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('productos', '0002_add_proveedor_contrato_lote'),
    ]

    operations = [
        # Paso 1: Renombrar codigo_utp existente a codigo_interno
        migrations.RenameField(
            model_name='item',
            old_name='codigo_utp',
            new_name='codigo_interno',
        ),

        # Paso 2: Modificar codigo_interno para que sea editable=False
        migrations.AlterField(
            model_name='item',
            name='codigo_interno',
            field=models.CharField(
                editable=False,
                help_text='Código interno autogenerado (ej: SIS-2026-0001)',
                max_length=50,
                unique=True
            ),
        ),

        # Paso 3: Agregar nuevo campo codigo_utp con default="PENDIENTE"
        migrations.AddField(
            model_name='item',
            name='codigo_utp',
            field=models.CharField(
                default='PENDIENTE',
                help_text='Código de etiqueta física de logística (ej: UTP296375) o PENDIENTE si aún no tiene',
                max_length=20
            ),
        ),

        # Paso 4: Actualizar índices
        migrations.AlterModelOptions(
            name='item',
            options={
                'ordering': ['-creado_en'],
                'verbose_name': 'Ítem',
                'verbose_name_plural': 'Ítems'
            },
        ),

        # Paso 5: Agregar índice para codigo_interno
        migrations.AddIndex(
            model_name='item',
            index=models.Index(fields=['codigo_interno'], name='productos_i_codigo__idx'),
        ),
    ]
