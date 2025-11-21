from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Contact, ContactList, EmailTemplate, 
    Distribution, DistributionRecipient, 
    Attachment, EmailLog
)


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'email', 'organization', 'category', 'is_active', 'created_at']
    list_filter = ['is_active', 'category', 'created_at']
    search_fields = ['first_name', 'last_name', 'email', 'organization', 'tags']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('first_name', 'last_name', 'email')
        }),
        ('Organization', {
            'fields': ('organization', 'job_title')
        }),
        ('Contact Details', {
            'fields': ('phone',)
        }),
        ('Address', {
            'fields': ('address', 'city', 'state', 'country', 'postal_code'),
            'classes': ('collapse',)
        }),
        ('Classification', {
            'fields': ('category', 'tags')
        }),
        ('Status & Notes', {
            'fields': ('is_active', 'notes')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by on creation
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ContactList)
class ContactListAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_count', 'created_at', 'created_by']
    search_fields = ['name', 'description']
    filter_horizontal = ['contacts']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'description')
        }),
        ('Contacts', {
            'fields': ('contacts',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'subject', 'body']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'is_active')
        }),
        ('Email Content', {
            'fields': ('subject', 'body'),
            'description': 'You can use mail merge variables: {{first_name}}, {{last_name}}, {{organization}}, {{job_title}}'
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 0
    readonly_fields = ['file_size', 'content_type', 'uploaded_at']


class DistributionRecipientInline(admin.TabularInline):
    model = DistributionRecipient
    extra = 0
    readonly_fields = ['status', 'sent_at', 'error_message']
    fields = ['contact', 'status', 'sent_at', 'error_message']
    can_delete = False


@admin.register(Distribution)
class DistributionAdmin(admin.ModelAdmin):
    list_display = ['name', 'subject', 'status_badge', 'total_recipients', 'progress_display', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'subject', 'body']
    readonly_fields = ['status', 'total_recipients', 'sent_count', 'failed_count', 'created_at', 'updated_at', 'sent_at', 'completed_at', 'progress_percentage']
    filter_horizontal = ['contact_lists']
    inlines = [AttachmentInline]
    
    fieldsets = (
        ('Campaign Details', {
            'fields': ('name', 'subject', 'body')
        }),
        ('Recipients', {
            'fields': ('contact_lists',),
            'description': 'Select contact lists to send to. Individual recipients are calculated automatically.'
        }),
        ('Scheduling', {
            'fields': ('scheduled_at',),
            'description': 'Leave blank to send immediately, or set a future date/time.'
        }),
        ('Status & Statistics', {
            'fields': ('status', 'total_recipients', 'sent_count', 'failed_count', 'progress_percentage'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'sent_at', 'completed_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'draft': '#6c757d',
            'scheduled': '#007bff',
            'sending': '#ffc107',
            'completed': '#28a745',
            'failed': '#dc3545',
            'cancelled': '#6c757d',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def progress_display(self, obj):
        if obj.total_recipients == 0:
            return "0%"
        percentage = obj.progress_percentage()
        return format_html(
            '<div style="width: 100px; background-color: #e9ecef; border-radius: 3px; overflow: hidden;">'
            '<div style="width: {}%; background-color: #28a745; color: white; text-align: center; font-size: 11px; padding: 2px 0;">{}%</div>'
            '</div>',
            percentage,
            percentage
        )
    progress_display.short_description = 'Progress'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(DistributionRecipient)
class DistributionRecipientAdmin(admin.ModelAdmin):
    list_display = ['distribution', 'contact', 'status', 'sent_at']
    list_filter = ['status', 'sent_at']
    search_fields = ['contact__email', 'contact__first_name', 'contact__last_name', 'distribution__name']
    readonly_fields = ['personalized_subject', 'personalized_body', 'sent_at', 'provider_message_id']
    
    fieldsets = (
        (None, {
            'fields': ('distribution', 'contact', 'status')
        }),
        ('Personalized Content', {
            'fields': ('personalized_subject', 'personalized_body'),
            'classes': ('collapse',)
        }),
        ('Delivery Tracking', {
            'fields': ('sent_at', 'error_message', 'provider_message_id'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ['filename', 'distribution', 'file_size_mb', 'content_type', 'uploaded_at']
    list_filter = ['content_type', 'uploaded_at']
    search_fields = ['filename', 'distribution__name']
    readonly_fields = ['file_size', 'content_type', 'uploaded_at', 'file_size_mb']


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ['contact', 'event', 'timestamp', 'distribution_link']
    list_filter = ['event', 'timestamp']
    search_fields = ['contact__email', 'contact__first_name', 'contact__last_name']
    readonly_fields = ['distribution_recipient', 'contact', 'event', 'event_data', 'timestamp']
    
    def distribution_link(self, obj):
        if obj.distribution_recipient:
            return format_html(
                '<a href="/admin/press_release_mailer/distribution/{}/change/">{}</a>',
                obj.distribution_recipient.distribution.id,
                obj.distribution_recipient.distribution.name
            )
        return "-"
    distribution_link.short_description = 'Distribution'
    
    def has_add_permission(self, request):
        return False  # Logs are created automatically
    
    def has_delete_permission(self, request, obj=None):
        return False  # Keep all logs for audit trail
