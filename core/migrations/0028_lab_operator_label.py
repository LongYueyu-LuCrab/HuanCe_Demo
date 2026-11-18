from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0027_merge_laboratory_roles'),
    ]

    operations = [
        migrations.AlterField(
            model_name='labstaffprofile',
            name='position',
            field=models.CharField(
                choices=[('manager', '实验室负责人'), ('operator', '实验室操作员')],
                default='operator',
                max_length=20,
                verbose_name='实验室岗位',
            ),
        ),
    ]
