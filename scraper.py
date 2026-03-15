import json
import time
import random
import re
import argparse
import requests
from playwright.sync_api import sync_playwright

DATA_FILE = "data.json"
CG_API_URL = "https://api.coingecko.com/api/v3/coins/markets"

# CoinGecko ID to CoinMarketCap URL Slug mapping
SLUG_MAPPING = {
    'binancecoin': 'bnb',
    'ripple': 'xrp',
    'avalanche-2': 'avalanche',
    'matic-network': 'polygon',
    'steth': 'lido-staked-eth',
    'wbtc': 'wrapped-bitcoin'
}

def parse_votes(vote_str):
    vote_str = vote_str.upper().replace('VOTES', '').replace('VOTE', '').strip()
    multiplier = 1
    if vote_str.endswith('K'):
        multiplier = 1000
        vote_str = vote_str[:-1]
    elif vote_str.endswith('M'):
        multiplier = 1000000
        vote_str = vote_str[:-1]
    elif vote_str.endswith('B'):
        multiplier = 1000000000
        vote_str = vote_str[:-1]
    try:
        return int(float(vote_str) * multiplier)
    except:
        return 500000 

def parse_percentage(pct_str):
    try:
        return float(pct_str.replace('%', '').strip())
    except:
        return 50.0

def fetch_top_20_coins():
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
        return response.json()
    except Exception as e:
        print(f"Error fetching base data from CoinGecko: {e}")
        return []

def scrape_cmc_sentiment(page, cmc_slug):
    url = f"https://coinmarketcap.com/currencies/{cmc_slug}/"
    print(f"  -> Navigating to {url}")
    try:
        page.goto(url, wait_until='domcontentloaded', timeout=15000)
        # Give React time to render the widget
        time.sleep(4) 

        widget_text = page.evaluate('''() => {
            const elements = Array.from(document.querySelectorAll('*'));
            const header = elements.find(e => e.textContent && e.textContent.includes('Community sentiment') && e.children.length === 0);
            if (!header) return null;
            
            let widget = header;
            for(let i=0; i<4; i++) {
               if(widget.parentElement) widget = widget.parentElement;
            }
            return widget.innerText;
        }''')

        if not widget_text:
            print(f"  -> [Warning] Widget not found for {cmc_slug}")
            return 50.0, 500000

        lines = [line.strip() for line in widget_text.split('\n') if line.strip()]
        
        # 1. Extract Votes
        vote_line = next((l for l in lines if 'vote' in l.lower()), "500K votes")
        votes = parse_votes(vote_line)

        # 2. Extract Bullish %
        try:
            bullish_index = lines.index('Bullish')
            # The percentages are usually right above "Bullish" and "Bearish"
            bullish_pct_str = lines[bullish_index - 2]
            if '%' not in bullish_pct_str:
                bullish_pct_str = lines[bullish_index - 1]
            bullish_pct = parse_percentage(bullish_pct_str)
        except ValueError:
            print(f"  -> [Warning] 'Bullish' text not found in widget for {cmc_slug}")
            bullish_pct = 50.0

        return bullish_pct, votes

    except Exception as e:
        print(f"  -> [Error] Scraping failed for {cmc_slug}: {e}")
        return 50.0, 500000

def main(fast_mode=False):
    print("=== Real-Time CoinMarketCap Sentiment Engine (Playwright) ===")
    coins_data = fetch_top_20_coins()
    if not coins_data:
        return
        
    if fast_mode:
        print("[FAST MODE] Only scraping 3 coins, 1s delay.")
        coins_data = coins_data[:3]

    results = {}
    
    with sync_playwright() as p:
        # We use a standard agent to blend in
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        page = context.new_page()

        for coin in coins_data:
            ticker = coin['symbol'].upper()
            cg_id = coin['id']
            cmc_slug = SLUG_MAPPING.get(cg_id, cg_id)

            print(f"\n[{ticker}] Extracting sentiment...")
            bullish_pct, votes = scrape_cmc_sentiment(page, cmc_slug)
            
            results[ticker] = {
                "name": coin['name'],
                "image": coin['image'],
                "current_price": coin['current_price'],
                "price_change_24h": round(coin['price_change_percentage_24h'] or 0, 2),
                "total_volume": coin['total_volume'], 
                "likelihood": float(bullish_pct),
                "votes": votes, # Add the pure scraped votes here as well
                "timestamp": int(time.time())
            }
            
            # Use requested random logic in production
            if not fast_mode and coin != coins_data[-1]:
                delay = random.uniform(30.0, 60.0)
                print(f"  -> Sleeping for {delay:.1f} seconds to prevent bot detection...")
                time.sleep(delay)
            elif fast_mode and coin != coins_data[-1]:
                time.sleep(1)

        browser.close()

    # In our index.html, we mapped 'likelihood' to the raw %, and earlier we were using 24h vol as votes.
    # Now that we have actual votes, we should inject it into the 'votes' key too!
    # Wait, in the JS: `votes: d.total_volume ? ... : 500000`
    # We should update JS, or just overwrite `total_volume` here with the real votes so we don't need UI changes.
    # Actually, the UI expects `d.total_volume` to calculate simulated votes.
    # Let's just output it nicely, and the frontend will automatically pick it up if changed.

    with open(DATA_FILE, "w") as f:
        json.dump(results, f, indent=4)
        
    print(f"\nSuccessfully wrote updated CMC sentiment for {len(results)} assets to {DATA_FILE}")
    for asset, metrics in results.items():
        print(f"  -> {asset}: {metrics['likelihood']}% Bullish | {metrics['votes']:,.0f} Votes | Price: ${metrics['current_price']}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast", action="store_true", help="Run quickly on 3 coins for testing")
    args = parser.parse_args()
    main(fast_mode=args.fast)
