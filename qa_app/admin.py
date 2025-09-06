from django.contrib import admin
from .models import Population, Question, SimulationResult


@admin.register(Population)
class PopulationAdmin(admin.ModelAdmin):
    list_display = ['name', 'population_id', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'population_id', 'description']
    readonly_fields = ['created_at']


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['question_text', 'question_type', 'population', 'created_by', 'created_at']
    list_filter = ['question_type', 'created_at', 'population']
    search_fields = ['question_text']
    readonly_fields = ['created_at']
    raw_id_fields = ['population', 'created_by']


@admin.register(SimulationResult)
class SimulationResultAdmin(admin.ModelAdmin):
    list_display = ['question', 'status', 'answer_id', 'created_at', 'updated_at']
    list_filter = ['status', 'created_at', 'updated_at']
    readonly_fields = ['created_at', 'updated_at', 'answer_id']
    raw_id_fields = ['question']
