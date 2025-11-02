# app/mpesa.py
import requests
import base64
from datetime import datetime
import json
from flask import current_app

class MpesaGateway:
    def __init__(self):
        self.consumer_key = current_app.config.get('MPESA_CONSUMER_KEY')
        self.consumer_secret = current_app.config.get('MPESA_CONSUMER_SECRET')
        self.base_url = current_app.config.get('MPESA_BASE_URL', 'https://sandbox.safaricom.co.ke')
        
    def get_access_token(self):
        """Get M-Pesa OAuth access token"""
        try:
            url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
            auth_string = f"{self.consumer_key}:{self.consumer_secret}"
            encoded_auth = base64.b64encode(auth_string.encode()).decode()
            
            headers = {
                'Authorization': f'Basic {encoded_auth}'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            token_data = response.json()
            return token_data.get('access_token')
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"M-Pesa token request error: {str(e)}")
            return None
        except Exception as e:
            current_app.logger.error(f"M-Pesa token error: {str(e)}")
            return None
    
    def stk_push(self, phone_number, amount, account_reference, description):
        """Initiate STK push for payment"""
        try:
            access_token = self.get_access_token()
            if not access_token:
                return None, "Failed to get access token"
            
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            business_shortcode = current_app.config.get('MPESA_SHORTCODE')
            passkey = current_app.config.get('MPESA_PASSKEY')
            
            if not all([business_shortcode, passkey]):
                return None, "M-Pesa configuration missing"
            
            # Generate password
            password_string = f"{business_shortcode}{passkey}{timestamp}"
            password = base64.b64encode(password_string.encode()).decode()
            
            # STK push payload
            payload = {
                "BusinessShortCode": business_shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": int(amount),
                "PartyA": phone_number,
                "PartyB": business_shortcode,
                "PhoneNumber": phone_number,
                "CallBackURL": f"{current_app.config.get('BASE_URL')}/products/payment-callback",
                "AccountReference": account_reference,
                "TransactionDesc": description
            }
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('ResponseCode') == '0':
                return result, "STK push initiated successfully"
            else:
                error_message = result.get('errorMessage', 'Unknown error')
                return result, f"STK push failed: {error_message}"
            
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"M-Pesa STK push request error: {str(e)}")
            return None, f"Network error: {str(e)}"
        except Exception as e:
            current_app.logger.error(f"M-Pesa STK push error: {str(e)}")
            return None, str(e)
    
    def check_transaction_status(self, checkout_request_id):
        """Check transaction status"""
        try:
            access_token = self.get_access_token()
            if not access_token:
                return None
            
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            business_shortcode = current_app.config.get('MPESA_SHORTCODE')
            passkey = current_app.config.get('MPESA_PASSKEY')
            
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
            
            url = f"{self.base_url}/mpesa/stkpushquery/v1/query"
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            current_app.logger.error(f"M-Pesa status check error: {str(e)}")
            return None