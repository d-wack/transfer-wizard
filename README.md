# TransferWizard

A Flask-based web application for managing and automating file transfer jobs between SFTP servers and SQL-to-CSV exports.

## Features

- SFTP-to-SFTP file transfers
- SQL-to-CSV exports with SFTP uploads
- Daily reporting on transfer job statuses
- User-friendly dashboard
- Secure credential storage
- Job scheduling and management

## Installation

1. Clone the repository
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
```

## Usage

1. Login to the dashboard
2. Configure your SFTP servers and database connections
3. Create transfer jobs
4. Monitor job status through the dashboard
5. Receive daily reports via email

## License

MIT License
