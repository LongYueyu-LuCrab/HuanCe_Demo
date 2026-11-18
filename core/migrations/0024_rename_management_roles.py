from django.db import migrations


def rename_management_roles(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    def merge_group(source, target):
        """Preserve users/permissions when a previous partial rename created target."""
        if not source or not target or source.pk == target.pk:
            return
        target.permissions.add(*source.permissions.all())
        for user in source.user_set.all():
            user.groups.add(target)
            user.groups.remove(source)
        source.delete()

    chairman = Group.objects.filter(name='董事长').first()
    general_manager = Group.objects.filter(name='总经理').first()
    standing_manager = Group.objects.filter(name='常务副总经理').first()

    # A previous release may already have created the final names while the
    # migration record was not applied. In that state, keep the final groups
    # and safely merge any remaining legacy chairman group into 总经理.
    if standing_manager:
        if chairman:
            if general_manager:
                merge_group(chairman, general_manager)
            else:
                chairman.name = '总经理'
                chairman.save(update_fields=['name'])
        return

    # Rename in two steps so the old and new names do not collide.
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
