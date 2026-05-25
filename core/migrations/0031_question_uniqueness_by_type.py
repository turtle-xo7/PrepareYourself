from django.db import migrations, models


def dedupe_by_type(apps, schema_editor):
    """Keep oldest row per (board, subject, class_obj, year, question_type); delete the rest."""
    Question = apps.get_model('core', 'Question')
    seen = set()
    to_delete = []
    for q in Question.objects.order_by('id').values(
        'id', 'board_id', 'subject_id', 'class_obj_id', 'year', 'question_type'
    ):
        key = (q['board_id'], q['subject_id'], q['class_obj_id'], q['year'], q['question_type'])
        if key in seen:
            to_delete.append(q['id'])
        else:
            seen.add(key)
    if to_delete:
        Question.objects.filter(id__in=to_delete).delete()


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0030_question_uniqueness'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='question',
            name='unique_question_per_board_subject_class_year',
        ),
        migrations.RunPython(dedupe_by_type, noop_reverse),
        migrations.AddConstraint(
            model_name='question',
            constraint=models.UniqueConstraint(
                fields=['board', 'subject', 'class_obj', 'year', 'question_type'],
                name='unique_question_per_board_subject_class_year_type',
            ),
        ),
        migrations.RemoveField(
            model_name='question',
            name='question_text_hash',
        ),
    ]
