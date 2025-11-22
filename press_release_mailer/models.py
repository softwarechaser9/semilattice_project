from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Contact(models.Model):
    """Individual contact in the database"""
    
    # Basic Information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()  # Removed unique=True - now handled by Meta constraint
    
    # Organization Details
    organization = models.CharField(max_length=200, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    
    # Contact Details
    phone = models.CharField(max_length=20, blank=True)
    
    # Address (optional)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=50, blank=True)
    country = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    
    # Categories/Tags for filtering
    category = models.CharField(max_length=100, blank=True, help_text="e.g., Press, Blogger, Influencer")
    tags = models.TextField(blank=True, help_text="Comma-separated tags for filtering")
    
    # Metadata
    is_active = models.BooleanField(default=True, help_text="Unsubscribed contacts are marked inactive")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='contacts_created')
    
    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name = 'Contact'
        verbose_name_plural = 'Contacts'
        # Unique constraint: email must be unique PER USER (not globally)
        constraints = [
            models.UniqueConstraint(
                fields=['email', 'created_by'],
                name='unique_email_per_user'
            )
        ]
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class ContactList(models.Model):
    """Saved lists/groups of contacts for easy selection"""
    
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    contacts = models.ManyToManyField(Contact, related_name='contact_lists', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='lists_created')
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Contact List'
        verbose_name_plural = 'Contact Lists'
    
    def __str__(self):
        return f"{self.name} ({self.contacts.count()} contacts)"
    
    def contact_count(self):
        return self.contacts.count()
    contact_count.short_description = 'Contacts'


class EmailTemplate(models.Model):
    """Reusable email templates with mail merge support"""
    
    name = models.CharField(max_length=200, unique=True)
    subject = models.CharField(max_length=300, help_text="Can use {{first_name}}, {{last_name}}, {{organization}}")
    body = models.TextField(help_text="Can use {{first_name}}, {{last_name}}, {{organization}}, {{job_title}}")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Email Template'
        verbose_name_plural = 'Email Templates'
    
    def __str__(self):
        return self.name


class Distribution(models.Model):
    """Email distribution/campaign"""
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('sending', 'Sending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Campaign Details
    name = models.CharField(max_length=200, help_text="Internal name for this distribution")
    subject = models.CharField(max_length=300)
    body = models.TextField()
    
    # Recipients
    recipients = models.ManyToManyField(Contact, through='DistributionRecipient', related_name='distributions')
    contact_lists = models.ManyToManyField(ContactList, blank=True, related_name='distributions')
    
    # Attachments
    # (We'll add file handling later)
    
    # Status & Scheduling
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    scheduled_at = models.DateTimeField(null=True, blank=True, help_text="Leave blank to send immediately")
    
    # Statistics
    total_recipients = models.IntegerField(default=0)
    sent_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='distributions_created')
    
    # Celery task tracking
    celery_task_id = models.CharField(max_length=255, null=True, blank=True, help_text="Celery task ID for background processing")
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Distribution'
        verbose_name_plural = 'Distributions'
    
    def __str__(self):
        return f"{self.name} - {self.get_status_display()}"
    
    def progress_percentage(self):
        if self.total_recipients == 0:
            return 0
        return int((self.sent_count / self.total_recipients) * 100)


class DistributionRecipient(models.Model):
    """Individual recipient status for each distribution"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sending', 'Sending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('bounced', 'Bounced'),
    ]
    
    distribution = models.ForeignKey(Distribution, on_delete=models.CASCADE, related_name='recipient_records')
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Personalized content (after mail merge)
    personalized_subject = models.CharField(max_length=300, blank=True)
    personalized_body = models.TextField(blank=True)
    
    # Delivery tracking
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    # External provider tracking
    provider_message_id = models.CharField(max_length=200, blank=True, help_text="SendGrid/provider message ID")
    
    class Meta:
        unique_together = ['distribution', 'contact']
        ordering = ['id']
        verbose_name = 'Distribution Recipient'
        verbose_name_plural = 'Distribution Recipients'
    
    def __str__(self):
        return f"{self.contact.email} - {self.get_status_display()}"


class Attachment(models.Model):
    """File attachments for distributions"""
    
    distribution = models.ForeignKey(Distribution, on_delete=models.CASCADE, related_name='attachments')
    
    file = models.FileField(upload_to='distribution_attachments/%Y/%m/%d/')
    filename = models.CharField(max_length=255)
    file_size = models.IntegerField(help_text="Size in bytes")
    content_type = models.CharField(max_length=100)
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['filename']
        verbose_name = 'Attachment'
        verbose_name_plural = 'Attachments'
    
    def __str__(self):
        if self.file_size:
            return f"{self.filename} ({self.file_size} bytes)"
        return f"{self.filename}"
    
    def file_size_mb(self):
        """Return file size in MB, or None if file_size is not set"""
        if self.file_size is None:
            return None
        return round(self.file_size / (1024 * 1024), 2)


class EmailLog(models.Model):
    """Detailed log of all email activities"""
    
    EVENT_CHOICES = [
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('opened', 'Opened'),
        ('clicked', 'Clicked'),
        ('bounced', 'Bounced'),
        ('spam', 'Spam Report'),
        ('unsubscribed', 'Unsubscribed'),
    ]
    
    distribution_recipient = models.ForeignKey(DistributionRecipient, on_delete=models.CASCADE, related_name='logs', null=True, blank=True)
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='email_logs')
    
    event = models.CharField(max_length=20, choices=EVENT_CHOICES)
    event_data = models.JSONField(blank=True, null=True, help_text="Raw event data from email provider")
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Email Log'
        verbose_name_plural = 'Email Logs'
    
    def __str__(self):
        return f"{self.contact.email} - {self.get_event_display()} at {self.timestamp}"
