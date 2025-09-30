from django.core.management.base import BaseCommand
from press_release_scorer.models import PressReleaseQuestionCategory, PressReleaseQuestion
from press_release_scorer.constants import PRESS_RELEASE_QUESTIONS


class Command(BaseCommand):
    help = 'Populate database with the 30 press release scoring questions from constants.py'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Delete existing questions and categories before populating',
        )
    
    def handle(self, *args, **options):
        if options['overwrite']:
            self.stdout.write('Deleting existing questions and categories...')
            PressReleaseQuestion.objects.all().delete()
            PressReleaseQuestionCategory.objects.all().delete()
        
        self.stdout.write('Populating question categories and questions...')
        
        category_order = 0
        total_questions = 0
        
        for category_key, category_data in PRESS_RELEASE_QUESTIONS.items():
            # Create or get category
            category, created = PressReleaseQuestionCategory.objects.get_or_create(
                category_key=category_key,
                defaults={
                    'display_name': category_data['display_name'],
                    'order': category_order
                }
            )
            
            if created:
                self.stdout.write(f'  Created category: {category.display_name}')
            else:
                self.stdout.write(f'  Using existing category: {category.display_name}')
            
            # Create questions for this category
            question_order = 1
            for question_text in category_data['questions']:
                question, created = PressReleaseQuestion.objects.get_or_create(
                    category=category,
                    order=question_order,
                    defaults={
                        'question_text': question_text,
                        'is_active': True
                    }
                )
                
                if created:
                    total_questions += 1
                    self.stdout.write(f'    Created Q{question_order}: {question_text[:50]}...')
                else:
                    self.stdout.write(f'    Using existing Q{question_order}: {question_text[:50]}...')
                
                question_order += 1
            
            category_order += 1
        
        # Verify we have 30 questions
        total_db_questions = PressReleaseQuestion.objects.filter(is_active=True).count()
        
        self.stdout.write(self.style.SUCCESS(f'\nSuccess! Database now contains:'))
        self.stdout.write(f'  - {PressReleaseQuestionCategory.objects.count()} categories')
        self.stdout.write(f'  - {total_db_questions} active questions')
        
        if total_db_questions == 30:
            self.stdout.write(self.style.SUCCESS('✓ All 30 questions are properly loaded!'))
        else:
            self.stdout.write(self.style.WARNING(f'⚠ Expected 30 questions, but found {total_db_questions}'))
        
        # Show summary by category
        self.stdout.write('\nQuestions by category:')
        for category in PressReleaseQuestionCategory.objects.all().order_by('order'):
            count = category.questions.filter(is_active=True).count()
            self.stdout.write(f'  {category.display_name}: {count} questions')
