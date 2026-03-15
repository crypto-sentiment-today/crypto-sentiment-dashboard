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

def calculate_posterior(prior, likelihood):
    """
    In a true Bayesian statistical sense, posterior is proportional to prior * likelihood.
    For this dashboard demo (0-100 scale), we use a normalized approximation.
    """
    return (prior + likelihood) / 2

def derive_sentiment_likelihood(price_change_24h, volume_24h, market_cap):
    """
    Algorithmically derives a 0-100 'Likelihood' (Current Sentiment) based on real market momentum.
    High positive price change + High volume = High Bullish Sentiment (>50)
    Negative price change + High volume = High Bearish Sentiment (<50)
    Flat price action = Neutral Sentiment (~50)
    """
    if price_change_24h is None:
        return 50 # Default neutral if data is missing
        
    # Baseline is exactly neutral
    base_sentiment = 50.0
    
    # Sigmoid mapping of price change to sentiment (-20% to +20% maps to roughly 0 to 100)
    # y = 1 / (1 + e^-x) -> scaled to 0-100
    # A 10% move is very significant in 24h. We scale x so that 10% gives a strong signal.
    # e.g. change of 10 -> x = 1.0 -> sentiment ~73%
    x = price_change_24h / 10.0 
    sigmoid_modifier = 1 / (1 + math.exp(-x))
    
    likelihood = sigmoid_modifier * 100
    
    # Cap between 10 and 90 to prevent extreme certainty 
    return int(max(10, min(90, likelihood)))
    

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
        
        print(f"[{ticker}] Processing momentum data...")
        
        likelihood = derive_sentiment_likelihood(change_24h, vol_24h, mcap)
            
        # Prior is carried over from last run, or defaulted to 50
        prior = existing_data.get(ticker, {}).get("posterior", 50)
        
        # Compute posterior
        posterior = calculate_posterior(prior, likelihood)
        
        # Determine signal flag
        if posterior >= 60:
            signal = "BULLISH"
        elif posterior <= 40:
            signal = "BEARISH"
        else:
            signal = "NEUTRAL"
            
        results[ticker] = {
            "name": name,
            "image": thumb,
            "current_price": price,
            "price_change_24h": round(change_24h, 2) if change_24h else 0,
            "prior": int(prior),
            "likelihood": likelihood,
            "posterior": round(posterior, 1),
            "signal": signal,
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
        
    print(f"\nSuccessfully wrote updated Bayesian sentiment for {len(data)} assets to {DATA_FILE}")
    for asset, metrics in data.items():
        print(f"  -> {asset}: Prior {metrics['prior']}% | Likelihood {metrics['likelihood']}% | Posterior {metrics['posterior']}% ({metrics['signal']}) | Price: ${metrics['current_price']} ({metrics['price_change_24h']}%)")
        
if __name__ == "__main__":
    main()
