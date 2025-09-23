from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
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
            
            # Start the scoring process with detailed logging
            logger.info(f"=== PRESS RELEASE SCORING STARTED ===")
            logger.info(f"User: {request.user.username} (ID: {request.user.id})")
            logger.info(f"Press release length: {len(press_release_text)} characters")
            logger.info(f"Population ID: {population_id}")
            logger.info(f"Population Name: {population.name}")
            logger.info(f"Timestamp: {timezone.now()}")
            
            messages.info(request, 'Starting press release analysis... This will take about 10-30 minutes for all 30 questions.')
            
            # Score the press release
            logger.info("🚀 Calling score_press_release method...")
            score_result = scoring_service.score_press_release(
                press_release_text=press_release_text,
                population_id=population_id,
                user=request.user
            )
            
            if score_result:
                logger.info(f"✅ SCORING COMPLETED SUCCESSFULLY!")
                logger.info(f"Final Score: {score_result.total_score}/180 ({score_result.score_percentage}%)")
                logger.info(f"Score ID: {score_result.id}")
                logger.info(f"=== PRESS RELEASE SCORING FINISHED ===")
                
                success_msg = f'Press release scored successfully! Total score: {score_result.total_score}/180 ({score_result.score_percentage}%)'
                messages.success(request, success_msg)
                return redirect('press_release_scorer:results', score_id=score_result.id)
            else:
                logger.error(f"❌ SCORING FAILED - No result returned")
                logger.error(f"=== PRESS RELEASE SCORING FAILED ===")
                messages.error(request, 'Failed to score the press release. Please try again.')
                
        except Exception as e:
            logger.error(f"Error in press release scoring: {e}")
            messages.error(request, 'An error occurred while scoring your press release. Please try again.')
    
    return render(request, 'press_release_scorer/scorer.html', context)


@login_required
def press_release_results(request, score_id):
    """Display press release scoring results"""
    logger.info(f"=== PRESS RELEASE RESULTS VIEW ACCESSED ===")
    logger.info(f"User: {request.user.username} (ID: {request.user.id})")
    logger.info(f"Requested Score ID: {score_id}")
    logger.info(f"Timestamp: {timezone.now()}")
    
    try:
        score = get_object_or_404(PressReleaseScore, id=score_id, created_by=request.user)
        logger.info(f"✅ Score found - ID: {score.id}")
        logger.info(f"📊 Press Release Details:")
        logger.info(f"   - Created: {score.created_at}")
        logger.info(f"   - Population: {score.population.name} (ID: {score.population.population_id})")
        logger.info(f"   - Total Score: {score.total_score}/180 ({score.score_percentage}%)")
        logger.info(f"   - Press Release Preview: {score.press_release_text[:100]}...")
        
        categories = CategoryScore.objects.filter(press_release=score).prefetch_related('question_scores')
        logger.info(f"📋 Categories loaded: {categories.count()}")
        
        # Log detailed category breakdown
        for i, category in enumerate(categories, 1):
            question_count = category.question_scores.count()
            logger.info(f"   Category {i}: {category.category_name}")
            logger.info(f"      - Score: {category.category_score}/36")
            logger.info(f"      - Questions: {question_count}")
            
            # Log individual question scores for this category
            for j, question_score in enumerate(category.question_scores.all(), 1):
                logger.info(f"         Q{j}: {question_score.score}/6 - {question_score.question_text[:50]}...")
        
        context = {
            'score': score,
            'categories': categories,
            'total_questions': 30,
            'max_total_score': 180,
            'max_category_score': 36
        }
        
        logger.info(f"🎯 Context prepared successfully")
        logger.info(f"=== PRESS RELEASE RESULTS VIEW COMPLETED ===")
        
        return render(request, 'press_release_scorer/results.html', context)
        
    except Exception as e:
        logger.error(f"❌ Error in press_release_results view: {e}")
        logger.error(f"=== PRESS RELEASE RESULTS VIEW FAILED ===")
        messages.error(request, 'Error loading results. Please try again.')
        return redirect('press_release_scorer:history')


@login_required
def press_release_history(request):
    """Display user's press release scoring history"""
    logger.info(f"=== PRESS RELEASE HISTORY VIEW ACCESSED ===")
    logger.info(f"User: {request.user.username} (ID: {request.user.id})")
    logger.info(f"Timestamp: {timezone.now()}")
    
    try:
        scores = PressReleaseScore.objects.filter(created_by=request.user).order_by('-created_at')
        score_count = scores.count()
        logger.info(f"📊 Found {score_count} press release scores for user")
        
        # Log summary of each score
        for i, score in enumerate(scores[:10], 1):  # Log first 10 for brevity
            logger.info(f"   Score {i}: ID={score.id}, Total={score.total_score}/180, Created={score.created_at}")
        
        if score_count > 10:
            logger.info(f"   ... and {score_count - 10} more scores")
        
        context = {
            'scores': scores
        }
        
        logger.info(f"✅ History context prepared successfully")
        logger.info(f"=== PRESS RELEASE HISTORY VIEW COMPLETED ===")
        
        return render(request, 'press_release_scorer/history.html', context)
        
    except Exception as e:
        logger.error(f"❌ Error in press_release_history view: {e}")
        logger.error(f"=== PRESS RELEASE HISTORY VIEW FAILED ===")
        messages.error(request, 'Error loading history. Please try again.')
        return render(request, 'press_release_scorer/history.html', {'scores': []})


@login_required
@require_http_methods(["POST"])
def delete_press_release_score(request, score_id):
    """Delete a press release score"""
    logger.info(f"=== PRESS RELEASE SCORE DELETE REQUESTED ===")
    logger.info(f"User: {request.user.username} (ID: {request.user.id})")
    logger.info(f"Score ID to delete: {score_id}")
    logger.info(f"Timestamp: {timezone.now()}")
    
    try:
        score = get_object_or_404(PressReleaseScore, id=score_id, created_by=request.user)
        logger.info(f"✅ Score found - preparing to delete")
        logger.info(f"   - Score Total: {score.total_score}/180")
        logger.info(f"   - Created: {score.created_at}")
        logger.info(f"   - Population: {score.population.name}")
        
        score.delete()
        logger.info(f"🗑️ Score deleted successfully")
        logger.info(f"=== PRESS RELEASE SCORE DELETE COMPLETED ===")
        messages.success(request, 'Press release score deleted successfully.')
        
    except Exception as e:
        logger.error(f"❌ Error deleting press release score: {e}")
        logger.error(f"=== PRESS RELEASE SCORE DELETE FAILED ===")
        messages.error(request, 'Failed to delete the press release score.')
    
    return redirect('press_release_scorer:history')
