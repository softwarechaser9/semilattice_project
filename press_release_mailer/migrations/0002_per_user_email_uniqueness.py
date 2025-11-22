# Generated migration for per-user email uniqueness

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('press_release_mailer', '0001_initial'),  # Adjust this to your last migration
    ]

    operations = [
        # Step 1: Remove the global unique constraint on email field
        migrations.AlterField(
            model_name='contact',
            name='email',
            field=models.EmailField(),  # Removed unique=True
        ),
        
        # Step 2: Add unique constraint for email per user
        migrations.AddConstraint(
            model_name='contact',
            constraint=models.UniqueConstraint(
                fields=['email', 'created_by'],
                name='unique_email_per_user'
            ),
        ),
    ]
