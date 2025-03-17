from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_apscheduler import APScheduler
from config import Config
from loguru import logger
import os
import sys
import datetime
import logging

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'
bcrypt = Bcrypt()
scheduler = APScheduler()

# Create Celery instance (imported, not initialized)
from app.celery_app import celery_app as celery

# Configure loguru
logger.remove()  # Remove default handler
logger.add(sys.stderr, level="INFO")  # Add stderr handler with INFO level
logger.add("logs/transferwizard_{time:%Y-%m-%d_%H-%M-%S_%f}.log", 
           rotation="500 MB", 
           retention="10 days", 
           level="DEBUG")

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Simplified logging setup to avoid recursion issues
    # Configure app.logger to write to a file
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Don't attempt complex logger integration which caused recursion
    logger.info("Application starting up")
    
    # Ensure instance folders exist
    for folder in [app.config['UPLOAD_FOLDER'], app.config['TEMP_FOLDER']]:
        if not os.path.exists(folder):
            os.makedirs(folder)
        
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    
    # Initialize scheduler only in web container (not in Celery workers)
    # This prevents SchedulerAlreadyRunningError in workers
    if os.environ.get('CONTAINER_TYPE') != 'worker':
        scheduler.init_app(app)
    
    # Configure Celery with app context
    celery.conf.update(app.config)
    
    # Import and register blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.jobs import jobs_bp
    from app.routes.credentials import credentials_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(jobs_bp, url_prefix='/jobs')
    app.register_blueprint(credentials_bp, url_prefix='/credentials')
    
    # Add context processors
    @app.context_processor
    def inject_now():
        return {'now': datetime.datetime.now()}
    
    # Start scheduler
    if os.environ.get('CONTAINER_TYPE') != 'worker':
        scheduler.start()
    
    logger.info(f"Application started with environment: {app.config.get('ENV', 'development')}")
    
    return app

# Import models to ensure they are registered with SQLAlchemy
from app.models import user, job, credential, log
