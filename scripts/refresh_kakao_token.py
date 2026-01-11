import requests
import os
import sys
import json

def refresh_token():
    client_id = os.environ.get('KAKAO_CLIENT_ID')
    refresh_token = os.environ.get('KAKAO_REFRESH_TOKEN')

    if not client_id or not refresh_token:
        print("Error: KAKAO_CLIENT_ID or KAKAO_REFRESH_TOKEN environment variables are not set.")
        sys.exit(1)

    url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "refresh_token": refresh_token
    }

    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        tokens = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error during token refresh request: {e}")
        if response is not None:
             print(f"Response content: {response.text}")
        sys.exit(1)
    except json.JSONDecodeError:
        print("Error: Failed to decode JSON response.")
        sys.exit(1)

    if "refresh_token" in tokens:
        print(f"NEW_REFRESH_TOKEN={tokens['refresh_token']}")
    else:
        print("NO_NEW_REFRESH_TOKEN")

    if "error" in tokens:
        print(f"Error in response: {tokens}")
        sys.exit(1)

    print("Token refresh successful.")

if __name__ == "__main__":
    refresh_token()
