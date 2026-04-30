+import hashlib
+import os
+import smtplib
+from datetime import datetime, timedelta, timezone
+from email.mime.text import MIMEText
+
+import requests
+from openai import OpenAI
+
+OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
+GMAIL_USER = os.getenv("GMAIL_USER")
+GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
+MAIL_TO = os.getenv("MAIL_TO")
+
+NEWS_API_KEY = os.getenv("NEWS_API_KEY")
+ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
+
+
+TICKERS = [
+    "AAPL",
+    "MSFT",
+    "NVDA",
+    "AMZN",
+    "GOOGL",
+    "META",
+    "TSLA",
+]
+
+
+def stable_id(title: str, url: str) -> str:
+    base = f"{title}|{url}".strip().encode("utf-8")
+    return hashlib.sha256(base).hexdigest()
+
+
+def fetch_newsapi() -> list[dict]:
+    if not NEWS_API_KEY:
+        return []
+
+    query = "(US stock OR S&P 500 OR Nasdaq OR Federal Reserve OR earnings)"
+    url = "https://newsapi.org/v2/everything"
+    params = {
+        "q": query,
+        "language": "en",
+        "sortBy": "publishedAt",
+        "pageSize": 30,
+        "apiKey": NEWS_API_KEY,
+    }
+
+    resp = requests.get(url, params=params, timeout=20)
+    resp.raise_for_status()
+    raw_articles = resp.json().get("articles", [])
+
+    normalized = []
+    for a in raw_articles:
+        title = a.get("title") or ""
+        article_url = a.get("url") or ""
+        normalized.append(
+            {
+                "id": stable_id(title, article_url),
+                "source": "NewsAPI",
+                "title": title,
+                "url": article_url,
+                "summary": a.get("description") or "",
+                "published_at": a.get("publishedAt") or "",
+            }
+        )
+    return normalized
+
+
+def fetch_alpha_vantage() -> list[dict]:
+    if not ALPHA_VANTAGE_API_KEY:
+        return []
+
+    tickers_joined = ",".join(TICKERS)
+    url = "https://www.alphavantage.co/query"
+    params = {
+        "function": "NEWS_SENTIMENT",
+        "tickers": tickers_joined,
+        "topics": "financial_markets,economy_fiscal,technology",
+        "sort": "LATEST",
+        "limit": 30,
+        "apikey": ALPHA_VANTAGE_API_KEY,
+    }
+
+    resp = requests.get(url, params=params, timeout=20)
+    resp.raise_for_status()
+    feed = resp.json().get("feed", [])
+
+    normalized = []
+    for item in feed:
+        title = item.get("title") or ""
+        article_url = item.get("url") or ""
+        normalized.append(
+            {
+                "id": stable_id(title, article_url),
+                "source": "AlphaVantage",
+                "title": title,
+                "url": article_url,
+                "summary": item.get("summary") or "",
+                "published_at": item.get("time_published") or "",
+            }
+        )
+    return normalized
+
+
+def dedupe_articles(*article_groups: list[dict]) -> list[dict]:
+    seen: set[str] = set()
+    merged: list[dict] = []
+    for group in article_groups:
+        for a in group:
+            if a["id"] in seen:
+                continue
+            seen.add(a["id"])
+            merged.append(a)
+
+    merged.sort(key=lambda x: x.get("published_at", ""), reverse=True)
+    return merged
+
+
+def summarize_korean(articles: list[dict]) -> str:
+    client = OpenAI(api_key=OPENAI_API_KEY)
+
+    top = articles[:20]
+    lines = []
+    for i, n in enumerate(top, 1):
+        lines.append(
+            f"{i}. [{n['source']}] {n['title']}\n"
+            f"   - {n['summary']}\n"
+            f"   - {n['url']}"
+        )
+
+    prompt = f"""
+너는 한국 개인 투자자를 위한 아침 브리핑 에디터다.
+아래 미국주식 관련 밤사이 뉴스를 읽고 한국어로 간결히 요약해라.
+
+출력 형식:
+1) 한 줄 시장 요약
+2) Top 5 뉴스 (각 항목: 핵심 1줄 + 시장 영향 1줄)
+3) 오늘 체크포인트 3개
+4) 출처 링크
+
+주의:
+- 과장 금지, 사실 중심
+- 불확실한 내용은 '추정'으로 표시
+
+뉴스 원문 목록:
+{chr(10).join(lines)}
+"""
+
+    response = client.chat.completions.create(
+        model="gpt-4.1-mini",
+        messages=[{"role": "user", "content": prompt}],
+        temperature=0.2,
+    )
+    return response.choices[0].message.content or "요약 생성 실패"
+
+
+def send_email(subject: str, body: str) -> None:
+    msg = MIMEText(body, "plain", "utf-8")
+    msg["Subject"] = subject
+    msg["From"] = GMAIL_USER
+    msg["To"] = MAIL_TO
+
+    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
+        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
+        server.sendmail(GMAIL_USER, [MAIL_TO], msg.as_string())
+
+
+def validate_env() -> None:
+    required = {
+        "OPENAI_API_KEY": OPENAI_API_KEY,
+        "GMAIL_USER": GMAIL_USER,
+        "GMAIL_APP_PASSWORD": GMAIL_APP_PASSWORD,
+        "MAIL_TO": MAIL_TO,
+    }
+    missing = [k for k, v in required.items() if not v]
+    if missing:
+        raise RuntimeError(f"필수 환경변수 누락: {', '.join(missing)}")
+
+    if not NEWS_API_KEY and not ALPHA_VANTAGE_API_KEY:
+        raise RuntimeError("NEWS_API_KEY 또는 ALPHA_VANTAGE_API_KEY 중 하나는 필요합니다.")
+
+
+def main() -> None:
+    validate_env()
+
+    from_newsapi = fetch_newsapi()
+    from_alpha = fetch_alpha_vantage()
+    merged = dedupe_articles(from_newsapi, from_alpha)
+
+    if not merged:
+        report = "수집된 뉴스가 없습니다. 키워드/쿼터/API 상태를 확인하세요."
+    else:
+        report = summarize_korean(merged)
+
+    kst = datetime.now(timezone.utc) + timedelta(hours=9)
+    subject = f"[아침브리핑] 미국주식 뉴스 요약 - {kst.strftime('%Y-%m-%d')}"
+    send_email(subject, report)
+
+
+if __name__ == "__main__":
+    main()
