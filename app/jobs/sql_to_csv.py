import os
import csv
import pymssql
import pysftp
import tempfile
import pandas as pd
from paramiko.ssh_exception import SSHException

class SqlToCsv:
    """Handler for SQL query to CSV file export and SFTP upload."""
    
    def __init__(self, job, source_credential, destination_credential):
        self.job = job
        self.source_credential = source_credential
        self.destination_credential = destination_credential
        self.config = job.get_config()
        self.csv_file = None
        
    def execute(self):
        """Execute the SQL to CSV job."""
        # Get configuration
        sql_query = self.config.get('sql_query')
        output_file = self.config.get('output_file')
        dest_path = self.config.get('destination_path')
        csv_delimiter = self.config.get('csv_delimiter', ',')
        include_headers = self.config.get('include_headers', True)
        
        if not sql_query or not output_file or not dest_path:
            raise ValueError("SQL query, output file, or destination path not specified")
        
        # Create temporary directory for file transfer
        with tempfile.TemporaryDirectory() as temp_dir:
            # Execute SQL query and save as CSV
            local_csv_path = self._execute_sql_query(sql_query, temp_dir, output_file, csv_delimiter, include_headers)
            
            # Upload CSV to destination SFTP
            self._upload_to_sftp(local_csv_path, dest_path, output_file)
        
        return {
            'message': f'Successfully exported SQL query to CSV and uploaded to SFTP',
            'details': f'File: {output_file}, Destination: {dest_path}'
        }
    
    def _execute_sql_query(self, sql_query, temp_dir, output_file, csv_delimiter, include_headers):
        """Execute SQL query and save results as CSV."""
        source_creds = self.source_credential.get_credentials()
        
        # Ensure output file has .csv extension
        if not output_file.lower().endswith('.csv'):
            output_file += '.csv'
        
        local_csv_path = os.path.join(temp_dir, output_file)
        
        # Connect to MSSQL database
        try:
            conn = pymssql.connect(
                server=source_creds.get('server'),
                user=source_creds.get('username'),
                password=source_creds.get('password'),
                database=source_creds.get('database'),
                port=source_creds.get('port', 1433)
            )
            
            # Use pandas to execute query and write CSV
            df = pd.read_sql(sql_query, conn)
            
            # Check if we got any results
            if df.empty:
                raise ValueError("SQL query returned no results")
            
            # Write to CSV
            df.to_csv(
                local_csv_path,
                sep=csv_delimiter,
                index=False,
                header=include_headers,
                quoting=csv.QUOTE_MINIMAL
            )
            
            conn.close()
            
            # Store CSV file path for potential future use
            self.csv_file = local_csv_path
            
            return local_csv_path
            
        except Exception as e:
            raise RuntimeError(f"SQL query error: {str(e)}")
    
    def _upload_to_sftp(self, local_file_path, dest_path, filename):
        """Upload CSV file to destination SFTP server."""
        dest_creds = self.destination_credential.get_credentials()
        temp_dir = os.path.dirname(local_file_path)
        
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
                
                # Upload the CSV file
                remote_path = os.path.join(dest_path, filename).replace('\\', '/')
                sftp.put(local_file_path, remote_path)
                
        except SSHException as e:
            raise RuntimeError(f"SFTP connection error: {str(e)}")
