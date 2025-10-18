from django.urls import path
from . import views

app_name = 'headline_tester'

urlpatterns = [
    # Step 1: Enter headline and generate alternatives
    path('', views.headline_input, name='input'),
    path('generate/', views.generate_headlines, name='generate'),
    
    # Step 2: Edit headlines and select audience
    path('edit/<int:test_id>/', views.edit_headlines, name='edit'),
    path('update/<int:test_id>/', views.update_headlines, name='update'),
    
    # Step 3: Test with audience
    path('test/<int:test_id>/', views.start_audience_test, name='start_test'),
    path('progress/<int:test_id>/', views.test_progress, name='progress'),
    path('progress-ajax/<int:test_id>/', views.get_progress_ajax, name='progress_ajax'),
    
    # Results
    path('results/<int:test_id>/', views.test_results, name='results'),
    
    # History
    path('history/', views.test_history, name='history'),
    
    # Delete test
    path('delete/<int:test_id>/', views.delete_test, name='delete'),
]
