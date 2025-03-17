import pysftp
import paramiko
from loguru import logger
import os
import socket
import traceback

def get_local_ip():
    """Get the local IP address of the machine"""
    try:
        # Create a socket to get the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Connect to Google DNS (doesn't actually send data)
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        logger.error(f"Failed to get local IP address: {str(e)}")
        return "Unknown"

class SftpClient:
    def __init__(self, host, port, username, password=None, private_key=None, private_key_passphrase=None, disable_host_key_checking=False):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.private_key = private_key
        self.private_key_passphrase = private_key_passphrase
        self.disable_host_key_checking = disable_host_key_checking
        self.connection = None
        self.local_ip = get_local_ip()
        
    def connect(self):
        """Establish a connection to the SFTP server"""
        temp_key_file = None
        try:
            logger.debug(f"Attempting to connect to SFTP server: {self.host}:{self.port} with username: {self.username} from local IP: {self.local_ip}")
            
            cnopts = pysftp.CnOpts()
            if self.disable_host_key_checking:
                logger.warning(f"Host key checking disabled for {self.host}")
                cnopts.hostkeys = None
                
            connect_kwargs = {
                'host': self.host,
                'port': self.port,
                'username': self.username,
                'cnopts': cnopts
            }
            
            # Determine authentication method
            if self.private_key and self.private_key.strip():
                logger.debug("Using private key authentication")
                
                # Save the private key to a temporary file
                temp_key_file = 'temp_key.pem'
                with open(temp_key_file, 'w') as f:
                    f.write(self.private_key)
                os.chmod(temp_key_file, 0o600)  # Set secure permissions
                
                connect_kwargs['private_key'] = temp_key_file
                if self.private_key_passphrase:
                    connect_kwargs['private_key_pass'] = self.private_key_passphrase
            elif self.password:
                logger.debug("Using password authentication")
                connect_kwargs['password'] = self.password
            else:
                logger.error("No authentication method provided")
                raise ValueError("Either password or private key must be provided")
            
            self.connection = pysftp.Connection(**connect_kwargs)
            logger.info(f"Successfully connected to SFTP server: {self.host} from local IP: {self.local_ip}")
            
            # Clean up key file if it exists
            if temp_key_file and os.path.exists(temp_key_file):
                os.remove(temp_key_file)
                
            return True
        
        except paramiko.ssh_exception.SSHException as e:
            # Handle specific SSH exceptions
            if "Connection reset by peer" in str(e):
                logger.error(f"Connection reset by server {self.host}. This could indicate a firewall blocking the connection from {self.local_ip}, incorrect port, or server rejecting the connection.")
            elif "Authentication failed" in str(e):
                logger.error(f"Authentication failed for user {self.username} on server {self.host}. Check credentials.")
            elif "No authentication methods available" in str(e):
                logger.error(f"No suitable authentication methods available for server {self.host}.")
            elif "Server connection dropped" in str(e):
                logger.error(f"Server {self.host} dropped the connection. The server might be configured to reject connections from {self.local_ip}.")
            else:
                logger.error(f"SSH error connecting to {self.host} from {self.local_ip}: {str(e)}")
            
            logger.debug(f"SSH Exception details: {traceback.format_exc()}")
            
            # Clean up key file if it exists
            if temp_key_file and os.path.exists(temp_key_file):
                os.remove(temp_key_file)
            raise
            
        except socket.error as e:
            # Handle network/socket errors
            if "Connection refused" in str(e):
                logger.error(f"Connection refused by server {self.host}:{self.port}. The server may not be running SFTP on this port or a firewall is blocking traffic from {self.local_ip}.")
            elif "Network is unreachable" in str(e):
                logger.error(f"Network is unreachable when connecting to {self.host} from {self.local_ip}. Check network connectivity.")
            elif "Connection timed out" in str(e):
                logger.error(f"Connection timed out when connecting to {self.host} from {self.local_ip}. Server may be down or blocked by firewall.")
            else:
                logger.error(f"Socket error connecting to {self.host} from {self.local_ip}: {str(e)}")
                
            logger.debug(f"Socket Exception details: {traceback.format_exc()}")
            
            # Clean up key file if it exists
            if temp_key_file and os.path.exists(temp_key_file):
                os.remove(temp_key_file)
            raise
        
        except Exception as e:
            # Handle all other exceptions
            logger.error(f"Failed to connect to SFTP server: {self.host} from {self.local_ip}. Error: {str(e)}")
            logger.debug(f"Exception details: {traceback.format_exc()}")
            
            # Clean up key file if it exists
            if temp_key_file and os.path.exists(temp_key_file):
                os.remove(temp_key_file)
            raise
    
    def disconnect(self):
        """Close the SFTP connection"""
        if self.connection:
            logger.debug(f"Disconnecting from SFTP server: {self.host}")
            self.connection.close()
            self.connection = None
    
    def test_connection(self):
        """Test the SFTP connection by connecting and listing directory contents"""
        try:
            self.connect()
            logger.debug(f"Testing connection by listing current directory on {self.host} from {self.local_ip}")
            
            # Try to list the contents of the current directory
            dir_contents = self.connection.listdir()
            logger.debug(f"Directory listing successful: {len(dir_contents)} items found")
            
            self.disconnect()
            return True, f"Successfully connected to SFTP server from {self.local_ip}"
        except paramiko.ssh_exception.SSHException as e:
            error_msg = str(e)
            logger.error(f"SFTP connection test failed (SSH error): {error_msg}")
            if self.connection:
                self.disconnect()
                
            # Provide more user-friendly error messages
            if "Connection reset by peer" in error_msg:
                return False, f"Server {self.host} reset the connection. This often indicates a firewall blocking connection from {self.local_ip}, incorrect port, or server configuration issue."
            elif "Authentication failed" in error_msg:
                return False, f"Authentication failed. Please check your username and password/key."
            else:
                return False, f"SSH error: {error_msg} (connecting from {self.local_ip})"
        except socket.error as e:
            error_msg = str(e)
            logger.error(f"SFTP connection test failed (Socket error): {error_msg}")
            if self.connection:
                self.disconnect()
                
            # Provide more user-friendly error messages for socket errors
            if "Connection refused" in error_msg:
                return False, f"Connection refused by server {self.host}:{self.port}. The server may not be running SFTP on this port."
            elif "Network is unreachable" in error_msg:
                return False, f"Network is unreachable. Check your network connectivity to {self.host} from {self.local_ip}."
            elif "Connection timed out" in error_msg:
                return False, f"Connection timed out. Server may be down or a firewall may be blocking traffic from {self.local_ip}."
            else:
                return False, f"Network error: {error_msg} (connecting from {self.local_ip})"
        except Exception as e:
            logger.error(f"SFTP connection test failed: {str(e)}")
            logger.debug(f"Full exception details: {traceback.format_exc()}")
            if self.connection:
                self.disconnect()
            return False, f"Failed to connect to SFTP server: {str(e)} (connecting from {self.local_ip})"
