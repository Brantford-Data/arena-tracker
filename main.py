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

# --- THE EXECUTIVE INPUT ---
# Update this number when you see the market move.
# Source: Your TradingView Account (TVC:CA30Y)
MANUAL_OVERRIDE = 3.861 

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
    
    # Smart Update: If we run this multiple times a day, just update the last line
    # so we don't have 10 entries for the same day.
    if file_exists:
        with open(CSV_FILE, 'r') as f:
            lines = f.readlines()
            if len(lines) > 1 and data["date"] in lines[-1]:
                print(f"♻️ Updating today's entry with new rate: {data['bond_yield']}%")
                lines[-1] = f"{data['date']},{data['bond_yield']},{data['total_rate']},{data['annual_payment']},{data['total_interest']},{data['household_impact']}\n"
                with open(CSV_FILE, 'w') as f_write:
                    f_write.writelines(lines)
                print(f"✅ Dashboard Updated.")
                return

    with open(CSV_FILE, mode='a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=data.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(data)
    print(f"✅ New Day Entry Saved.")

if __name__ == "__main__":
    print(f"--- Executive Update: {MANUAL_OVERRIDE}% ---")
    data = calculate_impact(MANUAL_OVERRIDE)
    update_csv(data)
