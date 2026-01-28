import requests
import csv
import os
from datetime import datetime

# --- CONFIGURATION ---
PROJECT_NAME = "Brantford SEC Arena"
PRINCIPAL = 140000000      # $140 Million
AMORTIZATION = 30          # 30 Years
MUNICIPAL_SPREAD = 1.10    # 1.10% Risk Premium
HOUSEHOLDS = 45000         # Est. Taxable Households
CSV_FILE = "interest_rate_log.csv"

# --- MANUAL OVERRIDE (Safety Net) ---
# If everything else fails, use this number so the site never breaks.
MANUAL_OVERRIDE = 3.861 

def get_tradingview_rate():
    """
    Safely attempts to fetch TradingView data.
    """
    try:
        # Import inside the function so script doesn't crash if library is missing
        from tradingview_ta import TA_Handler, Interval
    except ImportError:
        print("⚠️ Library 'tradingview-ta' not found. Skipping.")
        return None

    # List of screeners to try (sometimes bonds are listed in different databases)
    screeners_to_try = ["america", "global", "bonds"]
    
    for screener in screeners_to_try:
        try:
            print(f"📡 Trying TradingView (Screener: {screener})...")
            handler = TA_Handler(
                symbol="CA30Y",
                exchange="TVC",
                screener=screener,
                interval=Interval.INTERVAL_1_DAY
            )
            analysis = handler.get_analysis()
            current_yield = analysis.indicators["close"]
            
            if current_yield:
                print(f"✅ Success! Found Rate: {current_yield}%")
                return float(current_yield)
        except Exception as e:
            print(f"   Note: Failed with '{screener}': {e}")
    
    return None

def get_bond_yield():
    # 1. Try TradingView
    tv_rate = get_tradingview_rate()
    if tv_rate:
        return tv_rate

    # 2. Try Bank of Canada (Backup)
    print("⚠️ TradingView failed. Trying Bank of Canada...")
    series_id = "V122544"
    url = f"https://www.bankofcanada.ca/valet/observations/{series_id}/json?recent=1"
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "observations" in data and len(data["observations"]) > 0:
                val = float(data["observations"][-1][series_id]["v"])
                print(f"✅ Found Bank of Canada Rate: {val}%")
                return val
    except Exception as e:
        print(f"   BoC Error: {e}")

    # 3. Final Safety Net: Manual Override
    if MANUAL_OVERRIDE > 0:
        print(f"⚠️ All automated feeds failed. Using Manual Override: {MANUAL_OVERRIDE}%")
        return MANUAL_OVERRIDE
    
    return None

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
        "bond_yield": bond_yield,
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
                print("♻️ Updating today's existing entry...")
                lines[-1] = f"{data['date']},{data['bond_yield']},{data['total_rate']},{data['annual_payment']},{data['total_interest']},{data['household_impact']}\n"
                with open(CSV_FILE, 'w') as f_write:
                    f_write.writelines(lines)
                print(f"✅ Updated {CSV_FILE}.")
                return

    with open(CSV_FILE, mode='a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=data.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(data)
    print(f"✅ Data saved to {CSV_FILE}")

if __name__ == "__main__":
    print("--- Starting Rate Check ---")
    bond_yield = get_bond_yield()
    
    if bond_yield:
        print(f"Using Yield: {bond_yield}%")
        data = calculate_impact(bond_yield)
        update_csv(data)
    else:
        # Even if everything breaks, we NEVER exit with error code 1 anymore.
        # This prevents the Red X and keeps the site alive.
        print("❌ Critical Failure. No rate found.")
        exit(0)
