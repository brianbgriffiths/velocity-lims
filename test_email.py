#!/usr/bin/env python3
"""
Test script to verify email sending functionality.
Run this to test the mail command integration.
"""

import subprocess
import sys

def test_email_sending():
    """Test the email sending command"""
    
    # Test email details
    recipient = "crabrock@gmail.com"
    full_name = "Test User"
    login_code = "ABC123XY"
    login_link = f"http://localhost:8000/login/{login_code}"
    
    # Compose email content
    email_body = f"Dear {full_name},\n\nYour Velocity LIMS account has been created!\n\nClick the link below to activate your account:\n{login_link}\n\nAlternatively, you can login manually at http://localhost:8000/login with code: {login_code}\n\nWelcome to Velocity LIMS!\n\nBest regards,\nThe Velocity LIMS Team"
    
    # Prepare mail command
    subject = "Activate your Velocity LIMS Account"
    from_address = "Velocity LIMS <noreply@velocitylims.com>"
    
    print("Testing email sending...")
    print(f"To: {recipient}")
    print(f"Subject: {subject}")
    print(f"From: {from_address}")
    print(f"Body:\n{email_body}")
    print("-" * 50)
    
    try:
        # Create the mail command
        mail_cmd = [
            'mail',
            '-a', f'From: {from_address}',
            '-s', subject,
            recipient
        ]
        
        print(f"Running command: {' '.join(mail_cmd)}")
        
        # Send email using subprocess
        process = subprocess.run(
            mail_cmd,
            input=email_body,
            text=True,
            capture_output=True,
            check=True
        )
        
        print("✓ Email sent successfully!")
        print(f"Return code: {process.returncode}")
        if process.stdout:
            print(f"Output: {process.stdout}")
        if process.stderr:
            print(f"Stderr: {process.stderr}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to send email: {e}")
        print(f"Return code: {e.returncode}")
        print(f"Error output: {e.stderr}")
        return False
    except Exception as e:
        print(f"✗ Email sending error: {e}")
        return False

if __name__ == "__main__":
    print("Velocity LIMS Email Test")
    print("=" * 30)
    success = test_email_sending()
    sys.exit(0 if success else 1)
