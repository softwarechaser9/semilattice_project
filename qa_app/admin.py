from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from .models import Population, Question, SimulationResult


# Custom User Admin for approval management
class UserAdmin(BaseUserAdmin):
    """Custom User admin with approval functionality"""
    
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_active', 'is_staff', 'date_joined', 'approval_status']
    list_filter = ['is_active', 'is_staff', 'is_superuser', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['-date_joined']  # Show newest users first
    
    # Add approval actions
    actions = ['approve_users', 'deactivate_users']
    
    def approval_status(self, obj):
        """Display approval status with colors"""
        if obj.is_active:
            return format_html('<span style="color: green; font-weight: bold;">✓ Approved</span>')
        else:
            return format_html('<span style="color: orange; font-weight: bold;">⏳ Pending Approval</span>')
    approval_status.short_description = 'Status'
    
    def approve_users(self, request, queryset):
        """Action to approve selected users"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} user(s) have been approved and can now log in.')
    approve_users.short_description = "Approve selected users"
    
    def deactivate_users(self, request, queryset):
        """Action to deactivate selected users"""
        # Don't deactivate superusers
        queryset = queryset.exclude(is_superuser=True)
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} user(s) have been deactivated.')
    deactivate_users.short_description = "Deactivate selected users (except superusers)"

# Unregister the default User admin and register our custom one
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


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
