"""
Email utility functions for sending emails with mail merge support
Using Gmail SMTP configured in Django settings
"""
from django.core.mail import EmailMessage
from django.template import Template, Context
from django.conf import settings
from django.utils import timezone
import re
import logging

logger = logging.getLogger(__name__)


def apply_mail_merge(template_text, contact):
    """
    Apply mail merge to replace template variables with contact data
    
    Supported variables:
    - {{first_name}}
    - {{last_name}}
    - {{full_name}}
    - {{email}}
    - {{organization}}
    - {{job_title}}
    """
    replacements = {
        '{{first_name}}': contact.first_name or '',
        '{{last_name}}': contact.last_name or '',
        '{{full_name}}': contact.full_name or '',
        '{{email}}': contact.email or '',
        '{{organization}}': contact.organization or '',
        '{{job_title}}': contact.job_title or '',
    }
    
    result = template_text
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)
    
    return result


def send_single_email(recipient_email, subject, body, from_email=None, attachments=None):
    """
    Send a single email using Gmail SMTP
    
    Args:
        recipient_email: Email address of recipient
        subject: Email subject line
        body: Email body (plain text or HTML)
        from_email: Sender email (optional, uses DEFAULT_FROM_EMAIL if not provided)
        attachments: List of file paths to attach (optional)
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        if from_email is None:
            from_email = settings.DEFAULT_FROM_EMAIL
        
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=from_email,
            to=[recipient_email],
        )
        
        # Attach files if provided
        if attachments:
            for attachment in attachments:
                if hasattr(attachment, 'read'):  # File object
                    email.attach(attachment.name, attachment.read(), attachment.content_type)
                else:  # File path
                    email.attach_file(attachment)
        
        email.send(fail_silently=False)
        
        logger.info(f"Email sent successfully to {recipient_email}")
        return (True, f"Email sent successfully to {recipient_email}")
    
    except Exception as e:
        error_msg = f"Failed to send email to {recipient_email}: {str(e)}"
        logger.error(error_msg)
        return (False, error_msg)


def send_distribution_email(distribution_recipient):
    """
    Send email to a single DistributionRecipient with mail merge applied
    
    Args:
        distribution_recipient: DistributionRecipient instance
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        distribution = distribution_recipient.distribution
        contact = distribution_recipient.contact
        
        # Apply mail merge to subject and body
        personalized_subject = apply_mail_merge(distribution.subject, contact)
        personalized_body = apply_mail_merge(distribution.body, contact)
        
        # Store personalized content
        distribution_recipient.personalized_subject = personalized_subject
        distribution_recipient.personalized_body = personalized_body
        distribution_recipient.status = 'sending'
        distribution_recipient.save()
        
        # Get attachments if any
        attachments = []
        for attachment in distribution.attachments.all():
            attachments.append(attachment.file)
        
        # Send the email
        success, message = send_single_email(
            recipient_email=contact.email,
            subject=personalized_subject,
            body=personalized_body,
            attachments=attachments if attachments else None
        )
        
        # Update status
        if success:
            distribution_recipient.status = 'sent'
            distribution_recipient.sent_at = timezone.now()
            
            # Update distribution counters
            distribution.sent_count += 1
            distribution.save()
            
            # Log the email
            from .models import EmailLog
            EmailLog.objects.create(
                distribution_recipient=distribution_recipient,
                contact=contact,
                event='sent'
            )
        else:
            distribution_recipient.status = 'failed'
            distribution_recipient.error_message = message
        
        distribution_recipient.save()
        
        return (success, message)
    
    except Exception as e:
        error_msg = f"Error processing email for {distribution_recipient.contact.email}: {str(e)}"
        logger.error(error_msg)
        
        distribution_recipient.status = 'failed'
        distribution_recipient.error_message = error_msg
        distribution_recipient.save()
        
        return (False, error_msg)


def send_test_email(to_email, from_email=None):
    """
    Send a test email to verify Gmail SMTP configuration
    
    Args:
        to_email: Email address to send test email to
        from_email: Sender email (optional)
    
    Returns:
        tuple: (success: bool, message: str)
    """
    subject = "Test Email from Press Release Mailer"
    body = """
Hello!

This is a test email from your Press Release Mailer system.

If you're receiving this, your Gmail SMTP configuration is working correctly!

Best regards,
Press Release Mailer System
    """
    
    return send_single_email(to_email, subject, body, from_email)


def validate_email_settings():
    """
    Validate that email settings are properly configured
    
    Returns:
        tuple: (is_valid: bool, message: str)
    """
    required_settings = [
        'EMAIL_HOST',
        'EMAIL_PORT',
        'EMAIL_HOST_USER',
        'EMAIL_HOST_PASSWORD',
    ]
    
    missing = []
    for setting in required_settings:
        if not hasattr(settings, setting) or not getattr(settings, setting):
            missing.append(setting)
    
    if missing:
        return (False, f"Missing email settings: {', '.join(missing)}")
    
    return (True, "Email settings are configured")


def preview_mail_merge(template_text, contact):
    """
    Preview how mail merge will look for a specific contact
    Useful for testing templates
    
    Args:
        template_text: Template string with {{variables}}
        contact: Contact instance
    
    Returns:
        str: Processed template with contact data
    """
    return apply_mail_merge(template_text, contact)
