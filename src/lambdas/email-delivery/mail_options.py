import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.header import Header
from email import encoders

def generate_raw_email(event):
    """
    Generates raw email message (MIME) for AWS SES send_raw_email API.
    Supports attachments and all email features.
    
    Args:
        event (dict): Event data containing email information
        
    Returns:
        dict: Formatted mail options for SES send_raw_email API
    """
    # Create message container
    # Use 'mixed' if there are attachments, 'alternative' otherwise
    has_attachments = bool(event.get('attachments'))
    msg = MIMEMultipart('mixed' if has_attachments else 'alternative')
    msg['Subject'] = event['subject']
    msg['From'] = event['from']
    msg['To'] = ', '.join(event['to'])
    
    # Add CC if present
    if event.get('cc'):
        msg['Cc'] = ', '.join(event['cc'])
    
    # Add Reply-To if present
    if event.get('replyTo'):
        reply_to = event['replyTo']
        if isinstance(reply_to, list):
            msg['Reply-To'] = ', '.join(reply_to)
        else:
            msg['Reply-To'] = reply_to
    
    # Create alternative part for text and HTML
    if has_attachments:
        # If there are attachments, create an alternative part for text/html
        alternative_part = MIMEMultipart('alternative')
        text_part = MIMEText(event['text'], 'plain', 'utf-8')
        html_part = MIMEText(event['html'], 'html', 'utf-8')
        alternative_part.attach(text_part)
        alternative_part.attach(html_part)
        msg.attach(alternative_part)
    else:
        # If no attachments, attach text and HTML directly
        text_part = MIMEText(event['text'], 'plain', 'utf-8')
        html_part = MIMEText(event['html'], 'html', 'utf-8')
        msg.attach(text_part)
        msg.attach(html_part)
    
    # Add attachments if present
    if has_attachments:
        for attachment in event['attachments']:
            filename = attachment.get('filename', 'attachment')
            content = attachment.get('content', '')
            content_type = attachment.get('contentType', 'application/octet-stream')
            
            # Decode base64 content if needed
            try:
                # Try to decode as base64
                attachment_data = base64.b64decode(content)
            except Exception:
                # If not base64, use as-is (assuming it's already bytes or string)
                attachment_data = content.encode('utf-8') if isinstance(content, str) else content
            
            # Create attachment part
            attachment_part = MIMEBase('application', 'octet-stream')
            attachment_part.set_payload(attachment_data)
            encoders.encode_base64(attachment_part)
            
            # Handle filename encoding for special characters
            # Use Header to properly encode filenames with special characters
            encoded_filename = Header(filename, 'utf-8').encode()
            attachment_part.add_header(
                'Content-Disposition',
                f'attachment; filename="{encoded_filename}"'
            )
            
            # Override content type if provided
            if content_type:
                attachment_part.set_type(content_type)
            
            msg.attach(attachment_part)
    
    # Collect all destination addresses
    destinations = event['to'].copy()
    if event.get('cc'):
        destinations.extend(event['cc'])
    if event.get('bcc'):
        destinations.extend(event['bcc'])
    
    # Convert message to bytes (SES requires bytes, not string)
    # Use as_bytes() if available, otherwise encode the string
    try:
        raw_message_bytes = msg.as_bytes()
    except AttributeError:
        # Fallback for older Python versions
        raw_message_bytes = msg.as_string().encode('utf-8')
    
    # Validate message size (SES limit: 10MB)
    MAX_MESSAGE_SIZE = 10 * 1024 * 1024  # 10MB
    if len(raw_message_bytes) > MAX_MESSAGE_SIZE:
        raise ValueError(
            f"Email message size ({len(raw_message_bytes) / (1024 * 1024):.2f}MB) "
            f"exceeds SES limit of {MAX_MESSAGE_SIZE / (1024 * 1024):.1f}MB"
        )
    
    # Prepare options for send_raw_email
    mail_options = {
        'Source': event['from'],
        'Destinations': destinations,
        'RawMessage': {
            'Data': raw_message_bytes
        }
    }
    
    return mail_options