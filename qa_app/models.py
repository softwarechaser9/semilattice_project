from django.db import models
from django.contrib.auth.models import User
import json


class Population(models.Model):
    """Model to store Semilattice population information"""
    population_id = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.population_id})"


class Question(models.Model):
    """Model to store questions asked to the Semilattice API"""
    QUESTION_TYPES = (
        ('single-choice', 'Single Choice'),
        ('multiple-choice', 'Multiple Choice'),
        ('free-text', 'Free Text'),
    )
    
    population = models.ForeignKey(Population, on_delete=models.CASCADE)
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    answer_options = models.JSONField(blank=True, null=True)  # Store array of options
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
    def __str__(self):
        return f"Q: {self.question_text[:50]}..."


class SimulationResult(models.Model):
    """Model to store results from Semilattice API"""
    STATUS_CHOICES = (
        ('Queued', 'Queued'),        # Official API status
        ('Running', 'Running'),      # Official API status  
        ('Predicted', 'Predicted'),  # Official API status
        ('Failed', 'Failed'),        # Official API status
    )
    
    question = models.OneToOneField(Question, on_delete=models.CASCADE, related_name='result')
    answer_id = models.CharField(max_length=255)  # ID from Semilattice
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Queued')
    simulated_answer_percentages = models.JSONField(blank=True, null=True)
    raw_response = models.JSONField(blank=True, null=True)  # Store full API response
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Result for: {self.question.question_text[:30]}... - {self.status}"
    
    @property
    def is_complete(self):
        return self.status == 'Predicted'  # Official API uses 'Predicted' not 'predicted'
