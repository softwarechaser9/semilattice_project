"""
Django management command to retry stuck/failed campaigns
Usage: python manage.py retry_campaign <distribution_id>
"""
from django.core.management.base import BaseCommand, CommandError
from press_release_mailer.models import Distribution, DistributionRecipient
from press_release_mailer.tasks import send_distribution_async


class Command(BaseCommand):
    help = 'Retry sending a stuck or failed campaign'

    def add_arguments(self, parser):
        parser.add_argument(
            'distribution_id',
            type=int,
            help='ID of the distribution/campaign to retry'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force retry even if campaign is marked as completed'
        )

    def handle(self, *args, **options):
        distribution_id = options['distribution_id']
        force = options.get('force', False)

        try:
            distribution = Distribution.objects.get(id=distribution_id)
        except Distribution.DoesNotExist:
            raise CommandError(f'Distribution with ID {distribution_id} does not exist')

        self.stdout.write(self.style.WARNING(f'\n📧 Campaign: {distribution.name}'))
        self.stdout.write(f'Status: {distribution.get_status_display()}')
        self.stdout.write(f'Created: {distribution.created_at}')
        self.stdout.write(f'Total Recipients: {distribution.total_recipients}')
        self.stdout.write(f'Sent: {distribution.sent_count}')
        self.stdout.write(f'Failed: {distribution.failed_count}\n')

        # Show recipient breakdown
        pending = distribution.recipient_records.filter(status='pending').count()
        sending = distribution.recipient_records.filter(status='sending').count()
        sent = distribution.recipient_records.filter(status='sent').count()
        failed = distribution.recipient_records.filter(status='failed').count()

        self.stdout.write('📊 Recipient Status Breakdown:')
        if pending > 0:
            self.stdout.write(f'  ⏳ Pending: {pending}')
        if sending > 0:
            self.stdout.write(f'  📤 Sending: {sending}')
        if sent > 0:
            self.stdout.write(self.style.SUCCESS(f'  ✅ Sent: {sent}'))
        if failed > 0:
            self.stdout.write(self.style.ERROR(f'  ❌ Failed: {failed}'))

        # Check if campaign needs retry
        if distribution.status == 'completed' and not force:
            self.stdout.write(self.style.WARNING(
                '\n⚠️  Campaign is marked as completed. Use --force to retry anyway.'
            ))
            return

        if pending == 0 and sending == 0 and failed == 0:
            self.stdout.write(self.style.SUCCESS(
                '\n✅ All emails have been sent successfully. No retry needed.'
            ))
            return

        # Reset stuck "sending" recipients back to "pending"
        if sending > 0:
            self.stdout.write(f'\n🔄 Resetting {sending} stuck "sending" recipients to "pending"...')
            distribution.recipient_records.filter(status='sending').update(status='pending')

        # Ask for confirmation
        if not force:
            confirm = input('\n⚠️  Continue with retry? This will re-queue the campaign. [y/N]: ')
            if confirm.lower() != 'y':
                self.stdout.write(self.style.WARNING('Retry cancelled.'))
                return

        # Reset distribution status
        distribution.status = 'sending'
        distribution.save()

        # Queue the campaign
        self.stdout.write('\n📤 Queueing campaign for sending...')
        result = send_distribution_async.delay(distribution.id)

        self.stdout.write(self.style.SUCCESS(f'✅ Campaign queued successfully!'))
        self.stdout.write(f'Task ID: {result.id}')
        self.stdout.write(f'\n💡 Watch your Celery terminal for progress.')
        self.stdout.write(f'💡 Or check the web interface: http://127.0.0.1:8000/press-release-mailer/distribution/{distribution.id}/\n')
