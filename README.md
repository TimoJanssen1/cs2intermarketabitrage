# Current Phase: Data Collection and Analysis
# CS2 Spread Analysis

One-way strategy: buy on Buff, sell on Steam. Currently Phase: Collecting price data to quantify the spread after accounting for Steam's 15% fee and holding period risk.

## Background
Been doing this manually—buying items on Buff (Chinese CS:GO marketplace) and selling on Steam. Noticed consistent spreads on certain items. Using both platforms regularly, so figured I'd try to automate the data collection and analysis.

The spread exists because:
- Buff is China-focused, requires WeChat/Alipay (limits buyer base)
- Recent macro (aka valve update lol): Valve introduced Trade-Up to knives -> market cap crashed. China treats skins as investment, got spooked. Steam doesn't allow direct cashouts (unlike Buff) and western sites dont cash out in cny, creating ask-only makret on Buff. Testing this theory in notebook. Essentially, Chinese skin collectors might be stuck trading with other Chinese collectors, creating a different dynamic than the global market. (But why not sell on Steam for keys and keys on Chinese sites for cash? Too much effort, too many fees? idk?). My edge is essentially being a Euro collector with access to the Chinese market?
- Steam is global, higher demand for certain items
- Payment friction creates arbitrage opportunities
- Even after Steam's 15% fee, some items still show positive spreads

Main challenges:
- Buff API is undocumented and requires authentication
- Execution/automated payment via WeChat is non-trivial (Buff uses WeChat Pay/Alipay)
- Buff wallet balance management
- Steam's 1-7 day holding period adds price risk

This is exploratory work. Need to validate assumptions about execution, fees, and holding period risk with actual data. Also testing how unstable/bad Buff data collection is.

## The Opportunity

If we can consistently identify items where `Steam_bid * 0.85 - Buff_ask > threshold`, there's profit potential. The key is:
1. Finding items with sufficient spread to cover fees and risk
2. Managing holding period volatility (Steam holds items 1-7 days)
3. Ensuring execution probability (orders actually fill)
5. Scaling while managing Buff wallet balance and WeChat payment flow

Next steps after data collection and analysis:
- Build execution system (Buff purchase automation)
- Integrate WeChat Pay/Alipay API (or manual approval flow)
- Implement risk management (position sizing, stop losses)
- Monitor and optimize based on actual fill rates

Best Case:
- Buff has wallet & trade execution api access -> fully automated system
Worst Case:
- Buff isnt good for anything but data collection -> semi-manual proccess: Discord Bot sends manual steps to user. User confirms fill or no fill. Rest is handled by system (still can implement)

## Setup

```bash
pip install -r requirements.txt
python -m migrations.init_db
```

Set `BUFF_COOKIE` in `.env` for Buff auth. Get cookie from browser dev tools when logged into buff.163.com.

## Usage

```bash
python scripts/add_item.py "AK-47 | Redline (Field-Tested)"
python -m src.puller.daemon --once
python -m src.puller.daemon --interval 300
```

## Data Schema

SQLite snapshots:
- `steam_snapshots`: Price overview (median, lowest, volume)
- `buff_snapshots`: Order book (best ask/bid, depth, order counts)
- `fetch_logs`: Request metadata

## Analysis

After 7+ days of data, run `notebooks/market_analysis.ipynb` to:
- Explore spreads and volatility
- Test ask-only pressure theory (Steam cashout limitation creates more asks than bids on Buff)
- Identify opportunities

## Notes

- Steam: Public API, ~10 req/min
- Buff: Auth required, ~20 req/min, undocumented af. wtf maybe see https://github.com/markzhdan/buff163-unofficial-api at somepoint 
- Rate limits auto-enforced
- Data quality depends on API stability
- I dont want to get banned on Wechat.
-  
