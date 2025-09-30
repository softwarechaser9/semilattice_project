from django.contrib import admin
from django.core.exceptions import PermissionDenied
from .models import (
    PressReleaseScore, CategoryScore, QuestionScore,
    PressReleaseQuestionCategory, PressReleaseQuestion
)


class SuperuserOnlyAdminMixin:
    """Mixin to restrict admin access to superusers only"""
    
    def has_module_permission(self, request):
        return request.user.is_superuser
    
    def has_add_permission(self, request):
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
    
    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser


class PressReleaseQuestionInline(admin.TabularInline):
    model = PressReleaseQuestion
    extra = 1
    fields = ['question_text', 'order', 'is_active']
    ordering = ['order']


@admin.register(PressReleaseQuestionCategory)
class PressReleaseQuestionCategoryAdmin(SuperuserOnlyAdminMixin, admin.ModelAdmin):
    list_display = ['display_name', 'category_key', 'order', 'question_count', 'updated_at']
    list_editable = ['order']
    search_fields = ['display_name', 'category_key']
    ordering = ['order', 'display_name']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [PressReleaseQuestionInline]
    
    def question_count(self, obj):
        return obj.questions.filter(is_active=True).count()
    question_count.short_description = 'Active Questions'


@admin.register(PressReleaseQuestion)
class PressReleaseQuestionAdmin(SuperuserOnlyAdminMixin, admin.ModelAdmin):
    list_display = ['global_question_number', 'category', 'order', 'question_preview', 'is_active', 'updated_at']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['question_text', 'category__display_name']
    list_editable = ['order', 'is_active']
    ordering = ['category__order', 'order']
    readonly_fields = ['created_at', 'updated_at', 'global_question_number']
    
    fieldsets = (
        (None, {
            'fields': ('category', 'question_text', 'order', 'is_active')
        }),
        ('Metadata', {
            'fields': ('global_question_number', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def question_preview(self, obj):
        return obj.question_text[:80] + "..." if len(obj.question_text) > 80 else obj.question_text
    question_preview.short_description = 'Question Preview'


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
