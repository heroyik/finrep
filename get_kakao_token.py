import requests

# 1. Create an application at Kakao Developers (https://developers.kakao.com)
# 2. [My Application] > [App Settings] > [App Keys] -> Check 'REST API Key'
# 3. [My Application] > [Product Settings] > [Kakao Login] -> Turn 'Activation' ON
# 4. Add 'https://localhost:3000' to Redirect URI (use any arbitrary address)
# 5. [Product Settings] > [Kakao Login] > [Consent Items] -> Set 'Send KakaoTalk Message (talk_message)' to 'Optional Consent'

print("=== Kakao Initial Token Helper ===")
rest_api_key = input("Enter REST API Key: ")
print("\n--- How to find Client Secret (Updated UI) ---")
print("1. [앱 설정] > [앱 키] (또는 플랫폼 키)")
print("2. [REST API 키] 항목 옆의 '설정' 또는 하단 확인")
print("3. 'Client Secret' 항목의 코드를 복사")
print("4. (주의) '활성화 상태'가 ON이어야 합니다.")
client_secret = input("Enter Client Secret: ")
redirect_uri = "https://localhost:3000"

print("\nCopy and paste the following URL into your browser to log in:")
auth_url = f"https://kauth.kakao.com/oauth/authorize?client_id={rest_api_key}&redirect_uri={redirect_uri}&response_type=code&scope=talk_message"
print(auth_url)

print("\nAfter logging in, copy and enter the string following 'code=' in the redirected address bar.")
auth_code = input("Authorize Code: ")

url = "https://kauth.kakao.com/oauth/token"
data = {
    "grant_type": "authorization_code",
    "client_id": rest_api_key,
    "redirect_uri": redirect_uri,
    "code": auth_code,
    "client_secret": client_secret
}

response = requests.post(url, data=data)
tokens = response.json()

if "refresh_token" in tokens:
    print("\nToken issued successfully!")
    print(f"REFRESH_TOKEN: {tokens['refresh_token']}")
    print("\nRegister this REFRESH_TOKEN as 'KAKAO_REFRESH_TOKEN' in GitHub Secrets.")
else:
    print("\nToken issuance failed:")
    print(tokens)
