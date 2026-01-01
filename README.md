# 📊 FinRep: Daily US Stock Briefing

FinRep is an automated system that fetches daily closing prices and technical indicators (RSI, EMA) for specific US stocks and sends a visualized briefing to KakaoTalk.

## 🚀 Key Features

- **Data Collection**: Fetches historical data for specific tickers (BITU, ORCX, PLTG, CRWU, CCUP, OKLL) using `yfinance`.
- **Technical Analysis**: Calculates RSI(14) and EMA(20, 60, 120) using `pandas-ta`.
- **Visualized Report**: Generates a premium dark-themed HTML report.
- **KakaoTalk Integration**: Sends a summary "Feed" message with a direct link to the report via KakaoTalk.
- **Automation**: Runs every day at 7:00 AM KST using GitHub Actions and GitHub Pages.

## 🔗 Live Report

The latest briefing is available at:
[https://heroyik.github.io/finrep/](https://heroyik.github.io/finrep/)

## 🛠 Tech Stack

- **Language**: Python 3.13
- **Libraries**: `yfinance`, `pandas`, `pandas-ta`, `requests`
- **Infrastructure**: GitHub Actions, GitHub Pages (Deploying from `gh-pages` branch)
- **API**: Kakao Developers (OAuth 2.0)

## ⚙️ Setup & Secrets

To run this project, you need to set up the following GitHub Secrets:

| Secret Name | Description |
| :--- | :--- |
| `KAKAO_REST_API_KEY` | Kakao Developers REST API Key |
| `KAKAO_CLIENT_SECRET` | Kakao Login Security Client Secret |
| `KAKAO_REFRESH_TOKEN` | Initial OAuth 2.0 Refresh Token |

Additionally, ensure that:
1.  GitHub Actions has **Read and write permissions** (Settings > Actions > General).
2.  GitHub Pages is configured to deploy from the **gh-pages** branch.
3.  The domain `https://heroyik.github.io` is registered in the Kakao Developers Console (Platform > Web).

## 📅 Schedule

The automation script is scheduled via `.github/workflows/daily_briefing.yml`:
- **Cron**: `0 22 * * *` (UTC) / 07:00 (KST)

## 📄 License

MIT License.
