from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0024_question_solution_image'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='is_approved',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='teacher_bio',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='subject_expertise',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='nid_document',
            field=models.FileField(blank=True, null=True, upload_to='teacher_docs/nid/'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='qualification_document',
            field=models.FileField(blank=True, null=True, upload_to='teacher_docs/qual/'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='rejection_reason',
            field=models.TextField(blank=True),
        ),
    ]
