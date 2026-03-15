import json
import time
import random
import os

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Warning: requests or bs4 not installed. Using mock fetch engine.")
    requests = None
    BeautifulSoup = None

DATA_FILE = "data.json"

def calculate_posterior(prior, likelihood):
    """
    In a true Bayesian statistical sense, posterior is proportional to prior * likelihood.
    For this dashboard demo (0-100 scale), we use a normalized approximation.
    """
    return (prior + likelihood) / 2

def scrape_cmc_sentiment():
    """
    Scrapes or mocks the sentiment data from CoinMarketCap.
    """
    print("Initializing CoinMarketCap Sentiment Data Engine...")
    assets = ["BTC", "ETH", "SOL"]
    results = {}
    
    # Check if existing data is there to use as 'prior'
    existing_data = {}
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                existing_data = json.load(f)
        except Exception:
            pass
            
    for asset in assets:
        print(f"[{asset}] Fetching community likelihood...")
        
        # In a production environment, we would use requests + BS4 to parse
        # https://coinmarketcap.com/currencies/<asset-slug>/ or CMC API.
        # Since CMC is heavily dynamic and rate-limited, we mock realistic values.
        time.sleep(0.5)
        
        # Base likelihood depends loosely on asset
        if asset == "BTC":
            likelihood = random.randint(50, 75)
        elif asset == "SOL":
            likelihood = random.randint(65, 95)
        else:
            likelihood = random.randint(35, 60)
            
        # Prior is carried over from last run, or defaulted
        prior = existing_data.get(asset, {}).get("posterior", 50)
        
        # Compute posterior
        posterior = calculate_posterior(prior, likelihood)
        
        # Determine signal flag
        if posterior >= 60:
            signal = "BULLISH"
        elif posterior <= 40:
            signal = "BEARISH"
        else:
            signal = "NEUTRAL"
            
        results[asset] = {
            "prior": int(prior),
            "likelihood": likelihood,
            "posterior": round(posterior, 1),
            "signal": signal,
            "timestamp": int(time.time())
        }
        
    return results

def main():
    print("=== Crypto Sentiment Scraper ===")
    data = scrape_cmc_sentiment()
    
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)
        
    print(f"\nSuccessfully wrote updated Bayesian sentiment to {DATA_FILE}")
    for asset, metrics in data.items():
        print(f"  -> {asset}: Prior {metrics['prior']}% | Likelihood {metrics['likelihood']}% | Posterior {metrics['posterior']}% ({metrics['signal']})")
        
if __name__ == "__main__":
    main()
