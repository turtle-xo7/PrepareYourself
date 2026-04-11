from django.db import models

SCIENCE_SUBJECTS = ['Physics','Chemistry','Biology','Higher Math','ICT']

DIFFICULTY_CHOICES = [('Easy','Easy'),('Medium','Medium'),('Hard','Hard')]

class Question(models.Model):
    board         = models.CharField(max_length=100)
    class_name    = models.CharField(max_length=10)
    subject       = models.CharField(max_length=100)
    chapter       = models.CharField(max_length=200)
    year          = models.IntegerField()
    difficulty    = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES)
    question_text = models.TextField()
    is_mcq        = models.BooleanField(default=False)
    correct_option_index = models.IntegerField(default=0)  # 0-indexed

    def save(self, *args, **kwargs):
        if self.subject in SCIENCE_SUBJECTS:
            self.is_mcq = True
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.subject} — {self.chapter[:40]}"

class MCQOption(models.Model):
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name='options'
    )
    text  = models.CharField(max_length=500)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.text[:50]