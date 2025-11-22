"""
Celery tasks for asynchronous email sending
Handles background processing of email campaigns
"""
import logging
from celery import shared_task
from django.core.mail import EmailMessage
from django.conf import settings
from django.utils import timezone
from .models import Distribution, DistributionRecipient, EmailLog
from .email_utils import apply_mail_merge, validate_email_settings

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_single_email_async(self, recipient_id):
    """
    Send a single email asynchronously
    
    Args:
        recipient_id: ID of the DistributionRecipient to send to
    
    Returns:
        dict: Status information
    """
    try:
        recipient = DistributionRecipient.objects.get(id=recipient_id)
        distribution = recipient.distribution
        
        # Update status to sending
        recipient.status = 'sending'
        recipient.save()
        
        # Get personalized content (already stored during preparation)
        subject = recipient.personalized_subject or distribution.subject
        body = recipient.personalized_body or distribution.body
        
        # Create email message
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient.contact.email],
        )
        
        # Attach files if any
        for attachment in distribution.attachments.all():
            email.attach_file(attachment.file.path)
        
        # Send email
        email.send()
        
        # Update status to sent
        recipient.status = 'sent'
        recipient.sent_at = timezone.now()
        recipient.save()
        
        # Create email log
        EmailLog.objects.create(
            distribution_recipient=recipient,
            contact=recipient.contact,
            event='sent',
            event_data={'message': f'Email sent successfully to {recipient.contact.email}'}
        )
        
        logger.info(f"Email sent to {recipient.contact.email} for distribution {distribution.id}")
        
        # Update distribution status after this email
        update_distribution_status.delay(distribution.id)
        
        return {
            'status': 'success',
            'recipient_id': recipient_id,
            'email': recipient.contact.email
        }
        
    except DistributionRecipient.DoesNotExist:
        logger.error(f"DistributionRecipient {recipient_id} not found")
        return {'status': 'error', 'message': 'Recipient not found'}
        
    except Exception as e:
        logger.error(f"Error sending email to recipient {recipient_id}: {str(e)}")
        
        # Update recipient status
        try:
            recipient.status = 'failed'
            recipient.error_message = str(e)
            recipient.save()
            
            # Create error log
            EmailLog.objects.create(
                distribution_recipient=recipient,
                contact=recipient.contact,
                event='bounced',
                event_data={'error': str(e), 'message': f'Failed to send: {str(e)}'}
            )
            
            # Update distribution status
            update_distribution_status.delay(recipient.distribution.id)
        except:
            pass
        
        # Retry the task
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        
        return {
            'status': 'error',
            'recipient_id': recipient_id,
            'error': str(e)
        }


@shared_task(bind=True)
def send_distribution_async(self, distribution_id):
    """
    Send all emails for a distribution asynchronously
    
    Args:
        distribution_id: ID of the Distribution to send
    
    Returns:
        dict: Status information with counts
    """
    try:
        logger.info(f"[TASK START] send_distribution_async called for distribution_id={distribution_id}")
        distribution = Distribution.objects.get(id=distribution_id)
        logger.info(f"[TASK] Found distribution: {distribution.name}, current status: {distribution.status}")
        
        # IMPORTANT: Check if scheduled time has arrived
        from django.utils import timezone
        if distribution.scheduled_at and distribution.scheduled_at > timezone.now():
            logger.warning(f"[TASK] Distribution {distribution_id} scheduled for {distribution.scheduled_at}, not sending yet (current time: {timezone.now()})")
            return {
                'status': 'skipped',
                'message': 'Distribution scheduled for future time',
                'scheduled_at': distribution.scheduled_at.isoformat()
            }
        
        # Validate email settings
        is_valid, validation_message = validate_email_settings()
        logger.info(f"[TASK] Email validation result: {is_valid}, message: {validation_message}")
        if not is_valid:
            distribution.status = 'failed'
            distribution.save()
            logger.error(f"Email validation failed: {validation_message}")
            return {
                'status': 'error',
                'message': f'Email settings not configured: {validation_message}'
            }
        
        # Update status to sending
        distribution.status = 'sending'
        distribution.save()
        logger.info(f"[TASK] Updated distribution status to 'sending'")
        
        # Get all pending recipients
        recipients = distribution.recipient_records.filter(status='pending')
        total_recipients = recipients.count()
        logger.info(f"[TASK] Found {total_recipients} pending recipients")
        
        if total_recipients == 0:
            distribution.status = 'completed'
            distribution.save()
            return {
                'status': 'success',
                'message': 'No recipients to send to'
            }
        
        logger.info(f"Starting to send distribution {distribution_id} to {total_recipients} recipients")
        
        # Queue individual email tasks
        for recipient in recipients:
            logger.info(f"[TASK] Queuing email for recipient {recipient.id}: {recipient.contact.email}")
            # Chain the task - send each email individually
            send_single_email_async.delay(recipient.id)
        
        # Note: Distribution status will be updated by a separate task that checks progress
        # Or you can manually check it later
        
        return {
            'status': 'queued',
            'distribution_id': distribution_id,
            'total_recipients': total_recipients,
            'message': f'Queued {total_recipients} emails for sending'
        }
        
    except Distribution.DoesNotExist:
        logger.error(f"Distribution {distribution_id} not found")
        return {'status': 'error', 'message': 'Distribution not found'}
        
    except Exception as e:
        logger.error(f"Error sending distribution {distribution_id}: {str(e)}")
        
        try:
            distribution.status = 'failed'
            distribution.save()
        except:
            pass
        
        return {
            'status': 'error',
            'distribution_id': distribution_id,
            'error': str(e)
        }


@shared_task
def update_distribution_status(distribution_id):
    """
    Check and update the status of a distribution based on recipient statuses
    
    Args:
        distribution_id: ID of the Distribution to check
    """
    try:
        distribution = Distribution.objects.get(id=distribution_id)
        
        # Count statuses
        total = distribution.recipient_records.count()
        sent = distribution.recipient_records.filter(status='sent').count()
        failed = distribution.recipient_records.filter(status='failed').count()
        pending = distribution.recipient_records.filter(status='pending').count()
        sending = distribution.recipient_records.filter(status='sending').count()
        
        # Update distribution counts
        distribution.sent_count = sent
        distribution.failed_count = failed
        
        # Determine overall status
        if pending == 0 and sending == 0:
            # All done
            if failed == total:
                distribution.status = 'failed'
            else:
                # Mark as completed (even if some failed)
                distribution.status = 'completed'
                if not distribution.completed_at:
                    distribution.completed_at = timezone.now()
        elif sending > 0 or (pending > 0 and sent > 0):
            distribution.status = 'sending'
        
        distribution.save()
        
        logger.info(f"Updated distribution {distribution_id} status: {distribution.status} (sent: {sent}, failed: {failed}, pending: {pending})")
        
        return {
            'distribution_id': distribution_id,
            'status': distribution.status,
            'sent': sent,
            'failed': failed,
            'pending': pending
        }
        
    except Distribution.DoesNotExist:
        logger.error(f"Distribution {distribution_id} not found")
        return {'status': 'error', 'message': 'Distribution not found'}
    except Exception as e:
        logger.error(f"Error updating distribution status {distribution_id}: {str(e)}")
        return {'status': 'error', 'error': str(e)}


@shared_task
def cleanup_old_logs(days=90):
    """
    Clean up old email logs (optional maintenance task)
    
    Args:
        days: Delete logs older than this many days
    """
    from django.utils import timezone
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=days)
    deleted_count = EmailLog.objects.filter(timestamp__lt=cutoff_date).delete()[0]
    
    logger.info(f"Cleaned up {deleted_count} old email logs")
    
    return {
        'deleted_count': deleted_count,
        'cutoff_date': cutoff_date.isoformat()
    }


@shared_task
def test_celery():
    """
    Simple test task to verify Celery is working
    """
    logger.info("Celery test task executed successfully!")
    return {'status': 'success', 'message': 'Celery is working!'}


@shared_task
def check_scheduled_distributions():
    """
    Periodic task to check for distributions scheduled to be sent now
    Runs every minute via Celery Beat
    """
    from django.utils import timezone
    from .campaign_utils import prepare_distribution_recipients
    
    logger.info("Checking for scheduled distributions...")
    
    # Find distributions that are:
    # 1. Status is 'scheduled'
    # 2. scheduled_at time has passed (scheduled_at <= now)
    now = timezone.now()
    scheduled_distributions = Distribution.objects.filter(
        status='scheduled',
        scheduled_at__lte=now
    )
    
    count = scheduled_distributions.count()
    logger.info(f"Found {count} distributions ready to send")
    
    sent_count = 0
    for distribution in scheduled_distributions:
        logger.info(f"Triggering scheduled distribution: {distribution.name} (ID: {distribution.id})")
        
        # IMPORTANT: Prepare recipients if not already done
        if distribution.total_recipients == 0:
            success, message, recipient_count = prepare_distribution_recipients(distribution)
            if not success:
                logger.error(f"Failed to prepare recipients for distribution {distribution.id}: {message}")
                distribution.status = 'failed'
                distribution.save()
                continue
            logger.info(f"Prepared {recipient_count} recipients for distribution {distribution.id}")
        
        # Update status to 'sending' before triggering task
        distribution.status = 'sending'
        distribution.save()
        logger.info(f"Updated distribution {distribution.id} status to 'sending'")
        
        # Call the async send task
        result = send_distribution_async.delay(distribution.id)
        
        # Update distribution to track the task
        distribution.celery_task_id = result.id
        distribution.save()
        logger.info(f"Queued distribution {distribution.id} with task ID: {result.id}")
        
        sent_count += 1
    
    return {
        'status': 'success',
        'checked_at': now.isoformat(),
        'found': count,
        'triggered': sent_count
    }


@shared_task(bind=True)
def import_csv_async(self, csv_content, skip_duplicates, update_existing, user_id, import_job_id=None):
    """
    Import contacts from CSV file asynchronously (for large imports)
    
    Works with distributed containers (Django web + Celery worker on different machines)
    by passing CSV content directly instead of relying on shared filesystem.
    
    Args:
        csv_content: Raw CSV file content as string
        skip_duplicates: Skip contacts with duplicate emails
        update_existing: Update existing contacts if email matches
        user_id: ID of user importing contacts
        import_job_id: ID of ImportJob to track progress (optional)
    
    Returns:
        dict: Import results with counts and errors
    """
    from .csv_utils import import_contacts_from_csv
    from django.contrib.auth.models import User
    from .models import ImportJob
    from django.core.files.uploadedfile import InMemoryUploadedFile
    from io import BytesIO, StringIO
    from django.utils import timezone
    
    import_job = None
    
    try:
        user = User.objects.get(id=user_id)
        
        # Get ImportJob if provided
        if import_job_id:
            import_job = ImportJob.objects.get(id=import_job_id)
            import_job.status = 'processing'
            import_job.started_at = timezone.now()
            import_job.save()
        
        # Convert CSV content string to file-like object
        # csv_utils expects a file object with .read() method
        if isinstance(csv_content, bytes):
            csv_file = BytesIO(csv_content)
        else:
            # Convert string to bytes
            csv_file = BytesIO(csv_content.encode('utf-8'))
        
        # Set a name attribute (required by some CSV parsers)
        csv_file.name = 'uploaded.csv'
        
        # Import contacts using the file-like object
        result = import_contacts_from_csv(
            csv_file=csv_file,
            skip_duplicates=skip_duplicates,
            update_existing=update_existing,
            created_by=user
        )
        
        # Update ImportJob with results
        if import_job:
            # Consider it successful if:
            # 1. We imported or updated contacts, OR
            # 2. We processed rows and they were all skipped (duplicates/valid skips)
            # Only mark as failed if there were errors and nothing was processed
            has_results = (result['imported'] > 0 or result['updated'] > 0 or result['skipped'] > 0)
            has_only_errors = (result['errors'] and not has_results)
            
            import_job.status = 'failed' if has_only_errors else 'completed'
            import_job.total_rows = result['total_rows']
            import_job.imported = result['imported']
            import_job.updated = result['updated']
            import_job.skipped = result['skipped']
            import_job.errors = result['errors'][:50]  # Store first 50 errors
            import_job.warnings = result['warnings'][:100]  # Store first 100 warnings
            import_job.completed_at = timezone.now()
            import_job.save()
        
        logger.info(
            f"CSV async import completed for user {user_id}: "
            f"{result['imported']} imported, {result['updated']} updated, "
            f"{result['skipped']} skipped"
        )
        return result
        
    except Exception as e:
        import traceback
        error_msg = f"Import failed: {str(e)}"
        traceback_str = traceback.format_exc()
        logger.error(f"Error in async CSV import for user {user_id}: {error_msg}")
        logger.error(f"Traceback: {traceback_str}")
        
        # Update ImportJob with failure
        if import_job:
            import_job.status = 'failed'
            # Include exception type and first line of traceback for debugging
            import_job.errors = [
                error_msg,
                f"Exception type: {type(e).__name__}",
                f"Traceback (last line): {traceback_str.split(chr(10))[-2] if traceback_str else 'N/A'}"
            ]
            import_job.completed_at = timezone.now()
            import_job.save()
        
        return {
            'success': False,
            'errors': [error_msg],
            'imported': 0,
            'updated': 0,
            'skipped': 0,
            'total_rows': 0,
            'warnings': []
        }
