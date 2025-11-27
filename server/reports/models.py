from django.db import models
from authentication.models import User

class Report(models.Model):

    FEEDBACK_CHOICES = [
        ('very_bad', 'Very Bad'),
        ('bad', 'Bad'),
        ('good', 'Good'),
        ('excellent', 'Excellent'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports')
    title = models.CharField(max_length=200)
    overall_summary = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    feedback = models.CharField(
        max_length=50,
        choices=FEEDBACK_CHOICES,
        null=True,
        blank=True
    )

    def __str__(self):
        return self.title

class ReportInstance(models.Model):   # 👈 plural hataya, singular rakha
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='instances')
    file = models.TextField(null=True, blank=True)   # ya FileField agar chaho
    json = models.JSONField(null=True, blank=True)  # ✅ fixed
    instance_summary = models.TextField(null=True, blank=True)
    date_of_the_report = models.DateTimeField(auto_now_add=True)
    address_of_the_doctor = models.TextField(null=True, blank=True)
    name_of_the_doctor = models.CharField(max_length=200, null=True, blank=True)
    youtube_videos = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.instance_name} - {self.report.title}"


class ChatBot(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chatbots')
    memory = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"ChatBot - {self.user.username} - {self.report.title}"