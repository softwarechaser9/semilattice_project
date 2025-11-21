"""
Django management command to check campaign statuses
Usage: python manage.py check_campaigns
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from press_release_mailer.models import Distribution


class Command(BaseCommand):
    help = 'Check status of all campaigns'

    def add_arguments(self, parser):
        parser.add_argument(
            '--recent',
            type=int,
            default=10,
            help='Number of recent campaigns to show (default: 10)'
        )

    def handle(self, *args, **options):
        recent = options['recent']

        self.stdout.write(self.style.SUCCESS('\n📊 Campaign Status Report\n'))
        self.stdout.write('=' * 80)

        campaigns = Distribution.objects.order_by('-created_at')[:recent]

        if not campaigns:
            self.stdout.write(self.style.WARNING('\n⚠️  No campaigns found.\n'))
            return

        for dist in campaigns:
            # Header
            status_style = {
                'draft': self.style.WARNING,
                'scheduled': self.style.WARNING,
                'sending': self.style.HTTP_INFO,
                'completed': self.style.SUCCESS,
                'failed': self.style.ERROR,
                'cancelled': self.style.WARNING,
            }.get(dist.status, self.style.WARNING)

            self.stdout.write(f'\n📧 Campaign #{dist.id}: {dist.name}')
            self.stdout.write(status_style(f'   Status: {dist.get_status_display()}'))
            self.stdout.write(f'   Created: {dist.created_at.strftime("%Y-%m-%d %H:%M")}')

            # Progress
            if dist.total_recipients > 0:
                progress = (dist.sent_count / dist.total_recipients) * 100
                self.stdout.write(f'   Progress: {dist.sent_count}/{dist.total_recipients} ({progress:.1f}%)')

                if dist.failed_count > 0:
                    self.stdout.write(self.style.ERROR(f'   Failed: {dist.failed_count}'))

            # Recipient breakdown
            pending = dist.recipient_records.filter(status='pending').count()
            sending = dist.recipient_records.filter(status='sending').count()
            sent = dist.recipient_records.filter(status='sent').count()
            failed = dist.recipient_records.filter(status='failed').count()

            if pending > 0 or sending > 0:
                self.stdout.write('   Recipients:')
                if pending > 0:
                    self.stdout.write(f'     ⏳ Pending: {pending}')
                if sending > 0:
                    self.stdout.write(self.style.WARNING(f'     📤 Sending: {sending} (may be stuck!)'))
                if sent > 0:
                    self.stdout.write(self.style.SUCCESS(f'     ✅ Sent: {sent}'))
                if failed > 0:
                    self.stdout.write(self.style.ERROR(f'     ❌ Failed: {failed}'))

            # Suggest action for stuck campaigns
            if dist.status == 'sending':
                age = timezone.now() - dist.created_at
                if age > timedelta(minutes=10) and sending > 0:
                    self.stdout.write(self.style.WARNING(
                        f'   ⚠️  Campaign may be stuck! Use: python manage.py retry_campaign {dist.id}'
                    ))

        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS('\n✅ Report complete\n'))
        
        # Show commands
        self.stdout.write('💡 Useful commands:')
        self.stdout.write('   python manage.py retry_campaign <id>  # Retry a stuck campaign')
        self.stdout.write('   python manage.py check_campaigns --recent 20  # Show more campaigns\n')
