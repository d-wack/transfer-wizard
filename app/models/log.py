from app import db
from datetime import datetime

class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False)  # 'success', 'failure', 'warning'
    message = db.Column(db.Text, nullable=False)
    details = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Log {self.id} - {self.status}>'
    
    @staticmethod
    def create_log(job_id, status, message, details=None):
        """Create a new log entry."""
        log = Log(job_id=job_id, status=status, message=message, details=details)
        db.session.add(log)
        db.session.commit()
        return log
