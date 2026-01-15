"""
Migration para actualizar el formato de ubicaciones al estándar UTP.

Cambios:
- Sede: agregar codigo_sede (código numérico oficial UTP)
- Pabellon: renombrar nombre a letra, agregar sotanos, eliminar tiene_sotano
- Ambiente: agregar numero, actualizar algoritmo de codigo
"""

from django.db import migrations, models
import django.core.validators


def migrate_sede_data(apps, schema_editor):
    """Asignar codigo_sede temporal basado en el ID."""
    Sede = apps.get_model('productos', 'Sede')
    for i, sede in enumerate(Sede.objects.all(), start=1):
        sede.codigo_sede = i * 10  # Valores temporales: 10, 20, 30...
        sede.save()


def migrate_pabellon_data(apps, schema_editor):
    """Migrar datos de Pabellon: nombre -> letra, tiene_sotano -> sotanos."""
    Pabellon = apps.get_model('productos', 'Pabellon')
    for pabellon in Pabellon.objects.all():
        # Extraer primera letra del nombre como letra del pabellón
        if pabellon.nombre:
            pabellon.letra = pabellon.nombre[0].upper()
        else:
            pabellon.letra = 'A'
        # Convertir tiene_sotano a sotanos
        pabellon.sotanos = 1 if pabellon.tiene_sotano else 0
        pabellon.save()


def migrate_ambiente_data(apps, schema_editor):
    """Asignar numero a ambientes existentes y regenerar códigos."""
    Ambiente = apps.get_model('productos', 'Ambiente')

    # Agrupar por pabellon y piso para asignar números consecutivos
    from collections import defaultdict
    grupos = defaultdict(list)

    for ambiente in Ambiente.objects.all():
        key = (ambiente.pabellon_id, ambiente.piso)
        grupos[key].append(ambiente)

    for (pabellon_id, piso), ambientes in grupos.items():
        for i, ambiente in enumerate(ambientes, start=1):
            ambiente.numero = i

            # Regenerar código en formato UTP
            pabellon = ambiente.pabellon
            sede_codigo = pabellon.sede.codigo_sede
            pabellon_letra = pabellon.letra

            if piso < 0:
                piso_str = f"S{abs(piso)}"
            else:
                piso_str = str(piso)

            numero_str = f"{i:02d}"
            ambiente.codigo = f"{sede_codigo}{pabellon_letra}{piso_str}{numero_str}"
            ambiente.save()


def reverse_sede(apps, schema_editor):
    """Revertir no necesita acción especial."""
    pass


def reverse_pabellon(apps, schema_editor):
    """Revertir datos de Pabellon."""
    Pabellon = apps.get_model('productos', 'Pabellon')
    for pabellon in Pabellon.objects.all():
        pabellon.nombre = pabellon.letra
        pabellon.tiene_sotano = pabellon.sotanos > 0
        pabellon.save()


def reverse_ambiente(apps, schema_editor):
    """Revertir no necesita acción especial (el código se regenerará)."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('productos', '0004_mantenimiento_and_more'),
    ]

    operations = [
        # =========================================
        # SEDE: Agregar codigo_sede
        # =========================================
        migrations.AddField(
            model_name='sede',
            name='codigo_sede',
            field=models.PositiveIntegerField(
                default=1,  # Temporal, se actualizará en data migration
                help_text='Código numérico oficial UTP de la sede (Ej: 77, 78, 1)',
            ),
            preserve_default=False,
        ),
        migrations.RunPython(migrate_sede_data, reverse_sede),
        migrations.AlterField(
            model_name='sede',
            name='codigo_sede',
            field=models.PositiveIntegerField(
                unique=True,
                help_text='Código numérico oficial UTP de la sede (Ej: 77, 78, 1)',
            ),
        ),

        # =========================================
        # PABELLON: letra, sotanos
        # =========================================
        migrations.AddField(
            model_name='pabellon',
            name='letra',
            field=models.CharField(
                default='A',
                help_text='Letra del pabellón (A-Z)',
                max_length=1,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='pabellon',
            name='sotanos',
            field=models.IntegerField(default=0, help_text='Número de sótanos'),
        ),
        migrations.RunPython(migrate_pabellon_data, reverse_pabellon),
        # Hacer nombre opcional y eliminar tiene_sotano
        migrations.AlterField(
            model_name='pabellon',
            name='nombre',
            field=models.CharField(
                blank=True,
                help_text='Nombre descriptivo opcional (Ej: Pabellón Principal, Edificio de Ingenierías)',
                max_length=100,
            ),
        ),
        migrations.RemoveField(
            model_name='pabellon',
            name='tiene_sotano',
        ),
        # Actualizar unique_together
        migrations.AlterUniqueTogether(
            name='pabellon',
            unique_together={('sede', 'letra')},
        ),
        migrations.AlterModelOptions(
            name='pabellon',
            options={'ordering': ['sede', 'letra'], 'verbose_name': 'Pabellón', 'verbose_name_plural': 'Pabellones'},
        ),

        # =========================================
        # AMBIENTE: numero
        # =========================================
        migrations.AddField(
            model_name='ambiente',
            name='numero',
            field=models.PositiveIntegerField(
                default=1,
                help_text='Número de ambiente en el piso (01-99)',
            ),
            preserve_default=False,
        ),
        migrations.RunPython(migrate_ambiente_data, reverse_ambiente),
        # Actualizar unique_together y ordering
        migrations.AlterUniqueTogether(
            name='ambiente',
            unique_together={('pabellon', 'piso', 'numero')},
        ),
        migrations.AlterModelOptions(
            name='ambiente',
            options={'ordering': ['pabellon', 'piso', 'numero'], 'verbose_name': 'Ambiente', 'verbose_name_plural': 'Ambientes'},
        ),
        # Actualizar max_length del código
        migrations.AlterField(
            model_name='ambiente',
            name='codigo',
            field=models.CharField(blank=True, editable=False, max_length=20, unique=True),
        ),
    ]
