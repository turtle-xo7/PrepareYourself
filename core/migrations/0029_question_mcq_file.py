from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0028_question_cq_parts'),
    ]

    operations = [
        migrations.AddField(
            model_name='question',
            name='mcq_question_file',
            field=models.FileField(blank=True, null=True, upload_to='question_mcq/'),
        ),
    ]
