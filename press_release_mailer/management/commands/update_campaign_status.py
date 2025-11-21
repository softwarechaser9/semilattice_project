"""
Django management command to update campaign status
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from press_release_mailer.models import Distribution


class Command(BaseCommand):
    help = 'Update campaign status for completed campaigns'

    def handle(self, *args, **options):
        # Find campaigns that are still marked as "sending" but have all emails sent/failed
        distributions = Distribution.objects.filter(status='sending')

        self.stdout.write(f"\nFound {distributions.count()} campaigns with 'sending' status")
        self.stdout.write("=" * 70)

        updated_count = 0
        
        for dist in distributions:
            total = dist.recipient_records.count()
            sent = dist.recipient_records.filter(status='sent').count()
            failed = dist.recipient_records.filter(status='failed').count()
            pending = dist.recipient_records.filter(status='pending').count()
            sending = dist.recipient_records.filter(status='sending').count()
            
            self.stdout.write(f"\nCampaign: {dist.name} (ID: {dist.id})")
            self.stdout.write(f"  Current Status: {dist.status}")
            self.stdout.write(f"  Total Recipients: {total}")
            self.stdout.write(f"  Sent: {sent}")
            self.stdout.write(f"  Failed: {failed}")
            self.stdout.write(f"  Pending: {pending}")
            self.stdout.write(f"  Sending: {sending}")
            
            # Check if all emails are done
            if pending == 0 and sending == 0:
                old_status = dist.status
                if failed == total:
                    dist.status = 'failed'
                else:
                    dist.status = 'completed'
                    if not dist.completed_at:
                        dist.completed_at = timezone.now()
                
                dist.sent_count = sent
                dist.failed_count = failed
                dist.save()
                
                updated_count += 1
                self.stdout.write(self.style.SUCCESS(f"  ✅ Updated status: {old_status} → {dist.status}"))
            else:
                self.stdout.write(f"  ⏳ Still processing (pending: {pending}, sending: {sending})")

        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(self.style.SUCCESS(f"\nUpdated {updated_count} campaigns!\n"))
