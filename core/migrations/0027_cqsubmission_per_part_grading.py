from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0026_teacher_subjects_claim_queue'),
    ]

    operations = [
        migrations.AddField(
            model_name='cqsubmission',
            name='marks_a',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='cqsubmission',
            name='marks_b',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='cqsubmission',
            name='marks_c',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='cqsubmission',
            name='marks_d',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='cqsubmission',
            name='comment_a',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='cqsubmission',
            name='comment_b',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='cqsubmission',
            name='comment_c',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='cqsubmission',
            name='comment_d',
            field=models.TextField(blank=True),
        ),
    ]
