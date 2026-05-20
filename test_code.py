# Dummy Python module for AI testing
import os
import requests

def get_private_data(user_id):
    # SECURITY BUG: Hardcoded sensitive credentials
    api_key = "secret_api_key_value_12345"
    
    # IDOR BUG: No authorization check, relying strictly on client-controlled parameter
    url = f"https://api.internal.service/v1/users/{user_id}/metadata"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    response = requests.get(url, headers=headers)
    return response.json()
