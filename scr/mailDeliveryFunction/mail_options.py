def generate_mail_options(event):
    mail_options = {
        'Source': event['from'],
        'Destination': {
            'ToAddresses': event['to'],
            'CcAddresses': event.get('cc', []),
            'BccAddresses': event.get('bcc', [])
        },
        'Message': {
            'Subject': {'Data': event['subject']},
            'Body': {
                'Text': {'Data': event['text']},
                'Html': {'Data': event['html']}
            }
        }
    }
    
    if event.get('attachments'):
        mail_options['Message']['Attachments'] = [{'Filename': a['filename'], 'Content': a['content']} for a in event['attachments']]
    
    if event.get('replyTo'):
        mail_options['ReplyToAddresses'] = event['replyTo']
    
    return mail_options