import json
import boto3
import os
import traceback
from mail_options import generate_mail_options
from secretManager import getSecret

ses = boto3.client('ses', region_name=os.environ['AWS_REGION'])

credentials = json.loads(getSecret(os.environ['AWS_REGION'], os.environ['secretManagerArn']))

def wraped_send_mail(ses, mail_options):
    response = ses.send_email(**mail_options)
    return response

def lambda_handler(event, context):

    print(json.dumps(event))

    mail_options = generate_mail_options(event)

    transporter_config = {
        'SES': ses,
        'Source': event['from'],
        'Host': credentials['SMTP_SERVER'],
        'Port': int(credentials['SMTP_PORT']),
        'Secure': False
    }
    
    if event.get('auth'):
        transporter_config['Username'] = credentials['SMTP_USER']
        transporter_config['Password'] = credentials['SMTP_PASS']
    
    result = None
    error = None
    
    try:
        result = wraped_send_mail(ses, mail_options)
    except Exception as e:
        error = {'message': str(e), 'stack': traceback.format_exc()}
        print(e)
    
    return {'result': result, 'error': error}