from django.contrib import admin
from .models import HeadlineTest, AlternativeHeadline, HeadlineScore


@admin.register(HeadlineTest)
class HeadlineTestAdmin(admin.ModelAdmin):
    list_display = ['id', 'original_headline_short', 'status', 'created_by', 'created_at', 'winning_score']
    list_filter = ['status', 'created_at', 'created_by']
    search_fields = ['original_headline', 'created_by__username']
    readonly_fields = ['created_at', 'winning_headline', 'winning_score', 'original_score', 'improvement_percentage']
    ordering = ['-created_at']
    
    def original_headline_short(self, obj):
        return obj.original_headline[:50] + '...' if len(obj.original_headline) > 50 else obj.original_headline
    original_headline_short.short_description = 'Original Headline'


@admin.register(AlternativeHeadline)
class AlternativeHeadlineAdmin(admin.ModelAdmin):
    list_display = ['test', 'order', 'headline_short', 'angle_type', 'created_at']
    list_filter = ['angle_type', 'created_at']
    search_fields = ['headline_text', 'test__original_headline']
    ordering = ['test', 'order']
    
    def headline_short(self, obj):
        return obj.headline_text[:50] + '...' if len(obj.headline_text) > 50 else obj.headline_text
    headline_short.short_description = 'Headline'


@admin.register(HeadlineScore)
class HeadlineScoreAdmin(admin.ModelAdmin):
    list_display = ['test', 'headline_short', 'is_original', 'total_score', 'status', 'created_at']
    list_filter = ['is_original', 'status', 'created_at']
    search_fields = ['headline_text', 'test__original_headline']
    readonly_fields = ['created_at', 'completed_at']
    ordering = ['-created_at']
    
    def headline_short(self, obj):
        return obj.headline_text[:40] + '...' if len(obj.headline_text) > 40 else obj.headline_text
    headline_short.short_description = 'Headline'
