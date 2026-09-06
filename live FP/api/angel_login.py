from SmartApi import SmartConnect

class AngelOneManager:
    def __init__(self, api_key, client_id, pin, totp_code):
        self.client_id = client_id.strip()
        self.pin = pin.strip()
        self.api_key = api_key.strip()
        self.totp_code = totp_code.strip()  # 6-digit OTP code directly
        self.api = SmartConnect(api_key=self.api_key)
        self.feed_token = None
        self.refresh_token = None

    def login(self):
        try:
            # Directly pass the 6-digit OTP provided by the user
            response = self.api.generateSession(self.client_id, self.pin, self.totp_code)
            
            if response and response.get('status'):
                self.refresh_token = response['data']['refreshToken']
                self.feed_token = self.api.getfeedToken()
                return True, "🟢 Connected to Angel One successfully!"
            else:
                error_msg = response.get('message', 'Unknown Error') if response else 'No response from server'
                return False, f"🔴 Login Failed: {error_msg}"
                
        except Exception as e:
            return False, f"🔴 System Error during login: {str(e)}"