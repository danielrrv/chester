import os
import sys
import argparse
import resend

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Send an email using Resend.')
    parser.add_argument('--to', required=True, help='Recipient email address')
    parser.add_argument('--subject', required=True, help='Email subject')
    parser.add_argument('--body', required=True, help='Email body text')

    args = parser.parse_args()

    resend.api_key = os.environ.get('RESEND_API_KEY')
    if not resend.api_key:
        print('Error: RESEND_API_KEY environment variable not set.', file=sys.stderr)
        exit(1)

    try:
        r = resend.Emails.send({
            'from': 'onboarding@resend.dev', # This should be a verified sender in your Resend account
            'to': args.to,
            'subject': args.subject,
            'html': args.body
        })
        print(f'Email sent successfully: {r}', flush=True)
    except Exception as e:
        print(f'Error sending email: {e}', file=sys.stderr, flush=True)
        exit(1)
