import urllib.request
import json
import csv
import os
import ssl
from datetime import datetime

# --- CONFIGURATION ---
CSV_FILE = "interest_rate_log.csv"
MUNICIPAL_SPREAD = 0.90    # 0.90% Risk Premium
SAFE_FALLBACK_RATE = 3.86  # Safety Net

# --- THE DEBT "SHOPPING LIST" ---
PROJECTS = [
    {"name": "SEC Arena",                    "principal": 140000000, "term": 30},
    {"name": "Police Station Redevelop.",    "principal": 56000000,  "term": 30},
    {"name": "Southwest Community Centre",   "principal": 44000000,  "term": 30},
    {"name": "Oak Park Rd Extension",        "principal": 97000000,  "term": 30} 
]

def get_trading_economics_rate():
    """
    Connects to Trading Economics using standard libraries (No 'pip install' needed).
    Uses a fake User-Agent to avoid blocks.
    """
    url = "https://tradingeconomics.com/gcan30y:ind"
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })

    try:
        # Ignore SSL errors just in case
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        print(f"🌍 Connecting to Trading Economics...")
        with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
            html = response.read().decode('utf-8')
            
            # Manual Search for the rate (since we don't have BeautifulSoup)
            # We look for the specific ID: <div id="market_last">3.86</div>
            marker = 'id="market_last"'
            if marker in html:
                start_index = html.find(marker)
                # Find the first ">" after the marker
                value_start = html.find('>', start_index) + 1
                # Find the first "<" after the value
                value_end = html.find('<', value_start)
                
                raw_value = html[value_start:value_end].strip()
                val = float(raw_value)
                print(f"✅ Success: TradingEconomics Rate is {val}%")
                return val
            
            print("⚠️ Could not find rate in HTML.")
            
    except Exception as e:
        print(f"⚠️ TradingEconomics Failed: {e}")
    
    return None

def get_rate():
    # 1. Try Real-Time Source
    rate = get_trading_economics_rate()
    if rate:
        return rate

    # 2. Try Bank of Canada (Official Backup)
    try:
        url = "https://www.bankofcanada.ca/valet/observations/V122544/json?recent=10"
        print(f"🌍 Connecting to Bank of Canada...")
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        with urllib.request.urlopen(url, context=ctx, timeout=15) as response:
            data = json.loads(response.read().decode())
            if "observations" in data and len(data["observations"]) > 0:
                val = float(data["observations"][-1]["V122544"]["v"])
                print(f"✅ Success: Bank of Canada Rate is {val}%")
                return val
    except Exception as e:
        print(f"⚠️ Bank of Canada Failed: {e}")

    # 3. Safety Net
    print(f"❌ All APIs Failed. Using Fallback: {SAFE_FALLBACK_RATE}%")
    return SAFE_FALLBACK_RATE

def calculate_project_costs(bond_yield):
    total_rate = bond_yield + MUNICIPAL_SPREAD
    r = (total_rate / 100)
    grand_total_debt = 0
    grand_total_annual = 0
    grand_total_interest = 0
    
    for p in PROJECTS:
        numerator = p["principal"] * (r * (1 + r)**p["term"])
        denominator = ((1 + r)**p["term"]) - 1
        annual_payment = numerator / denominator
        total_cost = annual_payment * p["term"]
        grand_total_debt += p["principal"]
        grand_total_annual += annual_payment
        grand_total_interest += (total_cost - p["principal"])

    return {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "bond_yield": round(bond_yield, 3),
        "total_rate": round(total_rate, 3),
        "grand_annual": round(grand_total_annual, 2),
        "grand_interest": round(grand_total_interest, 2)
    }

def update_csv(data):
    file_exists = os.path.isfile(CSV_FILE)
    fieldnames = ["date", "bond_yield", "total_rate", "grand_annual", "grand_interest"]
    
    # Switch back to 'a' (Append) so the graph grows!
    mode = 'a' if file_exists else 'w'
    
    with open(CSV_FILE, mode=mode, newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(data)
    print(f"✅ Dashboard Updated.")

if __name__ == "__main__":
    rate = get_rate()
    data = calculate_project_costs(rate)
    update_csv(data)
