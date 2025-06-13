from flask import Flask, render_template, request, redirect, url_for
from dotenv import load_dotenv
import os
import requests
import json

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
SUPABASE_TABLE = 'registrations'

def check_table_exists(table):
    """Check if the table exists and is accessible"""
    url = f"{SUPABASE_URL}/rest/v1/{table}?select=*&limit=1"
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}'
    }
    
    try:
        print(f"\n--- Checking table {table} ---")
        response = requests.get(url, headers=headers)
        print(f"Table check status: {response.status_code}")
        if response.status_code == 200:
            return True, "Table exists and is accessible"
        return False, f"Error: {response.status_code} - {response.text}"
    except Exception as e:
        return False, f"Exception: {str(e)}"

def supabase_insert(table, data):
    """Insert data into Supabase table using REST API"""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'return=representation'  # Changed to get more detailed response
    }
    
    try:
        print(f"\n--- Attempting to insert into {table} ---")
        print(f"URL: {url}")
        print(f"Data: {data}")
        
        response = requests.post(url, headers=headers, json=data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        response.raise_for_status()
        return {'data': response.json(), 'error': None}
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Error: {str(e)}"
        if hasattr(e, 'response') and e.response is not None:
            error_msg += f"\nStatus Code: {e.response.status_code}"
            error_msg += f"\nResponse: {e.response.text}"
        print(error_msg)  # Print detailed error to console
        return {'data': None, 'error': error_msg}

def send_welcome_email(recipient_email: str):
    """Send welcome email via Brevo using template"""
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "accept": "application/json",
        "api-key": os.getenv('BREVO_API_KEY'),
        "content-type": "application/json"
    }
    
    data = {
        "templateId": int(os.getenv('BREVO_TEMPLATE_ID')),
        "to": [{"email": recipient_email}],
        "params": {
            "name": recipient_email.split('@')[0],
            "email": recipient_email
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    email = request.form.get('email')
    
    if not email:
        return "Email is required", 400
    
    try:
        # Get current timestamp in ISO format
        from datetime import datetime
        
        # Save to Supabase
        result = supabase_insert(SUPABASE_TABLE, {
            "email": email,
            "name": email.split('@')[0],
            "created_at": datetime.utcnow().isoformat() + 'Z'  # Current UTC time in ISO format
        })
        
        if result['error']:
            return f"Database error: {result['error']}", 500
            
        # Send welcome email
        if send_welcome_email(email):
            return redirect(url_for('success'))
        else:
            return "Registration saved, but failed to send welcome email", 500
            
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/success')
def success():
    return "Registration successful! Check your email for a welcome message."

if __name__ == '__main__':
    print("Starting Flask server...")
    print(f"Supabase URL: {SUPABASE_URL}")
    print(f"Supabase Table: {SUPABASE_TABLE}")
    
    # Check if table is accessible
    table_exists, message = check_table_exists(SUPABASE_TABLE)
    print(f"Table check: {message}")
    
    if not table_exists:
        print("\n⚠️  WARNING: Table check failed. The table might not exist or you might not have proper permissions.")
        print("Please verify in your Supabase dashboard:")
        print(f"1. Table '{SUPABASE_TABLE}' exists")
        print("2. RLS policies are properly set up")
        print("3. The API key has proper permissions\n")
    
    print("\nServer will be available at http://localhost:5001")
    app.run(host='0.0.0.0', port=5001, debug=True)
