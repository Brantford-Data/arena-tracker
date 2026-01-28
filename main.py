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

def get_live_bond_yield():
    # Priority List of Series IDs to try
    # 1. V122544: Long-Term Benchmark (Approx 30yr)
    # 2. V122530: Avg Yield Marketable Bonds > 10yrs (Excellent Proxy)
    # 3. V122543: 10-Year Benchmark (Safety Net)
    series_candidates = ["V122544", "V122530", "V122543"]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36"
    }

    for series_id in series_candidates:
        url = f"https://www.bankofcanada.ca/valet/observations/{series_id}/json?recent=1"
        try:
            print(f"Trying Series ID: {series_id}...")
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if "observations" in data and len(data["observations"]) > 0:
                    val = data["observations"][-1][series_id]["v"]
                    print(f"✅ Success! Found rate using {series_id}")
                    return float(val)
            else:
                print(f"⚠️ Failed to fetch {series_id} (Status: {response.status_code})")
                
        except Exception as e:
            print(f"⚠️ Error with {series_id}: {e}")
    
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
    
    # Prevent duplicate entries for the same day
    if file_exists:
        with open(CSV_FILE, 'r') as f:
            lines = f.readlines()
            if len(lines) > 1:
                last_line = lines[-1]
                if data["date"] in last_line:
                    print("⚠️ Data for today already exists. Skipping write.")
                    return

    with open(CSV_FILE, mode='a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=data.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(data)
    print(f"✅ Data saved to {CSV_FILE}")

if __name__ == "__main__":
    print("--- Starting Rate Check ---")
    bond_yield = get_live_bond_yield()
    
    if bond_yield:
        print(f"Live Yield: {bond_yield}%")
        data = calculate_impact(bond_yield)
        update_csv(data)
    else:
        print("❌ All Series IDs failed. Script aborted.")
        exit(1)
