from app import db
from app.models.job import Job
from app.models.log import Log
from app.models.credential import Credential
from app.jobs.sftp_transfer import SftpTransfer
from app.jobs.sql_to_csv import SqlToCsv
import traceback
from datetime import datetime

def execute_job(job_id):
    """Execute a job by ID."""
    job = Job.query.get(job_id)
    
    if not job:
        return False
    
    # Skip if job is not active
    if not job.is_active:
        return False
    
    try:
        # Update job status to running
        job.update_status('running')
        
        # Log job start
        Log.create_log(job.id, 'info', f"Job '{job.name}' started")
        
        # Load source and destination credentials
        source_cred = Credential.query.get(job.source_credential_id)
        dest_cred = Credential.query.get(job.destination_credential_id)
        
        if not source_cred or not dest_cred:
            raise ValueError("Source or destination credentials not found")
        
        # Execute based on job type
        if job.job_type == 'sftp_transfer':
            executor = SftpTransfer(job, source_cred, dest_cred)
            result = executor.execute()
        elif job.job_type == 'sql_to_csv':
            executor = SqlToCsv(job, source_cred, dest_cred)
            result = executor.execute()
        else:
            raise ValueError(f"Unknown job type: {job.job_type}")
        
        # Update job status
        job.update_status('success')
        
        # Log job completion
        if isinstance(result, dict):
            message = result.get('message', 'Job completed successfully')
            details = result.get('details')
            Log.create_log(job.id, 'success', message, details)
        else:
            Log.create_log(job.id, 'success', 'Job completed successfully')
        
        return True
        
    except Exception as e:
        # Log error
        error_details = traceback.format_exc()
        Log.create_log(job.id, 'failure', f"Job failed: {str(e)}", error_details)
        
        # Update job status
        job.update_status('failure')
        
        return False
