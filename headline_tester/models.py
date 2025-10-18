from django.db import models
from django.contrib.auth.models import User


class HeadlineTest(models.Model):
    """Model to store headline test information"""
    original_headline = models.CharField(max_length=500)
    context_url = models.URLField(blank=True, null=True, help_text="Optional URL for context")
    population_id = models.CharField(max_length=255, help_text="Semilattice population ID")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Processing status
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('generating', 'Generating Headlines'),
            ('generated', 'Headlines Generated'),
            ('testing', 'Testing Headlines'),
            ('completed', 'Completed'),
            ('failed', 'Failed')
        ],
        default='pending'
    )
    error_message = models.TextField(blank=True, null=True)
    
    # Results summary
    winning_headline = models.CharField(max_length=500, blank=True, null=True)
    winning_score = models.FloatField(blank=True, null=True)
    original_score = models.FloatField(blank=True, null=True)
    improvement_percentage = models.FloatField(blank=True, null=True)
    
    def __str__(self):
        return f"Headline Test: {self.original_headline[:50]}... - {self.created_at.strftime('%Y-%m-%d')}"

    @property
    def total_headlines(self):
        """Total number of headlines (original + alternatives)"""
        return 1 + self.alternatives.count()

    @property 
    def population_display_name(self):
        """Get formatted population display - set by view"""
        return getattr(self, '_population_display_name', self.population_id)


class AlternativeHeadline(models.Model):
    """Model to store Claude-generated alternative headlines"""
    ANGLE_CHOICES = [
        ('hard_news', 'Hard News Angle'),
        ('human_interest', 'Human Interest Angle'),
        ('conflict_controversy', 'Conflict/Controversy Angle'),
        ('local_angle', 'Local Angle'),
        ('trend_bigger_picture', 'Trend/Bigger Picture Angle'),
    ]
    
    test = models.ForeignKey(HeadlineTest, on_delete=models.CASCADE, related_name='alternatives')
    headline_text = models.CharField(max_length=500)
    angle_type = models.CharField(max_length=50, choices=ANGLE_CHOICES)
    claude_description = models.CharField(max_length=200, blank=True, null=True)
    order = models.IntegerField(help_text="Order from Claude (1-5)")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"Alt {self.order}: {self.headline_text[:50]}..."


class HeadlineScore(models.Model):
    """Model to store Semilattice test results for each headline"""
    test = models.ForeignKey(HeadlineTest, on_delete=models.CASCADE, related_name='scores')
    headline_text = models.CharField(max_length=500)
    is_original = models.BooleanField(default=False)
    alternative = models.ForeignKey(AlternativeHeadline, on_delete=models.CASCADE, blank=True, null=True)
    
    # Semilattice integration
    semilattice_response_id = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('running', 'Running'),
            ('completed', 'Completed'),
            ('failed', 'Failed')
        ],
        default='pending'
    )
    
    # Scoring (preference score 1-5)
    total_score = models.FloatField(blank=True, null=True)
    detailed_scores = models.JSONField(blank=True, null=True, help_text="Preference scoring details")
    
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-total_score', 'created_at']
    
    def __str__(self):
        if self.total_score:
            preference_text = self.get_preference_display()
            score_text = f"{preference_text} ({self.total_score})"
        else:
            score_text = "Pending"
        headline_type = "Original" if self.is_original else f"Alt {self.alternative.order if self.alternative else '?'}"
        return f"{headline_type}: {score_text}"

    def get_preference_display(self):
        """Convert numeric preference score to text"""
        if self.total_score is None:
            return "Pending"
        elif self.total_score >= 4.5:
            return "Very Appealing"
        elif self.total_score >= 3.5:
            return "Appealing"
        elif self.total_score >= 2.5:
            return "Neutral"
        elif self.total_score >= 1.5:
            return "Not Appealing"
        else:
            return "Very Unappealing"

    @property
    def score_percentage(self):
        if self.total_score is not None:
            return round((self.total_score / 5) * 100, 1)
        return None

    @property
    def headline_type_display(self):
        if self.is_original:
            return "Original"
        elif self.alternative:
            return f"Alternative {self.alternative.order}"
        return "Unknown"


class HeadlineQuestion(models.Model):
    """Model to store headline testing questions"""
    question_text = models.TextField()
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    max_score = models.IntegerField(default=10, help_text="Maximum score for this question")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'id']
    
    def __str__(self):
        return f"Q{self.order}: {self.question_text[:50]}..."

    def get_full_question_template(self):
        """Returns the question formatted for API use with headline"""
        return f"Please read the following headline '{{headline_text}}' and consider: {self.question_text}"
