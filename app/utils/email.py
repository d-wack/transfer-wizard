import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app
from datetime import datetime

logger = logging.getLogger(__name__)

def send_email(recipients, subject, html_content, text_content=None):
    """
    Send an email to the specified recipients.
    
    Args:
        recipients (list): List of email addresses to send to
        subject (str): Email subject
        html_content (str): HTML content of the email
        text_content (str, optional): Plain text content of the email
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    # Check if email configuration is available
    smtp_server = os.environ.get('SMTP_SERVER')
    smtp_port = os.environ.get('SMTP_PORT')
    smtp_username = os.environ.get('SMTP_USERNAME')
    smtp_password = os.environ.get('SMTP_PASSWORD')
    sender_email = os.environ.get('SENDER_EMAIL')
    
    if not all([smtp_server, smtp_port, smtp_username, smtp_password, sender_email]):
        logger.warning("Email configuration not complete. Cannot send email.")
        return False
    
    # Create message
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = ', '.join(recipients)
    
    # Add text content if provided
    if text_content:
        msg.attach(MIMEText(text_content, 'plain'))
    
    # Add HTML content
    msg.attach(MIMEText(html_content, 'html'))
    
    try:
        # Connect to SMTP server
        server = smtplib.SMTP(smtp_server, int(smtp_port))
        server.starttls()
        server.login(smtp_username, smtp_password)
        
        # Send email
        server.sendmail(sender_email, recipients, msg.as_string())
        server.quit()
        
        logger.info(f"Email sent successfully to {len(recipients)} recipients")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        return False

def generate_daily_report_email(job_results, date):
    """
    Generate HTML email content for daily job report.
    
    Args:
        job_results (dict): Dictionary containing job execution results
        date (date): Date of the report
    
    Returns:
        str: HTML content for email
    """
    # Calculate summary statistics
    total_jobs = len(job_results)
    successful_jobs = sum(1 for j in job_results.values() if j['last_status'] == 'success')
    failed_jobs = sum(1 for j in job_results.values() if j['last_status'] == 'failure')
    
    # Generate HTML content
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background-color: #f2f2f2; }}
            .success {{ color: green; }}
            .failure {{ color: red; }}
            .warning {{ color: orange; }}
        </style>
    </head>
    <body>
        <h1>Daily Job Execution Report</h1>
        <p>Date: {date.strftime('%Y-%m-%d')}</p>
        
        <h2>Summary</h2>
        <p>Total Jobs: {total_jobs}<br>
        Successful Jobs: {successful_jobs}<br>
        Failed Jobs: {failed_jobs}</p>
        
        <h2>Job Details</h2>
        <table>
            <tr>
                <th>Job Name</th>
                <th>Status</th>
                <th>Success</th>
                <th>Failure</th>
                <th>Warning</th>
                <th>Info</th>
            </tr>
    """
    
    # Add rows for each job
    for job_data in job_results.values():
        job = job_data['job']
        status_class = job_data['last_status']
        
        html += f"""
        <tr>
            <td>{job.name}</td>
            <td class="{status_class}">{job_data['last_status'].upper()}</td>
            <td>{job_data['success']}</td>
            <td>{job_data['failure']}</td>
            <td>{job_data['warning']}</td>
            <td>{job_data['info']}</td>
        </tr>
        """
    
    html += """
        </table>
        <p>This is an automated report from the TransferWizard system.</p>
    </body>
    </html>
    """
    
    return html
