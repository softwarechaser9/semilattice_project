from django.db import models
from django.contrib.auth.models import User


class PressReleaseScore(models.Model):
    """Model to store press release scoring results"""
    press_release_text = models.TextField()
    total_score = models.IntegerField()  # Out of 180 (30 questions × 6 max points)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    # Added fields for async/incremental processing
    population_id = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('running', 'Running'), ('done', 'Done'), ('failed', 'Failed')],
        default='pending'
    )
    processed_questions = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Press Release Score: {self.total_score}/180 - {self.created_at.strftime('%Y-%m-%d')}"
    
    @property
    def score_percentage(self):
        return round((self.total_score / 180) * 100, 1)


class CategoryScore(models.Model):
    """Model to store category-wise scores"""
    CATEGORY_CHOICES = [
        ('source_credibility', 'Source Credibility'),
        ('accuracy_evidence', 'Accuracy & Evidence'),
        ('newsworthiness', 'Newsworthiness'),
        ('bias_intent', 'Bias & Intent'),
        ('practicality_next_steps', 'Practicality & Next Steps'),
    ]
    
    press_release = models.ForeignKey(PressReleaseScore, on_delete=models.CASCADE, related_name='category_scores')
    category_name = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    category_display_name = models.CharField(max_length=100)
    score = models.IntegerField()  # Out of 36 (6 questions × 6 max points)
    
    def __str__(self):
        return f"{self.category_display_name}: {self.score}/36"
    
    @property
    def score_percentage(self):
        return round((self.score / 36) * 100, 1)


class QuestionScore(models.Model):
    """Model to store individual question scores"""
    category = models.ForeignKey(CategoryScore, on_delete=models.CASCADE, related_name='question_scores')
    question_text = models.TextField()  # Store just the base question text
    question_number = models.IntegerField()  # 1-30
    score = models.IntegerField()  # 1-6
    semilattice_answer_id = models.CharField(max_length=255, blank=True, null=True)
    raw_response = models.JSONField(blank=True, null=True)
    # Note: Full question with embedded press release is sent to API but not stored
    
    def __str__(self):
        return f"Q{self.question_number}: {self.score}/6"
