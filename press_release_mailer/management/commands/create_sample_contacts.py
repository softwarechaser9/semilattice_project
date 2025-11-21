"""
Management command to create sample data for testing the press release mailer
Usage: python manage.py create_sample_contacts
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from press_release_mailer.models import Contact, ContactList, EmailTemplate, Distribution


class Command(BaseCommand):
    help = 'Creates sample contacts and data for testing'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample data...')
        
        # Get or create a user
        user = User.objects.first()
        if not user:
            self.stdout.write(self.style.WARNING('No users found. Please create a superuser first.'))
            return
        
        # Create sample contacts
        contacts_data = [
            {
                'first_name': 'John',
                'last_name': 'Smith',
                'email': 'john.smith@example.com',
                'organization': 'Tech News Daily',
                'job_title': 'Editor',
                'category': 'Press',
                'tags': 'tech, news',
            },
            {
                'first_name': 'Sarah',
                'last_name': 'Johnson',
                'email': 'sarah.johnson@example.com',
                'organization': 'Business Weekly',
                'job_title': 'Senior Reporter',
                'category': 'Press',
                'tags': 'business, finance',
            },
            {
                'first_name': 'Mike',
                'last_name': 'Williams',
                'email': 'mike.williams@example.com',
                'organization': 'Tech Blog Pro',
                'job_title': 'Founder',
                'category': 'Blogger',
                'tags': 'tech, startups',
            },
            {
                'first_name': 'Emily',
                'last_name': 'Brown',
                'email': 'emily.brown@example.com',
                'organization': 'Marketing Today',
                'job_title': 'Content Director',
                'category': 'Press',
                'tags': 'marketing, business',
            },
            {
                'first_name': 'David',
                'last_name': 'Lee',
                'email': 'david.lee@example.com',
                'organization': 'Startup Insider',
                'job_title': 'Journalist',
                'category': 'Press',
                'tags': 'startups, innovation',
            },
            {
                'first_name': 'Jessica',
                'last_name': 'Taylor',
                'email': 'jessica.taylor@example.com',
                'organization': 'Social Media Guru',
                'job_title': 'Influencer',
                'category': 'Influencer',
                'tags': 'social media, digital',
            },
            {
                'first_name': 'Robert',
                'last_name': 'Anderson',
                'email': 'robert.anderson@example.com',
                'organization': 'Finance Tribune',
                'job_title': 'Finance Editor',
                'category': 'Press',
                'tags': 'finance, business',
            },
            {
                'first_name': 'Lisa',
                'last_name': 'Martinez',
                'email': 'lisa.martinez@example.com',
                'organization': 'Lifestyle Magazine',
                'job_title': 'Managing Editor',
                'category': 'Press',
                'tags': 'lifestyle, wellness',
            },
        ]
        
        created_contacts = []
        for data in contacts_data:
            contact, created = Contact.objects.get_or_create(
                email=data['email'],
                defaults={**data, 'created_by': user}
            )
            if created:
                created_contacts.append(contact)
                self.stdout.write(self.style.SUCCESS(f'✓ Created contact: {contact.full_name}'))
            else:
                self.stdout.write(f'  Contact already exists: {contact.full_name}')
        
        # Create sample contact lists
        if created_contacts:
            # Tech Press List
            tech_list, created = ContactList.objects.get_or_create(
                name='Tech Press',
                defaults={
                    'description': 'Technology journalists and bloggers',
                    'created_by': user
                }
            )
            if created:
                tech_contacts = [c for c in created_contacts if 'tech' in c.tags.lower()]
                tech_list.contacts.add(*tech_contacts)
                self.stdout.write(self.style.SUCCESS(f'✓ Created list: Tech Press ({len(tech_contacts)} contacts)'))
            
            # Business Press List
            business_list, created = ContactList.objects.get_or_create(
                name='Business Press',
                defaults={
                    'description': 'Business and finance journalists',
                    'created_by': user
                }
            )
            if created:
                business_contacts = [c for c in created_contacts if 'business' in c.tags.lower() or 'finance' in c.tags.lower()]
                business_list.contacts.add(*business_contacts)
                self.stdout.write(self.style.SUCCESS(f'✓ Created list: Business Press ({len(business_contacts)} contacts)'))
        
        # Create sample email template
        template, created = EmailTemplate.objects.get_or_create(
            name='Press Release Standard',
            defaults={
                'subject': 'Press Release: {{organization}} Announcement',
                'body': '''Hi {{first_name}},

I hope this email finds you well!

I wanted to share some exciting news from our organization that I think would be of interest to you and your readers at {{organization}}.

[Your press release content goes here]

Best regards,
Your Team

---
This is a personalized message for {{first_name}} {{last_name}}
''',
                'created_by': user,
                'is_active': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('✓ Created email template: Press Release Standard'))
        
        self.stdout.write(self.style.SUCCESS('\n✅ Sample data creation complete!'))
        self.stdout.write(f'\nCreated:')
        self.stdout.write(f'  - {len(created_contacts)} contacts')
        self.stdout.write(f'  - 2 contact lists')
        self.stdout.write(f'  - 1 email template')
        self.stdout.write(f'\nNext steps:')
        self.stdout.write(f'  1. Visit /admin/ to see the new data')
        self.stdout.write(f'  2. Visit /email-contacts/ to see the user interface')
