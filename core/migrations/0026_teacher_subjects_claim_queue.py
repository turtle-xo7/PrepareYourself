from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0025_teacher_verification'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='subjects',
            field=models.ManyToManyField(blank=True, related_name='teachers', to='core.subject'),
        ),
        migrations.AddField(
            model_name='examattempt',
            name='assigned_teacher',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='claimed_attempts',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='examattempt',
            name='claimed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
