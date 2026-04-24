---
name: resend_email
description: Skill to send emails using the Resend API.
---

# Resend Email Skill

This skill provides the capability to send emails programmatically using the Resend API. It's designed for simple, direct email sending from your agent.

## Prerequisites

1.  **Resend API Key**: Obtain your API key from [Resend](https://resend.com/) and set it as an environment variable named `RESEND_API_KEY`.

    bash
    export RESEND_API_KEY='re_YOUR_API_KEY'
    

2.  **Python Library**: Install the `resend` Python library.

    bash
    pip install resend
    

## Usage

The primary way to use this skill is by executing the `send_email.py` script located in the `scripts/` directory.

### Send Email

bash
python3 skills/resend_email/scripts/send_email.py \
    --to recipient@example.com \
    --subject 'Hello from Agent' \
    --body 'This is the email body.'


#### Arguments:

*   `--to`: The recipient's email address. (Required)
*   `--subject`: The subject line of the email. (Required)
*   `--body`: The main text content of the email. (Required)

## Example

To send an email:

bash
python3 skills/resend_email/scripts/send_email.py --to user@example.com --subject "Agent Update" --body "Your task has been completed successfully."

