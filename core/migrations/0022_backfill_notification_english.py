import re
from django.db import migrations


def _to_en_title(t):
    patterns = [
        (r'^নতুন Study Note: (.+)$',                     r'New Study Note: \1'),
        (r'^নতুন Exam Paper: (.+)$',                     r'New Exam Paper: \1'),
        (r'^নতুন Contest: (.+)$',                        r'New Contest: \1'),
        (r'^নতুন প্রশ্ন যোগ হয়েছে — (.+)$',            r'New Question Added — \1'),
        (r'^তোমার Note Request পূরণ হয়েছে!',            'Your Note Request is Fulfilled! 🎉'),
        (r'^Note Request আপডেট$',                        'Note Request Update'),
        (r'^নতুন Note Request: (.+)$',                   r'New Note Request: \1'),
    ]
    for pat, repl in patterns:
        m = re.match(pat, t)
        if m:
            return re.sub(pat, repl, t)
    return t  # unchanged if no pattern matched


def _to_en_message(m):
    patterns = [
        (r'^(.+) একটি নতুন study note আপলোড করেছেন — "(.+)" \((.+)\)$',
         r'\1 uploaded a new study note — "\2" (\3)'),
        (r'^(.+) একটি নতুন exam paper আপলোড করেছেন — "(.+)" \((.+)\)$',
         r'\1 uploaded a new exam paper — "\2" (\3)'),
        (r'^(.+) একটি নতুন contest তৈরি করেছেন — "(.+)" \((.+)\)$',
         r'\1 created a new contest — "\2" (\3)'),
        (r'^(.+), (.+) — অধ্যায়: (.+) \((.+)\)$',
         r'\1, \2 — Chapter: \3 (\4)'),
        (r'^"(.+)" বিষয়ে একটি নতুন study note যোগ করা হয়েছে।$',
         r'A new study note on "\1" has been added.'),
        (r'^"(.+)" বিষয়ে study note যোগ করা হয়েছে। এখনই দেখো!$',
         r'A study note on "\1" has been added. Check it out!'),
        (r'^"(.+)" বিষয়ে তোমার request টি এই মুহূর্তে পূরণ করা সম্ভব হয়নি।$',
         r'Your request for "\1" could not be fulfilled at this time.'),
        (r'^(.+) একটি note request করেছেন — "(.+)"$',
         r'\1 requested a note on "\2"'),
    ]
    for pat, repl in patterns:
        if re.search(pat, m):
            return re.sub(pat, repl, m)
    return m


def backfill(apps, schema_editor):
    Notification = apps.get_model('core', 'Notification')
    to_update = []
    for n in Notification.objects.filter(title_bn=''):
        n.title_bn = n.title
        n.message_bn = n.message
        n.title = _to_en_title(n.title)
        n.message = _to_en_message(n.message)
        to_update.append(n)
    if to_update:
        Notification.objects.bulk_update(to_update, ['title', 'message', 'title_bn', 'message_bn'])


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0021_notification_bilingual'),
    ]
    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
