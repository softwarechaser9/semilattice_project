"""
Helper functions for database-driven question management
"""
from typing import Dict, List, Optional, Tuple
from .models import PressReleaseQuestionCategory, PressReleaseQuestion


def get_all_questions_from_db() -> List[Dict]:
    """
    Returns a list of all active questions from database with metadata
    
    Returns:
        List of dictionaries with question data compatible with existing code
    """
    questions = []
    question_number = 1
    
    # Get all categories in order
    categories = PressReleaseQuestionCategory.objects.all().order_by('order', 'display_name')
    
    for category in categories:
        # Get all active questions in this category
        category_questions = category.questions.filter(is_active=True).order_by('order')
        
        for question in category_questions:
            questions.append({
                'number': question_number,
                'category_key': category.category_key,
                'category_display': category.display_name,
                'question': question.question_text,
                'question_id': question.id,
                'full_question_template': question.get_full_question_template()
            })
            question_number += 1
    
    return questions


def get_questions_by_category_from_db() -> Dict[str, Dict]:
    """
    Returns questions organized by category (compatible with PRESS_RELEASE_QUESTIONS format)
    
    Returns:
        Dictionary with category structure matching constants.py format
    """
    categories_dict = {}
    
    categories = PressReleaseQuestionCategory.objects.all().order_by('order', 'display_name')
    
    for category in categories:
        questions_list = []
        category_questions = category.questions.filter(is_active=True).order_by('order')
        
        for question in category_questions:
            questions_list.append(question.question_text)
        
        categories_dict[category.category_key] = {
            'display_name': category.display_name,
            'questions': questions_list
        }
    
    return categories_dict


def format_question_with_text_from_db(question_text: str, press_release_text: str) -> str:
    """
    Insert press release text into question template
    Compatible with existing format_question_with_text function
    """
    return f"Please read the following press release {press_release_text} and consider: {question_text}"


def get_question_by_number(question_number: int) -> Optional[PressReleaseQuestion]:
    """
    Get a specific question by its global number (1-30)
    
    Args:
        question_number: Global question number (1-30)
        
    Returns:
        PressReleaseQuestion instance or None if not found
    """
    current_number = 1
    
    categories = PressReleaseQuestionCategory.objects.all().order_by('order', 'display_name')
    
    for category in categories:
        category_questions = category.questions.filter(is_active=True).order_by('order')
        
        for question in category_questions:
            if current_number == question_number:
                return question
            current_number += 1
    
    return None


def get_total_active_questions_count() -> int:
    """
    Get the total number of active questions across all categories
    """
    return PressReleaseQuestion.objects.filter(is_active=True).count()


def validate_question_setup() -> Tuple[bool, List[str]]:
    """
    Validate that the question setup is correct (30 questions, proper ordering, etc.)
    
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []
    
    # Check total question count
    total_questions = get_total_active_questions_count()
    if total_questions != 30:
        issues.append(f"Expected 30 active questions, found {total_questions}")
    
    # Check category setup
    categories = PressReleaseQuestionCategory.objects.all().order_by('order')
    if categories.count() != 5:
        issues.append(f"Expected 5 categories, found {categories.count()}")
    
    # Check questions per category
    for category in categories:
        question_count = category.questions.filter(is_active=True).count()
        if question_count != 6:
            issues.append(f"Category '{category.display_name}' has {question_count} questions, expected 6")
    
    # Check for gaps in ordering within categories
    for category in categories:
        questions = category.questions.filter(is_active=True).order_by('order')
        expected_order = 1
        for question in questions:
            if question.order != expected_order:
                issues.append(f"Category '{category.display_name}' has ordering gap: found order {question.order}, expected {expected_order}")
            expected_order += 1
    
    return len(issues) == 0, issues
