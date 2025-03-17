"""
Celery tasks for job execution. These tasks run in separate worker processes
and are responsible for executing the actual job logic.
"""
from app.celery_app import celery_app
from app.jobs.sftp_transfer import SftpTransfer
from app.jobs.sql_to_csv import SqlToCsv
from datetime import datetime
from loguru import logger
import os
import sys
import traceback
import json

# Configure loguru for task logging
task_log_dir = os.path.join('logs', 'tasks')
if not os.path.exists(task_log_dir):
    os.makedirs(task_log_dir, exist_ok=True)
    print(f"Created log directory: {task_log_dir}")

# Print absolute path to task log directory for debugging
abs_log_dir = os.path.abspath(task_log_dir)
print(f"Absolute log directory path: {abs_log_dir}")

# Remove default logger and configure task-specific logger
logger.remove()
logger.add(sys.stderr, level="INFO")
try:
    # Add a general task log file with full timestamp
    log_file = os.path.join(task_log_dir, "job_{time:YYYY-MM-DD_HH-mm-ss}.log")
    print(f"Adding general log file: {log_file}")
    logger.add(
        log_file,
        rotation="500 MB", 
        retention="10 days", 
        level="DEBUG",
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    print("Logger configured successfully")
except Exception as e:
    print(f"Error configuring logger: {str(e)}")
    print(traceback.format_exc())

@celery_app.task(bind=True, name='execute_job')
def execute_job(self, job_id):
    """
    Execute a job by ID. This task runs in a separate process from the main application.
    
    Args:
        job_id (int): The ID of the job to execute
        
    Returns:
        dict: A dictionary containing the job execution results
    """
    print(f"Starting execute_job task for job ID: {job_id}")
    
    from app.models.job import Job
    from app.models.credential import Credential
    from app.models.log import Log
    from app import db, create_app
    
    # Create Flask app instance and app context
    print("Creating Flask application...")
    app = create_app()
    print(f"Flask app created: {app}")
    
    task_id = self.request.id
    print(f"Task ID: {task_id}")
    
    job_logger = logger.bind(job_id=job_id, task_id=task_id)
    job_logger.info(f"Starting job execution task {task_id} for job ID: {job_id}")
    print(f"Basic logging initialized for job ID: {job_id}, task ID: {task_id}")
    
    # Add job-specific log file
    try:
        job_log_file = os.path.join(task_log_dir, f"job_{job_id}_{task_id}.log")
        print(f"Adding job-specific log file: {job_log_file}")
        job_logger.add(
            job_log_file, 
            level="DEBUG",
            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <blue>Job {extra[job_id]}</blue> - <level>{message}</level>"
        )
        print(f"Job-specific logger configured with file: {job_log_file}")
    except Exception as e:
        print(f"Error setting up job-specific log file: {str(e)}")
        print(traceback.format_exc())
    
    # Initialize result dictionary with default values
    result = {
        'job_id': job_id,
        'task_id': task_id,
        'status': 'failure',
        'start_time': datetime.utcnow().isoformat(),
        'end_time': None,
        'message': None,
        'details': None,
        'error': None
    }
    
    # Create application context
    with app.app_context():
        try:
            # Get job from database
            job = Job.query.get(job_id)
            
            if not job:
                result['message'] = f"Job with ID {job_id} not found"
                result['error'] = "Job not found"
                return result
            
            # Skip if job is not active
            if not job.is_active:
                result['message'] = f"Job '{job.name}' is not active"
                result['status'] = 'skipped'
                return result
            
            # Update job status to running
            job.update_status('running')
            db.session.commit()
            
            # Log job start
            Log.create_log(job.id, 'info', f"Job '{job.name}' started (Task ID: {task_id})")
            job_logger.info(f"Executing job '{job.name}' (ID: {job_id})")
            
            # Load source and destination credentials
            source_cred = Credential.query.get(job.source_credential_id)
            dest_cred = Credential.query.get(job.destination_credential_id)
            
            if not source_cred or not dest_cred:
                raise ValueError("Source or destination credentials not found")
            
            # Execute based on job type
            if job.job_type == 'sftp_transfer':
                job_logger.info(f"Running SFTP transfer job '{job.name}'")
                job_logger.debug(f"Source path: {job.get_config().get('source_directory', '/')}")
                job_logger.debug(f"Destination path: {job.get_config().get('destination_directory', '/')}")
                job_logger.debug(f"File pattern: {job.get_config().get('file_pattern', '*')}")
                executor = SftpTransfer(job, source_cred, dest_cred)
                execution_result = executor.execute()
                job_logger.info(f"SFTP transfer complete: {execution_result['message']}")
            elif job.job_type == 'sql_to_csv':
                job_logger.info(f"Running SQL to CSV job '{job.name}'")
                job_logger.debug(f"SQL Query: {job.get_config().get('sql_query', '')[:100]}...")
                job_logger.debug(f"Output path: {job.get_config().get('output_path', '')}")
                executor = SqlToCsv(job, source_cred, dest_cred)
                execution_result = executor.execute()
                job_logger.info(f"SQL to CSV export complete: {execution_result['message']}")
            else:
                raise ValueError(f"Unknown job type: {job.job_type}")
            
            # Update job status
            job.update_status('success')
            db.session.commit()
            
            # Log more detailed success message if files were transferred
            if 'files' in execution_result and execution_result['files']:
                files_str = ', '.join(execution_result['files'])
                job_logger.info(f"Files transferred: {files_str}")
                
                # Create a log entry in the database
                Log.create_log(
                    job_id, 
                    'info', 
                    f"Files transferred: {files_str}", 
                    execution_result.get('details', '')
                )
            
            # Update result with execution output
            result['status'] = 'success'
            
            # Log job completion
            if isinstance(execution_result, dict):
                message = execution_result.get('message', 'Job completed successfully')
                details = execution_result.get('details')
                Log.create_log(job.id, 'success', message, details)
                job_logger.info(f"Job completed successfully: {message}")
                
                # Add execution details to result
                result['message'] = message
                result['details'] = details
            else:
                Log.create_log(job.id, 'success', 'Job completed successfully')
                job_logger.info("Job completed successfully")
                result['message'] = 'Job completed successfully'
            
        except Exception as e:
            # Get error details
            error_details = traceback.format_exc()
            error_message = str(e)
            
            # Log error
            job_logger.error(f"Job execution failed: {error_message}")
            job_logger.error(error_details)
            
            try:
                # Log to database if possible
                Log.create_log(job_id, 'failure', f"Job failed: {error_message}", error_details)
                
                # Update job status if we can access the job
                if 'job' in locals() and job is not None:
                    job.update_status('failure')
                    db.session.commit()
            except Exception as log_error:
                # If database logging fails, just log to file
                job_logger.error(f"Failed to log to database: {str(log_error)}")
            
            # Update result with error details
            result['message'] = f"Job failed: {error_message}"
            result['error'] = error_message
            result['details'] = error_details
    
    # Add end time
    result['end_time'] = datetime.utcnow().isoformat()
    
    # Log completion
    job_logger.info(f"Job execution task {task_id} completed with status: {result['status']}")
    
    # Update task status in job configuration
    try:
        # Re-query the job from the database to ensure it's bound to the session
        with app.app_context():
            job_fresh = Job.query.get(job_id)
            if job_fresh:
                # Update task status in the config
                job_config = job_fresh.get_config()
                if 'task_ids' in job_config:
                    for task_info in job_config['task_ids']:
                        if task_info.get('id') == task_id:
                            task_info['status'] = result['status']
                            break
                    job_fresh.set_config(job_config)
                    db.session.commit()
                    job_logger.info(f"Updated task status in job configuration to {result['status']}")
    except Exception as config_error:
        job_logger.error(f"Failed to update task status in job configuration: {str(config_error)}")
    
    return result
