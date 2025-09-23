import logging
import re
from typing import Dict, List, Optional
from qa_app.services import SemilatticeAPIClient
from .constants import get_all_questions, format_question_with_text, PRESS_RELEASE_QUESTIONS
from .models import PressReleaseScore, CategoryScore, QuestionScore

logger = logging.getLogger(__name__)


class PressReleaseScoringService:
    """Service to handle press release scoring using Semilattice API"""
    
    def __init__(self):
        self.semilattice_client = SemilatticeAPIClient()
    
    def score_press_release(self, press_release_text: str, population_id: str, user) -> Optional[PressReleaseScore]:
        """
        Score a press release using all 30 questions
        
        Args:
            press_release_text: The press release content
            population_id: Semilattice population ID to use for scoring
            user: Django user instance
            
        Returns:
            PressReleaseScore instance with all results
        """
        logger.info(f"Starting score_press_release for user {user.username}")
        try:
            # Create the main score record
            logger.info("Creating PressReleaseScore record...")
            press_release_score = PressReleaseScore.objects.create(
                press_release_text=press_release_text,
                total_score=0,  # Will update after scoring
                created_by=user
            )
            logger.info(f"Created score record with ID: {press_release_score.id}")
            
            # Get all questions
            all_questions = get_all_questions()
            logger.info(f"Retrieved {len(all_questions)} questions")
            total_score = 0
            
            # Process each category
            category_count = len(PRESS_RELEASE_QUESTIONS)
            current_category = 0
            
            for category_key, category_data in PRESS_RELEASE_QUESTIONS.items():
                current_category += 1
                logger.info(f"Processing category {current_category}/{category_count}: {category_data['display_name']}")
                category_score_obj = CategoryScore.objects.create(
                    press_release=press_release_score,
                    category_name=category_key,
                    category_display_name=category_data['display_name'],
                    score=0  # Will update after processing questions
                )
                
                category_total = 0
                
                # Process all 6 questions in the category
                questions_to_process = category_data['questions']
                question_count = len(questions_to_process)
                logger.info(f"Processing {question_count} questions for category {category_data['display_name']}")
                
                # Process each question in the category
                for i, question in enumerate(questions_to_process):
                    question_number = self._get_question_number(category_key, i)
                    progress = f"Q{question_number}/30 (Category {current_category}/{category_count})"
                    
                    logger.info(f"{progress}: Starting question - {question[:60]}...")
                    
                    # Format question with press release text (clean and truncate if needed)
                    cleaned_press_release = self._clean_press_release_text(press_release_text)
                    truncated_press_release = self._truncate_press_release(cleaned_press_release)
                    full_question = f"Please read the following press release {truncated_press_release} and consider: {question}"
                    
                    logger.debug(f"{progress}: Full question length: {len(full_question)} characters")
                    
                    # Send to Semilattice API
                    logger.info(f"{progress}: Submitting to API...")
                    score = self._get_question_score(full_question, population_id, question_number)
                    logger.info(f"{progress}: Completed with score: {score}/6")
                    
                    # Save question score (store only the base question, not the full text with press release)
                    QuestionScore.objects.create(
                        category=category_score_obj,
                        question_text=question,
                        question_number=question_number,
                        score=score
                    )
                    
                    category_total += score
                    total_score += score
                
                # Update category total
                category_score_obj.score = category_total
                category_score_obj.save()
                
                logger.info(f"Category '{category_data['display_name']}' total: {category_total}/36")
            
            # Update total score
            press_release_score.total_score = total_score
            press_release_score.save()
            
            logger.info(f"Press release scoring completed. Total: {total_score}/180")
            return press_release_score
            
        except Exception as e:
            logger.error(f"Error scoring press release: {e}")
            # Clean up if something went wrong
            if 'press_release_score' in locals():
                press_release_score.delete()
            raise
    
    def _get_question_number(self, category_key: str, question_index: int) -> int:
        """Calculate the global question number (1-30)"""
        category_order = list(PRESS_RELEASE_QUESTIONS.keys())
        category_position = category_order.index(category_key)
        return (category_position * 6) + question_index + 1
    
    def _get_question_score(self, question_text: str, population_id: str, question_number: int) -> int:
        """
        Send a single question to Semilattice and extract the 1-6 score
        
        Args:
            question_text: The full question with press release text
            population_id: Semilattice population ID
            question_number: Question number for logging (1-30)
            
        Returns:
            Integer score from 1-6
        """
        try:
            # Use single-choice question with 1-6 options
            answer_options = ["1", "2", "3", "4", "5", "6"]
            
            logger.debug(f"Question {question_number}: Preparing API call")
            
            # Submit question to Semilattice
            logger.debug(f"Question {question_number}: Calling simulate_answer")
            response = self.semilattice_client.simulate_answer(
                population_id=population_id,
                question=question_text,
                question_type="single-choice",
                answer_options=answer_options
            )
            
            logger.debug(f"Question {question_number}: API response received: {response}")
            
            if response and response.get('success'):
                answer_id = response.get('answer_id')
                logger.debug(f"Question {question_number}: Got answer_id: {answer_id}")
                
                # Poll for results with progress tracking
                logger.info(f"Question {question_number}: Starting polling (max 2 minutes)...")
                result = self.semilattice_client.poll_until_complete(
                    answer_id=answer_id,
                    max_wait_seconds=120  # Increased to 2 minutes for production
                )
                
                logger.debug(f"Question {question_number}: Polling completed: {result}")
                
                if result and result.get('success'):
                    if result.get('status') == 'Predicted':
                        # Extract score from response
                        score = self._extract_score_from_response(result)
                        logger.info(f"Question {question_number} scored: {score}/6")
                        return score
                    else:
                        logger.warning(f"Question {question_number} completed but status is {result.get('status')}: {result}")
                        return 3  # Default middle score if status is not 'Predicted'
                else:
                    error_msg = result.get('error', 'Unknown polling error') if isinstance(result, dict) else str(result)
                    logger.error(f"Question {question_number} polling failed: {error_msg}")
                    if 'Timeout' in error_msg:
                        logger.error(f"Question {question_number}: Consider increasing timeout - simulation may need more time")
                    return 3  # Default middle score if polling fails
            else:
                error_msg = response.get('error', 'Unknown error') if isinstance(response, dict) else str(response)
                logger.error(f"Failed to submit question {question_number}: {error_msg}")
                return 3  # Default middle score if API fails
                
        except Exception as e:
            logger.error(f"Error getting question score: {e}")
            return 3  # Default middle score if error occurs
    
    def _clean_press_release_text(self, text: str) -> str:
        """
        Clean press release text to remove newlines, tabs, and excessive whitespace
        that would cause API errors
        
        Args:
            text: The original press release text
            
        Returns:
            Cleaned text safe for API submission
        """
        # Replace newlines and tabs with spaces
        cleaned = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        
        # Replace multiple consecutive spaces with single spaces
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Strip leading/trailing whitespace
        cleaned = cleaned.strip()
        
        return cleaned
    
    def _truncate_press_release(self, press_release_text: str, max_length: int = 800) -> str:
        """
        Truncate press release text if it's too long to avoid API character limits
        
        Args:
            press_release_text: The full press release text
            max_length: Maximum allowed length (default 800 chars)
            
        Returns:
            Truncated text with ellipsis if needed
        """
        if len(press_release_text) <= max_length:
            return press_release_text
        
        # Truncate and add ellipsis
        truncated = press_release_text[:max_length].rsplit(' ', 1)[0]  # Don't cut words
        return truncated + "..."
    
    def _extract_score_from_response(self, api_response: Dict) -> int:
        """
        Extract the 1-6 score from Semilattice API response
        
        Args:
            api_response: The API response dictionary
            
        Returns:
            Integer score from 1-6
        """
        try:
            # Get the simulated percentages
            percentages = api_response.get('simulated_answer_percentages', {})
            
            if not percentages:
                logger.warning("No simulated_answer_percentages in response")
                return 3
            
            # Find the option with the highest percentage
            max_percentage = 0
            winning_score = 3
            
            for option, percentage in percentages.items():
                if percentage > max_percentage:
                    max_percentage = percentage
                    try:
                        winning_score = int(option)
                    except (ValueError, TypeError):
                        logger.warning(f"Could not parse score from option: {option}")
                        winning_score = 3
            
            # Ensure score is in valid range
            if 1 <= winning_score <= 6:
                return winning_score
            else:
                logger.warning(f"Score out of range: {winning_score}, defaulting to 3")
                return 3
                
        except Exception as e:
            logger.error(f"Error extracting score from response: {e}")
            return 3
