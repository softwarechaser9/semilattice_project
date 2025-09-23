from django.urls import path
from . import views

app_name = 'press_release_scorer'

urlpatterns = [
    path('', views.press_release_scorer, name='scorer'),
    path('results/<int:score_id>/', views.press_release_results, name='results'),
    path('history/', views.press_release_history, name='history'),
    path('delete/<int:score_id>/', views.delete_press_release_score, name='delete'),
]
