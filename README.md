# TransferWizard

A Flask-based web application for managing and automating file transfers between SFTP servers with real-time job status updates.

## Features

- SFTP-to-SFTP file transfers
- SQL-to-CSV exports with SFTP uploads
- Real-time job status updates without page refreshes
- Dynamic file renaming with pattern support
- Daily reporting on transfer job statuses
- User-friendly dashboard
- Secure credential storage
- Job scheduling and management

## Installation

### Using Docker (Recommended)

1. Clone the repository
    ```
    git clone https://github.com/d-wack/transfer-wizard.git
    cd transfer-wizard
    ```

2. Edit the `docker-compose.yml` file to configure environment variables

3. Build and start the containers
    ```
    docker-compose up -d
    ```

4. Access the application at http://localhost:5000

### Manual Installation

1. Clone the repository
    ```
    git clone https://github.com/d-wack/transfer-wizard.git
    cd transfer-wizard
    ```

2. Create a virtual environment:
    ```
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3. Install dependencies:
    ```
    pip install -r requirements.txt
    ```

4. Create a `.env` file with necessary environment variables

5. Initialize the database:
    ```
    flask db init
    flask db migrate -m "Initial migration"
    flask db upgrade
    ```

6. Run the application:
    ```
    flask run
    ```

## Environment Variables

Create a `.env` file in the root directory with the following variables:
```
SECRET_KEY=your_secret_key
FLASK_APP=run.py
FLASK_ENV=development
DATABASE_URL=sqlite:///app.db
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
CONTAINER_TYPE=web  # Set to 'worker' for Celery worker containers
```

## Docker Configuration

The application is containerized using Docker and can be deployed with docker-compose. The following services are defined:

- **web**: Flask web application
- **worker**: Celery worker for job processing
- **redis**: Message broker for Celery
- **db**: PostgreSQL database

## Usage

1. Login to the dashboard
2. Configure your SFTP servers and database connections
3. Create transfer jobs with optional file renaming patterns
4. Monitor job status through the dashboard in real-time
5. Receive daily reports via email

## Job Status Monitoring

TransferWizard features real-time job status updates without requiring page refreshes. The status badges update automatically as jobs progress from running to completion.

## File Renaming Patterns

When creating a job, you can specify file renaming patterns with the following placeholders:
- `{filename}` - Original filename
- `{timestamp}` - Current timestamp
- `{uuid}` - Unique identifier
- `{date}` - Current date

Example: `{filename}-backup-{date}` would rename `data.csv` to `data.csv-backup-20250317`

## License

MIT License
