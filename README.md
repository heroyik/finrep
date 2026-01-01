# 📊 FinRep: Daily US Stock Briefing

FinRep is an automated system that fetches daily closing prices and technical indicators (RSI, EMA) for specific US stocks and sends a visualized briefing to KakaoTalk.

## 🚀 Key Features

- **Data Collection**: Fetches historical data for specific tickers (BITU, ORCX, PLTG, CRWU, CCUP, OKLL) using `yfinance`.
- **Technical Analysis**: Calculates RSI(14) and EMA(20, 60, 120) using `pandas-ta`.
- **Visualized Report**: Generates a premium dark-themed HTML report hosted on GitHub Pages.
- **KakaoTalk Integration**: Sends a summary message with a direct "View Report" button via KakaoTalk.
- **Full Automation**: Scheduled execution every day at 7:00 AM KST using GitHub Actions.

## 🔗 Live Report

The latest briefing is always available at:
👉 [**https://heroyik.github.io/finrep/**](https://heroyik.github.io/finrep/)

## 🛠 Tech Stack

- **Language**: Python 3.13
- **Libraries**: `yfinance`, `pandas`, `pandas-ta`, `requests`
- **Infrastructure**: GitHub Actions, GitHub Pages (Deployed from `gh-pages` branch)
- **API**: Kakao Developers (OAuth 2.0 Message API)

## ⚙️ Setup & Secrets

To run this project, you need to set up the following GitHub Secrets under `Settings > Secrets and variables > Actions`:

| Secret Name | Description |
| :--- | :--- |
| `KAKAO_REST_API_KEY` | Kakao Developers REST API Key |
| `KAKAO_CLIENT_SECRET` | Kakao Login Security Client Secret |
| `KAKAO_REFRESH_TOKEN` | Initial OAuth 2.0 Refresh Token |

### Required Repository Settings
1.  **Workflow Permissions**: Set to **Read and write permissions** (*Settings > Actions > General*).
2.  **GitHub Pages**: Configure to deploy from the **gh-pages** branch (*Settings > Pages*).
3.  **Kakao Platform**: Register `https://heroyik.github.io` in **Web Platform Settings** (*Kakao Developers > My Application > Platform*).

## 📅 Schedule

The automation script is scheduled via `.github/workflows/daily_briefing.yml`:
- **Cron**: `0 22 * * *` (UTC) / 07:00 (KST)
- **Manual Trigger**: Supports `workflow_dispatch` for on-demand reports.

## 📄 License

MIT License.
