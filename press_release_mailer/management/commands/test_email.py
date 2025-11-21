"""
Management command to test Gmail SMTP configuration
Usage: python manage.py test_email your.email@example.com
"""
from django.core.management.base import BaseCommand
from press_release_mailer.email_utils import send_test_email, validate_email_settings


class Command(BaseCommand):
    help = 'Test Gmail SMTP configuration by sending a test email'

    def add_arguments(self, parser):
        parser.add_argument(
            'email',
            type=str,
            help='Email address to send test email to'
        )

    def handle(self, *args, **options):
        email = options['email']
        
        self.stdout.write('\n🔍 Checking email configuration...')
        
        # Validate settings
        is_valid, message = validate_email_settings()
        if not is_valid:
            self.stdout.write(self.style.ERROR(f'❌ {message}'))
            self.stdout.write('\nPlease check your .env file and ensure these variables are set:')
            self.stdout.write('  - EMAIL_HOST_USER (your Gmail address)')
            self.stdout.write('  - EMAIL_HOST_PASSWORD (your Gmail App Password)')
            self.stdout.write('\n💡 To generate a Gmail App Password:')
            self.stdout.write('  1. Go to https://myaccount.google.com/apppasswords')
            self.stdout.write('  2. Create a new app password')
            self.stdout.write('  3. Copy it to your .env file')
            return
        
        self.stdout.write(self.style.SUCCESS(f'✓ {message}'))
        
        # Send test email
        self.stdout.write(f'\n📧 Sending test email to {email}...')
        
        success, result_message = send_test_email(email)
        
        if success:
            self.stdout.write(self.style.SUCCESS(f'\n✅ {result_message}'))
            self.stdout.write('\nCheck your inbox! If you don\'t see it:')
            self.stdout.write('  - Check your spam folder')
            self.stdout.write('  - Make sure the email address is correct')
            self.stdout.write('  - Verify your Gmail settings allow sending')
        else:
            self.stdout.write(self.style.ERROR(f'\n❌ {result_message}'))
            self.stdout.write('\nTroubleshooting:')
            self.stdout.write('  - Verify your Gmail App Password is correct')
            self.stdout.write('  - Make sure 2-factor authentication is enabled')
            self.stdout.write('  - Check that "Less secure app access" is NOT needed (App Passwords are more secure)')
