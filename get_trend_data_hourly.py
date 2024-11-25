import MetaTrader5 as mt5
import mplfinance as mpf
from dotenv import load_dotenv
import pandas as pd
import os
from datetime import datetime, timedelta
import shutil
import random
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.dates as mdates

# Load environment variables for MT5 login credentials
load_dotenv()
login = int(os.getenv('MT5_LOGIN'))  # Replace with your login ID
password = os.getenv('MT5_PASSWORD')  # Replace with your password
server = os.getenv('MT5_SERVER')  # Replace with your server name

# Initialize MetaTrader 5 connection
if not mt5.initialize(login=login, password=password, server=server):
    print("Failed to initialize MT5, error code:", mt5.last_error())
    quit()

# Define parameters
symbols = ["EURUSD", "USDJPY", "GBPUSD", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD"]
timeframe = mt5.TIMEFRAME_H1  # 1-hour timeframe
interval = timedelta(hours=12)  # Data interval per image
output_dir = "output"
screenshots_dir = os.path.join(output_dir, "market_screenshots")
debug_log_file = os.path.join(output_dir, "debug_log.txt")
train_dir = os.path.join(output_dir, "train")
test_dir = os.path.join(output_dir, "test")

# Ensure all necessary directories exist
os.makedirs(train_dir, exist_ok=True)
os.makedirs(test_dir, exist_ok=True)
os.makedirs(screenshots_dir, exist_ok=True)
os.makedirs(output_dir, exist_ok=True)

def get_trend_label(df):
    """
    Determine the trend based on the open and close prices in the DataFrame.
    """
    open_price = df['open'].iloc[0]
    close_price = df['close'].iloc[-1]
    change = (close_price - open_price) / open_price

    if change > 0.005:  # Bullish threshold
        return "bullish"
    elif change < -0.005:  # Bearish threshold
        return "bearish"
    else:
        return "sideways"

def save_candlestick_chart(df, filename):
    """
    Save a candlestick chart from DataFrame `df` to `filename`.
    """
    df = df[['open', 'high', 'low', 'close']].apply(pd.to_numeric, errors='coerce').dropna()
    fig, ax = plt.subplots()
    mpf.plot(df, type='candle', style='charles', ax=ax)
    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    plt.savefig(filename, dpi=100, bbox_inches='tight', pad_inches=0)
    plt.close()

def get_rates(symbol, timeframe, start, end):
    rates = mt5.copy_rates_range(symbol, timeframe, start, end)
    if rates is None or len(rates) == 0:
        with open(debug_log_file, "a") as log:
            log.write(f"No data for {symbol} from {start} to {end}.\n")
        return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    return df

# Process each symbol
for symbol in symbols:
    print(f"Processing symbol: {symbol}")
    
    # Main loop through each interval for the current symbol
    current_date = datetime.now() - timedelta(days=1826)
    end_date = datetime.now()
    
    while current_date <= end_date:
        next_date = current_date + interval
        main_filename = os.path.join(screenshots_dir, f"{symbol}_{current_date.strftime('%Y%m%d%H%M')}.png")
        
        # Retrieve the 12-hour data period
        df = get_rates(symbol, timeframe, current_date, next_date)
        if df is not None and len(df) >= interval.total_seconds() / 3600:
            save_candlestick_chart(df, main_filename)  # Save the main chart image
            
            trend_label = get_trend_label(df)
            if trend_label is not None:
                # Log the trend decision
                with open(debug_log_file, "a") as log:
                    log.write(f"{symbol}: {current_date} to {next_date}, Trend: {trend_label}\n")
                
                # Move the main chart to train/test directories based on the label
                destination_dir = train_dir if random.random() < 0.8 else test_dir
                label_dir = os.path.join(destination_dir, trend_label)
                os.makedirs(label_dir, exist_ok=True)
                
                # Move main chart
                shutil.move(main_filename, os.path.join(label_dir, os.path.basename(main_filename)))
        else:
            with open(debug_log_file, "a") as log:
                log.write(f"{symbol} No valid data for interval {current_date} to {next_date}.\n")
        
        # Move to the next interval
        current_date = next_date

shutil.rmtree(screenshots_dir)  # Delete the directory and all its contents once done

# Shut down MetaTrader 5 connection
mt5.shutdown()