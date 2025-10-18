import anthropic
import logging
import json
import re
from django.conf import settings
from django.utils import timezone
from .models import HeadlineTest, AlternativeHeadline, HeadlineScore
from qa_app.services import SemilatticeAPIClient

logger = logging.getLogger(__name__)


class ClaudeService:
    """Service for integrating with Claude API to generate alternative headlines"""
    
    def __init__(self):
        self.client = anthropic.Anthropic(
            api_key=settings.ANTHROPIC_API_KEY
        )
    
    def generate_headlines(self, original_headline, context_url=None):
        """
        Generate 5 alternative headlines using Claude API
        
        Args:
            original_headline (str): The original headline to improve
            context_url (str, optional): URL for additional context
            
        Returns:
            list: List of dictionaries with headline data
        """
        try:
            # Build the prompt
            user_message = self._build_prompt(original_headline, context_url)
            
            # Call Claude API
            message = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=20000,
                temperature=1.0,
                system="PR expert providing 5 suggestions on alternative headlines",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": user_message
                            }
                        ]
                    }
                ]
            )
            
            # Parse the response
            response_text = message.content[0].text
            headlines = self._parse_headlines(response_text)
            
            logger.info(f"Claude generated {len(headlines)} headlines for: {original_headline[:50]}...")
            return headlines
            
        except Exception as e:
            logger.error(f"Error generating headlines with Claude: {e}")
            raise Exception(f"Failed to generate headlines: {str(e)}")
    
    def _build_prompt(self, original_headline, context_url=None):
        """Build the complete prompt for Claude"""
        
        prompt = f'''<?xml version="1.0" encoding="UTF-8"?>
<pr_expert_system>
  <role>
    <title>Seasoned Broadcast PR Professional</title>
    <experience>15+ years with major UK broadcasters</experience>
    <outlets>BBC, ITV, Sky News, Channel 4</outlets>
    <approach>Provide expert feedback and actionable recommendations rather than rewriting releases</approach>
  </role>

  <expertise>
    <skill>Understanding what makes stories compelling for broadcast journalists</skill>
    <skill>Identifying structural weaknesses and opportunities in press releases</skill>
    <skill>Recognizing strong soundbites and visual opportunities</skill>
    <skill>Advising on how to structure releases for maximum impact</skill>
    <skill>Knowing the difference between print and broadcast storytelling</skill>
  </expertise>

  <critical_rules>
    <rule priority="highest">
      <name>NEVER alter or invent factual information</name>
      <description>All recommendations must preserve facts, figures, dates, names, statistics, and substantive claims exactly as provided</description>
    </rule>
    <rule priority="highest">
      <name>Think deeply before responding</name>
      <description>Take time to carefully analyze the release, consider multiple angles, and craft thoughtful recommendations rather than rushing to the first idea</description>
    </rule>
    <rule priority="highest">
      <name>Recommend improvements to presentation, not substance</name>
      <description>Advise on HOW information is communicated, not WHAT is communicated</description>
    </rule>
  </critical_rules>

  <headline_analysis>
    <instruction>When provided with a press release headline, analyze it and provide 5 alternative headlines</instruction>
    
    <analysis_criteria>
      <criterion>Does it lead with the most newsworthy element?</criterion>
      <criterion>Is it concrete and specific rather than vague?</criterion>
      <criterion>Does it avoid jargon and corporate speak?</criterion>
      <criterion>Would it work as a broadcast intro?</criterion>
      <criterion>Does it create immediate interest?</criterion>
    </analysis_criteria>
    
    <alternative_headlines>
      <headline number="1">
        <angle>Hard news angle</angle>
        <focus>Emphasizing impact, scale, or timeliness</focus>
      </headline>
      <headline number="2">
        <angle>Human interest angle</angle>
        <focus>Focusing on people affected</focus>
      </headline>
      <headline number="3">
        <angle>Conflict/controversy angle</angle>
        <focus>Highlighting tension or debate (if applicable)</focus>
      </headline>
      <headline number="4">
        <angle>Local angle</angle>
        <focus>Emphasizing regional impact (if relevant)</focus>
      </headline>
      <headline number="5">
        <angle>Trend/bigger picture angle</angle>
        <focus>Connecting to wider issues</focus>
      </headline>
    </alternative_headlines>
    
    <output_format>
      <instruction>Provide ONLY the 5 alternative headlines without rationale or explanation</instruction>
      <instruction>Number each headline clearly (1-5)</instruction>
      <instruction>Keep headlines concise and broadcast-ready</instruction>
      <instruction>Preserve all factual accuracy from the original</instruction>
    </output_format>
  </headline_analysis>
</pr_expert_system>

ORIGINAL HEADLINE: "{original_headline}"'''

        if context_url:
            prompt += f'\nCONTEXT URL: {context_url}'
            
        prompt += '\n\nPlease provide 5 alternative headlines numbered 1-5:'
        
        return prompt
    
    def _parse_headlines(self, response_text):
        """Parse Claude's response to extract the 5 headlines"""
        headlines = []
        
        # Define angle mapping
        angle_mapping = {
            1: 'hard_news',
            2: 'human_interest', 
            3: 'conflict_controversy',
            4: 'local_angle',
            5: 'trend_bigger_picture'
        }
        
        # Split response into lines and look for numbered headlines
        lines = response_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Look for numbered headlines (1., 2., etc.)
            match = re.match(r'^(\d+)\.?\s*(.+)$', line)
            if match:
                number = int(match.group(1))
                headline_text = match.group(2).strip()
                
                # Remove quotes if present
                headline_text = headline_text.strip('"\'')
                
                if 1 <= number <= 5 and headline_text:
                    headlines.append({
                        'order': number,
                        'headline_text': headline_text,
                        'angle_type': angle_mapping.get(number, 'hard_news'),
                        'claude_description': f"Generated as {angle_mapping.get(number, 'unknown')} approach"
                    })
        
        # Sort by order and return
        headlines.sort(key=lambda x: x['order'])
        
        if len(headlines) != 5:
            logger.warning(f"Expected 5 headlines, got {len(headlines)}. Response: {response_text}")
        
        return headlines[:5]  # Ensure we only return max 5


class HeadlineTestingService:
    """Service for orchestrating headline testing workflow"""
    
    def __init__(self):
        self.claude_service = ClaudeService()
    
    def generate_alternatives_only(self, original_headline, context_url, user):
        """
        Just generate alternative headlines using Claude (Step 1)
        
        Args:
            original_headline (str): Original headline to improve
            context_url (str, optional): URL for additional context
            user: Django User object
            
        Returns:
            HeadlineTest: Created test instance with alternatives
        """
        try:
            # Create the test record
            test = HeadlineTest.objects.create(
                original_headline=original_headline,
                context_url=context_url,
                created_by=user,
                status='generated'  # New status for generated but not tested
            )
            
            logger.info(f"Started headline generation {test.id} for user {user.username}")
            
            # Generate alternatives with Claude
            self._generate_alternatives(test)
            
            return test
            
        except Exception as e:
            logger.error(f"Error generating headlines: {e}")
            if 'test' in locals():
                test.status = 'failed'
                test.error_message = str(e)
                test.save()
            raise
    
    def start_audience_testing(self, test, population_id):
        """
        Start Semilattice testing for an existing test with generated headlines (Step 2)
        
        Args:
            test: HeadlineTest instance with generated alternatives
            population_id (str): Semilattice population ID
            
        Returns:
            HeadlineTest: Updated test instance
        """
        try:
            # Update test with population and status
            test.population_id = population_id
            test.status = 'testing'
            test.save()
            
            logger.info(f"Started audience testing {test.id} with population {population_id}")
            
            # Start Semilattice testing
            self._start_semilattice_testing(test)
            
            return test
            
        except Exception as e:
            logger.error(f"Error starting audience testing for test {test.id}: {e}")
            test.status = 'failed'
            test.error_message = f"Failed to start testing: {str(e)}"
            test.save()
            raise
    
    def _generate_alternatives(self, test):
        """Generate alternative headlines using Claude"""
        try:
            headlines = self.claude_service.generate_headlines(
                test.original_headline, 
                test.context_url
            )
            
            # Save alternatives to database
            for headline_data in headlines:
                AlternativeHeadline.objects.create(
                    test=test,
                    headline_text=headline_data['headline_text'],
                    angle_type=headline_data['angle_type'],
                    claude_description=headline_data['claude_description'],
                    order=headline_data['order']
                )
            
            logger.info(f"Saved {len(headlines)} alternatives for test {test.id}")
            
        except Exception as e:
            logger.error(f"Error generating alternatives for test {test.id}: {e}")
            raise
    
    def _start_semilattice_testing(self, test):
        """Start Semilattice testing for alternative headlines only"""
        try:
            # Create score records only for alternatives (not original)
            for alternative in test.alternatives.all():
                HeadlineScore.objects.create(
                    test=test,
                    headline_text=alternative.headline_text,
                    is_original=False,
                    alternative=alternative,
                    status='pending'
                )
            
            logger.info(f"Created {test.scores.count()} score records for test {test.id}")
            
            # Start actual Semilattice testing for each headline
            self._test_headlines_with_semilattice(test)
            
        except Exception as e:
            logger.error(f"Error starting Semilattice testing for test {test.id}: {e}")
            test.status = 'failed'
            test.error_message = f"Failed to start testing: {str(e)}"
            test.save()
            raise
    
    def _test_headlines_with_semilattice(self, test):
        """Test each headline directly with Semilattice - simple preference testing"""
        semilattice_client = SemilatticeAPIClient()
        
        # Test each headline score record
        for score_record in test.scores.filter(status='pending'):
            try:
                self._test_single_headline_simple(score_record, semilattice_client, test.population_id)
            except Exception as e:
                logger.error(f"Error testing headline {score_record.id}: {e}")
                score_record.status = 'failed'
                score_record.save()
    
    def _test_single_headline_simple(self, score_record, semilattice_client, population_id):
        """Test a single headline directly with Semilattice - preference only"""
        score_record.status = 'running'
        score_record.save()
        
        logger.info(f"Testing headline with Semilattice: {score_record.headline_text[:50]}...")
        
        try:
            # Simple preference question - no scoring, just ask for preference
            question = f"Please evaluate this headline: '{score_record.headline_text}'\n\nDo you find this headline appealing?"
            
            # Submit to Semilattice
            result = semilattice_client.simulate_answer(
                population_id=population_id,
                question=question,
                question_type='single-choice',
                answer_options=['Very Appealing', 'Appealing', 'Neutral', 'Not Appealing', 'Very Unappealing']
            )
            
            if result['success'] and result.get('answer_id'):
                logger.info(f"Question submitted. Answer ID: {result['answer_id']}")
                
                # Poll for completion
                poll_result = semilattice_client.poll_until_complete(
                    answer_id=result['answer_id'],
                    max_wait_seconds=60
                )
                
                if poll_result['success'] and poll_result.get('status') == 'Predicted':
                    # Extract preference score from Semilattice response
                    preference_score = self._extract_preference_score(poll_result)
                    
                    # Save results
                    score_record.total_score = preference_score
                    score_record.detailed_scores = {
                        'preference_rating': {
                            'score': preference_score,
                            'method': 'semilattice_preference',
                            'answer_id': result['answer_id'],
                            'semilattice_data': poll_result
                        }
                    }
                    score_record.status = 'completed'
                    score_record.completed_at = timezone.now()
                    score_record.save()
                    
                    logger.info(f"Headline preference score {preference_score} for: {score_record.headline_text[:50]}...")
                else:
                    logger.error(f"Failed to get results: {poll_result}")
                    self._set_fallback_score(score_record)
            else:
                logger.error(f"Failed to submit to Semilattice: {result}")
                self._set_fallback_score(score_record)
                
        except Exception as e:
            logger.error(f"Error testing headline: {e}")
            self._set_fallback_score(score_record)
    
    def _extract_preference_score(self, semilattice_data):
        """Extract preference score from Semilattice response - convert to numeric for ranking"""
        try:
            logger.info(f"Extracting preference from: {semilattice_data}")
            
            # Preference mapping
            preference_values = {
                'Very Appealing': 5,
                'Appealing': 4,
                'Neutral': 3,
                'Not Appealing': 2,
                'Very Unappealing': 1
            }
            
            # Check if we have simulated_answer_percentages
            if isinstance(semilattice_data, dict) and 'simulated_answer_percentages' in semilattice_data:
                percentages = semilattice_data['simulated_answer_percentages']
                logger.info(f"Found answer percentages: {percentages}")
                
                if percentages and isinstance(percentages, dict):
                    # Calculate weighted average based on response percentages
                    total_score = 0
                    total_percentage = 0
                    
                    for answer, percentage in percentages.items():
                        value = preference_values.get(answer, 3)  # Default to neutral
                        weight = float(percentage)
                        total_score += value * weight
                        total_percentage += weight
                    
                    if total_percentage > 0:
                        weighted_score = total_score / total_percentage
                        logger.info(f"Calculated preference score: {weighted_score}")
                        return round(weighted_score, 2)
            
            # Fallback to neutral preference
            logger.warning(f"Could not extract preference from Semilattice data: {semilattice_data}")
            return 3.0  # Neutral
            
        except Exception as e:
            logger.error(f"Error extracting preference score: {e}")
            return 3.0  # Return neutral on error
    
    def _set_fallback_score(self, score_record):
        """Set a fallback score when Semilattice testing fails"""
        fallback_score = 3.0  # Neutral preference
        score_record.total_score = fallback_score
        score_record.detailed_scores = {
            'preference_rating': {
                'score': fallback_score,
                'method': 'fallback',
                'error': 'Failed to get Semilattice results'
            }
        }
        score_record.status = 'completed'
        score_record.completed_at = timezone.now()
        score_record.save()

    
    def get_test_progress(self, test_id):
        """Get current progress of a test"""
        try:
            test = HeadlineTest.objects.get(id=test_id)
            
            # Check if test should be marked as completed
            self._check_and_update_test_completion(test)
            
            # Calculate progress percentages
            total_scores = test.scores.count()
            completed_scores = test.scores.filter(status='completed').count()
            
            if total_scores == 0:
                semilattice_progress = 0
            else:
                semilattice_progress = round((completed_scores / total_scores) * 100)
            
            # Claude progress (either 0% or 100%)
            claude_progress = 100 if test.alternatives.exists() else 0
            
            # Overall status
            if test.status == 'completed':
                overall_progress = 100
            elif test.status == 'testing':
                overall_progress = 50 + (semilattice_progress // 2)
            elif test.status == 'generating':
                overall_progress = claude_progress // 2
            else:
                overall_progress = 0
            
            return {
                'status': test.status,
                'claude_progress': claude_progress,
                'semilattice_progress': semilattice_progress,
                'overall_progress': overall_progress,
                'total_headlines': test.total_headlines,
                'completed_headlines': completed_scores,
                'error_message': test.error_message
            }
            
        except HeadlineTest.DoesNotExist:
            return {'status': 'not_found', 'error_message': 'Test not found'}
        except Exception as e:
            logger.error(f"Error getting test progress: {e}")
            return {'status': 'error', 'error_message': str(e)}
    
    def _check_and_update_test_completion(self, test):
        """Check if test is complete and update status accordingly"""
        if test.status != 'testing':
            return
            
        # Check if all headlines have been scored
        total_scores = test.scores.count()
        completed_scores = test.scores.filter(status='completed').count()
        failed_scores = test.scores.filter(status='failed').count()
        
        # If all scores are either completed or failed
        if (completed_scores + failed_scores) >= total_scores and total_scores > 0:
            test.status = 'completed'
            test.completed_at = timezone.now()
            
            # Calculate winning headline and improvement stats
            best_score = test.scores.filter(status='completed').order_by('-total_score').first()
            if best_score:
                test.winning_headline = best_score.headline_text
                test.winning_score = best_score.total_score
                
            # Calculate improvement if we have original score
            original_score = test.scores.filter(is_original=True, status='completed').first()
            if original_score and original_score.total_score is not None:
                test.original_score = original_score.total_score
                if original_score.total_score > 0:
                    improvement = ((best_score.total_score - original_score.total_score) / original_score.total_score) * 100
                    test.improvement_percentage = round(improvement, 1)
            
            test.save()
            logger.info(f"Test {test.id} marked as completed")

