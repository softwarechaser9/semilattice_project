"""
Campaign/Distribution utilities for sending bulk emails
"""
from django.utils import timezone
from django.db import transaction
from .models import Distribution, DistributionRecipient, Contact, Attachment
from .email_utils import send_single_email, apply_mail_merge
import logging

logger = logging.getLogger(__name__)


def prepare_distribution_recipients(distribution):
    """
    Prepare distribution by creating DistributionRecipient records
    for all contacts in the selected lists and individual contacts.
    Also applies mail merge to personalize content for each recipient.
    
    Returns: tuple (success, message, recipient_count)
    """
    try:
        with transaction.atomic():
            # Collect all unique contacts
            contacts = set()
            
            # Add contacts from contact lists
            for contact_list in distribution.contact_lists.all():
                for contact in contact_list.contacts.filter(is_active=True):
                    contacts.add(contact)
            
            if not contacts:
                return False, "No active contacts found in selected lists", 0
            
            # Create DistributionRecipient records with personalized content
            recipient_records = []
            for contact in contacts:
                # Apply mail merge immediately during preparation
                personalized_subject = apply_mail_merge(distribution.subject, contact)
                personalized_body = apply_mail_merge(distribution.body, contact)
                
                recipient_records.append(
                    DistributionRecipient(
                        distribution=distribution,
                        contact=contact,
                        status='pending',
                        personalized_subject=personalized_subject,
                        personalized_body=personalized_body
                    )
                )
            
            # Bulk create all recipients
            DistributionRecipient.objects.bulk_create(
                recipient_records,
                ignore_conflicts=True  # Skip if already exists
            )
            
            # Update distribution statistics
            distribution.total_recipients = len(recipient_records)
            distribution.save()
            
            return True, f"Prepared {len(recipient_records)} recipients", len(recipient_records)
            
    except Exception as e:
        logger.error(f"Error preparing distribution recipients: {str(e)}")
        return False, f"Error: {str(e)}", 0


def send_distribution(distribution, user=None):
    """
    Send a distribution to all prepared recipients.
    
    For now, this sends emails synchronously. Later we'll add Celery for background processing.
    
    Returns: tuple (success, message, sent_count, failed_count)
    """
    if distribution.status not in ['draft', 'scheduled']:
        return False, "Distribution cannot be sent in current status", 0, 0
    
    # Prepare recipients if not already done
    if distribution.total_recipients == 0:
        success, message, count = prepare_distribution_recipients(distribution)
        if not success:
            return False, message, 0, 0
    
    # Update status to sending
    distribution.status = 'sending'
    distribution.sent_at = timezone.now()
    distribution.save()
    
    sent_count = 0
    failed_count = 0
    
    # Get all pending recipients
    recipients = distribution.recipient_records.filter(status='pending')
    
    logger.info(f"Starting to send distribution '{distribution.name}' to {recipients.count()} recipients")
    
    for recipient in recipients:
        try:
            # Apply mail merge to subject and body
            personalized_subject = apply_mail_merge(distribution.subject, recipient.contact)
            personalized_body = apply_mail_merge(distribution.body, recipient.contact)
            
            # Store personalized content
            recipient.personalized_subject = personalized_subject
            recipient.personalized_body = personalized_body
            recipient.status = 'sending'
            recipient.save()
            
            # Get attachments if any
            attachment_files = []
            for attachment in distribution.attachments.all():
                attachment_files.append(attachment.file.path)
            
            # Send the email
            success, message = send_single_email(
                to_email=recipient.contact.email,
                subject=personalized_subject,
                body=personalized_body,
                attachments=attachment_files
            )
            
            if success:
                recipient.status = 'sent'
                recipient.sent_at = timezone.now()
                sent_count += 1
                logger.info(f"Sent to {recipient.contact.email}")
            else:
                recipient.status = 'failed'
                recipient.error_message = message
                failed_count += 1
                logger.error(f"Failed to send to {recipient.contact.email}: {message}")
            
            recipient.save()
            
        except Exception as e:
            recipient.status = 'failed'
            recipient.error_message = str(e)
            recipient.save()
            failed_count += 1
            logger.error(f"Exception sending to {recipient.contact.email}: {str(e)}")
    
    # Update distribution statistics
    distribution.sent_count = sent_count
    distribution.failed_count = failed_count
    
    if failed_count == 0:
        distribution.status = 'completed'
    elif sent_count == 0:
        distribution.status = 'failed'
    else:
        distribution.status = 'completed'  # Partial success still counts as completed
    
    distribution.completed_at = timezone.now()
    distribution.save()
    
    message = f"Distribution completed: {sent_count} sent, {failed_count} failed"
    logger.info(message)
    
    return True, message, sent_count, failed_count


def get_preview_recipients(distribution, limit=3):
    """
    Get a sample of recipients for preview with mail merge applied.
    
    Returns: list of dicts with contact info and personalized content
    """
    previews = []
    
    # Get sample contacts from lists
    contacts = set()
    for contact_list in distribution.contact_lists.all():
        for contact in contact_list.contacts.filter(is_active=True)[:limit]:
            contacts.add(contact)
            if len(contacts) >= limit:
                break
        if len(contacts) >= limit:
            break
    
    for contact in list(contacts)[:limit]:
        personalized_subject = apply_mail_merge(distribution.subject, contact)
        personalized_body = apply_mail_merge(distribution.body, contact)
        
        previews.append({
            'contact': contact,
            'personalized_subject': personalized_subject,
            'personalized_body': personalized_body,
        })
    
    return previews


def handle_distribution_attachments(distribution, files):
    """
    Handle file uploads for distribution attachments.
    
    Args:
        distribution: Distribution instance
        files: List of uploaded files from request.FILES
    
    Returns: tuple (success, message, attachment_count)
    """
    if not files:
        return True, "No attachments", 0
    
    attachment_count = 0
    
    try:
        for uploaded_file in files:
            # Create attachment record
            attachment = Attachment(
                distribution=distribution,
                file=uploaded_file,
                filename=uploaded_file.name,
                file_size=uploaded_file.size,
                content_type=uploaded_file.content_type or 'application/octet-stream'
            )
            attachment.save()
            attachment_count += 1
            logger.info(f"Attached file: {uploaded_file.name} ({uploaded_file.size} bytes)")
        
        return True, f"Uploaded {attachment_count} attachment(s)", attachment_count
        
    except Exception as e:
        logger.error(f"Error handling attachments: {str(e)}")
        return False, f"Error uploading attachments: {str(e)}", attachment_count


def send_distribution_async(distribution, user=None):
    """
    Send a distribution asynchronously using Celery.
    Queues the email sending task in the background.
    
    Returns: tuple (success, message, total_recipients)
    """
    from .tasks import send_distribution_async as celery_task
    
    if distribution.status not in ['draft', 'scheduled']:
        return False, "Distribution cannot be sent in current status", 0
    
    # Prepare recipients if not already done
    if distribution.total_recipients == 0:
        success, message, count = prepare_distribution_recipients(distribution)
        if not success:
            return False, message, 0
    
    # Check if this is a scheduled send or immediate send
    from django.utils import timezone
    is_scheduled = distribution.scheduled_at and distribution.scheduled_at > timezone.now()
    
    # Update status based on send time
    if is_scheduled:
        distribution.status = 'scheduled'
    else:
        # Immediate send - set to sending (Celery will process immediately)
        distribution.status = 'sending'
    distribution.save()
    
    # Queue the Celery task
    try:
        task = celery_task.delay(distribution.id)
        logger.info(f"Queued distribution {distribution.id} for sending. Task ID: {task.id}")
        
        # Store task ID for tracking (optional)
        distribution.celery_task_id = task.id
        distribution.save()
        
        return True, f"Email campaign queued for {distribution.total_recipients} recipients", distribution.total_recipients
    
    except Exception as e:
        logger.error(f"Error queuing distribution task: {str(e)}")
        distribution.status = 'failed'
        distribution.save()
        return False, f"Error queuing task: {str(e)}", 0
