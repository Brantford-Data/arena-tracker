import requests
import csv
import os
from datetime import datetime
import yfinance as yf

# --- CONFIGURATION ---
PROJECT_NAME = "Brantford SEC Arena"
PRINCIPAL = 140000000      # $140 Million
AMORTIZATION = 30          # 30 Years
MUNICIPAL_SPREAD = 1.10    # 1.10% Risk Premium
HOUSEHOLDS = 45000         # Est. Taxable Households
CSV_FILE = "interest_rate_log.csv"

# --- MANUAL OVERRIDE (Backup) ---
# Set to 0 to use Yahoo Finance. 
MANUAL_OVERRIDE = 0 

def get_yahoo_rate():
    """
    Fetches the live Canada 30-Year Bond Yield from Yahoo Finance.
    We use the ticker 'GC=F' (Gold) or similar proxies if specific bonds aren't listed,
    but for Canada 10Y+ we often use US proxies or specific indices.
    
    Better yet: We can calculate the closest proxy or just use the highly liquid
    US 30Y (^TYX) and apply a standard 'Canada Spread' if the direct ticker is missing.
    
    HOWEVER, for simplicity, we will try to pull the 'Can 10Y Benchmark' and adjust,
    or use the direct 'CAD 30Y' if available. 
    
    Yahoo Ticker for Canada 10Y Bond Yield: "GCAN10YR" (Index) or similar.
    Let's try the widely available 'Global Rates' approach.
    """
    try:
        # Ticker for US 30 Year Treasury Yield is ^TYX
        # Canadian long-term bonds usually trade very closely to US rates + a small spread.
        # But let's try to get a direct Canadian ETF yield like 'XLB.TO' (Canadian Long Bond ETF).
        # We can calculate yield from price, OR just use the US 30Y (^TYX) which is 99% reliable uptime.
        
        # STRATEGY: Get US 30Y Yield (^TYX) and adjust for the CAD/US Spread (approx -0.1% to +0.1% currently).
        # This is often more reliable than finding a delayed CAD ticker.
        
        # ALTERNATIVE: Use the manual override if this fails.
        
        print("📡 Connecting to Yahoo Finance...")
        
        # Let's try the US 30 Year Treasury (^TYX) as a reliable proxy base
        # (It divides by 10, so 38.60 becomes 3.86%)
        ticker = yf.Ticker("^TYX") 
        data = ticker.history(period="1d")
        
        if not data.empty:
            # ^TYX is often quoted as "38.60" for 3.86%
            val = data['Close'].iloc[-1]
            if val > 10:
                val = val / 10
            
            # Correction: Canadian bonds are currently trading slightly ABOVE US bonds.
            # Let's add a small 'Basis Adjustment' or just accept US 30Y as a solid conservative proxy.
            # For this specific project, let's trust the US 30Y trend as the driver.
            print(f"✅ Yahoo Success! Found Base Rate: {val}%")
            return float(val)
            
    except Exception as e:
        print(f"⚠️ Yahoo Finance Error: {e}")
    
    return None

def get_bond_yield():
    # 1. Check Manual Override first
    if MANUAL_OVERRIDE > 0:
        print(f"⚠️ Using Manual Override Rate: {MANUAL_OVERRIDE}%")
        return MANUAL_OVERRIDE

    # 2. Try Yahoo Finance
    yahoo_rate = get_yahoo_rate()
    if yahoo_rate:
        return yahoo_rate

    # 3. Fallback: Bank of Canada
    print("⚠️ Yahoo failed. Trying Bank of Canada fallback...")
    series_id = "V122544"
    url = f"https://www.bankofcanada.ca/valet/observations/{series_id}/json?recent=1"
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        data = response.json()
        if "observations" in data and len(data["observations"]) > 0:
            return float(data["observations"][-1][series_id]["v"])
    except:
        pass
    
    # 4. Final Safety Net (The number you verified today)
    print("⚠️ All feeds failed. Defaulting to last known good rate.")
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
        print("❌ Critical Failure.")
        exit(0)
