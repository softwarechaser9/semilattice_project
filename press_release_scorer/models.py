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
    score = models.IntegerField(blank=True, null=True)  # 1-6, can be null until completed
    semilattice_answer_id = models.CharField(max_length=255, blank=True, null=True)
    raw_response = models.JSONField(blank=True, null=True)
    # Note: Full question with embedded press release is sent to API but not stored
    
    def __str__(self):
        return f"Q{self.question_number}: {self.score}/6"


class PressReleaseQuestionCategory(models.Model):
    """Model to store question categories for press release scoring"""
    category_key = models.CharField(max_length=50, unique=True)  # e.g., 'source_credibility'
    display_name = models.CharField(max_length=100)  # e.g., 'Source Credibility'
    order = models.IntegerField(default=0)  # For ordering categories
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Press Release Question Category'
        verbose_name_plural = 'Press Release Question Categories'
        ordering = ['order', 'display_name']
    
    def __str__(self):
        return self.display_name


class PressReleaseQuestion(models.Model):
    """Model to store individual press release scoring questions"""
    category = models.ForeignKey(PressReleaseQuestionCategory, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    order = models.IntegerField(default=0)  # For ordering within category
    is_active = models.BooleanField(default=True)  # Allow disabling questions
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Press Release Question'
        verbose_name_plural = 'Press Release Questions'
        ordering = ['category__order', 'order', 'id']
        unique_together = [['category', 'order']]  # Prevent duplicate ordering within category
    
    def __str__(self):
        return f"{self.category.display_name} - Q{self.order}: {self.question_text[:50]}..."
    
    @property
    def global_question_number(self):
        """Calculate the global question number (1-30) based on category and order"""
        # Get all categories ordered properly
        categories = PressReleaseQuestionCategory.objects.all().order_by('order', 'display_name')
        question_number = 0
        
        for cat in categories:
            if cat.id == self.category.id:
                # Add questions from current category up to this question
                questions_in_category = self.category.questions.filter(
                    is_active=True, order__lt=self.order
                ).count()
                question_number += questions_in_category + 1
                break
            else:
                # Add all questions from previous categories
                question_number += cat.questions.filter(is_active=True).count()
        
        return question_number
    
    def get_full_question_template(self):
        """Returns the question formatted for API use"""
        return f"Please read the following press release {{press_release_text}} and consider: {self.question_text}"
