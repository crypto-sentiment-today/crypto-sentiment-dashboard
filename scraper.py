import json
import time
import os
import math

try:
    import requests
except ImportError:
    print("Warning: requests not installed. Cannot fetch live data.")
    requests = None

DATA_FILE = "data.json"
CG_API_URL = "https://api.coingecko.com/api/v3/coins/markets"

def fetch_top_20_crypto_sentiment():
    """
    Fetches the top 20 cryptocurrencies by market cap from CoinGecko
    and derives their sentiment likelihood.
    """
    print(f"Fetching Top 20 Cryptos from CoinGecko API...")
    
    if not requests:
        return {}

    # Fetch Top 20 by Market Cap
    params = {
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': 20,
        'page': 1,
        'sparkline': False,
        'price_change_percentage': '24h'
    }
    
    try:
        response = requests.get(CG_API_URL, params=params, timeout=10)
        response.raise_for_status()
        coins_data = response.json()
    except Exception as e:
        print(f"Error fetching data from CoinGecko: {e}")
        return {}

    results = {}
    
    # Check if existing data is there to use as 'prior'
    existing_data = {}
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                existing_data = json.load(f)
        except Exception:
            pass
            
    for coin in coins_data:
        ticker = coin['symbol'].upper()
        name = coin['name']
        thumb = coin['image']
        price = coin['current_price']
        change_24h = coin['price_change_percentage_24h']
        vol_24h = coin['total_volume']
        mcap = coin['market_cap']
        
        print(f"[{ticker}] Processing real sentiment data...")
        
        # We need to make a specific call to the individual coin endpoint to get sentiment
        # The markets list endpoint doesn't include 'sentiment_votes_up_percentage' by default
        coin_id = coin['id']
        raw_sentiment = 50 # Default if API fails
        try:
            # We add a tiny delay to avoid hitting rate limits on the free API tier
            time.sleep(0.5) 
            detail_res = requests.get(f"https://api.coingecko.com/api/v3/coins/{coin_id}", timeout=5)
            if detail_res.ok:
                detail_data = detail_res.json()
                up_votes = detail_data.get('sentiment_votes_up_percentage')
                if up_votes is not None:
                    raw_sentiment = up_votes
        except Exception as e:
            print(f"  -> Error fetching sentiment for {ticker}: {e}")
            
        results[ticker] = {
            "name": name,
            "image": thumb,
            "current_price": price,
            "price_change_24h": round(change_24h, 2) if change_24h else 0,
            "total_volume": vol_24h,
            "likelihood": float(raw_sentiment),
            "timestamp": int(time.time())
        }
        
    return results

def main():
    print("=== Real-Time Crypto Sentiment Engine ===")
    data = fetch_top_20_crypto_sentiment()
    
    if not data:
        print("Failed to fetch or process any data.")
        return
        
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)
        
    print(f"\nSuccessfully wrote updated sentiment for {len(data)} assets to {DATA_FILE}")
    for asset, metrics in data.items():
        print(f"  -> {asset}: Raw {metrics['likelihood']}% | Vol {metrics['total_volume']} | Price: ${metrics['current_price']} ({metrics['price_change_24h']}%)")
        
if __name__ == "__main__":
    main()
