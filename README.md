# Semilattice Q&A Django Application

A Django web application that integrates with the Semilattice AI API to simulate survey responses from different populations.

## Features

- **Product Demo Page**: Interactive demo showcasing Semilattice AI capabilities
- **Population Management**: Add and manage your Semilattice populations
- **Question Simulation**: Ask questions and get AI-predicted response patterns
- **Real-time Polling**: Live updates as simulations complete
- **Multiple Question Types**: Support for single-choice, multiple-choice, and free-text questions
- **Visual Results**: Clean charts showing response percentages

## Project Structure

```
.
├── manage.py
├── requirements.txt
├── .env                          # Environment variables
├── templates/                    # Project-level templates
│   └── qa_app/
│       ├── base.html
│       ├── home.html
│       ├── product_demo.html
│       ├── question_detail.html
│       └── manage_populations.html
├── semilattice_project/          # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── qa_app/                       # Main application
    ├── models.py                 # Database models
    ├── views.py                  # View controllers
    ├── services.py               # Semilattice API client
    ├── admin.py                  # Admin interface
    └── urls.py                   # URL routing
```

## Setup

### 1. Environment Variables

Create a `.env` file in the project root:

```env
SEMILATTICE_API_KEY=your_semilattice_api_key_here
SEMILATTICE_BASE=https://api.semilattice.ai
SECRET_KEY=your-django-secret-key
DEBUG=True
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Database Setup

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser  # Optional: create admin user
```

### 4. Run the Application

```bash
python manage.py runserver
```

Visit `http://localhost:8000` to access the application.

## API Integration

This application uses the official Semilattice API with the following endpoints:

- `GET /v1/populations/{population_id}` - Fetch population details
- `POST /v1/answers` - Start answer simulation
- `GET /v1/answers/{answer_id}` - Poll simulation status

### Authentication

The API uses bearer token authentication via the `authorization` header.

### Question Types Supported

1. **Single Choice**: Users select one option
2. **Multiple Choice**: Users can select multiple options
3. **Free Text**: Open-ended text responses

## Usage

### Adding Populations

1. Go to **Populations** page
2. Enter your Semilattice Population ID (from your dashboard)
3. Add a display name and optional description

### Asking Questions

1. Go to **Home** or **Product Demo**
2. Select or enter a Population ID
3. Enter your question
4. Choose question type and provide options (for choice questions)
5. Submit and view real-time results

### Viewing Results

Results are displayed as percentage breakdowns with visual charts. The system polls the Semilattice API until simulation completion.

## Models

### Population
- Stores Semilattice population metadata
- Links to questions asked against this population

### Question
- Stores question text, type, and answer options
- Links to simulation results

### SimulationResult
- Stores API response and status
- Tracks simulation progress from queued → running → predicted

## Development

### Key Files

- `services.py`: Semilattice API client with error handling and polling
- `views.py`: Django views handling web requests and API calls
- `models.py`: Database schema for populations, questions, and results

### Adding New Features

The application is structured to easily extend with additional Semilattice API features like:
- Population creation via CSV upload
- Batch question processing
- Historical result analysis
- Custom simulation engines

## Deployment Notes

For production deployment:

1. Set `DEBUG=False` in environment
2. Configure proper database (PostgreSQL recommended)
3. Set up static file serving
4. Use secure secret keys
5. Configure ALLOWED_HOSTS

### Railway Deployment

This application is configured for easy deployment on Railway using GitHub integration.

#### Prerequisites
- GitHub account
- Railway account (sign up at [railway.app](https://railway.app))

#### Deployment Steps

1. **Push to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/yourusername/your-repo-name.git
   git push -u origin main
   ```

2. **Connect to Railway**
   - Go to [Railway Dashboard](https://railway.app/dashboard)
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository
   - Railway will auto-detect Django and deploy

3. **Environment Variables**
   In Railway project settings, add these variables:
   ```
   SEMILATTICE_API_KEY=your_semilattice_api_key
   SEMILATTICE_BASE=https://api.semilattice.ai
   SECRET_KEY=your-secure-django-secret-key
   DEBUG=False
   ALLOWED_HOSTS=your-app-name.up.railway.app
   ```

4. **Database**
   - Railway automatically provisions PostgreSQL
   - The app will use the `DATABASE_URL` environment variable

5. **Static Files**
   - WhiteNoise is configured for static file serving
   - Files are automatically collected during deployment

6. **Access Your App**
   - Once deployed, Railway provides a URL like `https://your-app-name.up.railway.app`
   - Visit the URL to access your Semilattice demo

#### Troubleshooting
- Check Railway build logs for any errors
- Ensure all environment variables are set correctly
- For database issues, verify migrations ran successfully
- Static files should be served automatically via WhiteNoise

## Support

For API-related questions, see the [Semilattice Documentation](https://docs.semilattice.ai/).

For application issues, check the Django logs and ensure your API key has proper permissions.
