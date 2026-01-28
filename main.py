import requests
import json
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
    series_id = "V122544"
    url = f"https://www.bankofcanada.ca/valet/observations/{series_id}/json?recent=1"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if "observations" in data and len(data["observations"]) > 0:
            val = data["observations"][-1][series_id]["v"]
            return float(val)
    except Exception as e:
        print(f"Error fetching data: {e}")
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
    with open(CSV_FILE, mode='a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=data.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(data)
    print(f"Data saved to {CSV_FILE}")

if __name__ == "__main__":
    bond_yield = get_live_bond_yield()
    if bond_yield:
        print(f"Live Yield: {bond_yield}%")
        data = calculate_impact(bond_yield)
        update_csv(data)
