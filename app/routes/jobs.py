from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db, scheduler
from app.models.job import Job
from app.models.credential import Credential
from app.models.log import Log
from app.forms.job import JobForm, SftpTransferConfigForm, SqlToCsvConfigForm
from app.jobs.executor import execute_job
from sqlalchemy import desc
import json
from datetime import datetime

jobs_bp = Blueprint('jobs', __name__)

@jobs_bp.route('/')
@login_required
def index():
    jobs = Job.query.filter_by(user_id=current_user.id).order_by(Job.name).all()
    return render_template('jobs/index.html', title='Jobs', jobs=jobs)

@jobs_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    form = JobForm()
    # Populate credential choices
    form.source_credential_id.choices = [(c.id, c.name) for c in 
        Credential.query.filter_by(user_id=current_user.id).order_by(Credential.name)]
    form.destination_credential_id.choices = [(c.id, c.name) for c in 
        Credential.query.filter_by(user_id=current_user.id).order_by(Credential.name)]
    
    if form.validate_on_submit():
        job = Job(
            name=form.name.data,
            description=form.description.data,
            job_type=form.job_type.data,
            schedule=form.schedule.data,
            is_active=form.is_active.data,
            user_id=current_user.id,
            source_credential_id=form.source_credential_id.data,
            destination_credential_id=form.destination_credential_id.data
        )
        
        # Set default config based on job type
        if form.job_type.data == 'sftp_transfer':
            config = {
                'source_directory': form.source_directory.data or '',
                'destination_directory': form.destination_directory.data or '',
                'file_pattern': form.file_pattern.data or '*',
                'file_rename_pattern': '',
                'recursive': False,
                'create_directories': True,
                'overwrite_existing': False,
                'delete_after_download': False,
                'max_file_age_days': 0,
                'max_files_per_run': 0,
                'fail_on_empty': False,
                'preserve_timestamps': True
            }
        elif form.job_type.data == 'sql_to_csv':
            config = {
                'sql_query': '',
                'output_file': '',
                'destination_path': '',
                'csv_delimiter': ',',
                'include_headers': True
            }
        
        job.set_config(config)
        db.session.add(job)
        db.session.commit()
        
        flash('Job created successfully!', 'success')
        return redirect(url_for('jobs.configure', job_id=job.id))
    
    return render_template('jobs/create.html', title='Create Job', form=form)

@jobs_bp.route('/<int:job_id>/configure', methods=['GET', 'POST'])
@login_required
def configure(job_id):
    job = Job.query.get_or_404(job_id)
    
    # Check ownership
    if job.user_id != current_user.id:
        flash('You do not have permission to access this job', 'danger')
        return redirect(url_for('jobs.index'))
    
    # Get the right form based on job type
    if job.job_type == 'sftp_transfer':
        # Get SFTP credentials for the user
        sftp_credentials = Credential.query.filter_by(
            user_id=current_user.id, 
            credential_type='sftp'
        ).all()
        
        # Create choices for select fields
        credential_choices = [(c.id, c.name) for c in sftp_credentials]
        
        form = SftpTransferConfigForm()
        form.source_credential_id.choices = credential_choices
        form.destination_credential_id.choices = credential_choices
        
        if request.method == 'GET':
            config = job.get_config()
            form.source_credential_id.data = config.get('source_credential_id')
            form.destination_credential_id.data = config.get('destination_credential_id')
            form.source_directory.data = config.get('source_directory', '')
            form.destination_directory.data = config.get('destination_directory', '')
            form.file_pattern.data = config.get('file_pattern', '*')
            form.file_rename_pattern.data = config.get('file_rename_pattern', '')
            form.recursive.data = config.get('recursive', False)
            form.create_directories.data = config.get('create_directories', True)
            form.overwrite_existing.data = config.get('overwrite_existing', False)
            form.delete_after_download.data = config.get('delete_after_download', False)
            form.max_file_age_days.data = config.get('max_file_age_days', 0)
            form.max_files_per_run.data = config.get('max_files_per_run', 0)
            form.fail_on_empty.data = config.get('fail_on_empty', False)
            form.preserve_timestamps.data = config.get('preserve_timestamps', True)
        
        if form.validate_on_submit():
            config = {
                'source_credential_id': form.source_credential_id.data,
                'destination_credential_id': form.destination_credential_id.data,
                'source_directory': form.source_directory.data,
                'destination_directory': form.destination_directory.data,
                'file_pattern': form.file_pattern.data,
                'file_rename_pattern': form.file_rename_pattern.data,
                'recursive': form.recursive.data,
                'create_directories': form.create_directories.data,
                'overwrite_existing': form.overwrite_existing.data,
                'delete_after_download': form.delete_after_download.data,
                'max_file_age_days': form.max_file_age_days.data,
                'max_files_per_run': form.max_files_per_run.data,
                'fail_on_empty': form.fail_on_empty.data,
                'preserve_timestamps': form.preserve_timestamps.data
            }
            job.set_config(config)
            db.session.commit()
            flash('Job configuration updated successfully!', 'success')
            return redirect(url_for('jobs.index'))
        
        return render_template(
            f'jobs/configure_{job.job_type}.html',
            title=f'Configure {job.name}',
            job=job,
            form=form,
            sftp_credentials=sftp_credentials
        )
        
    elif job.job_type == 'sql_to_csv':
        # Get MSSQL credentials for the user
        mssql_credentials = Credential.query.filter_by(
            user_id=current_user.id, 
            credential_type='mssql'
        ).all()
        
        # Get SFTP credentials for the user
        sftp_credentials = Credential.query.filter_by(
            user_id=current_user.id, 
            credential_type='sftp'
        ).all()
        
        # Create choices for select fields
        mssql_choices = [(c.id, c.name) for c in mssql_credentials]
        sftp_choices = [(c.id, c.name) for c in sftp_credentials]
        
        form = SqlToCsvConfigForm()
        form.source_credential_id.choices = mssql_choices
        form.destination_credential_id.choices = sftp_choices
        
        if request.method == 'GET':
            config = job.get_config()
            form.source_credential_id.data = config.get('source_credential_id')
            form.destination_credential_id.data = config.get('destination_credential_id')
            form.sql_query.data = config.get('sql_query', '')
            form.output_file.data = config.get('output_file', '')
            form.destination_path.data = config.get('destination_path', '')
            form.csv_delimiter.data = config.get('csv_delimiter', ',')
            form.include_headers.data = config.get('include_headers', True)
        
        if form.validate_on_submit():
            config = {
                'source_credential_id': form.source_credential_id.data,
                'destination_credential_id': form.destination_credential_id.data,
                'sql_query': form.sql_query.data,
                'output_file': form.output_file.data,
                'destination_path': form.destination_path.data,
                'csv_delimiter': form.csv_delimiter.data,
                'include_headers': form.include_headers.data
            }
            job.set_config(config)
            db.session.commit()
            flash('Job configuration updated successfully!', 'success')
            return redirect(url_for('jobs.index'))
            
        return render_template(
            f'jobs/configure_{job.job_type}.html',
            title=f'Configure {job.name}',
            job=job,
            form=form,
            mssql_credentials=mssql_credentials,
            sftp_credentials=sftp_credentials
        )
    
    # Generic fallback for unknown job types
    return render_template(
        f'jobs/configure_{job.job_type}.html',
        title=f'Configure {job.name}',
        job=job,
        form=form
    )

@jobs_bp.route('/<int:job_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(job_id):
    job = Job.query.get_or_404(job_id)
    
    # Check ownership
    if job.user_id != current_user.id:
        flash('You do not have permission to access this job', 'danger')
        return redirect(url_for('jobs.index'))
    
    form = JobForm()
    # Populate credential choices
    form.source_credential_id.choices = [(c.id, c.name) for c in 
        Credential.query.filter_by(user_id=current_user.id).order_by(Credential.name)]
    form.destination_credential_id.choices = [(c.id, c.name) for c in 
        Credential.query.filter_by(user_id=current_user.id).order_by(Credential.name)]
    
    if request.method == 'GET':
        form.name.data = job.name
        form.description.data = job.description
        form.job_type.data = job.job_type
        form.schedule.data = job.schedule
        form.is_active.data = job.is_active
        form.source_credential_id.data = job.source_credential_id
        form.destination_credential_id.data = job.destination_credential_id
    
    if form.validate_on_submit():
        job.name = form.name.data
        job.description = form.description.data
        job.schedule = form.schedule.data
        job.is_active = form.is_active.data
        job.source_credential_id = form.source_credential_id.data
        job.destination_credential_id = form.destination_credential_id.data
        
        db.session.commit()
        flash('Job updated successfully!', 'success')
        return redirect(url_for('jobs.index'))
    
    return render_template('jobs/edit.html', title='Edit Job', form=form, job=job)

@jobs_bp.route('/<int:job_id>/delete', methods=['POST'])
@login_required
def delete(job_id):
    job = Job.query.get_or_404(job_id)
    
    # Check ownership
    if job.user_id != current_user.id:
        flash('You do not have permission to access this job', 'danger')
        return redirect(url_for('jobs.index'))
    
    # Delete associated logs
    Log.query.filter_by(job_id=job.id).delete()
    
    # Delete job
    db.session.delete(job)
    db.session.commit()
    
    flash('Job deleted successfully!', 'success')
    return redirect(url_for('jobs.index'))

@jobs_bp.route('/<int:job_id>/toggle', methods=['POST'])
@login_required
def toggle(job_id):
    job = Job.query.get_or_404(job_id)
    
    # Check ownership
    if job.user_id != current_user.id:
        flash('You do not have permission to access this job', 'danger')
        return redirect(url_for('jobs.index'))
    
    job.is_active = not job.is_active
    db.session.commit()
    
    status = 'activated' if job.is_active else 'deactivated'
    flash(f'Job {status} successfully!', 'success')
    return redirect(url_for('jobs.index'))

@jobs_bp.route('/<int:job_id>/run', methods=['POST'])
@login_required
def run(job_id):
    job = Job.query.get_or_404(job_id)
    
    # Check ownership
    if job.user_id != current_user.id:
        flash('You do not have permission to access this job', 'danger')
        return redirect(url_for('jobs.index'))
    
    # Execute the job using Celery
    from app.tasks.job_tasks import execute_job
    task = execute_job.delay(job.id)
    
    # Store task ID in job metadata
    config = job.get_config()
    if 'task_ids' not in config:
        config['task_ids'] = []
    
    # Add task to the beginning of the list (most recent first)
    config['task_ids'].insert(0, {
        'id': task.id,
        'timestamp': datetime.utcnow().isoformat(),
        'status': 'PENDING'
    })
    
    # Keep only the last 10 task IDs
    if len(config['task_ids']) > 10:
        config['task_ids'] = config['task_ids'][:10]
    
    job.set_config(config)
    db.session.commit()
    
    flash('Job execution started!', 'success')
    return redirect(url_for('jobs.view', job_id=job.id))

@jobs_bp.route('/<int:job_id>')
@login_required
def view(job_id):
    job = Job.query.get_or_404(job_id)
    
    # Check ownership
    if job.user_id != current_user.id:
        flash('You do not have permission to access this job', 'danger')
        return redirect(url_for('jobs.index'))
    
    # Get recent logs for this job
    logs = Log.query.filter_by(job_id=job.id).order_by(desc(Log.timestamp)).limit(20).all()
    
    return render_template('jobs/view.html', title=job.name, job=job, logs=logs)

@jobs_bp.route('/<int:job_id>/logs')
@login_required
def logs(job_id):
    job = Job.query.get_or_404(job_id)
    
    # Check ownership
    if job.user_id != current_user.id:
        flash('You do not have permission to access this job', 'danger')
        return redirect(url_for('jobs.index'))
    
    page = request.args.get('page', 1, type=int)
    logs_pagination = Log.query.filter_by(job_id=job.id).order_by(
        desc(Log.timestamp)).paginate(page=page, per_page=20)
    
    return render_template('jobs/logs.html', title=f'Logs - {job.name}', 
                          job=job, logs=logs_pagination)
