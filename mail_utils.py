from flask_mail import Message
from threading import Thread
from flask import current_app

def send_async_email(app, msg):
    """Send email asynchronously with proper app context."""
    with app.app_context():
        try:
            from application import mail
            mail.send(msg)
            current_app.logger.info(f"Email sent successfully to {msg.recipients}")
        except Exception as e:
            current_app.logger.error(f"Failed to send email to {msg.recipients}: {str(e)}")

def send_email(subject, recipients, body, html=None, sender=None):
    """
    Send email asynchronously.
    
    Args:
        subject (str): Email subject
        recipients (list): List of recipient emails
        body (str): Plain text body
        html (str, optional): HTML body
        sender (str, optional): Override default sender
    """
    from flask import current_app
    
    if not recipients:
        current_app.logger.warning("No recipients provided for email")
        return
    
    # Ensure recipients is a list
    if isinstance(recipients, str):
        recipients = [recipients]
    
    msg = Message(
        subject=subject, 
        recipients=recipients,
        sender=sender
    )
    msg.body = body
    if html:
        msg.html = html
    
    # Get current app for context
    app = current_app._get_current_object()
    thr = Thread(target=send_async_email, args=(app, msg))
    thr.daemon = True
    thr.start()

def send_email_with_attachment(subject, recipients, body, attachment_data, attachment_name, html=None):
    """
    Send email with attachment asynchronously.
    
    Args:
        subject (str): Email subject
        recipients (list): List of recipient emails
        body (str): Plain text body
        attachment_data (bytes): File data
        attachment_name (str): Name of the attachment
        html (str, optional): HTML body
    """
    from flask import current_app
    
    if not recipients:
        current_app.logger.warning("No recipients provided for email")
        return
    
    if isinstance(recipients, str):
        recipients = [recipients]
    
    msg = Message(subject=subject, recipients=recipients)
    msg.body = body
    if html:
        msg.html = html
    
    # Add attachment
    if attachment_data and attachment_name:
        msg.attach(
            attachment_name,
            "application/octet-stream",
            attachment_data
        )
    
    app = current_app._get_current_object()
    thr = Thread(target=send_async_email, args=(app, msg))
    thr.daemon = True
    thr.start()