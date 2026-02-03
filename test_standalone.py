import yfinance as yf
import pandas as pd
import pandas_ta as ta
import os
import mplfinance as mpf
import matplotlib.pyplot as plt

def generate_chart_standalone(symbol, df, filename):
    # Use more trading days for better context (120 days)
    plot_df = df.tail(120).copy()
    
    # Remove empty data
    plot_df = plot_df.dropna(subset=['Open', 'High', 'Low', 'Close'])
    
    # EMA line settings (Add only if data exists)
    apds = []
    
    # EMA 20
    if 'EMA20' in plot_df.columns and not plot_df['EMA20'].isnull().all():
        apds.append(mpf.make_addplot(plot_df['EMA20'], color='#f59e0b', width=1.2, label='EMA 20'))
        
    # EMA 60
    if 'EMA60' in plot_df.columns and not plot_df['EMA60'].isnull().all():
        apds.append(mpf.make_addplot(plot_df['EMA60'], color='#8b5cf6', width=1.2, label='EMA 60'))
        
    # EMA 120 (Exclude if insufficient data)
    if 'EMA120' in plot_df.columns and not plot_df['EMA120'].isnull().all():
        apds.append(mpf.make_addplot(plot_df['EMA120'], color='#64748b', width=1.2, label='EMA 120'))
        
    # RSI
    if 'RSI' in plot_df.columns and not plot_df['RSI'].isnull().all():
        apds.append(mpf.make_addplot(plot_df['RSI'], panel=1, color='#313d4a', width=1.0, secondary_y=False))
    
    # Minimal style settings
    mc = mpf.make_marketcolors(up='#10b981', down='#f43f5e', edge='inherit', wick='inherit', volume='inherit')
    style = mpf.make_mpf_style(
        marketcolors=mc, 
        gridstyle=':', 
        gridcolor='#f1f5f9',
        facecolor='white', 
        edgecolor='#cbd5e1',
        rc={'font.family': 'sans-serif', 'font.size': 6.5}
    )
    
    # Create chart folder
    if not os.path.exists("public/charts"):
        os.makedirs("public/charts")
    
    # Save chart
    full_path = os.path.join("public/charts", filename)
    print(f"Generating chart: {full_path}")
    
    # Plotting
    fig, axes = mpf.plot(
        plot_df,
        type='candle',
        addplot=apds,
        volume=False,
        figratio=(12, 8),
        style=style,
        returnfig=True,
        panel_ratios=(2, 1),
        tight_layout=False,
        ylabel='',
        ylabel_lower=''
    )
    
    plt.subplots_adjust(left=0.12, right=0.85, top=0.8, bottom=0.2)
    
    # Legend settings (Simple)
    axes[0].legend(loc='upper left', fontsize=6, frameon=False)
    
    # RSI Horizontal lines
    axes[2].axhline(y=70, color='#f43f5e', linestyle='--', linewidth=0.6, alpha=0.3)
    axes[2].axhline(y=30, color='#10b981', linestyle='--', linewidth=0.6, alpha=0.3)
    
    # Axis alignment settings
    axes[0].set_ylabel('')
    axes[2].set_ylabel('')
    
    # Add Current EMA values as text labels on the right margin
    last_p = plot_df.iloc[-1]
    last_vals = []
    if 'EMA20' in last_p: last_vals.append(('EMA20', last_p['EMA20'], '#f59e0b'))
    if 'EMA60' in last_p: last_vals.append(('EMA60', last_p['EMA60'], '#8b5cf6'))
    if 'EMA120' in last_p: last_vals.append(('EMA120', last_p['EMA120'], '#475569'))
    
    for name, val, color in last_vals:
        if not pd.isna(val):
            axes[0].text(len(plot_df)-0.5, val, f' {val:.2f}', color=color, 
                        fontsize=6, fontweight='bold', va='center', ha='left')
    
    # Font and tick settings
    for ax in axes:
        ax.tick_params(axis='y', labelsize=6, pad=5)
        ax.tick_params(axis='x', labelsize=6, pad=5)
    
    # Add High/Low price annotations
    max_idx = plot_df['High'].idxmax()
    max_val = plot_df.loc[max_idx, 'High']
    min_idx = plot_df['Low'].idxmin()
    min_val = plot_df.loc[min_idx, 'Low']

    max_pos = plot_df.index.get_loc(max_idx)
    min_pos = plot_df.index.get_loc(min_idx)

    # Annotate Highest Point
    axes[0].annotate(f'{max_val:.2f}',
                 xy=(max_pos, max_val),
                 xytext=(0, 5),
                 textcoords='offset points',
                 ha='center',
                 va='bottom',
                 fontsize=6,
                 fontweight='bold',
                 color='#f43f5e',
                 arrowprops=dict(arrowstyle='-', color='#f43f5e', linewidth=0.5))

    # Annotate Lowest Point
    axes[0].annotate(f'{min_val:.2f}',
                 xy=(min_pos, min_val),
                 xytext=(0, -5),
                 textcoords='offset points',
                 ha='center',
                 va='top',
                 fontsize=6,
                 fontweight='bold',
                 color='#10b981',
                 arrowprops=dict(arrowstyle='-', color='#10b981', linewidth=0.5))

    plt.savefig(full_path, dpi=160)
    plt.close()
    return full_path

def test_annotation():
    symbol = "NVDA"
    ticker = yf.Ticker(symbol)
    df = ticker.history(period="1y")
    
    df['RSI'] = ta.rsi(df['Close'], length=14)
    df['EMA20'] = ta.ema(df['Close'], length=20)
    df['EMA60'] = ta.ema(df['Close'], length=60)
    df['EMA120'] = ta.ema(df['Close'], length=120)
    
    filename = "test_annotation_chart.png"
    result_path = generate_chart_standalone(symbol, df, filename)
    
    if os.path.exists(result_path):
        print(f"✅ Test successful! Chart saved to: {result_path}")
    else:
        print("❌ Test failed!")

if __name__ == "__main__":
    test_annotation()
