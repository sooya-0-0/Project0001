# Project0001
+# Project0001
+
+개인용 미국주식 아침 뉴스 브리핑 자동화 예시입니다.
+
+## 구성
+- GitHub Actions 스케줄 실행
+- NewsAPI + Alpha Vantage 뉴스 수집
+- OpenAI 요약 생성
+- Gmail SMTP 발송
+
+## 필요한 GitHub Secrets
+- `OPENAI_API_KEY`
+- `GMAIL_USER`
+- `GMAIL_APP_PASSWORD`
+- `MAIL_TO`
+- `NEWS_API_KEY` (선택: NewsAPI 사용 시)
+- `ALPHA_VANTAGE_API_KEY` (선택: Alpha Vantage 사용 시)
+
+※ `NEWS_API_KEY`와 `ALPHA_VANTAGE_API_KEY` 중 최소 하나는 필요합니다.
+
+## 실행
+로컬 테스트:
+
+```bash
+pip install -r requirements.txt
+python main.py
+```
+
+자동 실행:
+- `.github/workflows/morning_us_stocks.yml`
+- 매일 22:30 UTC (= KST 07:30)
+
+
+## 보안 주의사항 (중요)
+- API 키를 `main.py`에 하드코딩하면 안 됩니다.
+- 키를 GitHub에 푸시하면 공개 저장소에서는 누구나 볼 수 있고, 비공개 저장소여도 권한 있는 사람은 볼 수 있습니다.
+- 반드시 GitHub Actions Secrets에 저장해서 사용하세요.
+- 로컬 실행은 `.env`를 사용하되, `.env`는 커밋하지 마세요 (`.gitignore` 포함).
+- 실수로 키를 커밋했다면 즉시 OpenAI/서비스 키를 폐기(revoke) 후 재발급하세요.
+
+### 권장 방식
+1. `.env.example`를 복사해 `.env` 생성 (로컬 전용)
+2. 실제 배포/자동실행은 GitHub Secrets 사용
+3. 코드에는 `os.getenv(...)`만 사용
