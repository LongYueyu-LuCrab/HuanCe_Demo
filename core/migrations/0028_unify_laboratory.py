from django.db import migrations


def unify_laboratory_data(apps, schema_editor):
    """Collapse the former Suzhou/Jiangyin split into one laboratory.

    The numeric value 1 is retained as the canonical value so existing
    records remain queryable and historical foreign-key relationships are not
    touched.  Only the obsolete laboratory discriminator values are mapped.
    """
    LabDevice = apps.get_model('core', 'LabDevice')
    LabStaffProfile = apps.get_model('core', 'LabStaffProfile')
    SchedulePlan = apps.get_model('core', 'SchedulePlan')
    Experiment = apps.get_model('core', 'Experiment')
    LabOrder = apps.get_model('core', 'LabOrder')
    Group = apps.get_model('auth', 'Group')

    LabDevice.objects.exclude(lab_type=1).update(lab_type=1)
    LabStaffProfile.objects.exclude(lab_type=1).update(lab_type=1)
    SchedulePlan.objects.filter(test_type=2).update(test_type=1)
    Experiment.objects.filter(test_type=2).update(test_type=1)
    LabOrder.objects.filter(execution_mode=2).update(execution_mode=1)

    # Old groups must not continue to create a second permission scope.
    Group.objects.filter(name__in=['苏州实验室', '江阴实验室']).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0028_lab_operator_label'),
    ]

    operations = [
        migrations.RunPython(unify_laboratory_data, migrations.RunPython.noop),
    ]
