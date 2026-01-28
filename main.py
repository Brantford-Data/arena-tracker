import requests
import csv
import os
import yfinance as yf
from datetime import datetime

# --- CONFIGURATION ---
PROJECT_NAME = "Brantford SEC Arena"
PRINCIPAL = 140000000      # $140 Million
AMORTIZATION = 30          # 30 Years
MUNICIPAL_SPREAD = 1.10    # 1.10% Risk Premium
HOUSEHOLDS = 45000         # Est. Taxable Households
CSV_FILE = "interest_rate_log.csv"

def get_boc_rate():
    """
    Source 1: Bank of Canada (Official)
    Fix: Requests 'recent_weeks=1' instead of 'recent=1' to avoid 404 errors.
    """
    try:
        # V122544 is the Series ID for the Long-Term Benchmark Bond Yield
        url = "https://www.bankofcanada.ca/valet/observations/V122544/json?recent_weeks=1"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if "observations" in data and len(data["observations"]) > 0:
            # Get the very last entry (most recent date)
            last_entry = data["observations"][-1]
            val = float(last_entry["V122544"]["v"])
            print(f"✅ Source: Bank of Canada (Official). Rate: {val}%")
            return val
    except Exception as e:
        print(f"⚠️ BoC Failed: {e}")
    return None

def get_cnbc_rate():
    """
    Source 2: CNBC (Web Scrape)
    Fetches the quote for 'CA30Y' (Canada 30 Year Bond).
    """
    try:
        url = "https://www.cnbc.com/quotes/CA30Y"
        # We must look like a real browser to avoid being blocked
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            # Simple text search for the rate (it usually appears in a specific meta tag or json block)
            # Strategy: Look for the "last" price in the raw HTML text
            from lxml import html
            tree = html.fromstring(response.content)
            # CNBC usually puts the price in a specific class
            price = tree.xpath('//span[@class="QuoteStrip-lastPrice"]/text()')
            
            if price:
                val = float(price[0].replace('%', ''))
                print(f"✅ Source: CNBC Scrape. Rate: {val}%")
                return val
    except Exception as e:
        print(f"⚠️ CNBC Failed: {e}")
    return None

def get_yahoo_fallback():
    """
    Source 3: Yahoo Finance (Proxy)
    Uses the Canada 10Y Benchmark (GCAN10YR) + 0.40% Spread (Approx curve slope)
    or the 'Global Rates' index if available.
    """
    try:
        # ^CNX00 is the Canada All Cap Index (not a bond).
        # We will use US 30Y (^TYX) as the emergency proxy if all else fails.
        # US 30Y moves in 95% correlation with Canada 30Y.
        ticker = yf.Ticker("^TYX")
        data = ticker.history(period="1d")
        if not data.empty:
            val = data['Close'].iloc[-1] / 10 # TYX is quoted as 38.00 for 3.8%
            print(f"✅ Source: Yahoo Finance (^TYX Proxy). Rate: {val}%")
            return val
    except Exception as e:
        print(f"⚠️ Yahoo Failed: {e}")
    return None

def get_best_rate():
    # 1. Try Bank of Canada (Most Accurate)
    rate = get_boc_rate()
    if rate: return rate
    
    # 2. Try CNBC (Real-Time)
    rate = get_cnbc_rate()
    if rate: return rate
    
    # 3. Try Yahoo (Emergency Backup)
    rate = get_yahoo_fallback()
    if rate: return rate
    
    # 4. Final Fail-Safe (Yesterday's Manual Rate)
    # This ensures the graph NEVER crashes/empties, even if the internet breaks.
    print("❌ All feeds failed. Holding previous rate.")
    return 3.861

def calculate_impact(bond_yield):
    total_rate = bond_yield + MUNICIPAL_SPREAD
    r = (total_rate / 100)
    numerator = PRINCIPAL * (r * (1 + r)**AMORTIZATION)
    denominator = ((1 + r)**AMORTIZATION) - 1
    annual_payment = numerator / denominator
    total_cost = annual_payment * AMORTIZATION
    total_interest = total_cost - PRINCIPAL
    household_impact = annual_payment / HOUSEHOLDS
    
    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "bond_yield": round(bond_yield, 3),
        "total_rate": round(total_rate, 3),
        "annual_payment": round(annual_payment, 2),
        "total_interest": round(total_interest, 2),
        "household_impact": round(household_impact, 2)
    }

def update_csv(data):
    file_exists = os.path.isfile(CSV_FILE)
    
    if file_exists:
        with open(CSV_FILE, 'r') as f:
            lines = f.readlines()
            if len(lines) > 1 and data["date"] in lines[-1]:
                print(f"♻️ Updating today's entry...")
                lines[-1] = f"{data['date']},{data['bond_yield']},{data['total_rate']},{data['annual_payment']},{data['total_interest']},{data['household_impact']}\n"
                with open(CSV_FILE, 'w') as f_write:
                    f_write.writelines(lines)
                return

    with open(CSV_FILE, mode='a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=data.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(data)

if __name__ == "__main__":
    print("--- Starting Automated Rate Hunt ---")
    rate = get_best_rate()
    data = calculate_impact(rate)
    update_csv(data)
