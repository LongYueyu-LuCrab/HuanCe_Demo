from django.db import migrations


def create_sales_manager_group(apps, schema_editor):
    group_model = apps.get_model('auth', 'Group')
    group_model.objects.get_or_create(name='销售经理')


def remove_sales_manager_group(apps, schema_editor):
    group_model = apps.get_model('auth', 'Group')
    group_model.objects.filter(name='销售经理', user__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0016_invoice_voiding'),
    ]

    operations = [
        migrations.RunPython(create_sales_manager_group, remove_sales_manager_group),
    ]
