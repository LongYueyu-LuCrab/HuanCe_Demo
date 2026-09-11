from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_scheduling_confirmation(apps, schema_editor):
    SchedulePlan = apps.get_model('core', 'SchedulePlan')
    WorkflowEvent = apps.get_model('core', 'WorkflowEvent')

    events = WorkflowEvent.objects.filter(
        action_code__in=['lab_schedule_assign', 'lab_change_process'],
        schedule_id__isnull=False,
    ).order_by('schedule_id', '-create_time')
    latest_by_schedule = {}
    for event in events.iterator():
        latest_by_schedule.setdefault(event.schedule_id, event)

    for schedule_id, event in latest_by_schedule.items():
        SchedulePlan.objects.filter(pk=schedule_id).update(
            scheduled_at=event.create_time,
            scheduled_by_id=event.actor_id,
        )

    SchedulePlan.objects.filter(
        scheduled_at__isnull=True,
        schedule_status__in=[3, 4, 5],
    ).update(scheduled_at=models.F('update_time'))


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0017_sales_manager_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='scheduleplan',
            name='scheduled_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='实验室确认排期时间'),
        ),
        migrations.AddField(
            model_name='scheduleplan',
            name='scheduled_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='lims_confirmed_schedules',
                to=settings.AUTH_USER_MODEL,
                verbose_name='实验室排期操作人',
            ),
        ),
        migrations.RunPython(backfill_scheduling_confirmation, migrations.RunPython.noop),
    ]
