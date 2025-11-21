from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count
from .models import Contact, ContactList, EmailTemplate, Distribution, DistributionRecipient, Attachment
from .email_utils import send_test_email, send_single_email, apply_mail_merge, validate_email_settings
from .forms import ContactForm, CSVImportForm, ContactListForm, EmailTemplateForm, DistributionForm
from .csv_utils import import_contacts_from_csv, generate_sample_csv
from .campaign_utils import prepare_distribution_recipients, send_distribution, get_preview_recipients, handle_distribution_attachments
import csv
from io import StringIO


@login_required
def test_email_page(request):
    """Test email sending with Gmail SMTP"""
    if request.method == 'POST':
        recipient_email = request.POST.get('recipient_email')
        test_type = request.POST.get('test_type', 'simple')
        
        # Validate email settings first
        is_valid, validation_message = validate_email_settings()
        if not is_valid:
            messages.error(request, f'Email configuration error: {validation_message}')
            return render(request, 'press_release_mailer/test_email.html')
        
        if test_type == 'simple':
            # Send simple test email
            success, message = send_test_email(recipient_email)
        else:
            # Send mail merge test with sample contact
            sample_contact = Contact.objects.first()
            if not sample_contact:
                messages.error(request, 'No contacts in database. Please add a contact first.')
                return render(request, 'press_release_mailer/test_email.html')
            
            subject_template = "Hello {{first_name}} from {{organization}}!"
            body_template = """
Hi {{first_name}} {{last_name}},

This is a test email demonstrating mail merge functionality.

Your details:
- Name: {{full_name}}
- Email: {{email}}
- Organization: {{organization}}
- Job Title: {{job_title}}

If you can see your personalized information above, mail merge is working correctly!

Best regards,
Press Release Mailer
            """
            
            personalized_subject = apply_mail_merge(subject_template, sample_contact)
            personalized_body = apply_mail_merge(body_template, sample_contact)
            
            success, message = send_single_email(
                recipient_email=recipient_email,
                subject=personalized_subject,
                body=personalized_body
            )
        
        if success:
            messages.success(request, f'✅ Test email sent successfully to {recipient_email}! Check your inbox.')
        else:
            messages.error(request, f'❌ Failed to send email: {message}')
    
    return render(request, 'press_release_mailer/test_email.html')


@login_required
def dashboard(request):
    """Main dashboard for press release mailer"""
    context = {
        'total_contacts': Contact.objects.filter(is_active=True).count(),
        'total_lists': ContactList.objects.count(),
        'total_templates': EmailTemplate.objects.filter(is_active=True).count(),
        'total_distributions': Distribution.objects.count(),
        'recent_distributions': Distribution.objects.all().order_by('-created_at')[:5],
        'recent_contacts': Contact.objects.filter(is_active=True).order_by('-created_at')[:5],
        'contact_lists': ContactList.objects.all().order_by('-created_at')[:5],
    }
    return render(request, 'press_release_mailer/dashboard.html', context)


@login_required
def contact_list(request):
    """List all contacts with search and filter"""
    contacts = Contact.objects.all()
    
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        contacts = contacts.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(organization__icontains=search_query)
        )
    
    # Filter by category
    category = request.GET.get('category', '')
    if category:
        contacts = contacts.filter(category=category)
    
    # Filter by active status
    is_active = request.GET.get('is_active', '')
    if is_active == 'true':
        contacts = contacts.filter(is_active=True)
    elif is_active == 'false':
        contacts = contacts.filter(is_active=False)
    
    context = {
        'contacts': contacts,
        'search_query': search_query,
        'categories': Contact.objects.values_list('category', flat=True).distinct(),
    }
    return render(request, 'press_release_mailer/contact_list.html', context)


@login_required
def contact_add(request):
    """Add new contact"""
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            contact = form.save(commit=False)
            contact.created_by = request.user
            contact.save()
            messages.success(request, f'✅ Contact "{contact.full_name}" added successfully!')
            return redirect('press_release_mailer:contact_detail', pk=contact.pk)
    else:
        form = ContactForm()
    
    return render(request, 'press_release_mailer/contact_form.html', {
        'form': form,
        'title': 'Add New Contact',
        'action': 'Add'
    })


@login_required
def contact_detail(request, pk):
    """View contact details"""
    contact = get_object_or_404(Contact, pk=pk)
    context = {
        'contact': contact,
        'email_history': contact.email_logs.all()[:10],
    }
    return render(request, 'press_release_mailer/contact_detail.html', context)


@login_required
def contact_edit(request, pk):
    """Edit contact"""
    contact = get_object_or_404(Contact, pk=pk)
    
    if request.method == 'POST':
        form = ContactForm(request.POST, instance=contact)
        if form.is_valid():
            form.save()
            messages.success(request, f'✅ Contact "{contact.full_name}" updated successfully!')
            return redirect('press_release_mailer:contact_detail', pk=pk)
    else:
        form = ContactForm(instance=contact)
    
    return render(request, 'press_release_mailer/contact_form.html', {
        'form': form,
        'contact': contact,
        'title': f'Edit Contact: {contact.full_name}',
        'action': 'Update'
    })


@login_required
def contact_delete(request, pk):
    """Delete contact"""
    contact = get_object_or_404(Contact, pk=pk)
    if request.method == 'POST':
        contact.delete()
        messages.success(request, f'Contact {contact.full_name} deleted successfully!')
        return redirect('press_release_mailer:contact_list')
    return render(request, 'press_release_mailer/contact_confirm_delete.html', {'contact': contact})


@login_required
def contact_import(request):
    """Import contacts from CSV"""
    if request.method == 'POST':
        form = CSVImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            skip_duplicates = form.cleaned_data['skip_duplicates']
            update_existing = form.cleaned_data['update_existing']
            
            # Import contacts
            result = import_contacts_from_csv(
                csv_file=csv_file,
                skip_duplicates=skip_duplicates,
                update_existing=update_existing,
                created_by=request.user
            )
            
            # Show results
            if result['success']:
                success_msg = f"✅ Import complete! Imported: {result['imported']}, Updated: {result['updated']}, Skipped: {result['skipped']}"
                messages.success(request, success_msg)
                
                if result['warnings']:
                    for warning in result['warnings'][:5]:  # Show first 5 warnings
                        messages.warning(request, warning)
                
                if result['errors']:
                    for error in result['errors'][:5]:  # Show first 5 errors
                        messages.error(request, error)
            else:
                messages.error(request, f"❌ Import failed: {', '.join(result['errors'])}")
            
            return redirect('press_release_mailer:contact_list')
    else:
        form = CSVImportForm()
    
    return render(request, 'press_release_mailer/contact_import.html', {'form': form})


@login_required
def contact_export(request):
    """Export contacts to CSV"""
    contacts = Contact.objects.all()
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="contacts.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['First Name', 'Last Name', 'Email', 'Organization', 'Job Title', 'Phone', 'Category', 'Tags', 'Active'])
    
    for contact in contacts:
        writer.writerow([
            contact.first_name,
            contact.last_name,
            contact.email,
            contact.organization,
            contact.job_title,
            contact.phone,
            contact.category,
            contact.tags,
            contact.is_active,
        ])
    
    return response


@login_required
def download_sample_csv(request):
    """Download sample CSV template"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="contact_import_template.csv"'
    response.write(generate_sample_csv())
    return response


@login_required
def contactlist_list(request):
    """List all contact lists"""
    lists = ContactList.objects.annotate(contact_count=Count('contacts'))
    context = {'lists': lists}
    return render(request, 'press_release_mailer/contactlist_list.html', context)


@login_required
def contactlist_add(request):
    """Add new contact list"""
    if request.method == 'POST':
        form = ContactListForm(request.POST)
        if form.is_valid():
            contact_list = form.save(commit=False)
            contact_list.created_by = request.user
            contact_list.save()
            form.save_m2m()  # Save many-to-many relationships
            messages.success(request, f'✅ Contact list "{contact_list.name}" created successfully!')
            return redirect('press_release_mailer:contactlist_detail', pk=contact_list.pk)
    else:
        form = ContactListForm()
    
    return render(request, 'press_release_mailer/contactlist_form.html', {
        'form': form,
        'title': 'Create New Contact List',
        'action': 'Create'
    })


@login_required
def contactlist_detail(request, pk):
    """View contact list details"""
    contact_list = get_object_or_404(ContactList, pk=pk)
    context = {
        'contact_list': contact_list,
        'contacts': contact_list.contacts.all(),
    }
    return render(request, 'press_release_mailer/contactlist_detail.html', context)


@login_required
def contactlist_edit(request, pk):
    """Edit contact list"""
    contact_list = get_object_or_404(ContactList, pk=pk)
    
    if request.method == 'POST':
        form = ContactListForm(request.POST, instance=contact_list)
        if form.is_valid():
            form.save()
            messages.success(request, f'✅ Contact list "{contact_list.name}" updated successfully!')
            return redirect('press_release_mailer:contactlist_detail', pk=pk)
    else:
        form = ContactListForm(instance=contact_list)
    
    return render(request, 'press_release_mailer/contactlist_form.html', {
        'form': form,
        'contact_list': contact_list,
        'title': f'Edit: {contact_list.name}',
        'action': 'Update'
    })


@login_required
def contactlist_delete(request, pk):
    """Delete contact list"""
    contact_list = get_object_or_404(ContactList, pk=pk)
    if request.method == 'POST':
        name = contact_list.name
        contact_list.delete()
        messages.success(request, f'✅ Contact list "{name}" deleted successfully!')
        return redirect('press_release_mailer:contactlist_list')
    return render(request, 'press_release_mailer/contactlist_confirm_delete.html', {'contact_list': contact_list})


@login_required
def template_add(request):
    """Add new template"""
    if request.method == 'POST':
        form = EmailTemplateForm(request.POST)
        if form.is_valid():
            template = form.save(commit=False)
            template.created_by = request.user
            template.save()
            messages.success(request, f'✅ Email template "{template.name}" created successfully!')
            return redirect('press_release_mailer:template_detail', pk=template.pk)
    else:
        form = EmailTemplateForm()
    
    return render(request, 'press_release_mailer/template_form.html', {
        'form': form,
        'title': 'Create New Email Template',
        'action': 'Create'
    })

@login_required
def template_list(request):
    """List all email templates"""
    templates = EmailTemplate.objects.all()
    context = {'templates': templates}
    return render(request, 'press_release_mailer/template_list.html', context)


@login_required
def template_edit(request, pk):
    """Edit template"""
    template = get_object_or_404(EmailTemplate, pk=pk)
    
    if request.method == 'POST':
        form = EmailTemplateForm(request.POST, instance=template)
        if form.is_valid():
            form.save()
            messages.success(request, f'✅ Email template "{template.name}" updated successfully!')
            return redirect('press_release_mailer:template_detail', pk=pk)
    else:
        form = EmailTemplateForm(instance=template)
    
    return render(request, 'press_release_mailer/template_form.html', {
        'form': form,
        'template': template,
        'title': f'Edit: {template.name}',
        'action': 'Update'
    })


@login_required
def template_detail(request, pk):
    """View template details"""
    template = get_object_or_404(EmailTemplate, pk=pk)
    context = {'template': template}
    return render(request, 'press_release_mailer/template_detail.html', context)


@login_required
def template_delete(request, pk):
    """Delete template"""
    template = get_object_or_404(EmailTemplate, pk=pk)
    if request.method == 'POST':
        template.delete()
        messages.success(request, f'Template "{template.name}" deleted successfully!')
        return redirect('press_release_mailer:template_list')
    return render(request, 'press_release_mailer/template_confirm_delete.html', {'template': template})


@login_required
def distribution_list(request):
    """List all distributions"""
    distributions = Distribution.objects.all()
    context = {'distributions': distributions}
    return render(request, 'press_release_mailer/distribution_list.html', context)


@login_required
def distribution_create(request):
    """Create new distribution/campaign"""
    if request.method == 'POST':
        form = DistributionForm(request.POST, request.FILES)
        if form.is_valid():
            # Create distribution
            distribution = form.save(commit=False)
            distribution.created_by = request.user
            distribution.status = 'draft'
            distribution.save()
            
            # Save many-to-many relationships
            form.save_m2m()
            
            # Handle attachments
            files = request.FILES.getlist('attachments')
            if files:
                success, message, count = handle_distribution_attachments(distribution, files)
                if success:
                    messages.success(request, f'📎 {message}')
                else:
                    messages.warning(request, f'⚠️ {message}')
            
            # Prepare recipients
            success, message, count = prepare_distribution_recipients(distribution)
            if success:
                messages.success(request, f'✅ Campaign "{distribution.name}" created with {count} recipients!')
                return redirect('press_release_mailer:distribution_preview', pk=distribution.pk)
            else:
                messages.error(request, f'❌ {message}')
                return redirect('press_release_mailer:distribution_edit', pk=distribution.pk)
    else:
        # Pre-fill with first template if use_template is checked
        form = DistributionForm()
    
    return render(request, 'press_release_mailer/distribution_form.html', {
        'form': form,
        'title': 'Create New Campaign',
        'action': 'Create'
    })


@login_required
def distribution_detail(request, pk):
    """View distribution details"""
    distribution = get_object_or_404(Distribution, pk=pk)
    context = {
        'distribution': distribution,
        'recipients': distribution.recipient_records.all()[:50],  # Show first 50
    }
    return render(request, 'press_release_mailer/distribution_detail.html', context)


@login_required
def distribution_edit(request, pk):
    """Edit distribution"""
    distribution = get_object_or_404(Distribution, pk=pk)
    if distribution.status != 'draft':
        messages.error(request, '❌ Cannot edit a campaign that is not in draft status!')
        return redirect('press_release_mailer:distribution_detail', pk=pk)
    
    if request.method == 'POST':
        form = DistributionForm(request.POST, request.FILES, instance=distribution)
        if form.is_valid():
            # Save with commit=False to handle M2M relationships manually
            distribution = form.save(commit=False)
            distribution.save()
            form.save_m2m()  # Now save the many-to-many relationships
            
            # Handle new attachments
            files = request.FILES.getlist('attachments')
            if files:
                success, message, count = handle_distribution_attachments(distribution, files)
                if success:
                    messages.success(request, f'📎 {message}')
                else:
                    messages.warning(request, f'⚠️ {message}')
            
            # Re-prepare recipients
            distribution.recipient_records.all().delete()  # Clear old recipients
            success, message, count = prepare_distribution_recipients(distribution)
            if success:
                messages.success(request, f'✅ Campaign updated with {count} recipients!')
            
            return redirect('press_release_mailer:distribution_preview', pk=pk)
    else:
        form = DistributionForm(instance=distribution)
    
    return render(request, 'press_release_mailer/distribution_form.html', {
        'form': form,
        'distribution': distribution,
        'title': f'Edit: {distribution.name}',
        'action': 'Update'
    })


@login_required
def distribution_preview(request, pk):
    """Preview campaign with mail merge samples"""
    distribution = get_object_or_404(Distribution, pk=pk)
    
    # Get preview samples
    previews = get_preview_recipients(distribution, limit=3)
    
    context = {
        'distribution': distribution,
        'previews': previews,
        'attachments': distribution.attachments.all(),
        'total_recipients': distribution.total_recipients,
    }
    
    return render(request, 'press_release_mailer/distribution_preview.html', context)


@login_required
def distribution_send(request, pk):
    """Send distribution (async with Celery)"""
    distribution = get_object_or_404(Distribution, pk=pk)
    
    if request.method == 'POST':
        # Validate email settings first
        is_valid, validation_message = validate_email_settings()
        if not is_valid:
            messages.error(request, f'❌ Email configuration error: {validation_message}')
            return redirect('press_release_mailer:distribution_detail', pk=pk)
        
        # Check if Celery is available
        try:
            from .tasks import test_celery
            # Try to use async sending
            from .campaign_utils import send_distribution_async
            success, message, total = send_distribution_async(distribution, request.user)
            
            if success:
                messages.success(request, f'✅ {message}. Emails are being sent in the background.')
                messages.info(request, '📊 You can monitor progress on this page. Refresh to see updates.')
            else:
                messages.error(request, f'❌ {message}')
        except ImportError:
            # Celery not available, fall back to synchronous sending
            from .campaign_utils import send_distribution
            messages.warning(request, '⚠️ Celery not running. Sending emails synchronously (may take a while)...')
            success, message, sent_count, failed_count = send_distribution(distribution, request.user)
            
            if success:
                if failed_count == 0:
                    messages.success(request, f'✅ {message}')
                else:
                    messages.warning(request, f'⚠️ {message}')
            else:
                messages.error(request, f'❌ {message}')
        
        return redirect('press_release_mailer:distribution_detail', pk=pk)
    
    return render(request, 'press_release_mailer/distribution_confirm_send.html', {
        'distribution': distribution,
        'attachments': distribution.attachments.all()
    })


@login_required
def distribution_cancel(request, pk):
    """Cancel distribution"""
    distribution = get_object_or_404(Distribution, pk=pk)
    if request.method == 'POST':
        distribution.status = 'cancelled'
        distribution.save()
        messages.success(request, 'Distribution cancelled successfully!')
        return redirect('press_release_mailer:distribution_detail', pk=pk)
    return render(request, 'press_release_mailer/distribution_confirm_cancel.html', {'distribution': distribution})


@login_required
def distribution_delete(request, pk):
    """Delete distribution"""
    distribution = get_object_or_404(Distribution, pk=pk)
    if request.method == 'POST':
        distribution.delete()
        messages.success(request, f'Distribution "{distribution.name}" deleted successfully!')
        return redirect('press_release_mailer:distribution_list')
    return render(request, 'press_release_mailer/distribution_confirm_delete.html', {'distribution': distribution})


@login_required
def distribution_retry(request, pk):
    """Retry sending a failed or stuck distribution"""
    distribution = get_object_or_404(Distribution, pk=pk)
    
    if distribution.status not in ['scheduled', 'failed', 'sending']:
        messages.error(request, '❌ This campaign cannot be retried.')
        return redirect('press_release_mailer:distribution_detail', pk=pk)
    
    # Reset status to draft so it can be sent again
    distribution.status = 'draft'
    distribution.save()
    
    # Reset all recipient statuses
    distribution.recipient_records.update(status='pending', sent_at=None, error_message='')
    
    messages.success(request, f'✅ Campaign "{distribution.name}" has been reset. You can send it again.')
    return redirect('press_release_mailer:distribution_preview', pk=pk)


@login_required
def api_contact_search(request):
    """AJAX endpoint for contact search"""
    query = request.GET.get('q', '')
    contacts = Contact.objects.filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(email__icontains=query)
    )[:10]
    
    results = [
        {
            'id': c.id,
            'name': c.full_name,
            'email': c.email,
            'organization': c.organization,
        }
        for c in contacts
    ]
    
    return JsonResponse({'results': results})


@login_required
def api_contact_filter(request):
    """AJAX endpoint for contact filtering"""
    category = request.GET.get('category', '')
    tags = request.GET.get('tags', '')
    
    contacts = Contact.objects.filter(is_active=True)
    
    if category:
        contacts = contacts.filter(category=category)
    
    if tags:
        contacts = contacts.filter(tags__icontains=tags)
    
    results = [
        {
            'id': c.id,
            'name': c.full_name,
            'email': c.email,
        }
        for c in contacts
    ]
    
    return JsonResponse({'results': results, 'count': len(results)})


@login_required
def api_template_get(request, pk):
    """API endpoint to get template data for form population"""
    try:
        template = EmailTemplate.objects.get(pk=pk, is_active=True)
        return JsonResponse({
            'success': True,
            'template': {
                'id': template.id,
                'name': template.name,
                'subject': template.subject,
                'body': template.body,
            }
        })
    except EmailTemplate.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Template not found'
        }, status=404)
