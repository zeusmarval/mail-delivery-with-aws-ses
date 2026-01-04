import json
import logging
import re
import boto3
import os
from botocore.exceptions import ClientError
from mail_options import generate_raw_email

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ses = boto3.client('ses', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

# SES limits
MAX_RECIPIENTS = 50  # SES limit for total recipients (To + Cc + Bcc)
MAX_MESSAGE_SIZE = 10 * 1024 * 1024  # 10MB - SES limit for raw email messages
MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024  # 10MB - Individual attachment size limit

def is_valid_email(email):
    """
    Basic email format validation.
    
    Args:
        email (str): Email address to validate
        
    Returns:
        bool: True if email format is valid
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_event(event):
    """
    Validates that required fields are present and valid in the event.
    
    Args:
        event (dict): Event data
        
    Returns:
        tuple: (is_valid, error_message)
    """
    # Check required fields
    required_fields = ['from', 'to', 'subject', 'text', 'html']
    missing_fields = [field for field in required_fields if field not in event]
    
    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"
    
    # Validate 'to' field
    if not isinstance(event.get('to'), list) or len(event.get('to', [])) == 0:
        return False, "Field 'to' must be a non-empty list"
    
    # Validate email addresses
    if not is_valid_email(event['from']):
        return False, f"Invalid 'from' email address: {event['from']}"
    
    # Validate all 'to' addresses
    invalid_emails = [email for email in event['to'] if not is_valid_email(email)]
    if invalid_emails:
        return False, f"Invalid email addresses in 'to': {', '.join(invalid_emails)}"
    
    # Validate optional 'cc' field if present
    if 'cc' in event:
        if not isinstance(event['cc'], list):
            return False, "Field 'cc' must be a list"
        invalid_emails = [email for email in event['cc'] if not is_valid_email(email)]
        if invalid_emails:
            return False, f"Invalid email addresses in 'cc': {', '.join(invalid_emails)}"
    
    # Validate optional 'bcc' field if present
    if 'bcc' in event:
        if not isinstance(event['bcc'], list):
            return False, "Field 'bcc' must be a list"
        invalid_emails = [email for email in event['bcc'] if not is_valid_email(email)]
        if invalid_emails:
            return False, f"Invalid email addresses in 'bcc': {', '.join(invalid_emails)}"
    
    # Validate total recipients count (SES limit)
    total_recipients = len(event['to']) + len(event.get('cc', [])) + len(event.get('bcc', []))
    if total_recipients > MAX_RECIPIENTS:
        return False, f"Total recipients ({total_recipients}) exceeds SES limit of {MAX_RECIPIENTS}"
    
    # Validate that subject, text, and html are not empty
    if not event['subject'] or not event['subject'].strip():
        return False, "Field 'subject' cannot be empty"
    
    if not event['text'] or not event['text'].strip():
        return False, "Field 'text' cannot be empty"
    
    if not event['html'] or not event['html'].strip():
        return False, "Field 'html' cannot be empty"
    
    # Validate replyTo if present
    if 'replyTo' in event:
        reply_to = event['replyTo']
        reply_to_list = reply_to if isinstance(reply_to, list) else [reply_to]
        invalid_emails = [email for email in reply_to_list if not is_valid_email(email)]
        if invalid_emails:
            return False, f"Invalid email addresses in 'replyTo': {', '.join(invalid_emails)}"
    
    # Validate attachments if present
    if 'attachments' in event:
        if not isinstance(event['attachments'], list):
            return False, "Field 'attachments' must be a list"
        
        for idx, attachment in enumerate(event['attachments']):
            if not isinstance(attachment, dict):
                return False, f"Attachment at index {idx} must be an object"
            
            if 'filename' not in attachment:
                return False, f"Attachment at index {idx} is missing required field 'filename'"
            
            if 'content' not in attachment:
                return False, f"Attachment at index {idx} is missing required field 'content'"
            
            if not attachment['filename'] or not attachment['filename'].strip():
                return False, f"Attachment at index {idx} has empty filename"
            
            if not attachment['content']:
                return False, f"Attachment at index {idx} has empty content"
            
            # Validate attachment size (approximate after base64 encoding)
            try:
                import base64
                decoded_size = len(base64.b64decode(attachment['content']))
                if decoded_size > MAX_ATTACHMENT_SIZE:
                    return False, f"Attachment at index {idx} exceeds maximum size of {MAX_ATTACHMENT_SIZE / (1024 * 1024):.1f}MB"
            except Exception:
                # If not base64, estimate size from string length
                content_size = len(str(attachment['content']))
                if content_size > MAX_ATTACHMENT_SIZE:
                    return False, f"Attachment at index {idx} exceeds maximum size of {MAX_ATTACHMENT_SIZE / (1024 * 1024):.1f}MB"
    
    return True, None

def lambda_handler(event, context):
    """
    Lambda handler for sending emails via AWS SES.
    
    Args:
        event (dict): Event data containing email information
        context: Lambda context object
        
    Returns:
        dict: Response with result or error
    """
    # Log request without sensitive data
    log_event = {
        'from': event.get('from'),
        'to_count': len(event.get('to', [])),
        'has_cc': bool(event.get('cc')),
        'has_bcc': bool(event.get('bcc')),
        'has_attachments': bool(event.get('attachments')),
        'attachments_count': len(event.get('attachments', []))
    }
    logger.info(f"Processing email delivery request: {json.dumps(log_event)}")
    
    # Validate event
    is_valid, error_message = validate_event(event)
    if not is_valid:
        logger.error(f"Invalid event: {error_message}")
        return {
            'statusCode': 400,
            'error': {
                'message': error_message,
                'type': 'ValidationError'
            }
        }
    
    try:
        # Generate raw email message (MIME) from event
        mail_options = generate_raw_email(event)
        
        has_attachments = bool(event.get('attachments'))
        recipients_count = len(event['to']) + len(event.get('cc', [])) + len(event.get('bcc', []))
        logger.info(f"Sending email from {event['from']} to {recipients_count} recipient(s) (attachments: {has_attachments})")
        
        # Send email via SES using send_raw_email (supports attachments)
        response = ses.send_raw_email(**mail_options)
        
        message_id = response.get('MessageId')
        logger.info(f"Email sent successfully. MessageId: {message_id}")
        
        return {
            'statusCode': 200,
            'result': response
        }
        
    except ValueError as e:
        # Handle validation errors from generate_raw_email (e.g., message size)
        logger.error(f"Email generation error: {str(e)}")
        return {
            'statusCode': 400,
            'error': {
                'message': str(e),
                'type': 'EmailGenerationError'
            }
        }
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', str(e))
        logger.error(f"SES ClientError: {error_code} - {error_message}")
        
        return {
            'statusCode': 500,
            'error': {
                'message': error_message,
                'code': error_code,
                'type': 'SESClientError'
            }
        }
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        
        return {
            'statusCode': 500,
            'error': {
                'message': str(e),
                'type': 'UnexpectedError'
            }
        }

