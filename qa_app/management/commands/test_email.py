from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings


class Command(BaseCommand):
    help = 'Test Django email configuration'
    
    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Email address to send test to')
    
    def handle(self, *args, **options):
        email = options['email']
        
        self.stdout.write('=== Django Email Settings ===')
        self.stdout.write(f'EMAIL_BACKEND: {settings.EMAIL_BACKEND}')
        self.stdout.write(f'EMAIL_HOST: {settings.EMAIL_HOST}')
        self.stdout.write(f'EMAIL_PORT: {settings.EMAIL_PORT}')
        self.stdout.write(f'EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}')
        self.stdout.write(f'EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}')
        self.stdout.write(f'EMAIL_HOST_PASSWORD: {settings.EMAIL_HOST_PASSWORD[:4]}***{settings.EMAIL_HOST_PASSWORD[-4:] if len(settings.EMAIL_HOST_PASSWORD) > 8 else "***"}')
        self.stdout.write(f'DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}')
        self.stdout.write('')
        
        try:
            self.stdout.write('🔄 Sending test email via Django...')
            send_mail(
                subject='Django Email Test',
                message='This is a test email from Django using Gmail SMTP.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False
            )
            self.stdout.write(self.style.SUCCESS('✅ Email sent successfully via Django!'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Django email failed: {e}'))
            
            # Provide troubleshooting
            self.stdout.write('')
            self.stdout.write('🔧 Troubleshooting:')
            if not settings.EMAIL_HOST_USER:
                self.stdout.write('- EMAIL_HOST_USER is empty - check your .env file')
            if not settings.EMAIL_HOST_PASSWORD:
                self.stdout.write('- EMAIL_HOST_PASSWORD is empty - check your .env file')
            if settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD:
                self.stdout.write('- Credentials look OK, this might be a Django configuration issue')
