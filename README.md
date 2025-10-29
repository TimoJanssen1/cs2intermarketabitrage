# cs2intermarketarbitrage

**Very Basic Strategy:**  
Fill Steam’s highest bids using Buff’s lowest asks, under condition: `(PnL > 0) & (PnL > MinPnL)`  
`PnL = SteamBid * (1 - TC_Steam) - BuffAsk` (TC_Steam = 15%, Buff fees included in BuffAsk)

---

## What is Causing this?
- **Recent market shifts?** — To be tested.  
- **Payment friction:** Buff only accepts **WeChat Pay** and **Alipay**, which limits the buyer base and cross-border capital flows.  
- **Regional sentiment / demand differences:** Buyer demand on Steam (global) may diverge from Buff (China-centric). Sellers constrained by payment rails may prefer Buff, preserving the spread.  
- **Fee offset:** Steam’s higher bids can sometimes offset Steam’s 15% fee; whether net PnL is positive depends on depth and realized execution price.

---

## Risk / Constrains
- **Steam hold time:** Steam may hold items for **1–7 days** after a listed sale — exposure to price moves during this window.  
- **Volatility:** For high-volume items, observed 7-day volatility is typically low, but this must be measured per-item.  
- **Order-book dynamics:** High-volume items often have deep order books. To reduce execution risk, consider selling into bids a bit (lol) below top-of-book rather than assuming top-of-book fills will be possible after Hold time.  
- **China, ToS & API:** Buff has API Access but no docs but seems to be unrealible sometimes. This might be against ToS? Trade Ban while holding invetory of worth will destroy any positive PnL made. Weixin, Alipay is required.

**Notes:** Long-term risk modelling is valuable, but for initial deployment, using a conservative bid level (further down the Steam book) can materially reduce slippage and execution failure.

---

## Execution of Strategy (practical outline)
Execution is **non-trivial**. Example steps:

1. **Find items where a c

---

## Data
**BUFF**
- Best ask: GET https://buff.163.com/api/market/goods/sell_order?game=csgo&goods_id=<id>&page_num=1&sort_by=default
- Best bid: GET https://buff.163.com/api/market/goods/buy_order?game=csgo&goods_id=<id>&page_num=1
- Name → goods_id search (works with cookie): GET https://buff.163.com/api/market/goods?game=csgo&search=<name>&page_num=1&sort_by=sell_num.desc
- Headers: include full “Cookie” header string from browser session; also User-Agent, Accept=application/json, Referer=https://buff.163.com/market/?game=csgo, X-Requested-With=XMLHttpRequest.
**Steam:**
EUR snapshot: GET https://steamcommunity.com/market/priceoverview/?appid=730&currency=3&market_hash_name=<name>
