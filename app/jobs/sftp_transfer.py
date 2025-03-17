import os
import pysftp
import fnmatch
import tempfile
from paramiko.ssh_exception import SSHException
import datetime
import uuid
import random

class SftpTransfer:
    """Handler for SFTP to SFTP file transfers."""
    
    def __init__(self, job, source_credential, destination_credential):
        self.job = job
        self.source_credential = source_credential
        self.destination_credential = destination_credential
        self.config = job.get_config()
        self.transferred_files = []
        
    def execute(self):
        """Execute the SFTP transfer job."""
        # Get configuration
        source_path = self.config.get('source_directory') or self.config.get('source_path')
        dest_path = self.config.get('destination_directory') or self.config.get('destination_path')
        file_pattern = self.config.get('file_pattern', '*')
        delete_after = self.config.get('delete_after_transfer', False)
        file_rename_pattern = self.config.get('file_rename_pattern', '')
        
        if not source_path or not dest_path:
            raise ValueError("Source or destination path not specified")
        
        # Create temporary directory for file transfers
        with tempfile.TemporaryDirectory() as temp_dir:
            # Connect to source SFTP
            source_files = self._download_from_source(source_path, temp_dir, file_pattern)
            
            if not source_files:
                return {
                    'message': 'No files found matching the pattern',
                    'details': f"Path: {source_path}, Pattern: {file_pattern}"
                }
            
            # Upload to destination SFTP
            self._upload_to_destination(temp_dir, dest_path, source_files, file_rename_pattern)
            
            # Delete source files if configured
            if delete_after and self.transferred_files:
                self._delete_source_files(source_path)
        
        return {
            'message': f'Successfully transferred {len(self.transferred_files)} files',
            'details': '\n'.join(self.transferred_files),
            'files': self.transferred_files
        }
    
    def _download_from_source(self, source_path, temp_dir, file_pattern):
        """Download files from source SFTP to local temp directory."""
        source_creds = self.source_credential.get_credentials()
        source_files = []
        
        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None  # Disable host key checking - not recommended for production
        
        # Setup connection parameters
        conn_params = {
            'host': source_creds.get('host'),
            'port': source_creds.get('port', 22),
            'username': source_creds.get('username'),
            'cnopts': cnopts
        }
        
        # Add either password or private key
        if source_creds.get('password'):
            conn_params['password'] = source_creds.get('password')
        elif source_creds.get('private_key'):
            private_key_file = os.path.join(temp_dir, 'source_key')
            with open(private_key_file, 'w') as f:
                f.write(source_creds.get('private_key'))
            os.chmod(private_key_file, 0o600)
            conn_params['private_key'] = private_key_file
            if source_creds.get('private_key_pass'):
                conn_params['private_key_pass'] = source_creds.get('private_key_pass')
        
        try:
            with pysftp.Connection(**conn_params) as sftp:
                # Check if source is a directory or file
                if sftp.isdir(source_path):
                    # List directory and filter by pattern
                    all_files = sftp.listdir(source_path)
                    matching_files = [f for f in all_files if fnmatch.fnmatch(f, file_pattern)]
                    
                    # Download each matching file
                    for filename in matching_files:
                        remote_path = os.path.join(source_path, filename).replace('\\', '/')
                        local_path = os.path.join(temp_dir, filename)
                        sftp.get(remote_path, local_path)
                        source_files.append(filename)
                else:
                    # Single file - check if it matches pattern
                    filename = os.path.basename(source_path)
                    if fnmatch.fnmatch(filename, file_pattern):
                        local_path = os.path.join(temp_dir, filename)
                        sftp.get(source_path, local_path)
                        source_files.append(filename)
        except SSHException as e:
            raise RuntimeError(f"SFTP connection error: {str(e)}")
        
        return source_files
    
    def _upload_to_destination(self, temp_dir, dest_path, filenames, file_rename_pattern=None):
        """Upload files from local temp directory to destination SFTP."""
        dest_creds = self.destination_credential.get_credentials()
        
        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None  # Disable host key checking - not recommended for production
        
        # Setup connection parameters
        conn_params = {
            'host': dest_creds.get('host'),
            'port': dest_creds.get('port', 22),
            'username': dest_creds.get('username'),
            'cnopts': cnopts
        }
        
        # Add either password or private key
        if dest_creds.get('password'):
            conn_params['password'] = dest_creds.get('password')
        elif dest_creds.get('private_key'):
            private_key_file = os.path.join(temp_dir, 'dest_key')
            with open(private_key_file, 'w') as f:
                f.write(dest_creds.get('private_key'))
            os.chmod(private_key_file, 0o600)
            conn_params['private_key'] = private_key_file
            if dest_creds.get('private_key_pass'):
                conn_params['private_key_pass'] = dest_creds.get('private_key_pass')
        
        try:
            with pysftp.Connection(**conn_params) as sftp:
                # Ensure destination directory exists
                if not sftp.exists(dest_path):
                    sftp.makedirs(dest_path)
                
                # Upload each file
                for filename in filenames:
                    local_path = os.path.join(temp_dir, filename)
                    
                    # Apply rename pattern if provided
                    dest_filename = self._apply_rename_pattern(filename, file_rename_pattern)
                    remote_path = os.path.join(dest_path, dest_filename).replace('\\', '/')
                    
                    # Get file size for logging
                    file_size = os.path.getsize(local_path)
                    
                    # Log the transfer
                    if filename != dest_filename and file_rename_pattern:
                        print(f"Transferring file: {filename} as {dest_filename} ({self._format_size(file_size)})")
                        self.transferred_files.append(f"{filename} → {dest_filename} ({self._format_size(file_size)})")
                    else:
                        print(f"Transferring file: {filename} ({self._format_size(file_size)})")
                        self.transferred_files.append(f"{filename} ({self._format_size(file_size)})")
                    
                    # Upload the file
                    sftp.put(local_path, remote_path)
                    
        except SSHException as e:
            raise RuntimeError(f"SFTP connection error: {str(e)}")
    
    def _delete_source_files(self, source_path):
        """Delete files from source SFTP after successful transfer."""
        source_creds = self.source_credential.get_credentials()
        
        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None  # Disable host key checking - not recommended for production
        
        # Setup connection parameters
        conn_params = {
            'host': source_creds.get('host'),
            'port': source_creds.get('port', 22),
            'username': source_creds.get('username'),
            'cnopts': cnopts
        }
        
        # Add either password or private key
        if source_creds.get('password'):
            conn_params['password'] = source_creds.get('password')
        elif source_creds.get('private_key'):
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as key_file:
                key_file.write(source_creds.get('private_key'))
                key_path = key_file.name
            os.chmod(key_path, 0o600)
            conn_params['private_key'] = key_path
            if source_creds.get('private_key_pass'):
                conn_params['private_key_pass'] = source_creds.get('private_key_pass')
        
        try:
            with pysftp.Connection(**conn_params) as sftp:
                # Delete each transferred file
                for filename in self.transferred_files:
                    if sftp.isdir(source_path):
                        remote_path = os.path.join(source_path, filename).replace('\\', '/')
                    else:
                        remote_path = source_path
                    
                    if sftp.exists(remote_path):
                        sftp.remove(remote_path)
        except SSHException as e:
            raise RuntimeError(f"SFTP connection error during cleanup: {str(e)}")
        finally:
            # Clean up temp key file if it was created
            if source_creds.get('private_key') and 'key_path' in locals():
                os.unlink(key_path)
    
    def _apply_rename_pattern(self, filename, rename_pattern):
        """Apply rename pattern to filename."""
        if not rename_pattern:
            return filename
            
        # Get file parts
        basename, extension = os.path.splitext(filename)
        
        # Define replacement variables
        replacements = {
            '{filename}': filename,
            '{basename}': basename,
            '{ext}': extension,
            '{timestamp}': datetime.datetime.now().strftime('%Y%m%d%H%M%S'),
            '{date}': datetime.datetime.now().strftime('%Y%m%d'),
            '{time}': datetime.datetime.now().strftime('%H%M%S'),
            '{uuid}': str(uuid.uuid4()),
            '{random}': ''.join(random.choices('0123456789abcdef', k=8))
        }
        
        # Apply replacements
        new_filename = rename_pattern
        for key, value in replacements.items():
            new_filename = new_filename.replace(key, value)
            
        # If the pattern didn't result in any changes, return original
        if new_filename == rename_pattern:
            return filename
            
        return new_filename
    
    def _format_size(self, size_bytes):
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"
