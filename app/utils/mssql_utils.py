import pymssql
from loguru import logger
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

class MssqlClient:
    def __init__(self, server, database, username, password, port=1433, encrypt='yes', trust_server_certificate=False):
        self.server = server
        self.database = database
        self.username = username
        self.password = password
        self.port = port
        self.encrypt = encrypt
        self.trust_server_certificate = trust_server_certificate
        self.connection = None
        self.local_ip = get_local_ip()
        
    def connect(self):
        """Establish a connection to the MSSQL server"""
        try:
            logger.debug(f"Attempting to connect to MSSQL server: {self.server}:{self.port}, database: {self.database}, user: {self.username} from local IP: {self.local_ip}")
            
            # Configure encryption settings
            if self.encrypt == 'yes':
                encrypt_setting = True
            elif self.encrypt == 'no':
                encrypt_setting = False
            elif self.encrypt == 'strict':
                encrypt_setting = 'strict'
            else:
                encrypt_setting = True
                
            self.connection = pymssql.connect(
                server=self.server,
                user=self.username,
                password=self.password,
                database=self.database,
                port=self.port,
                encrypt=encrypt_setting,
                trust_server_certificate=self.trust_server_certificate
            )
            
            logger.info(f"Successfully connected to MSSQL server: {self.server}, database: {self.database} from local IP: {self.local_ip}")
            return True
            
        except pymssql.OperationalError as e:
            # Handle connection and operational errors
            error_msg = str(e)
            if "Connection refused" in error_msg:
                logger.error(f"Connection refused by server {self.server}:{self.port}. Server may not be running or a firewall is blocking traffic from {self.local_ip}.")
            elif "Login timeout expired" in error_msg:
                logger.error(f"Login timeout expired when connecting to {self.server} from {self.local_ip}. Server may be down or network issues.")
            elif "Login failed for user" in error_msg:
                logger.error(f"Login failed for user {self.username} on server {self.server}. Check credentials.")
            elif "Cannot open database" in error_msg:
                logger.error(f"Cannot open database {self.database} on server {self.server}. Database may not exist or user does not have permissions.")
            elif "SSL Provider" in error_msg:
                logger.error(f"SSL/TLS error connecting to {self.server} from {self.local_ip}. Check encrypt and trust_server_certificate settings.")
            else:
                logger.error(f"Operational error connecting to {self.server} from {self.local_ip}: {error_msg}")
                
            logger.debug(f"SQL Exception details: {traceback.format_exc()}")
            raise
            
        except socket.error as e:
            # Handle network errors
            error_msg = str(e)
            if "Connection refused" in error_msg:
                logger.error(f"Connection refused by server {self.server}:{self.port}. The server may not be running SQL Server on this port or a firewall is blocking traffic from {self.local_ip}.")
            elif "Network is unreachable" in error_msg:
                logger.error(f"Network is unreachable when connecting to {self.server} from {self.local_ip}. Check network connectivity.")
            elif "Connection timed out" in error_msg:
                logger.error(f"Connection timed out when connecting to {self.server} from {self.local_ip}. Server may be down or blocked by firewall.")
            else:
                logger.error(f"Socket error connecting to {self.server} from {self.local_ip}: {error_msg}")
                
            logger.debug(f"Socket Exception details: {traceback.format_exc()}")
            raise
            
        except Exception as e:
            logger.error(f"Failed to connect to MSSQL server: {self.server} from {self.local_ip}. Error: {str(e)}")
            logger.debug(f"Exception details: {traceback.format_exc()}")
            raise
    
    def disconnect(self):
        """Close the MSSQL connection"""
        if self.connection:
            logger.debug(f"Disconnecting from MSSQL server: {self.server}")
            self.connection.close()
            self.connection = None
    
    def test_connection(self):
        """Test the MSSQL connection by connecting and executing a simple query"""
        try:
            self.connect()
            logger.debug(f"Testing connection with simple query on {self.server} from {self.local_ip}")
            
            cursor = self.connection.cursor()
            cursor.execute('SELECT @@VERSION')
            version = cursor.fetchone()[0]
            logger.debug(f"Query successful, SQL Server version: {version[:30]}...")
            
            self.disconnect()
            return True, f"Successfully connected to MSSQL server from {self.local_ip}"
            
        except pymssql.OperationalError as e:
            error_msg = str(e)
            logger.error(f"MSSQL connection test failed (Operational error): {error_msg}")
            if self.connection:
                self.disconnect()
                
            # Provide more user-friendly error messages
            if "Connection refused" in error_msg:
                return False, f"Connection refused by server {self.server}:{self.port}. Server may not be running or a firewall is blocking traffic from {self.local_ip}."
            elif "Login timeout expired" in error_msg:
                return False, f"Login timeout expired. Server {self.server} may be down or there are network issues."
            elif "Login failed for user" in error_msg:
                return False, f"Login failed. Please check your username and password for {self.server}."
            elif "Cannot open database" in error_msg:
                return False, f"Cannot open database {self.database}. It may not exist or you don't have permissions."
            elif "SSL Provider" in error_msg:
                return False, f"SSL/TLS error connecting to {self.server}. Try adjusting the encrypt or trust_server_certificate settings."
            else:
                return False, f"SQL error: {error_msg} (connecting from {self.local_ip})"
                
        except socket.error as e:
            error_msg = str(e)
            logger.error(f"MSSQL connection test failed (Socket error): {error_msg}")
            if self.connection:
                self.disconnect()
                
            # Provide more user-friendly error messages for socket errors
            if "Connection refused" in error_msg:
                return False, f"Connection refused by server {self.server}:{self.port}. The server may not be running SQL Server on this port."
            elif "Network is unreachable" in error_msg:
                return False, f"Network is unreachable. Check your network connectivity to {self.server} from {self.local_ip}."
            elif "Connection timed out" in error_msg:
                return False, f"Connection timed out. Server may be down or a firewall may be blocking traffic from {self.local_ip}."
            else:
                return False, f"Network error: {error_msg} (connecting from {self.local_ip})"
                
        except Exception as e:
            logger.error(f"MSSQL connection test failed: {str(e)}")
            logger.debug(f"Full exception details: {traceback.format_exc()}")
            if self.connection:
                self.disconnect()
            return False, f"Failed to connect to MSSQL server: {str(e)} (connecting from {self.local_ip})"
