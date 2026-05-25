import hashlib

from django.db import migrations, models


def _hash(text):
    normalized = ' '.join((text or '').lower().split())
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def backfill_hash_and_dedupe(apps, schema_editor):
    Question = apps.get_model('core', 'Question')
    # Compute hash for every row
    for q in Question.objects.all():
        q.question_text_hash = _hash(q.question_text)
        q.save(update_fields=['question_text_hash'])

    # Delete duplicates: keep the oldest (lowest id) per (board, subject, class_obj, year, hash)
    seen = set()
    to_delete = []
    for q in Question.objects.order_by('id').values(
        'id', 'board_id', 'subject_id', 'class_obj_id', 'year', 'question_text_hash'
    ):
        key = (q['board_id'], q['subject_id'], q['class_obj_id'], q['year'], q['question_text_hash'])
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
        ('core', '0029_question_mcq_file'),
    ]

    operations = [
        migrations.AddField(
            model_name='question',
            name='question_text_hash',
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
        migrations.RunPython(backfill_hash_and_dedupe, noop_reverse),
        migrations.AddConstraint(
            model_name='question',
            constraint=models.UniqueConstraint(
                fields=['board', 'subject', 'class_obj', 'year', 'question_text_hash'],
                name='unique_question_per_board_subject_class_year',
            ),
        ),
    ]
