from app import scheduler, db
from app.models.job import Job
from app.jobs.executor import execute_job
from datetime import datetime, timedelta
import traceback
import logging

logger = logging.getLogger(__name__)

def initialize_jobs():
    """Initialize all active jobs in the scheduler."""
    try:
        # Load all active jobs from database
        active_jobs = Job.query.filter_by(is_active=True).all()
        
        # Clear existing jobs
        scheduler.remove_all_jobs()
        
        # Add each job to scheduler
        for job in active_jobs:
            if job.schedule:
                try:
                    scheduler.add_job(
                        func=execute_job,
                        trigger='cron',
                        id=f'job_{job.id}_{job.name}',
                        args=[job.id],
                        replace_existing=True,
                        **parse_cron_expression(job.schedule)
                    )
                    logger.info(f"Scheduled job {job.name} (ID: {job.id}) with schedule: {job.schedule}")
                except Exception as e:
                    logger.error(f"Error scheduling job {job.name} (ID: {job.id}): {str(e)}")
        
        # Add daily report job
        scheduler.add_job(
            func=generate_daily_report,
            trigger='cron',
            id='daily_report',
            hour=0,
            minute=0,
            replace_existing=True
        )
        
        return True
    except Exception as e:
        logger.error(f"Error initializing scheduler: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def parse_cron_expression(cron_expr):
    """Parse a cron expression into kwargs for APScheduler."""
    # Basic parsing for common cron expressions
    parts = cron_expr.split()
    
    if len(parts) != 5:
        raise ValueError("Invalid cron expression format. Expected 5 parts: minute hour day_of_month month day_of_week")
    
    return {
        'minute': parts[0],
        'hour': parts[1],
        'day': parts[2],
        'month': parts[3],
        'day_of_week': parts[4]
    }

def update_job_schedule(job_id):
    """Update a job's schedule in the scheduler."""
    job = Job.query.get(job_id)
    if not job:
        return False
    
    # Remove existing job from scheduler
    try:
        scheduler.remove_job(f'job_{job.id}_{job.name}')
    except:
        pass  # Job may not exist in scheduler
    
    # If job is active and has a schedule, add it to scheduler
    if job.is_active and job.schedule:
        try:
            scheduler.add_job(
                func=execute_job,
                trigger='cron',
                id=f'job_{job.id}_{job.name}',
                args=[job.id],
                replace_existing=True,
                **parse_cron_expression(job.schedule)
            )
            return True
        except Exception as e:
            logger.error(f"Error scheduling job {job.name} (ID: {job.id}): {str(e)}")
            return False
    
    return True

def generate_daily_report():
    """Generate a daily report of job executions."""
    from app.models.log import Log
    from app.models.user import User
    from app.utils.email import send_email
    
    # Get yesterday's date range
    today = datetime.utcnow().date()
    yesterday = today - timedelta(days=1)
    start_time = datetime.combine(yesterday, datetime.min.time())
    end_time = datetime.combine(yesterday, datetime.max.time())
    
    # Get all logs from yesterday
    logs = Log.query.filter(Log.timestamp.between(start_time, end_time)).all()
    
    # Group by job
    job_results = {}
    for log in logs:
        job_id = log.job_id
        if job_id not in job_results:
            job = Job.query.get(job_id)
            if job:
                job_results[job_id] = {
                    'job': job,
                    'success': 0,
                    'failure': 0,
                    'warning': 0,
                    'info': 0,
                    'last_message': None,
                    'last_status': None
                }
        
        if job_id in job_results:
            job_results[job_id][log.status] += 1
            
            # Update last message and status if this is the most recent log
            if not job_results[job_id]['last_message'] or log.timestamp > job_results[job_id]['last_message']:
                job_results[job_id]['last_message'] = log.timestamp
                job_results[job_id]['last_status'] = log.status
    
    # TODO: Generate report and send to admins
    # This would typically involve creating an HTML email with the job results
    # For now, we'll just log the report
    logger.info(f"Daily job report for {yesterday}: {len(job_results)} jobs executed")
    
    # In a complete implementation, you would send this report via email to admin users
