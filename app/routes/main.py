from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from app.models.job import Job
from app.models.log import Log
from app import db
from sqlalchemy import desc, func
from datetime import datetime, timedelta

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html', title='Welcome')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    # Get job statistics
    total_jobs = Job.query.filter_by(user_id=current_user.id).count()
    active_jobs = Job.query.filter_by(user_id=current_user.id, is_active=True).count()
    
    # Get recent jobs
    recent_jobs = Job.query.filter_by(user_id=current_user.id).order_by(desc(Job.updated_at)).limit(5).all()
    
    # Get recent logs
    recent_logs = db.session.query(Log).join(Job).filter(Job.user_id == current_user.id).order_by(desc(Log.timestamp)).limit(10).all()
    
    # Calculate success rate for the last 24 hours
    yesterday = datetime.utcnow() - timedelta(days=1)
    success_logs = db.session.query(func.count(Log.id)).join(Job).filter(
        Job.user_id == current_user.id,
        Log.status == 'success',
        Log.timestamp > yesterday
    ).scalar() or 0
    
    failure_logs = db.session.query(func.count(Log.id)).join(Job).filter(
        Job.user_id == current_user.id,
        Log.status == 'failure',
        Log.timestamp > yesterday
    ).scalar() or 0
    
    total_logs = success_logs + failure_logs
    success_rate = (success_logs / total_logs * 100) if total_logs > 0 else 0
    
    return render_template('dashboard.html', 
                           title='Dashboard',
                           total_jobs=total_jobs,
                           active_jobs=active_jobs,
                           recent_jobs=recent_jobs,
                           recent_logs=recent_logs,
                           success_rate=success_rate)
