"""
Forms for press_release_mailer app
"""
from django import forms
from .models import Contact, ContactList, EmailTemplate, Distribution


class ContactForm(forms.ModelForm):
    """Form for creating/editing contacts"""
    
    class Meta:
        model = Contact
        fields = [
            'first_name', 'last_name', 'email', 
            'organization', 'job_title', 'phone',
            'address', 'city', 'state', 'country', 'postal_code',
            'category', 'tags', 'is_active', 'notes'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'John'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Smith'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'john.smith@example.com'
            }),
            'organization': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Company Name'
            }),
            'job_title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Editor, Reporter, etc.'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': '+1 234 567 8900'
            }),
            'address': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'rows': 2,
                'placeholder': 'Street address'
            }),
            'city': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'City'
            }),
            'state': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'State/Province'
            }),
            'country': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Country'
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Postal Code'
            }),
            'category': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Press, Blogger, Influencer, etc.'
            }),
            'tags': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'tech, news, business (comma-separated)'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'Additional notes about this contact'
            }),
        }


class CSVImportForm(forms.Form):
    """Form for CSV import"""
    csv_file = forms.FileField(
        label='CSV File',
        help_text='Upload a CSV file with contact information',
        widget=forms.FileInput(attrs={
            'class': 'block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100',
            'accept': '.csv'
        })
    )
    
    skip_duplicates = forms.BooleanField(
        required=False,
        initial=True,
        label='Skip duplicate emails',
        widget=forms.CheckboxInput(attrs={
            'class': 'rounded border-gray-300 text-blue-600 focus:ring-blue-500'
        })
    )
    
    update_existing = forms.BooleanField(
        required=False,
        initial=False,
        label='Update existing contacts (if email matches)',
        widget=forms.CheckboxInput(attrs={
            'class': 'rounded border-gray-300 text-blue-600 focus:ring-blue-500'
        })
    )


class ContactListForm(forms.ModelForm):
    """Form for creating/editing contact lists"""
    
    def __init__(self, *args, **kwargs):
        # Extract user from kwargs
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter contacts to only show the current user's contacts
        if self.user:
            self.fields['contacts'].queryset = Contact.objects.filter(created_by=self.user, is_active=True)
    
    class Meta:
        model = ContactList
        fields = ['name', 'description', 'contacts']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'My Contact List'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'Description of this contact list'
            }),
            'contacts': forms.SelectMultiple(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'size': 10
            }),
        }


class EmailTemplateForm(forms.ModelForm):
    """Form for creating/editing email templates"""
    
    class Meta:
        model = EmailTemplate
        fields = ['name', 'subject', 'body', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Template Name'
            }),
            'subject': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Email subject with {{first_name}}, {{organization}}, etc.'
            }),
            'body': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 font-mono',
                'rows': 15,
                'placeholder': 'Email body with mail merge variables like {{first_name}}, {{last_name}}, {{organization}}, {{job_title}}'
            }),
        }
        help_texts = {
            'subject': 'You can use: {{first_name}}, {{last_name}}, {{organization}}, {{job_title}}',
            'body': 'Available variables: {{first_name}}, {{last_name}}, {{full_name}}, {{email}}, {{organization}}, {{job_title}}',
        }


class DistributionForm(forms.ModelForm):
    """Form for creating email distributions/campaigns"""
    
    def __init__(self, *args, **kwargs):
        # Extract user from kwargs
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter dropdowns to only show the current user's data
        if self.user:
            self.fields['email_template'].queryset = EmailTemplate.objects.filter(created_by=self.user, is_active=True)
            self.fields['individual_contacts'].queryset = Contact.objects.filter(created_by=self.user, is_active=True)
            self.fields['contact_lists'].queryset = ContactList.objects.filter(created_by=self.user)
    
    # Add custom field for template selection
    use_template = forms.BooleanField(
        required=False,
        initial=False,
        label='Use Template',
        widget=forms.CheckboxInput(attrs={
            'class': 'rounded border-gray-300 text-blue-600 focus:ring-blue-500',
            'onchange': 'toggleTemplateSelect()'
        })
    )
    
    email_template = forms.ModelChoiceField(
        queryset=EmailTemplate.objects.filter(is_active=True),
        required=False,
        label='Select Template',
        empty_label='-- Choose a template --',
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
            'onchange': 'loadTemplate()'
        })
    )
    
    # Add field for individual contacts (in addition to lists)
    individual_contacts = forms.ModelMultipleChoiceField(
        queryset=Contact.objects.filter(is_active=True),
        required=False,
        label='Individual Contacts',
        widget=forms.SelectMultiple(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
            'size': 6
        })
    )
    
    # File attachments - Note: multiple file handling done in view via request.FILES.getlist()
    attachments = forms.FileField(
        required=False,
        label='Attachments',
        widget=forms.FileInput(attrs={
            'class': 'block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100',
        }),
        help_text='You can select one file at a time. To add multiple, use this field multiple times when editing.'
    )
    
    class Meta:
        model = Distribution
        fields = ['name', 'subject', 'body', 'contact_lists', 'scheduled_at']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Campaign Name (internal use only)'
            }),
            'subject': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Email subject with {{first_name}}, {{organization}}, etc.'
            }),
            'body': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 font-mono',
                'rows': 15,
                'placeholder': 'Email body with mail merge variables'
            }),
            'contact_lists': forms.SelectMultiple(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'size': 8
            }),
            'scheduled_at': forms.DateTimeInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'type': 'datetime-local',
                'placeholder': 'Leave blank to send immediately'
            }),
        }
        help_texts = {
            'name': 'Internal name for this campaign',
            'subject': 'Available variables: {{first_name}}, {{last_name}}, {{organization}}, {{job_title}}',
            'body': 'Available variables: {{first_name}}, {{last_name}}, {{full_name}}, {{email}}, {{organization}}, {{job_title}}',
            'contact_lists': 'Select one or more contact lists to send to',
            'scheduled_at': 'Optional: Schedule for later. Leave blank to send immediately.',
        }
