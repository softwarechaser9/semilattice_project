"""
CSV import utility for bulk contact imports
"""
import csv
import io
from django.db import transaction
from .models import Contact


def parse_csv_file(csv_file):
    """
    Parse uploaded CSV file and return list of dictionaries
    
    Args:
        csv_file: Uploaded file object
    
    Returns:
        tuple: (success: bool, data: list or error_message: str)
    """
    try:
        # Read and decode the file
        file_data = csv_file.read()
        
        # Try different encodings
        for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
            try:
                decoded_data = file_data.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            return (False, "Unable to decode CSV file. Please ensure it's saved with UTF-8 encoding.")
        
        # Auto-detect delimiter (comma or tab)
        # Check first few lines to determine delimiter
        sample_lines = decoded_data.split('\n')[:5]
        sample_text = '\n'.join(sample_lines)
        
        # Use csv.Sniffer to detect delimiter
        try:
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample_text).delimiter
        except Exception:
            # Fallback: count commas vs tabs in first line
            first_line = sample_lines[0] if sample_lines else ''
            comma_count = first_line.count(',')
            tab_count = first_line.count('\t')
            delimiter = '\t' if tab_count > comma_count else ','
        
        # Parse CSV with detected delimiter
        csv_reader = csv.DictReader(io.StringIO(decoded_data), delimiter=delimiter)
        
        # Validate headers
        fieldnames = csv_reader.fieldnames
        if not fieldnames:
            return (False, "CSV file is empty or has no headers.")
        
        # Read all rows and filter out completely empty rows
        all_rows = list(csv_reader)
        
        # Filter out rows where ALL fields are empty (common in Excel exports)
        # Also filter out rows that have no email address (likely invalid/empty)
        rows = []
        for row in all_rows:
            # Check if at least one field has meaningful data
            has_data = any(str(value).strip() for value in row.values() if value)
            
            if not has_data:
                continue  # Skip completely empty rows
            
            # Check if row has an email-like field
            normalized_row = {k.lower().strip().replace(' ', '_'): v.strip() if isinstance(v, str) else v 
                             for k, v in row.items()}
            
            has_email = False
            for key in ['email', 'e-mail', 'e_mail', 'email_address']:
                if key in normalized_row and normalized_row[key]:
                    has_email = True
                    break
            
            # Only include rows that have data AND have an email
            # This filters out Excel artifact rows more aggressively
            if has_data and has_email:
                rows.append(row)
        
        if not rows:
            return (False, "CSV file contains headers but no data rows.")
        
        return (True, rows)
    
    except Exception as e:
        return (False, f"Error parsing CSV file: {str(e)}")


def validate_contact_data(row, row_number):
    """
    Validate a single contact row
    
    Args:
        row: Dictionary with contact data (should be normalized keys)
        row_number: Row number for error reporting
    
    Returns:
        tuple: (is_valid: bool, errors: list, warnings: list)
    """
    errors = []
    warnings = []
    
    # Normalize row keys to handle different CSV column names
    normalized_row = {k.lower().strip().replace(' ', '_'): v.strip() if isinstance(v, str) else v 
                     for k, v in row.items()}
    
    # Check for email in various formats
    email = None
    for key in ['email', 'e-mail', 'e_mail', 'email_address']:
        if key in normalized_row and normalized_row[key]:
            email = normalized_row[key]
            break
    
    # Required fields
    if not email:
        errors.append(f"Row {row_number}: Email is required")
    
    # Check for first/last name in various formats
    first_name = None
    for key in ['first_name', 'firstname', 'first', 'given_name']:
        if key in normalized_row and normalized_row[key]:
            first_name = normalized_row[key]
            break
    
    last_name = None
    for key in ['last_name', 'lastname', 'last', 'surname', 'family_name']:
        if key in normalized_row and normalized_row[key]:
            last_name = normalized_row[key]
            break
    
    # Only warn about missing names if email exists AND both names are missing
    # Don't warn if at least one name exists (many contacts only have first OR last name)
    if email and not first_name and not last_name:
        # This is just a warning, not an error - we can still import with email only
        pass  # Don't add warning - email is the most important field
    
    # Validate email format (basic)
    if email and '@' not in email:
        errors.append(f"Row {row_number}: Invalid email format: {email}")
    
    is_valid = len(errors) == 0
    return (is_valid, errors, warnings)


def map_csv_to_contact(row, row_number=None, warnings_list=None):
    """
    Map CSV row to Contact model fields
    
    Supports common CSV column name variations:
    - email, Email, EMAIL, e-mail
    - first_name, First Name, FirstName, first name
    - etc.
    
    Automatically truncates values that exceed database field limits.
    
    Args:
        row: Dictionary with CSV data
        row_number: Optional row number for warning messages
        warnings_list: Optional list to append truncation warnings
    
    Returns:
        dict: Cleaned contact data
    """
    # Field length limits from Contact model
    FIELD_LIMITS = {
        'first_name': 100,
        'last_name': 100,
        'email': 254,  # EmailField default
        'organization': 200,
        'job_title': 100,
        'phone': 20,
        'city': 100,
        'state': 50,
        'country': 100,
        'postal_code': 20,
        'category': 100,
    }
    
    def truncate_field(field_name, value):
        """Truncate value to fit database field limit and add warning"""
        if not value:
            return value
        max_length = FIELD_LIMITS.get(field_name)
        if max_length and len(value) > max_length:
            if warnings_list is not None and row_number:
                warnings_list.append(
                    f"Row {row_number}: {field_name} truncated from {len(value)} to {max_length} characters"
                )
            return value[:max_length]
        return value
    
    # Normalize keys (lowercase, strip spaces)
    normalized_row = {k.lower().strip().replace(' ', '_'): v.strip() if isinstance(v, str) else v 
                     for k, v in row.items()}
    
    # Map to contact fields
    contact_data = {}
    
    # Email (required)
    for key in ['email', 'e-mail', 'e_mail', 'email_address']:
        if key in normalized_row and normalized_row[key]:
            contact_data['email'] = truncate_field('email', normalized_row[key])
            break
    
    # First name
    for key in ['first_name', 'firstname', 'first', 'given_name']:
        if key in normalized_row and normalized_row[key]:
            contact_data['first_name'] = truncate_field('first_name', normalized_row[key])
            break
    
    # Last name
    for key in ['last_name', 'lastname', 'last', 'surname', 'family_name']:
        if key in normalized_row and normalized_row[key]:
            contact_data['last_name'] = truncate_field('last_name', normalized_row[key])
            break
    
    # Organization
    for key in ['organization', 'organisation', 'company', 'company_name']:
        if key in normalized_row and normalized_row[key]:
            contact_data['organization'] = truncate_field('organization', normalized_row[key])
            break
    
    # Job title
    for key in ['job_title', 'jobtitle', 'title', 'position', 'role']:
        if key in normalized_row and normalized_row[key]:
            contact_data['job_title'] = truncate_field('job_title', normalized_row[key])
            break
    
    # Phone
    for key in ['phone', 'phone_number', 'telephone', 'mobile', 'cell']:
        if key in normalized_row and normalized_row[key]:
            contact_data['phone'] = truncate_field('phone', normalized_row[key])
            break
    
    # Address
    for key in ['address', 'street', 'street_address']:
        if key in normalized_row and normalized_row[key]:
            contact_data['address'] = normalized_row[key]  # TextField, no limit
            break
    
    # City
    for key in ['city', 'town']:
        if key in normalized_row and normalized_row[key]:
            contact_data['city'] = truncate_field('city', normalized_row[key])
            break
    
    # State
    for key in ['state', 'province', 'region']:
        if key in normalized_row and normalized_row[key]:
            contact_data['state'] = truncate_field('state', normalized_row[key])
            break
    
    # Country
    for key in ['country']:
        if key in normalized_row and normalized_row[key]:
            contact_data['country'] = truncate_field('country', normalized_row[key])
            break
    
    # Postal code
    for key in ['postal_code', 'postalcode', 'zip', 'zip_code', 'postcode']:
        if key in normalized_row and normalized_row[key]:
            contact_data['postal_code'] = truncate_field('postal_code', normalized_row[key])
            break
    
    # Category
    for key in ['category', 'type', 'group']:
        if key in normalized_row and normalized_row[key]:
            contact_data['category'] = truncate_field('category', normalized_row[key])
            break
    
    # Tags
    for key in ['tags', 'labels', 'keywords']:
        if key in normalized_row and normalized_row[key]:
            contact_data['tags'] = normalized_row[key]  # TextField, no limit
            break
    
    # Notes
    for key in ['notes', 'note', 'comments', 'description']:
        if key in normalized_row and normalized_row[key]:
            contact_data['notes'] = normalized_row[key]  # TextField, no limit
            break
    
    # Set defaults
    contact_data.setdefault('first_name', '')
    contact_data.setdefault('last_name', '')
    contact_data.setdefault('is_active', True)
    
    return contact_data


def import_contacts_from_csv(csv_file, skip_duplicates=True, update_existing=False, created_by=None):
    """
    Import contacts from CSV file
    
    Args:
        csv_file: Uploaded CSV file
        skip_duplicates: Skip contacts with duplicate emails
        update_existing: Update existing contacts if email matches
        created_by: User who is importing
    
    Returns:
        dict: Import results with counts and errors
    """
    result = {
        'success': False,
        'total_rows': 0,
        'imported': 0,
        'updated': 0,
        'skipped': 0,
        'errors': [],
        'warnings': [],
    }
    
    # Parse CSV
    parse_success, data_or_error = parse_csv_file(csv_file)
    if not parse_success:
        result['errors'].append(data_or_error)
        return result
    
    rows = data_or_error
    result['total_rows'] = len(rows)
    
    # OPTIMIZATION: Fetch all existing emails in ONE query (instead of 1 query per row)
    all_emails_in_csv = []
    for row in rows:
        normalized_row = {k.lower().strip().replace(' ', '_'): v.strip() if isinstance(v, str) else v 
                         for k, v in row.items()}
        for key in ['email', 'e-mail', 'e_mail', 'email_address']:
            if key in normalized_row and normalized_row[key]:
                all_emails_in_csv.append(normalized_row[key].lower())
                break
    
    # Get existing contacts for THIS USER ONLY
    # With the new database constraint, each user can have their own copy of an email
    existing_contacts_dict = {}
    
    if all_emails_in_csv:
        # Query for existing contacts ONLY for the current user
        user_existing_contacts = Contact.objects.filter(
            created_by=created_by,
            email__in=[e.lower() for e in all_emails_in_csv]
        )
        existing_contacts_dict = {c.email.lower(): c for c in user_existing_contacts}
    
    # Validate and import (process row by row, but with pre-fetched duplicate data)
    for idx, row in enumerate(rows, start=2):  # Start at 2 (1 is header)
        try:
            # Validate
            is_valid, errors, warnings = validate_contact_data(row, idx)
            result['errors'].extend(errors)
            result['warnings'].extend(warnings)
            
            if not is_valid:
                result['skipped'] += 1
                continue
            
            # Map to contact data
            contact_data = map_csv_to_contact(row, row_number=idx, warnings_list=result['warnings'])
            
            if not contact_data.get('email'):
                result['errors'].append(f"Row {idx}: No email found")
                result['skipped'] += 1
                continue
            
            email = contact_data['email'].lower()
            
            # Check for duplicates (only within current user's contacts)
            existing_contact = existing_contacts_dict.get(email)
            
            if existing_contact:
                if update_existing:
                    # Update existing contact (user's own contact)
                    for key, value in contact_data.items():
                        if key != 'email' and value:  # Don't update email, only non-empty values
                            setattr(existing_contact, key, value)
                    existing_contact.save()
                    result['updated'] += 1
                elif skip_duplicates:
                    # Skip duplicate (user's own contact)
                    result['skipped'] += 1
                    result['warnings'].append(f"Row {idx}: Skipped duplicate email (already in your contacts): {email}")
                else:
                    # Error on duplicate
                    result['errors'].append(f"Row {idx}: Duplicate email: {email}")
                    result['skipped'] += 1
            else:
                # Create new contact
                try:
                    new_contact = Contact.objects.create(
                        **contact_data,
                        created_by=created_by
                    )
                    # Add to dict to detect duplicates within same CSV
                    existing_contacts_dict[email] = new_contact
                    result['imported'] += 1
                except Exception as e:
                    error_str = str(e).lower()
                    # Check if it's a duplicate email error (catch both PostgreSQL and SQLite)
                    # PostgreSQL: "duplicate key value violates unique constraint unique_email_per_user"
                    # SQLite: "UNIQUE constraint failed: press_release_mailer_contact.email, press_release_mailer_contact.created_by_id"
                    is_duplicate_error = (
                        'unique_email_per_user' in error_str or 
                        'duplicate key' in error_str or
                        'unique constraint failed' in error_str or
                        'press_release_mailer_contact.email' in error_str
                    )
                    
                    if is_duplicate_error:
                        # This is a duplicate - treat as warning, not error
                        result['skipped'] += 1
                        result['warnings'].append(f"Row {idx}: Skipped duplicate email (already in your contacts): {email}")
                    else:
                        # Some other error (real problem)
                        result['errors'].append(f"Row {idx}: Error creating contact: {str(e)}")
                        result['skipped'] += 1
        
        except Exception as e:
            # Catch any unexpected errors for this row
            result['errors'].append(f"Row {idx}: Unexpected error: {str(e)}")
            result['skipped'] += 1
            continue
    
    result['success'] = result['imported'] > 0 or result['updated'] > 0
    
    return result


def generate_sample_csv():
    """
    Generate a sample CSV template for users to download
    
    Returns:
        str: CSV content
    """
    headers = [
        'first_name', 'last_name', 'email', 'organization', 
        'job_title', 'phone', 'category', 'tags', 'notes'
    ]
    
    sample_data = [
        ['John', 'Smith', 'john.smith@example.com', 'Tech News', 'Editor', '+1 234 567 8900', 'Press', 'tech, news', 'Sample contact'],
        ['Sarah', 'Johnson', 'sarah.j@example.com', 'Business Weekly', 'Reporter', '+1 234 567 8901', 'Press', 'business, finance', ''],
        ['Mike', 'Williams', 'mike.w@example.com', 'Startup Blog', 'Founder', '', 'Blogger', 'startups, tech', 'Influential blogger'],
    ]
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(sample_data)
    
    return output.getvalue()
