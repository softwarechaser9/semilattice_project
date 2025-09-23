from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import logging

from qa_app.models import Population
from .models import PressReleaseScore, CategoryScore
from .services import PressReleaseScoringService
from .constants import PRESS_RELEASE_QUESTIONS

logger = logging.getLogger(__name__)


@login_required
def press_release_scorer(request):
    """Main press release scoring page"""
    populations = Population.objects.filter(created_by=request.user).order_by('name')
    
    context = {
        'populations': populations,
        'categories': [data['display_name'] for data in PRESS_RELEASE_QUESTIONS.values()]
    }
    
    if request.method == 'POST':
        press_release_text = request.POST.get('press_release_text', '').strip()
        population_id = request.POST.get('population_id', '').strip()
        
        # Validation
        if not press_release_text:
            messages.error(request, 'Please enter the press release text.')
            return render(request, 'press_release_scorer/scorer.html', context)
        
        if not population_id:
            messages.error(request, 'Please select a population.')
            return render(request, 'press_release_scorer/scorer.html', context)
        
        if len(press_release_text) < 50:
            messages.error(request, 'Press release text should be at least 50 characters long.')
            return render(request, 'press_release_scorer/scorer.html', context)
            
        if len(press_release_text) > 999:
            messages.error(request, 'Press release text should be no more than 999 characters long.')
            return render(request, 'press_release_scorer/scorer.html', context)
        
        # Additional validation for press release content
        cleaned_text = press_release_text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        if not cleaned_text.strip():
            messages.error(request, 'Please enter valid press release content.')
            return render(request, 'press_release_scorer/scorer.html', context)
        
        # Check if population belongs to user
        try:
            population = Population.objects.get(population_id=population_id, created_by=request.user)
        except Population.DoesNotExist:
            messages.error(request, 'Invalid population selected.')
            return render(request, 'press_release_scorer/scorer.html', context)
        
        try:
            # Initialize the scoring service
            scoring_service = PressReleaseScoringService()
            
            # Start the scoring process
            logger.info(f"Starting press release analysis for user {request.user.username}")
            logger.info(f"Press release length: {len(press_release_text)} characters")
            logger.info(f"Population: {population_id}")
            messages.info(request, 'Starting press release analysis... This may take a few minutes.')
            
            # Score the press release
            logger.info("Calling score_press_release method...")
            score_result = scoring_service.score_press_release(
                press_release_text=press_release_text,
                population_id=population_id,
                user=request.user
            )
            logger.info(f"Scoring completed. Result: {score_result}")
            
            if score_result:
                success_msg = f'Press release scored successfully! Total score: {score_result.total_score}/180 ({score_result.score_percentage}%)'
                messages.success(request, success_msg)
                return redirect('press_release_scorer:results', score_id=score_result.id)
            else:
                messages.error(request, 'Failed to score the press release. Please try again.')
                
        except Exception as e:
            logger.error(f"Error in press release scoring: {e}")
            messages.error(request, 'An error occurred while scoring your press release. Please try again.')
    
    return render(request, 'press_release_scorer/scorer.html', context)


@login_required
def press_release_results(request, score_id):
    """Display press release scoring results"""
    score = get_object_or_404(PressReleaseScore, id=score_id, created_by=request.user)
    categories = CategoryScore.objects.filter(press_release=score).prefetch_related('question_scores')
    
    context = {
        'score': score,
        'categories': categories,
        'total_questions': 30,
        'max_total_score': 180,
        'max_category_score': 36
    }
    
    return render(request, 'press_release_scorer/results.html', context)


@login_required
def press_release_history(request):
    """Display user's press release scoring history"""
    scores = PressReleaseScore.objects.filter(created_by=request.user).order_by('-created_at')
    
    context = {
        'scores': scores
    }
    
    return render(request, 'press_release_scorer/history.html', context)


@login_required
@require_http_methods(["POST"])
def delete_press_release_score(request, score_id):
    """Delete a press release score"""
    score = get_object_or_404(PressReleaseScore, id=score_id, created_by=request.user)
    
    try:
        score.delete()
        messages.success(request, 'Press release score deleted successfully.')
    except Exception as e:
        logger.error(f"Error deleting press release score: {e}")
        messages.error(request, 'Failed to delete the press release score.')
    
    return redirect('press_release_scorer:history')
