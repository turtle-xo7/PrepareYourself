from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0027_cqsubmission_per_part_grading'),
    ]

    operations = [
        migrations.AddField(
            model_name='question',
            name='part_a',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='question',
            name='part_b',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='question',
            name='part_c',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='question',
            name='part_d',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='question',
            name='marks_a',
            field=models.IntegerField(default=1),
        ),
        migrations.AddField(
            model_name='question',
            name='marks_b',
            field=models.IntegerField(default=2),
        ),
        migrations.AddField(
            model_name='question',
            name='marks_c',
            field=models.IntegerField(default=3),
        ),
        migrations.AddField(
            model_name='question',
            name='marks_d',
            field=models.IntegerField(default=4),
        ),
    ]
