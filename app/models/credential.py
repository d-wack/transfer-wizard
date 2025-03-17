from app import db
from datetime import datetime
from cryptography.fernet import Fernet
import os
import json

# Ensure encryption key exists
def get_or_create_key():
    key_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'instance', 'enc_key')
    if os.path.exists(key_file):
        with open(key_file, 'rb') as f:
            return f.read()
    else:
        # Generate a new key
        key = Fernet.generate_key()
        os.makedirs(os.path.dirname(key_file), exist_ok=True)
        with open(key_file, 'wb') as f:
            f.write(key)
        # Set restrictive permissions
        os.chmod(key_file, 0o600)
        return key

# Initialize encryption cipher
encryption_key = get_or_create_key()
cipher_suite = Fernet(encryption_key)

class Credential(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    credential_type = db.Column(db.String(50), nullable=False)  # 'sftp', 'mssql', etc.
    encrypted_data = db.Column(db.LargeBinary, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def __repr__(self):
        return f'<Credential {self.name}>'
    
    def set_credentials(self, cred_dict):
        """Encrypt and store credentials."""
        json_data = json.dumps(cred_dict)
        self.encrypted_data = cipher_suite.encrypt(json_data.encode('utf-8'))
    
    def get_credentials(self):
        """Decrypt and return credentials."""
        decrypted_data = cipher_suite.decrypt(self.encrypted_data)
        return json.loads(decrypted_data.decode('utf-8'))
        
    @staticmethod
    def get_default_config(credential_type):
        """Return a default configuration template for a given credential type."""
        if credential_type == 'sftp':
            return {
                'host': '',
                'port': 22,
                'username': '',
                'password': '',
                'private_key': '',
                'private_key_pass': ''
            }
        elif credential_type == 'mssql':
            return {
                'server': '',
                'database': '',
                'username': '',
                'password': '',
                'port': 1433
            }
        else:
            return {}
