from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
import logging

from qa_app.models import Population
from .models import HeadlineTest, AlternativeHeadline, HeadlineScore
from .services import HeadlineTestingService

logger = logging.getLogger(__name__)


@login_required
def headline_input(request):
    """Main headline tester input page"""
    if request.method == 'POST':
        # Get form data
        original_headline = request.POST.get('original_headline', '').strip()
        context_url = request.POST.get('context_url', '').strip() or None
        population_id = request.POST.get('population_id', '').strip()
        
        # Validate input
        if not original_headline:
            messages.error(request, 'Please enter a headline to test.')
            return redirect('headline_tester:input')
        
        if len(original_headline) > 500:
            messages.error(request, 'Headline must be 500 characters or less.')
            return redirect('headline_tester:input')
        
        if not population_id:
            messages.error(request, 'Please select a population to test against.')
            return redirect('headline_tester:input')
        
        # Verify population belongs to user
        try:
            Population.objects.get(population_id=population_id, created_by=request.user)
        except Population.DoesNotExist:
            messages.error(request, 'Selected population not found.')
            return redirect('headline_tester:input')
        
        try:
            # Start the headline test
            service = HeadlineTestingService()
            test = service.start_test(
                original_headline=original_headline,
                context_url=context_url,
                population_id=population_id,
                user=request.user
            )
            
            messages.success(request, 'Headline test started! Generating alternatives...')
            return redirect('headline_tester:progress', test_id=test.id)
            
        except Exception as e:
            logger.error(f"Error starting headline test: {e}")
            messages.error(request, f'Failed to start headline test: {str(e)}')
            return redirect('headline_tester:input')
    
    # GET request - show the form
    populations = Population.objects.filter(created_by=request.user).order_by('-created_at')
    
    context = {
        'populations': populations,
        'page_title': 'Headline Tester',
        'max_headline_length': 500,
    }
    
    return render(request, 'headline_tester/input.html', context)


@login_required
def test_progress(request, test_id):
    """Show test progress page with real-time updates"""
    test = get_object_or_404(HeadlineTest, id=test_id, created_by=request.user)
    
    context = {
        'test': test,
        'page_title': f'Testing Headlines - {test.original_headline[:50]}...',
    }
    
    return render(request, 'headline_tester/progress.html', context)


@login_required
def get_progress_ajax(request, test_id):
    """AJAX endpoint for getting test progress"""
    test = get_object_or_404(HeadlineTest, id=test_id, created_by=request.user)
    
    try:
        service = HeadlineTestingService()
        progress_data = service.get_test_progress(test_id)
        
        # Add headline details
        headlines_status = []
        
        # Original headline
        original_score = test.scores.filter(is_original=True).first()
        headlines_status.append({
            'text': test.original_headline,
            'type': 'Original',
            'status': original_score.status if original_score else 'pending',
            'score': original_score.total_score if original_score and original_score.total_score else None
        })
        
        # Alternative headlines
        for alt in test.alternatives.all():
            alt_score = test.scores.filter(alternative=alt).first()
            headlines_status.append({
                'text': alt.headline_text,
                'type': f'Alternative {alt.order} ({alt.get_angle_type_display()})',
                'status': alt_score.status if alt_score else 'pending',
                'score': alt_score.total_score if alt_score and alt_score.total_score else None
            })
        
        progress_data['headlines_status'] = headlines_status
        
        return JsonResponse(progress_data)
        
    except Exception as e:
        logger.error(f"Error getting progress for test {test_id}: {e}")
        return JsonResponse({'status': 'error', 'error_message': str(e)})


@login_required
def test_results(request, test_id):
    """Display test results with headline comparison"""
    test = get_object_or_404(HeadlineTest, id=test_id, created_by=request.user)
    
    # Get population display name
    try:
        population = Population.objects.get(
            population_id=test.population_id,
            created_by=request.user
        )
        test._population_display_name = f"{population.name} ({test.population_id})"
    except Population.DoesNotExist:
        test._population_display_name = test.population_id
    
    # Get all scores ordered by total_score (highest first)
    scores = test.scores.filter(status='completed').order_by('-total_score')
    
    results_data = []
    for score in scores:
        results_data.append({
            'score': score,
            'rank': len(results_data) + 1
        })
    
    context = {
        'test': test,
        'results_data': results_data,
        'best_score': scores.first() if scores else None,
        'page_title': f'Results - {test.original_headline[:50]}...',
    }
    
    return render(request, 'headline_tester/results.html', context)


@login_required
def detailed_breakdown(request, test_id):
    """Show detailed score breakdown by question"""
    test = get_object_or_404(HeadlineTest, id=test_id, created_by=request.user)
    
    # TODO: Implement detailed breakdown
    # This will show question-by-question comparison
    
    context = {
        'test': test,
        'page_title': f'Detailed Analysis - {test.original_headline[:50]}...',
    }
    
    return render(request, 'headline_tester/detailed.html', context)


@login_required
def test_history(request):
    """Show user's headline test history"""
    tests = HeadlineTest.objects.filter(created_by=request.user).order_by('-created_at')
    
    # Add population display names
    population_ids = [test.population_id for test in tests if test.population_id]
    if population_ids:
        populations = Population.objects.filter(
            population_id__in=population_ids,
            created_by=request.user
        )
        population_names = {pop.population_id: pop.name for pop in populations}
        
        for test in tests:
            if test.population_id and test.population_id in population_names:
                test._population_display_name = f"{population_names[test.population_id]} ({test.population_id})"
            else:
                test._population_display_name = test.population_id if test.population_id else None
    
    context = {
        'tests': tests,
        'page_title': 'Headline Test History',
    }
    
    return render(request, 'headline_tester/history.html', context)


@login_required
@require_http_methods(["POST"])
def delete_test(request, test_id):
    """Delete a headline test"""
    test = get_object_or_404(HeadlineTest, id=test_id, created_by=request.user)
    
    try:
        test.delete()
        messages.success(request, 'Headline test deleted successfully.')
    except Exception as e:
        logger.error(f"Error deleting headline test: {e}")
        messages.error(request, 'Failed to delete the headline test.')
    
    return redirect('headline_tester:history')
