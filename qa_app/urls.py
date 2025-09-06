from django.urls import path
from . import views

urlpatterns = [
    path('', views.product_demo, name='home'),  # Make product-demo the main page
    path('ask-questions/', views.home, name='ask_questions'),  # Move original home to ask-questions
    path('product-demo/', views.product_demo, name='product_demo'),  # Keep for backward compatibility
    path('ask/', views.ask_question, name='ask_question'),
    path('question/<int:question_id>/', views.question_detail, name='question_detail'),
    path('question/<int:question_id>/delete/', views.delete_question, name='delete_question'),
    path('poll/<int:question_id>/', views.poll_result, name='poll_result'),
    path('populations/', views.manage_populations, name='manage_populations'),
    path('populations/delete/<int:population_id>/', views.delete_population, name='delete_population'),
]
