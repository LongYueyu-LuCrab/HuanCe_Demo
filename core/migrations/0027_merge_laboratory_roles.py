from django.db import migrations


def merge_laboratory_roles(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    User = apps.get_model('auth', 'User')
    LabStaffProfile = apps.get_model('core', 'LabStaffProfile')

    manager_group, _ = Group.objects.get_or_create(name='实验室负责人')
    operator_group, _ = Group.objects.get_or_create(name='实验室操作员')
    legacy_operator_group = Group.objects.filter(name='实验操作员').first()
    suzhou_group = Group.objects.filter(name='苏州实验室').first()
    jiangyin_group = Group.objects.filter(name='江阴实验室').first()

    # 历史两地负责人统一为“实验室负责人”，所属实验室仍由人员档案保留，
    # 这样不会改变既有设备、排期和订单的物理实验室归属。
    for group in [suzhou_group, jiangyin_group]:
        if not group:
            continue
        for user in group.user_set.all():
            user.groups.add(manager_group)
            user.groups.remove(group)
            profile, _ = LabStaffProfile.objects.get_or_create(
                user=user,
                defaults={'lab_type': 1 if group.name == '苏州实验室' else 2, 'position': 'manager'},
            )
            if profile.position != 'manager':
                profile.position = 'manager'
                profile.save(update_fields=['position', 'update_time'])

    # 人事确认的两个账号按最终名单覆盖历史角色。
    ya_fei = User.objects.filter(username='HCT03').first()
    if ya_fei:
        if suzhou_group:
            ya_fei.groups.remove(suzhou_group)
        if jiangyin_group:
            ya_fei.groups.remove(jiangyin_group)
        ya_fei.groups.remove(operator_group)
        ya_fei.groups.add(manager_group)
        profile, _ = LabStaffProfile.objects.get_or_create(user=ya_fei, defaults={'lab_type': 2, 'position': 'manager'})
        profile.lab_type = 2
        profile.position = 'manager'
        profile.save(update_fields=['lab_type', 'position', 'update_time'])

    qiu_lei = User.objects.filter(username='HCT11').first()
    if qiu_lei:
        if suzhou_group:
            qiu_lei.groups.remove(suzhou_group)
        if jiangyin_group:
            qiu_lei.groups.remove(jiangyin_group)
        qiu_lei.groups.remove(manager_group)
        qiu_lei.groups.add(operator_group)
        profile, _ = LabStaffProfile.objects.get_or_create(user=qiu_lei, defaults={'lab_type': 1, 'position': 'operator'})
        profile.lab_type = 1
        profile.position = 'operator'
        profile.save(update_fields=['lab_type', 'position', 'update_time'])

    if legacy_operator_group:
        for user in legacy_operator_group.user_set.all():
            user.groups.add(operator_group)
            user.groups.remove(legacy_operator_group)
        legacy_operator_group.delete()

    if suzhou_group:
        suzhou_group.delete()
    if jiangyin_group:
        jiangyin_group.delete()


def reverse_merge_laboratory_roles(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    User = apps.get_model('auth', 'User')
    manager_group = Group.objects.filter(name='实验室负责人').first()
    suzhou_group, _ = Group.objects.get_or_create(name='苏州实验室')
    jiangyin_group, _ = Group.objects.get_or_create(name='江阴实验室')
    if manager_group:
        for user in manager_group.user_set.all():
            profile = getattr(user, 'lims_lab_profile', None)
            target = jiangyin_group if profile and profile.lab_type == 2 else suzhou_group
            user.groups.add(target)
            user.groups.remove(manager_group)
    qiu_lei = User.objects.filter(username='HCT11').first()
    operator_group = Group.objects.filter(name='实验室操作员').first()
    if qiu_lei and operator_group:
        qiu_lei.groups.remove(operator_group)
        qiu_lei.groups.add(suzhou_group)


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0026_allow_deferred_outsource_details'),
    ]

    operations = [
        migrations.RunPython(merge_laboratory_roles, reverse_merge_laboratory_roles),
    ]
