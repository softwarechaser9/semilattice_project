from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from unittest.mock import patch, MagicMock
from qa_app.models import Population
from .models import PressReleaseScore, CategoryScore, QuestionScore
from .services import PressReleaseScoringService
from .constants import get_all_questions


class PressReleaseScorerTestCase(TestCase):
    """Test cases for the Press Release Scorer app"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test population
        self.population = Population.objects.create(
            name='Test Population',
            description='A test population for scoring',
            population_id='test-pop-123',
            created_by=self.user
        )
        
        # Sample press release for testing
        self.sample_press_release = """
        FOR IMMEDIATE RELEASE
        
        TechCorp Announces Revolutionary AI Breakthrough
        
        SAN FRANCISCO, CA - September 20, 2025 - TechCorp, a leading technology company, today announced a major breakthrough in artificial intelligence that could transform healthcare diagnostics. The new AI system, called MedAI Pro, demonstrates 99.7% accuracy in detecting early-stage cancer from medical imaging, significantly outperforming current diagnostic methods.
        
        "This breakthrough represents a paradigm shift in how we approach medical diagnostics," said Dr. Sarah Johnson, Chief Technology Officer at TechCorp. "MedAI Pro has the potential to save millions of lives through early detection."
        
        Key features of MedAI Pro include:
        - 99.7% accuracy rate in clinical trials involving 50,000 patients
        - Ability to detect 15 different types of cancer
        - Processing time reduced from hours to minutes
        - Integration with existing hospital systems
        
        The technology was developed over five years by a team of 200 researchers and validated through peer-reviewed studies published in the Journal of Medical AI. Clinical trials were conducted at Mayo Clinic, Johns Hopkins, and Stanford Medical Center.
        
        TechCorp plans to begin FDA approval process next month, with commercial availability expected in Q2 2026. The company has already secured partnerships with three major hospital networks for pilot implementations.
        
        About TechCorp:
        Founded in 2010, TechCorp is a publicly traded company (NASDAQ: TECH) specializing in AI-powered healthcare solutions. The company is headquartered in San Francisco with offices in Boston, London, and Tokyo.
        
        Contact Information:
        Media Relations: media@techcorp.com
        Investor Relations: investors@techcorp.com
        Phone: (555) 123-4567
        Website: www.techcorp.com
        """
        
        # Long press release for testing truncation
        self.long_press_release = self.sample_press_release + """
        
        Additional detailed technical information about the AI system:
        
        The MedAI Pro system utilizes advanced deep learning algorithms based on convolutional neural networks (CNNs) and transformer architectures. The training dataset consisted of over 10 million medical images sourced from leading medical institutions worldwide. The system underwent rigorous validation using cross-validation techniques and was tested against a diverse patient population representing different demographics, ages, and medical conditions.
        
        The technology incorporates several innovative features including multi-modal analysis capability, real-time processing optimization, and adaptive learning mechanisms that improve accuracy over time. The system can analyze various types of medical imaging including CT scans, MRI images, X-rays, and ultrasounds.
        
        Performance metrics from clinical trials showed:
        - Sensitivity: 99.7%
        - Specificity: 98.9%
        - Positive Predictive Value: 97.8%
        - Negative Predictive Value: 99.9%
        - Area Under the Curve (AUC): 0.994
        
        The economic impact study conducted by independent research firm MedEcon Analytics projects that widespread adoption of MedAI Pro could reduce healthcare costs by $50 billion annually in the United States alone through earlier detection and reduced need for invasive diagnostic procedures.
        
        Regulatory pathway includes FDA 510(k) clearance followed by PMA application. International regulatory approvals will be sought in European Union (CE marking), Canada (Health Canada), Japan (PMDA), and Australia (TGA).
        """ * 3  # Repeat to make it very long
    
    def test_models_creation(self):
        """Test that all models can be created successfully"""
        # Create press release score
        score = PressReleaseScore.objects.create(
            press_release_text=self.sample_press_release,
            total_score=150,
            created_by=self.user
        )
        
        self.assertEqual(score.total_score, 150)
        self.assertEqual(score.score_percentage, 83.3)
        self.assertEqual(score.created_by, self.user)
        
        # Create category score
        category = CategoryScore.objects.create(
            press_release=score,
            category_name='source_credibility',
            category_display_name='Source Credibility',
            score=30
        )
        
        self.assertEqual(category.score, 30)
        self.assertEqual(category.score_percentage, 83.3)
        
        # Create question score
        question = QuestionScore.objects.create(
            category=category,
            question_text='Test question?',
            question_number=1,
            score=5
        )
        
        self.assertEqual(question.score, 5)
        self.assertEqual(str(question), 'Q1: 5/6')
    
    def test_constants_questions(self):
        """Test that all 30 questions are properly defined"""
        all_questions = get_all_questions()
        
        self.assertEqual(len(all_questions), 30)
        
        # Check that questions are numbered 1-30
        question_numbers = [q['number'] for q in all_questions]
        self.assertEqual(question_numbers, list(range(1, 31)))
        
        # Check that we have 5 categories with 6 questions each
        categories = set(q['category_key'] for q in all_questions)
        self.assertEqual(len(categories), 5)
        
        for category in categories:
            category_questions = [q for q in all_questions if q['category_key'] == category]
            self.assertEqual(len(category_questions), 6)
    
    @patch('press_release_scorer.services.SemilatticeAPIClient')
    def test_scoring_service_truncation(self, mock_client):
        """Test that long press releases are properly truncated"""
        # Mock the API client
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        
        # Mock API response
        mock_instance.send_question.return_value = {
            'answer_id': 'test-123',
            'simulated_answer_percentages': {'5': 60, '4': 25, '3': 15}
        }
        
        service = PressReleaseScoringService()
        
        # Test truncation method
        truncated = service._truncate_press_release(self.long_press_release, max_length=100)
        self.assertLessEqual(len(truncated), 103)  # 100 + "..."
        self.assertTrue(truncated.endswith('...'))
        
        # Test that short text is not truncated
        short_text = "Short press release"
        not_truncated = service._truncate_press_release(short_text, max_length=100)
        self.assertEqual(not_truncated, short_text)
    
    @patch('press_release_scorer.services.SemilatticeAPIClient')
    def test_scoring_service_full_workflow(self, mock_client):
        """Test the complete scoring workflow"""
        # Mock the API client
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        
        # Mock API response with varying scores
        def mock_send_question(*args, **kwargs):
            return {
                'answer_id': 'test-123',
                'simulated_answer_percentages': {'5': 60, '4': 25, '3': 15}
            }
        
        mock_instance.send_question.side_effect = mock_send_question
        
        service = PressReleaseScoringService()
        
        # Score the press release
        result = service.score_press_release(
            press_release_text=self.sample_press_release,
            population_id=self.population.population_id,
            user=self.user
        )
        
        # Verify results
        self.assertIsInstance(result, PressReleaseScore)
        self.assertEqual(result.total_score, 150)  # 30 questions × 5 points each
        self.assertEqual(result.created_by, self.user)
        
        # Check categories
        categories = result.category_scores.all()
        self.assertEqual(categories.count(), 5)
        
        for category in categories:
            self.assertEqual(category.score, 30)  # 6 questions × 5 points each
            
            # Check questions in each category
            questions = category.question_scores.all()
            self.assertEqual(questions.count(), 6)
            
            for question in questions:
                self.assertEqual(question.score, 5)
    
    def test_scorer_view_requires_login(self):
        """Test that scorer view requires authentication"""
        url = reverse('press_release_scorer:scorer')
        response = self.client.get(url)
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
    
    def test_scorer_view_authenticated(self):
        """Test scorer view with authenticated user"""
        self.client.login(username='testuser', password='testpass123')
        
        url = reverse('press_release_scorer:scorer')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Press Release Scorer')
        self.assertContains(response, 'Test Population')  # User's population should be in dropdown
    
    @patch('press_release_scorer.views.PressReleaseScoringService.score_press_release')
    def test_scorer_post_request(self, mock_score):
        """Test posting a press release for scoring"""
        # Mock the scoring service
        mock_score_result = PressReleaseScore.objects.create(
            press_release_text=self.sample_press_release,
            total_score=150,
            created_by=self.user
        )
        mock_score.return_value = mock_score_result
        
        self.client.login(username='testuser', password='testpass123')
        
        url = reverse('press_release_scorer:scorer')
        response = self.client.post(url, {
            'press_release_text': self.sample_press_release,
            'population': self.population.population_id
        })
        
        # Should redirect to results
        self.assertEqual(response.status_code, 302)
        self.assertIn('results', response.url)
        
        # Verify service was called
        mock_score.assert_called_once_with(
            self.sample_press_release,
            self.population.population_id,
            self.user
        )
    
    def test_results_view(self):
        """Test the results view"""
        self.client.login(username='testuser', password='testpass123')
        
        # Create test score data
        score = PressReleaseScore.objects.create(
            press_release_text=self.sample_press_release,
            total_score=150,
            created_by=self.user
        )
        
        category = CategoryScore.objects.create(
            press_release=score,
            category_name='source_credibility',
            category_display_name='Source Credibility',
            score=30
        )
        
        QuestionScore.objects.create(
            category=category,
            question_text='Test question?',
            question_number=1,
            score=5
        )
        
        url = reverse('press_release_scorer:results', args=[score.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '150/180')
        self.assertContains(response, 'Source Credibility')
        self.assertContains(response, '30/36')
    
    def test_history_view(self):
        """Test the history view"""
        self.client.login(username='testuser', password='testpass123')
        
        # Create test scores
        for i in range(3):
            PressReleaseScore.objects.create(
                press_release_text=f"Test press release {i}",
                total_score=100 + i * 10,
                created_by=self.user
            )
        
        url = reverse('press_release_scorer:history')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Press Release Scoring History')
        self.assertContains(response, '110/180')  # Should show all scores
        self.assertContains(response, '120/180')
        self.assertContains(response, '100/180')


# Sample data for manual testing
SAMPLE_PRESS_RELEASES = {
    'high_quality': """
FOR IMMEDIATE RELEASE

Mayo Clinic Publishes Groundbreaking Study on Early Alzheimer's Detection

ROCHESTER, MN - September 20, 2025 - Mayo Clinic researchers have published a peer-reviewed study in Nature Medicine demonstrating a new blood test that can detect Alzheimer's disease 15 years before symptoms appear, with 96% accuracy across diverse populations.

The study, led by Dr. Michelle Rodriguez, analyzed blood samples from 12,000 participants over 20 years. "This represents the most significant advance in Alzheimer's early detection in decades," said Dr. Rodriguez, who heads Mayo's Neurodegenerative Disease Research Center.

Key findings include:
- 96% accuracy in detecting early-stage biomarkers
- Test works across all ethnic groups and ages 50-85
- Results available in 24 hours vs. weeks for current tests
- Cost estimated at $200 vs. $3,000 for brain imaging

The research was funded by the National Institute on Aging and involved collaboration with Johns Hopkins, Stanford, and the University of Cambridge. Clinical validation included participants from the Mayo Clinic Study of Aging, with independent verification by three external laboratories.

Dr. James Patterson, Director of the Alzheimer's Association Research Division (not involved in the study), called the results "tremendously promising but requiring broader validation before clinical implementation."

Mayo Clinic plans to submit for FDA approval in Q1 2026, with pilot programs beginning at Mayo locations. The clinic has no commercial interests in the test development.

Contact: Mayo Clinic Media Relations, 507-284-5005, newsbureau@mayo.edu
""",
    
    'medium_quality': """
FOR IMMEDIATE RELEASE

LocalTech Solutions Launches New Software Platform

AUSTIN, TX - September 20, 2025 - LocalTech Solutions today announced the launch of BusinessPro 2.0, a comprehensive business management software designed for small to medium enterprises.

"We're excited to bring this innovative solution to market," said CEO Mark Johnson. "BusinessPro 2.0 will help businesses streamline their operations and increase productivity."

The software includes features for accounting, inventory management, customer relationship management, and reporting. Early beta testing showed positive feedback from 50 local businesses.

BusinessPro 2.0 is available starting at $99/month with a 30-day free trial. The company expects the software to help businesses save time and reduce operational costs.

LocalTech Solutions has been serving the Austin business community since 2018 and has over 200 clients. The company specializes in custom software solutions and IT consulting.

For more information, visit www.localtech-solutions.com or call 512-555-0123.

Contact: info@localtech-solutions.com
""",
    
    'low_quality': """
AMAZING BREAKTHROUGH!!!

SuperCorp Discovers Cure for Aging - Scientists Stunned!

SOMEWHERE, USA - SuperCorp's revolutionary new supplement AgeAway has shown incredible results in making people look 20 years younger in just 30 days! Thousands of people are already seeing amazing transformations.

"I can't believe how young I look!" says Sarah, 55, who now looks 35 according to her friends. "This product is absolutely miraculous!"

Our proprietary blend of secret ingredients (developed by top scientists) works by activating your body's natural youth genes. Clinical studies prove it works 99.9% of the time with no side effects.

Limited time offer: Get AgeAway for only $19.99 (normally $199.99) but hurry - supplies are running out fast! Don't miss this once-in-a-lifetime opportunity to turn back the clock!

Order now by calling 1-800-AGELESS or visit our website. Results guaranteed or your money back!

*This product has not been evaluated by the FDA.
"""
}


if __name__ == '__main__':
    print("=== SAMPLE PRESS RELEASES FOR TESTING ===")
    print("\n1. HIGH QUALITY EXAMPLE:")
    print(SAMPLE_PRESS_RELEASES['high_quality'])
    print("\n2. MEDIUM QUALITY EXAMPLE:")
    print(SAMPLE_PRESS_RELEASES['medium_quality'])
    print("\n3. LOW QUALITY EXAMPLE:")
    print(SAMPLE_PRESS_RELEASES['low_quality'])
