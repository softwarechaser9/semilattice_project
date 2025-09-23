from django.contrib import admin
from .models import PressReleaseScore, CategoryScore, QuestionScore


@admin.register(PressReleaseScore)
class PressReleaseScoreAdmin(admin.ModelAdmin):
    list_display = ['id', 'total_score', 'score_percentage', 'created_by', 'created_at']
    list_filter = ['created_at', 'created_by']
    search_fields = ['press_release_text', 'created_by__username']
    readonly_fields = ['created_at']
    
    def score_percentage(self, obj):
        return f"{obj.score_percentage}%"
    score_percentage.short_description = 'Score %'


@admin.register(CategoryScore)
class CategoryScoreAdmin(admin.ModelAdmin):
    list_display = ['id', 'category_display_name', 'score', 'score_percentage', 'press_release']
    list_filter = ['category_name', 'press_release__created_at']
    search_fields = ['category_display_name', 'press_release__press_release_text']
    
    def score_percentage(self, obj):
        return f"{obj.score_percentage}%"
    score_percentage.short_description = 'Score %'


@admin.register(QuestionScore)
class QuestionScoreAdmin(admin.ModelAdmin):
    list_display = ['id', 'question_number', 'score', 'category', 'question_text_short']
    list_filter = ['score', 'category__category_name']
    search_fields = ['question_text']
    
    def question_text_short(self, obj):
        return obj.question_text[:50] + "..." if len(obj.question_text) > 50 else obj.question_text
    question_text_short.short_description = 'Question'
