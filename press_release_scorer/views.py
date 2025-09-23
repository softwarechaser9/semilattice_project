from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseBadRequest
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
        # Prevent long-running sync processing on Render; front-end uses async endpoints instead
        messages.error(request, 'Long-running sync scoring is disabled. Please use the button to start and wait for progress.')
        return render(request, 'press_release_scorer/scorer.html', context)
    
    return render(request, 'press_release_scorer/scorer.html', context)


@login_required
@require_http_methods(["POST"])
def start_scoring(request):
    """Start a scoring session and return a score_id for incremental processing."""
    press_release_text = request.POST.get('press_release_text', '').strip()
    population_id = request.POST.get('population_id', '').strip()
    logger.info(f"[START] User={request.user.username} starting scoring. Pop={population_id}")
    
    # Validation
    if not press_release_text or not population_id:
        return JsonResponse({'success': False, 'error': 'press_release_text and population_id are required.'}, status=400)
    if len(press_release_text) < 50 or len(press_release_text) > 999:
        return JsonResponse({'success': False, 'error': 'Press release must be between 50 and 999 characters.'}, status=400)
    cleaned_text = press_release_text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ').strip()
    if not cleaned_text:
        return JsonResponse({'success': False, 'error': 'Invalid press release content.'}, status=400)
    
    try:
        population = Population.objects.get(population_id=population_id, created_by=request.user)
    except Population.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Invalid population selected.'}, status=400)
    
    # Create the score shell
    score = PressReleaseScore.objects.create(
        press_release_text=cleaned_text,
        total_score=0,
        created_by=request.user,
        population_id=population_id,
        status='running',
        processed_questions=0,
    )
    logger.info(f"[START] Created score_id={score.id}")
    
    return JsonResponse({'success': True, 'score_id': score.id})


@login_required
@require_http_methods(["POST"])
def process_single_question(request):
    """Process a single question (1..30) for a given score_id."""
    try:
        score_id = int(request.POST.get('score_id'))
        question_number = int(request.POST.get('question_number'))
    except (TypeError, ValueError):
        return JsonResponse({'success': False, 'error': 'score_id and question_number are required integers.'}, status=400)
    
    score = get_object_or_404(PressReleaseScore, id=score_id, created_by=request.user)
    if score.status in ['failed', 'done'] and score.processed_questions >= question_number:
        return JsonResponse({'success': True, 'already_done': True, 'total_score': score.total_score, 'processed_questions': score.processed_questions, 'status': score.status})
    
    service = PressReleaseScoringService()
    try:
        result_score = service.score_single_question(score, question_number)
        # Refresh
        score.refresh_from_db()
        return JsonResponse({
            'success': True,
            'question_score': result_score,
            'total_score': score.total_score,
            'processed_questions': score.processed_questions,
            'status': score.status,
        })
    except Exception as e:
        logger.error(f"[INC] Error processing Q{question_number} for score {score_id}: {e}")
        score.status = 'failed'
        score.error_message = str(e)
        score.save(update_fields=['status', 'error_message'])
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def score_status(request, score_id):
    """Return current status of a scoring session."""
    score = get_object_or_404(PressReleaseScore, id=score_id, created_by=request.user)
    return JsonResponse({
        'success': True,
        'status': score.status,
        'processed_questions': score.processed_questions,
        'total_score': score.total_score,
        'score_percentage': round((score.total_score / 180) * 100, 1) if score.total_score else 0,
    })


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
