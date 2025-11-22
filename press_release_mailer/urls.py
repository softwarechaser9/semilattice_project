from django.urls import path
from . import views

app_name = 'press_release_mailer'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    path('test-email/', views.test_email_page, name='test_email'),
    
    # Contacts
    path('contacts/', views.contact_list, name='contact_list'),
    path('contacts/add/', views.contact_add, name='contact_add'),
    path('contacts/<int:pk>/', views.contact_detail, name='contact_detail'),
    path('contacts/<int:pk>/edit/', views.contact_edit, name='contact_edit'),
    path('contacts/<int:pk>/delete/', views.contact_delete, name='contact_delete'),
    path('contacts/import/', views.contact_import, name='contact_import'),
    path('contacts/export/', views.contact_export, name='contact_export'),
    path('contacts/sample-csv/', views.download_sample_csv, name='download_sample_csv'),
    path('contacts/import-job/<int:pk>/delete/', views.import_job_delete, name='import_job_delete'),
    
    # Contact Lists
    path('lists/', views.contactlist_list, name='contactlist_list'),
    path('lists/add/', views.contactlist_add, name='contactlist_add'),
    path('lists/<int:pk>/', views.contactlist_detail, name='contactlist_detail'),
    path('lists/<int:pk>/edit/', views.contactlist_edit, name='contactlist_edit'),
    path('lists/<int:pk>/delete/', views.contactlist_delete, name='contactlist_delete'),
    
    # Email Templates
    path('templates/', views.template_list, name='template_list'),
    path('templates/add/', views.template_add, name='template_add'),
    path('templates/<int:pk>/', views.template_detail, name='template_detail'),
    path('templates/<int:pk>/edit/', views.template_edit, name='template_edit'),
    path('templates/<int:pk>/delete/', views.template_delete, name='template_delete'),
    
    # Distributions (Email Campaigns)
    path('distributions/', views.distribution_list, name='distribution_list'),
    path('distributions/create/', views.distribution_create, name='distribution_create'),
    path('distributions/<int:pk>/', views.distribution_detail, name='distribution_detail'),
    path('distributions/<int:pk>/preview/', views.distribution_preview, name='distribution_preview'),
    path('distributions/<int:pk>/edit/', views.distribution_edit, name='distribution_edit'),
    path('distributions/<int:pk>/send/', views.distribution_send, name='distribution_send'),
    path('distributions/<int:pk>/retry/', views.distribution_retry, name='distribution_retry'),
    path('distributions/<int:pk>/cancel/', views.distribution_cancel, name='distribution_cancel'),
    path('distributions/<int:pk>/delete/', views.distribution_delete, name='distribution_delete'),
    
    # AJAX endpoints for dynamic features
    path('api/contacts/search/', views.api_contact_search, name='api_contact_search'),
    path('api/contacts/filter/', views.api_contact_filter, name='api_contact_filter'),
    path('api/templates/<int:pk>/', views.api_template_get, name='api_template_get'),
]
