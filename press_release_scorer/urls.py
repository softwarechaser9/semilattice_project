from django.urls import path
from . import views

app_name = 'press_release_scorer'

urlpatterns = [
    path('', views.press_release_scorer, name='scorer'),
    path('start/', views.start_scoring, name='start_scoring'),
    path('process-question/', views.process_single_question, name='process_single_question'),
    path('process-question-step/', views.process_question_step, name='process_question_step'),
    path('status/<int:score_id>/', views.score_status, name='score_status'),
    path('results/<int:score_id>/', views.press_release_results, name='results'),
    path('history/', views.press_release_history, name='history'),
    path('delete/<int:score_id>/', views.delete_press_release_score, name='delete'),
]
