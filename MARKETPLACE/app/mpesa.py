# app/mpesa.py
import requests
import base64
from datetime import datetime
import json
from flask import current_app

class MpesaGateway:
    def __init__(self):
        # Don't load config here - it's too early
        pass
    
    def get_access_token(self):
        """Get M-Pesa OAuth access token"""
        try:
            # Get config directly in this method
            consumer_key = current_app.config.get('MPESA_CONSUMER_KEY')
            consumer_secret = current_app.config.get('MPESA_CONSUMER_SECRET')
            base_url = current_app.config.get('MPESA_BASE_URL', 'https://sandbox.safaricom.co.ke')
            
            print(f"DEBUG: Consumer Key: {consumer_key}")
            print(f"DEBUG: Consumer Secret: {consumer_secret}")
            
            if not consumer_key or not consumer_secret:
                print("DEBUG: Missing M-Pesa credentials")
                return None
            
            url = f"{base_url}/oauth/v1/generate?grant_type=client_credentials"
            auth_string = f"{consumer_key}:{consumer_secret}"
            encoded_auth = base64.b64encode(auth_string.encode()).decode()
            
            headers = {
                'Authorization': f'Basic {encoded_auth}'
            }
            
            print(f"DEBUG: Token URL: {url}")
            
            response = requests.get(url, headers=headers, timeout=30)
            print(f"DEBUG: Token Response Status: {response.status_code}")
            print(f"DEBUG: Token Response Headers: {dict(response.headers)}")
            print(f"DEBUG: Token Response Text: {response.text}")
            
            response.raise_for_status()
            
            token_data = response.json()
            token = token_data.get('access_token')
            
            if token:
                print(f"DEBUG: Access Token Received: {token[:50]}...")
                # Test if token is valid by making a simple API call
                test_headers = {'Authorization': f'Bearer {token}'}
                test_response = requests.get(f"{base_url}/oauth/v1/check", headers=test_headers, timeout=10)
                print(f"DEBUG: Token Validation Status: {test_response.status_code}")
            else:
                print("DEBUG: No access token in response")
                
            return token
            
        except requests.exceptions.RequestException as e:
            print(f"DEBUG: Token Request Error: {str(e)}")
            return None
        except Exception as e:
            print(f"DEBUG: Token General Error: {str(e)}")
            return None
    
    def stk_push(self, phone_number, amount, account_reference, description):
        """Initiate STK push for payment"""
        try:
            access_token = self.get_access_token()
            if not access_token:
                return None, "Failed to get access token"
            
            # Get config directly in this method
            business_shortcode = current_app.config.get('MPESA_SHORTCODE')
            passkey = current_app.config.get('MPESA_PASSKEY')
            base_url = current_app.config.get('MPESA_BASE_URL', 'https://sandbox.safaricom.co.ke')
            callback_url = current_app.config.get('BASE_URL', 'http://localhost:5000')
            
            print(f"DEBUG: Shortcode: {business_shortcode}")
            print(f"DEBUG: Passkey: {passkey}")
            
            if not business_shortcode or not passkey:
                return None, "M-Pesa configuration missing"
            
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            
            # Generate password - EXACTLY like the working example
            password_string = f"{business_shortcode}{passkey}{timestamp}"
            password = base64.b64encode(password_string.encode()).decode()
            
            # STK push payload - EXACT format from working example
            payload = {
                "BusinessShortCode": int(business_shortcode),  # Convert to int like example
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": int(amount),
                "PartyA": int(phone_number),  # Convert to int like example
                "PartyB": int(business_shortcode),  # Convert to int like example
                "PhoneNumber": int(phone_number),  # Convert to int like example
                "CallBackURL": "https://hedgy-marvella-nonsubsiding.ngrok-free.dev/payment-callback",
                "AccountReference": account_reference,
                "TransactionDesc": description
            }
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # Use the exact URL from working example
            url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
            print(f"DEBUG: STK Push URL: {url}")
            print(f"DEBUG: STK Payload: {json.dumps(payload, indent=2)}")
            print(f"DEBUG: Headers: {headers}")
            
            # Send request EXACTLY like the working example
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            print(f"DEBUG: STK Response Status: {response.status_code}")
            print(f"DEBUG: STK Response Text: {response.text}")
            
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('ResponseCode') == '0':
                return result, "STK push initiated successfully"
            else:
                error_message = result.get('errorMessage', 'Unknown error')
                return result, f"STK push failed: {error_message}"
            
        except requests.exceptions.RequestException as e:
            print(f"DEBUG: STK Request Error: {str(e)}")
            return None, f"Network error: {str(e)}"
        except Exception as e:
            print(f"DEBUG: STK General Error: {str(e)}")
            return None, str(e)
    def stk_push1(self, phone_number, amount, account_reference, description):
        """Initiate STK push for payment"""
        try:
            access_token = self.get_access_token()
            if not access_token:
                return None, "Failed to get access token"
            
            # Get config directly in this method
            business_shortcode = current_app.config.get('MPESA_SHORTCODE')
            passkey = current_app.config.get('MPESA_PASSKEY')
            base_url = current_app.config.get('MPESA_BASE_URL', 'https://sandbox.safaricom.co.ke')
            callback_url = current_app.config.get('BASE_URL', 'http://localhost:5000')
            
            print(f"DEBUG: Shortcode: {business_shortcode}")
            print(f"DEBUG: Passkey: {passkey}")
            
            if not business_shortcode or not passkey:
                return None, "M-Pesa configuration missing"
            
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            
            # Generate password - EXACTLY like the working example
            password_string = f"{business_shortcode}{passkey}{timestamp}"
            password = base64.b64encode(password_string.encode()).decode()
            
            # STK push payload - EXACT format from working example
            payload = {
                "BusinessShortCode": int(business_shortcode),  # Convert to int like example
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": int(amount),
                "PartyA": int(phone_number),  # Convert to int like example
                "PartyB": int(business_shortcode),  # Convert to int like example
                "PhoneNumber": int(phone_number),  # Convert to int like example
                "CallBackURL": "https://hedgy-marvella-nonsubsiding.ngrok-free.dev/unlock/callback",
                "AccountReference": account_reference,
                "TransactionDesc": description
            }
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # Use the exact URL from working example
            url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
            print(f"DEBUG: STK Push URL: {url}")
            print(f"DEBUG: STK Payload: {json.dumps(payload, indent=2)}")
            print(f"DEBUG: Headers: {headers}")
            
            # Send request EXACTLY like the working example
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            print(f"DEBUG: STK Response Status: {response.status_code}")
            print(f"DEBUG: STK Response Text: {response.text}")
            
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('ResponseCode') == '0':
                return result, "STK push initiated successfully"
            else:
                error_message = result.get('errorMessage', 'Unknown error')
                return result, f"STK push failed: {error_message}"
            
        except requests.exceptions.RequestException as e:
            print(f"DEBUG: STK Request Error: {str(e)}")
            return None, f"Network error: {str(e)}"
        except Exception as e:
            print(f"DEBUG: STK General Error: {str(e)}")
            return None, str(e)
    
    def check_transaction_status(self, checkout_request_id):
        """Check transaction status"""
        try:
            access_token = self.get_access_token()
            if not access_token:
                return None
            
            # Get config directly in this method
            business_shortcode = current_app.config.get('MPESA_SHORTCODE')
            passkey = current_app.config.get('MPESA_PASSKEY')
            base_url = current_app.config.get('MPESA_BASE_URL', 'https://sandbox.safaricom.co.ke')
            
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            
            password_string = f"{business_shortcode}{passkey}{timestamp}"
            password = base64.b64encode(password_string.encode()).decode()
            
            payload = {
                "BusinessShortCode": business_shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "CheckoutRequestID": checkout_request_id
            }
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            url = f"{base_url}/mpesa/stkpushquery/v1/query"
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            print(f"DEBUG: Status Check Error: {str(e)}")
            return None
            