import requests

# 1. Kakao Developers (https://developers.kakao.com)에서 애플리케이션 생성
# 2. 내 애플리케이션 > 앱 설정 > 앱 키에서 'REST API 키' 확인
# 3. 내 애플리케이션 > 제품 설정 > 카카오 로그인에서 '활성화 설정' ON
# 4. Redirect URI에 'https://localhost:3000' 추가 (임의의 주소)
# 5. 제품 설정 > 카카오 로그인 > 동의항목에서 '카카오톡 메시지 전송(talk_message)' 권한을 '선택 동의'로 설정

print("=== Kakao Initial Token Helper ===")
rest_api_key = input("REST API 키를 입력하세요: ")
redirect_uri = "https://localhost:3000"

print("\n다음 URL을 브라우저에 복사하여 붙여넣고 로그인하세요:")
auth_url = f"https://kauth.kakao.com/oauth/authorize?client_id={rest_api_key}&redirect_uri={redirect_uri}&response_type=code&scope=talk_message"
print(auth_url)

print("\n로그인 후 리다이렉트된 주소창의 'code=' 뒤에 나오는 문자열을 복사해서 입력하세요.")
auth_code = input("Authorize Code: ")

url = "https://kauth.kakao.com/oauth/token"
data = {
    "grant_type": "authorization_code",
    "client_id": rest_api_key,
    "redirect_uri": redirect_uri,
    "code": auth_code
}

response = requests.post(url, data=data)
tokens = response.json()

if "refresh_token" in tokens:
    print("\n성공적으로 토큰을 발급받았습니다!")
    print(f"REFRESH_TOKEN: {tokens['refresh_token']}")
    print("\n이 REFRESH_TOKEN을 GitHub Secrets의 'KAKAO_REFRESH_TOKEN'으로 등록하세요.")
else:
    print("\n토큰 발급 실패:")
    print(tokens)
