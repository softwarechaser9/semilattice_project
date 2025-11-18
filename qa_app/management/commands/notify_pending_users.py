from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings


class Command(BaseCommand):
    help = 'Send email notifications to admins about pending user approvals'
    
    def handle(self, *args, **options):
        # Get all inactive users (pending approval)
        pending_users = User.objects.filter(is_active=False, is_superuser=False)
        
        if not pending_users.exists():
            self.stdout.write(self.style.SUCCESS('No users pending approval.'))
            return
        
        # Get all superusers to notify
        admins = User.objects.filter(is_superuser=True, is_active=True)
        admin_emails = [admin.email for admin in admins if admin.email]
        
        if not admin_emails:
            self.stdout.write(self.style.WARNING('No admin emails found.'))
            return
        
        # Create email content
        user_list = '\n'.join([f"- {user.username} ({user.email}) - Registered: {user.date_joined.strftime('%Y-%m-%d %H:%M')}" for user in pending_users])
        
        subject = f'Semilattice App: {pending_users.count()} User(s) Pending Approval'
        message = f"""
Hello Admin,

The following users are waiting for account approval:

{user_list}

To approve these users:
1. Log in to the Django admin panel
2. Go to Users section
3. Select the users you want to approve
4. Choose "Approve selected users" from the Actions dropdown

Best regards,
Semilattice System
"""
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=admin_emails,
                fail_silently=False
            )
            self.stdout.write(self.style.SUCCESS(f'Notification sent to {len(admin_emails)} admin(s) about {pending_users.count()} pending user(s).'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to send email: {e}'))
