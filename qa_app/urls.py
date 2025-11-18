from django.urls import path
from . import views

urlpatterns = [
    # Authentication URLs
    path('login/', views.user_login, name='login'),
    path('signup/', views.user_signup, name='signup'),
    path('logout/', views.user_logout, name='logout'),
    
    # Main application URLs
    path('', views.home, name='home'),  # Main page - Ask Questions
    path('ask/', views.ask_question, name='ask_question'),
    path('question/<int:question_id>/', views.question_detail, name='question_detail'),
    path('question/<int:question_id>/delete/', views.delete_question, name='delete_question'),
    path('poll/<int:question_id>/', views.poll_result, name='poll_result'),
    path('populations/', views.manage_populations, name='manage_populations'),
    path('populations/delete/<int:population_id>/', views.delete_population, name='delete_population'),
]
