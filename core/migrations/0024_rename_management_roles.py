from django.db import migrations


def rename_management_roles(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    # Rename in two steps so the old and new names do not collide.
    chairman = Group.objects.filter(name='董事长').first()
    general_manager = Group.objects.filter(name='总经理').first()
    if chairman:
        chairman.name = '__rename_chairman__'
        chairman.save(update_fields=['name'])
    if general_manager:
        general_manager.name = '常务副总经理'
        general_manager.save(update_fields=['name'])
    if chairman:
        chairman.name = '总经理'
        chairman.save(update_fields=['name'])


def reverse_management_roles(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    chairman = Group.objects.filter(name='总经理').first()
    general_manager = Group.objects.filter(name='常务副总经理').first()
    if chairman:
        chairman.name = '__rename_general_manager__'
        chairman.save(update_fields=['name'])
    if general_manager:
        general_manager.name = '总经理'
        general_manager.save(update_fields=['name'])
    if chairman:
        chairman.name = '董事长'
        chairman.save(update_fields=['name'])


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0023_orderpayment'),
    ]

    operations = [
        migrations.RunPython(rename_management_roles, reverse_management_roles),
    ]
