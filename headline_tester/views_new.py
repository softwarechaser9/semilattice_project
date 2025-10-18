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
    """Step 1: Enter headline and context URL"""
    context = {
        'page_title': 'Headline Tester - Step 1',
        'max_headline_length': 500,
    }
    return render(request, 'headline_tester/input.html', context)


@login_required 
def generate_headlines(request):
    """Step 1: Generate 5 alternative headlines using Claude"""
    if request.method != 'POST':
        return redirect('headline_tester:input')
    
    # Get form data
    original_headline = request.POST.get('original_headline', '').strip()
    context_url = request.POST.get('context_url', '').strip() or None
    
    # Validate input
    if not original_headline:
        messages.error(request, 'Please enter a headline to test.')
        return redirect('headline_tester:input')
    
    if len(original_headline) > 500:
        messages.error(request, 'Headline must be 500 characters or less.')
        return redirect('headline_tester:input')
    
    try:
        # Generate alternatives with Claude
        service = HeadlineTestingService()
        test = service.generate_alternatives_only(
            original_headline=original_headline,
            context_url=context_url,
            user=request.user
        )
        
        messages.success(request, 'Headlines generated successfully! You can now edit them and select your audience.')
        return redirect('headline_tester:edit', test_id=test.id)
        
    except Exception as e:
        logger.error(f"Error generating headlines: {e}")
        messages.error(request, f'Failed to generate headlines: {str(e)}')
        return redirect('headline_tester:input')


@login_required
def edit_headlines(request, test_id):
    """Step 2: Edit generated headlines and select audience"""
    test = get_object_or_404(HeadlineTest, id=test_id, created_by=request.user)
    
    if test.status != 'generated':
        messages.error(request, 'This test is not available for editing.')
        return redirect('headline_tester:input')
    
    # Get populations for selection
    populations = Population.objects.filter(created_by=request.user).order_by('-created_at')
    
    context = {
        'test': test,
        'populations': populations,
        'page_title': f'Edit Headlines - {test.original_headline[:50]}...',
    }
    
    return render(request, 'headline_tester/edit.html', context)


@login_required
def update_headlines(request, test_id):
    """Update headline texts before testing"""
    if request.method != 'POST':
        return redirect('headline_tester:input')
    
    test = get_object_or_404(HeadlineTest, id=test_id, created_by=request.user)
    
    if test.status != 'generated':
        messages.error(request, 'This test is not available for editing.')
        return redirect('headline_tester:input')
    
    try:
        # Update alternative headlines
        for alternative in test.alternatives.all():
            field_name = f'headline_{alternative.id}'
            new_text = request.POST.get(field_name, '').strip()
            if new_text and len(new_text) <= 500:
                alternative.headline_text = new_text
                alternative.save()
        
        messages.success(request, 'Headlines updated successfully!')
        return redirect('headline_tester:edit', test_id=test.id)
        
    except Exception as e:
        logger.error(f"Error updating headlines: {e}")
        messages.error(request, f'Failed to update headlines: {str(e)}')
        return redirect('headline_tester:edit', test_id=test.id)


@login_required
def start_audience_test(request, test_id):
    """Step 3: Start audience testing with Semilattice"""
    if request.method != 'POST':
        return redirect('headline_tester:input')
    
    test = get_object_or_404(HeadlineTest, id=test_id, created_by=request.user)
    population_id = request.POST.get('population_id', '').strip()
    
    if test.status != 'generated':
        messages.error(request, 'This test is not ready for audience testing.')
        return redirect('headline_tester:input')
    
    if not population_id:
        messages.error(request, 'Please select an audience to test against.')
        return redirect('headline_tester:edit', test_id=test.id)
    
    # Verify population belongs to user
    try:
        Population.objects.get(population_id=population_id, created_by=request.user)
    except Population.DoesNotExist:
        messages.error(request, 'Selected audience not found.')
        return redirect('headline_tester:edit', test_id=test.id)
    
    try:
        # Start audience testing
        service = HeadlineTestingService()
        test = service.start_audience_testing(test, population_id)
        
        messages.success(request, 'Audience testing started! Please wait for results...')
        return redirect('headline_tester:progress', test_id=test.id)
        
    except Exception as e:
        logger.error(f"Error starting audience test: {e}")
        messages.error(request, f'Failed to start audience testing: {str(e)}')
        return redirect('headline_tester:edit', test_id=test.id)


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
        population_dict = {p.population_id: p.name for p in populations}
        
        for test in tests:
            if test.population_id and test.population_id in population_dict:
                test._population_display_name = f"{population_dict[test.population_id]} ({test.population_id})"
            else:
                test._population_display_name = test.population_id or "No audience selected"
    
    context = {
        'tests': tests,
        'page_title': 'Headline Test History',
    }
    
    return render(request, 'headline_tester/history.html', context)
