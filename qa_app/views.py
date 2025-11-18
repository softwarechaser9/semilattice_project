from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.urls import reverse
import json
import logging

from .models import Population, Question, SimulationResult
from .services import SemilatticeAPIClient

logger = logging.getLogger(__name__)


@login_required
def home(request):
    """Home page with question form"""
    populations = Population.objects.filter(created_by=request.user).order_by('name')
    recent_questions = Question.objects.select_related('population', 'result').filter(created_by=request.user).order_by('-created_at')[:10]
    
    context = {
        'populations': populations,
        'recent_questions': recent_questions,
    }
    return render(request, 'qa_app/home.html', context)


@login_required
@require_http_methods(["POST"])
def ask_question(request):
    """Handle question submission and start Semilattice simulation"""
    try:
        # Get form data
        population_id = request.POST.get('population_id')
        question_text = request.POST.get('question')
        question_type = request.POST.get('question_type', 'single-choice')
        answer_options_text = request.POST.get('answer_options', '')
        
        if not population_id or not question_text:
            messages.error(request, 'Population and question are required.')
            return redirect('home')
        
        # Parse answer options
        answer_options = []
        if question_type in ['single-choice', 'multiple-choice'] and answer_options_text:
            answer_options = [opt.strip() for opt in answer_options_text.split('\n') if opt.strip()]
            if not answer_options:
                messages.error(request, 'Answer options are required for choice questions.')
                return redirect('home')
        
        # Get or create population (filter by current user to avoid duplicates)
        try:
            population = Population.objects.get(
                population_id=population_id,
                created_by=request.user
            )
        except Population.DoesNotExist:
            population = Population.objects.create(
                population_id=population_id,
                name=f"Population {population_id}",
                description="Auto-created population",
                created_by=request.user
            )
        
        # Create question
        question = Question.objects.create(
            population=population,
            question_text=question_text,
            question_type=question_type,
            answer_options=answer_options if answer_options else None,
            created_by=request.user if request.user.is_authenticated else None
        )
        
        # Start Semilattice simulation
        client = SemilatticeAPIClient()
        sim_result = client.simulate_answer(
            population_id=population_id,
            question=question_text,
            question_type=question_type,
            answer_options=answer_options if answer_options else None
        )
        
        if sim_result["success"]:
            # Ensure data is JSON serializable before storing
            try:
                raw_data = sim_result["data"]
                # Test JSON serialization
                json.dumps(raw_data)
                logger.info("Raw data is JSON serializable")
            except Exception as e:
                logger.error(f"Raw data not JSON serializable: {e}")
                raw_data = {"error": "Data serialization failed", "original_error": str(e)}
            
            # Create simulation result record
            SimulationResult.objects.create(
                question=question,
                answer_id=sim_result["answer_id"],
                status=sim_result["status"],  # Keep original case from API
                raw_response=raw_data
            )
            messages.success(request, 'Question submitted! Simulation in progress...')
            return redirect('question_detail', question_id=question.id)
        else:
            messages.error(request, f'Error starting simulation: {sim_result.get("error", "Unknown error")}')
            return redirect('home')
            
    except Exception as e:
        logger.error(f"Error in ask_question: {e}")
        messages.error(request, 'An error occurred while processing your question.')
        return redirect('home')


@login_required
def question_detail(request, question_id):
    """Display question and its results"""
    question = get_object_or_404(Question, id=question_id)
    
    context = {
        'question': question,
    }
    return render(request, 'qa_app/question_detail.html', context)


@csrf_exempt
@require_http_methods(["GET"])
@login_required
def poll_result(request, question_id):
    """AJAX endpoint to poll for question results"""
    try:
        question = get_object_or_404(Question, id=question_id)
        
        if not hasattr(question, 'result'):
            return JsonResponse({
                'status': 'error',
                'message': 'No simulation result found'
            })
        
        result = question.result
        client = SemilatticeAPIClient()
        
        # Poll current status
        status_result = client.get_answer_status(result.answer_id)
        
        if status_result["success"]:
            # Ensure data is JSON serializable before storing
            try:
                raw_data = status_result["raw_data"]
                # Test JSON serialization
                json.dumps(raw_data)
                logger.info("Poll result raw data is JSON serializable")
            except Exception as e:
                logger.error(f"Poll result raw data not JSON serializable: {e}")
                raw_data = {"error": "Data serialization failed in poll", "original_error": str(e)}
            
            # Update result in database
            result.status = status_result["status"]  # Keep original case from API
            result.simulated_answer_percentages = status_result["simulated_answer_percentages"]
            result.raw_response = raw_data
            result.save()
            
            return JsonResponse({
                'status': result.status,
                'is_complete': result.is_complete,
                'percentages': result.simulated_answer_percentages,
                'answer_options': question.answer_options
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': status_result.get('error', 'Unknown error')
            })
            
    except Exception as e:
        logger.error(f"Error in poll_result: {e}")
        return JsonResponse({
            'status': 'error',
            'message': 'An error occurred while polling results'
        })


@login_required
def manage_populations(request):
    """View to manage populations"""
    if request.method == 'POST':
        population_id = request.POST.get('population_id')
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        
        logger.info(f"[POPULATION] User {request.user.username} attempting to add population_id='{population_id}', name='{name}'")
        
        if population_id and name:
            try:
                # Use get_or_create for this user - now works since unique constraint is removed
                population, created = Population.objects.get_or_create(
                    population_id=population_id,
                    created_by=request.user,
                    defaults={
                        'name': name,
                        'description': description,
                    }
                )
                if created:
                    messages.success(request, f'Population "{name}" added successfully!')
                else:
                    # Update existing population for this user
                    population.name = name
                    population.description = description
                    population.save()
                    messages.success(request, f'Population "{name}" updated successfully!')
            except Exception as e:
                logger.error(f"Error adding/updating population {population_id}: {e}")
                messages.error(request, f'Error saving population: {str(e)}')
        else:
            messages.error(request, 'Population ID and name are required.')
    
    populations = Population.objects.filter(created_by=request.user).order_by('name')
    context = {'populations': populations}
    return render(request, 'qa_app/manage_populations.html', context)


@require_http_methods(["POST"])
@login_required
def delete_population(request, population_id):
    """Delete a population and all its associated questions"""
    try:
        population = get_object_or_404(Population, id=population_id)
        population_name = population.name
        question_count = population.question_set.count()
        
        # Delete the population (this will cascade delete questions and results)
        population.delete()
        
        messages.success(request, f'Population "{population_name}" and {question_count} associated question(s) deleted successfully.')
    except Exception as e:
        logger.error(f"Error deleting population {population_id}: {e}")
        messages.error(request, 'An error occurred while deleting the population.')
    
    return redirect('manage_populations')


@require_http_methods(["POST"])
@login_required
def delete_question(request, question_id):
    """Delete a specific question and its simulation result"""
    try:
        question = get_object_or_404(Question, id=question_id)
        question_text = question.question_text[:50] + "..." if len(question.question_text) > 50 else question.question_text
        population_name = question.population.name
        
        # Delete the question (this will cascade delete the simulation result due to OneToOneField)
        question.delete()
        
        messages.success(request, f'Question "{question_text}" from population "{population_name}" deleted successfully.')
        
        # Redirect to home page (ask questions)
        return redirect('home')
        
    except Exception as e:
        logger.error(f"Error deleting question {question_id}: {e}")
        messages.error(request, 'An error occurred while deleting the question.')
        return redirect('question_detail', question_id=question_id)


def user_login(request):
    """Login view"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                messages.success(request, f'Welcome back, {user.username}!')
                return redirect('home')
            else:
                messages.warning(request, 'Your account is pending approval. Please wait for an administrator to activate your account.')
        else:
            # Check if user exists but wrong password vs doesn't exist
            try:
                existing_user = User.objects.get(username=username)
                if not existing_user.is_active:
                    messages.warning(request, 'Your account is pending approval. Please wait for an administrator to activate your account.')
                else:
                    messages.error(request, 'Invalid username or password.')
            except User.DoesNotExist:
                messages.error(request, 'Invalid username or password.')
    
    return render(request, 'qa_app/login.html')


def user_signup(request):
    """Signup view"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        # Validation
        if not all([username, email, password1, password2]):
            messages.error(request, 'All fields are required.')
        elif password1 != password2:
            messages.error(request, 'Passwords do not match.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
        elif User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
        else:
            # Create user (inactive by default - needs admin approval)
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password1,
                is_active=False  # Require admin approval
            )
            messages.success(request, f'Account created successfully! Your account is pending approval. You will be able to log in once an administrator approves your account.')
            return redirect('login')
    
    return render(request, 'qa_app/signup.html')


def user_logout(request):
    """Logout view"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')
