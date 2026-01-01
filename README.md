# 📊 FinRep: Daily US Stock Briefing

FinRep is an automated system that fetches daily closing prices and technical indicators (RSI, EMA) for specific US stocks and sends a visualized briefing to KakaoTalk.

## 🚀 Key Features

- **Data Collection**: Fetches historical data using `yfinance` for tracked tickers (BITU, ORCX, PLTG, CRWU, CCUP, OKLL).
- **Dynamic Signal Dashboard**: A conditional "Signal Board" at the top of the report instantly highlights assets triggering specific trading setups (Bullish Trend, Oversold, Overbought). Empty signals are automatically hidden for clarity.
- **Smart News Integration**: Automatically curates relevant news for each asset. For leverage ETFs (e.g., BITU), it intelligently fetches news for the underlying asset (e.g., Bitcoin) to provide context.
- **Premium Charting**:
    - **Minimalist Design**: Symmetric margins, custom EMA color palettes (Orange/Purple/Slate), and clear visibility.
    - **Interactive Analysis**: Features a **Click-to-Zoom** modal for high-resolution chart inspection.
- **Visualized Report**: Generates a sleek, dark-themed HTML report hosted on GitHub Pages with **KST Timezone** support.
- **KakaoTalk Integration**: Sends a summary message with a direct "View Report" button via KakaoTalk.
- **Full Automation**: Scheduled execution every day at 7:00 AM KST using GitHub Actions.

## 🔗 Live Report

The latest briefing is always available at:
👉 [**https://heroyik.github.io/finrep/**](https://heroyik.github.io/finrep/)

## 🛠 Tech Stack

- **Language**: Python 3.13
- **Libraries**: `yfinance` (Data), `pandas-ta` (Analysis), `mplfinance` (Charting), `requests` (News & API)
- **Infrastructure**: GitHub Actions, GitHub Pages (Deployed from `gh-pages` branch)
- **API**: Kakao Developers (OAuth 2.0 Message API)

## ⚙️ Setup & Secrets: Step-by-Step

To run this project, you need to configure the Kakao API and GitHub Secrets.

### 1. Kakao Developers Setup

1.  Go to [Kakao Developers](https://developers.kakao.com/) and Log in.
2.  Click **"Add An Application"** and create a new app (e.g., "StockBriefing").
3.  Go to **[My Application] > [App Keys]** and copy the **REST API Key**.
4.  Go to **[Product Settings] > [Kakao Login]**:
    *   Turn **ON** the activation switch.
    *   Under **Redirect URI**, clicking "Register Redirect URI" and add: `https://localhost:3000`.
5.  Go to **[Product Settings] > [Kakao Login] > [Security]**:
    *   Click "Generate code" for **Client Secret**.
    *   Copy the **Client Secret** string.
    *   Set **Activation State** to **Enable**.
6.  Go to **[Product Settings] > [Platfrom]**:
    *   Click "Register Web Platform".
    *   Add your GitHub Pages URL: `https://heroyik.github.io`.

### 2. Get Access/Refresh Token

You need to authorize your app once to get the initial tokens.

1.  **Get Authorization Code**:
    *   Replace `{REST_API_KEY}` in the URL below and visit it in your browser:
        ```
        https://kauth.kakao.com/oauth/authorize?client_id={REST_API_KEY}&redirect_uri=https://localhost:3000&response_type=code
        ```
    *   Log in and agree to permissions.
    *   You will be redirected to an error page (localhost). **Copy the `code=` value** from the address bar URL.

2.  **Generate Tokens**:
    *   Run the provided helper script `get_kakao_token.py` (if available) OR use this curl command (Terminal/Git Bash): // turbo
        ```bash
        curl -v -X POST "https://kauth.kakao.com/oauth/token" \
         -d "grant_type=authorization_code" \
         -d "client_id={REST_API_KEY}" \
         -d "redirect_uri=https://localhost:3000" \
         -d "code={AUTHORIZATION_CODE}" \
         -d "client_secret={CLIENT_SECRET}"
        ```
    *   Copy the `"refresh_token"` from the JSON response.

### 3. GitHub Secrets Configuration

Go to your repository **Settings > Secrets and variables > Actions** and add these repository secrets:

| Secret Name | Value to Enter |
| :--- | :--- |
| `KAKAO_REST_API_KEY` | The **REST API Key** from Step 1. |
| `KAKAO_CLIENT_SECRET` | The **Client Secret** from Step 1. |
| `KAKAO_REFRESH_TOKEN` | The **refresh_token** from Step 2. |

### 4. GitHub Actions Permissions

1.  Go to **Settings > Actions > General**.
2.  Scroll to **Workflow permissions**.
3.  Select **Read and write permissions**.
4.  Click **Save**.

## 📅 Schedule

The automation script is scheduled via `.github/workflows/daily_briefing.yml`:
- **Cron**: `0 22 * * *` (UTC) / 07:00 (KST)
- **Manual Trigger**: Supports `workflow_dispatch` for on-demand reports.

## 📄 License

MIT License.

## 👨‍💻 Credits

Crafted by **antigravity** based on [**nIcK**](mailto:heroyik@gmail.com)'s investment strategy.
