from app import db
from datetime import datetime
import json

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    job_type = db.Column(db.String(50), nullable=False)  # 'sftp_transfer', 'sql_to_csv'
    schedule = db.Column(db.String(100))  # Cron expression
    is_active = db.Column(db.Boolean, default=True)
    config = db.Column(db.Text, nullable=False)  # JSON configuration
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_run = db.Column(db.DateTime)
    last_status = db.Column(db.String(20))  # 'success', 'failure', 'running', 'pending'
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    source_credential_id = db.Column(db.Integer, db.ForeignKey('credential.id'))
    destination_credential_id = db.Column(db.Integer, db.ForeignKey('credential.id'))
    
    # Relationships
    logs = db.relationship('Log', backref='job', lazy='dynamic')
    source_credential = db.relationship('Credential', foreign_keys=[source_credential_id])
    destination_credential = db.relationship('Credential', foreign_keys=[destination_credential_id])
    
    def __repr__(self):
        return f'<Job {self.name}>'
    
    def get_config(self):
        """Deserialize the JSON configuration."""
        return json.loads(self.config)
    
    def set_config(self, config_dict):
        """Serialize the configuration as JSON."""
        self.config = json.dumps(config_dict)
    
    def update_status(self, status):
        """Update the job status and last run time."""
        self.last_status = status
        if status != 'running':
            self.last_run = datetime.utcnow()
        db.session.commit()
