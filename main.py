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

def get_rate():
    # --- ATTEMPT 1: BANK OF CANADA (Official) ---
    # We use urllib (Standard Library) so we don't need 'pip install requests'
    try:
        url = "https://www.bankofcanada.ca/valet/observations/V122544/json?recent=10"
        print(f"🌍 Connecting to Bank of Canada...")
        
        # Create a context that ignores SSL verification (fixes common server blocks)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
            data = json.loads(response.read().decode())
            
            if "observations" in data and len(data["observations"]) > 0:
                last_entry = data["observations"][-1]
                val = float(last_entry["V122544"]["v"])
                print(f"✅ Success: Bank of Canada Rate is {val}%")
                return val
    except Exception as e:
        print(f"⚠️ Bank of Canada Failed: {e}")

    # --- ATTEMPT 2: SAFETY NET ---
    # If the API fails, we return the fallback immediately so the CSV is never empty.
    print(f"❌ API Failed. Using Fallback: {SAFE_FALLBACK_RATE}%")
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
    
    # OVERWRITE MODE ('w') - Ensures we create a clean, valid file every time
    with open(CSV_FILE, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(data)
    print(f"✅ Dashboard Updated.")

if __name__ == "__main__":
    rate = get_rate()
    data = calculate_project_costs(rate)
    update_csv(data)
