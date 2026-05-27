import os
import sys
from dotenv import load_dotenv

# Ensure we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

from app.services.competitor_agent import scrape_competitor_prices

def run_test():
    product_name = "Sony WH-1000XM5"
    print(f"Testing Competitor Agent for: {product_name}")
    
    results = scrape_competitor_prices(product_name)
    
    print("\n--- RESULTS ---")
    if not results:
        print("No results found.")
    else:
        for r in results:
            print(f"{r['competitor_name']}: ₹{r['price']}")

if __name__ == "__main__":
    run_test()
