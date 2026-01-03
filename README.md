# 📊 FinRep: Daily US Stock Briefing

![FinRep Icon](stock_briefing_icon.jpg)

FinRep is an automated, high-precision system designed to empower investors with daily insights. It meticulously analyzes closing prices, technical indicators (RSI, EMA), and market sentiment for a curated list of US stocks/ETFs, delivering a visually stunning and actionable briefing directly to KakaoTalk.

## 🚀 Key Features

- **Data Collection**: Fetches historical data using `yfinance` for tracked tickers (BITU, ORCX, PLTG, CRWU, CCUP, OKLL, USD, GGLL).
- **Dynamic Signal Dashboard**: Instantly highlights assets triggering specific trading setups:
  - **1st Buy**: Bearish Alignment (20 < 60 < 120*) + Close < EMA(20). (*EMA 120 is optional for new listings)
  - **2nd Buy**: 1st Buy condition met + RSI < 30 (Deep Oversold).
  - **1st Sell**: Bullish Alignment (20 > 60 > 120*) + Close > EMA(20) + RSI > 70. (*EMA 120 is optional for new listings)
  Empty signals are automatically hidden for clarity.
- **Smart News Integration**: Automatically curates relevant news for each asset. For leverage ETFs (e.g., BITU), it intelligently fetches news for the underlying asset (e.g., Bitcoin) to provide context.
- **Premium Charting**:
  - **Minimalist Design**: Symmetric margins, custom EMA color palettes (Orange/Purple/Slate), and clear visibility.
  - **Interactive Analysis**: Features a **Click-to-Zoom** modal for high-resolution chart inspection.
- **Visualized Report**: Generates a sleek, dark-themed HTML report (Fully English) hosted on GitHub Pages with **KST Timezone** support.
- **Smart KakaoTalk Notifications**:
  - **Dynamic Signal Summary**: Instantly see which tickers triggered **1st Buy**, **2nd Buy**, or **1st Sell** directly in the message body.
  - **nIcK's Exclusive Briefing**: Customized branding and header for a personalized experience.
  - **Contextual Brilliance**: Automatically hides signal categories with no detected tickers, ensuring zero clutter.
  - **US Market Date Integration**: Specifically mentions the actual US trading date analyzed, synchronizing perfectly with market hours.
  - **One-Tap Access**: Features a direct **"상세 리포트 보기"** (View Detailed Report) button for a deep-dive into the full analysis.
- **Smart Scheduling & Reliability**:
  - **Intelligent Holiday Detection**: Automatically monitors US market status (via SPY) to skip generation during holidays or weekends.
  - **Zero-Touch Automation**: Runs with 100% reliability every day at 7:00 AM KST via GitHub Actions.

## 🔗 Live Report

The latest briefing is always available at:
👉 [**https://heroyik.github.io/finrep/**](https://heroyik.github.io/finrep/)

## 🛠 Tech Stack

- **Language**: Python 3.13
- **Libraries**: `yfinance`, `pandas`, `pandas_ta`, `mplfinance`, `requests`
- **Infrastructure**: GitHub Actions, GitHub Pages (Deployed from `gh-pages` branch)
  - **Synchronization Policy**: Testing image files and charts generated in `public/charts/` are excluded from version control to maintain a clean repository.
- **API**: Kakao Developers (OAuth 2.0 Message API)

## ⚙️ Setup & Secrets: Step-by-Step

To run this project, you need to configure the Kakao API and GitHub Secrets.

### 1. Kakao Developers Setup

1. Go to [Kakao Developers](https://developers.kakao.com/) and Log in.
2. Click **"Add An Application"** and create a new app (e.g., "StockBriefing").
3. Go to **[My Application] > [App Keys]** and copy the **REST API Key**.
4. Go to **[Product Settings] > [Kakao Login]**:
   - Turn **ON** the activation switch.
   - Under **Redirect URI**, clicking "Register Redirect URI" and add: `https://localhost:3000`.
5. Go to **[Product Settings] > [Kakao Login] > [Security]**:
   - Click "Generate code" for **Client Secret**.
   - Copy the **Client Secret** string.
   - Set **Activation State** to **Enable**.
6. Go to **[Product Settings] > [Platform]**:
   - Click "Register Web Platform".
   - Add your GitHub Pages URL: `https://heroyik.github.io`.

### 2. Get Access/Refresh Token

You need to authorize your app once to get the initial tokens.

1. **Get Authorization Code**:
   - Replace `{REST_API_KEY}` in the URL below and visit it in your browser:

     ```text
     https://kauth.kakao.com/oauth/authorize?client_id={REST_API_KEY}&redirect_uri=https://localhost:3000&response_type=code
     ```

   - Log in and agree to permissions.
   - You will be redirected to an error page (localhost). **Copy the `code=` value** from the address bar URL.

2. **Generate Tokens**:
   - Run the provided helper script `get_kakao_token.py` (if available) OR use this curl command (Terminal/Git Bash): // turbo

     ```bash
     curl -v -X POST "https://kauth.kakao.com/oauth/token" \
      -d "grant_type=authorization_code" \
      -d "client_id={REST_API_KEY}" \
      -d "redirect_uri=https://localhost:3000" \
      -d "code={AUTHORIZATION_CODE}" \
      -d "client_secret={CLIENT_SECRET}"
     ```

   - Copy the `"refresh_token"` from the JSON response.

### 3. GitHub Secrets Configuration

Go to your repository **Settings > Secrets and variables > Actions** and add these repository secrets:

| Secret Name           | Value to Enter                      |
| :-------------------- | :---------------------------------- |
| `KAKAO_REST_API_KEY`  | The **REST API Key** from Step 1.   |
| `KAKAO_CLIENT_SECRET` | The **Client Secret** from Step 1.  |
| `KAKAO_REFRESH_TOKEN` | The **refresh_token** from Step 2.  |

### 4. GitHub Actions Permissions

1. Go to **Settings > Actions > General**.
2. Scroll to **Workflow permissions**.
3. Select **Read and write permissions**.
4. Click **Save**.

## 📅 Schedule

The automation script is scheduled via `.github/workflows/daily_briefing.yml`:

- **Cron**: `0 22 * * *` (UTC) / 07:00 (KST)
- **Manual Trigger**: Supports `workflow_dispatch` for on-demand reports.

## 📄 License

MIT License.

## 👨‍💻 Credits

Crafted by **antigravity** based on [**nIcK**](mailto:heroyik@gmail.com)'s investment strategy.
