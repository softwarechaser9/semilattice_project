from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from press_release_scorer.models import PressReleaseScore
from press_release_scorer.services import PressReleaseScoringService
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Process pending press release scores'

    def add_arguments(self, parser):
        parser.add_argument('--score-id', type=int, help='Process specific score ID')
        parser.add_argument('--population-id', type=str, help='Population ID to use')

    def handle(self, *args, **options):
        score_id = options.get('score_id')
        population_id = options.get('population_id')
        
        if not score_id:
            self.stdout.write(self.style.ERROR('--score-id is required'))
            return
            
        if not population_id:
            self.stdout.write(self.style.ERROR('--population-id is required'))
            return

        try:
            # Get the score record
            score = PressReleaseScore.objects.get(id=score_id)
            
            if score.total_score > 0:
                self.stdout.write(self.style.WARNING(f'Score {score_id} already processed'))
                return
            
            self.stdout.write(f'Processing score {score_id} for user {score.created_by.username}...')
            
            # Initialize scoring service
            scoring_service = PressReleaseScoringService()
            
            # Process the scoring (this will take time)
            result = scoring_service.score_press_release(
                press_release_text=score.press_release_text,
                population_id=population_id,
                user=score.created_by
            )
            
            if result and result.total_score > 0:
                # Delete the old empty record and keep the new one
                score.delete()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Score {score_id} processed successfully! New score: {result.total_score}/180'
                    )
                )
            else:
                self.stdout.write(self.style.ERROR(f'Failed to process score {score_id}'))
                
        except PressReleaseScore.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Score {score_id} not found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error processing score {score_id}: {e}'))
            logger.error(f'Error processing score {score_id}: {e}')
