import sqlite3
import pandas as pd
import yfinance as yf
from config import DB_PATH

# Caches
_overview_cache = {}
_news_cache = {}
_gainers_losers_cache = {}

# Tool 1: Price Performance
def get_price_performance(tickers: list, period: str = "1y") -> dict:
    results = {}
    for ticker in tickers:
        try:
            data = yf.download(ticker, period=period, progress=False, auto_adjust=True)
            if data.empty:
                results[ticker] = {"error": "No data — possibly delisted"}
                continue
            start = float(data["Close"].iloc[0].item())
            end = float(data["Close"].iloc[-1].item())
            results[ticker] = {
                "start_price": round(start, 2),
                "end_price": round(end, 2),
                "pct_change": round((end - start) / start * 100, 2),
                "period": period,
            }
        except Exception as e:
            results[ticker] = {"error": str(e)}
    return results

# Tool 2: Market Status
def get_market_status() -> dict:
    import datetime, pytz
    now_et = datetime.datetime.now(pytz.timezone('US/Eastern'))
    weekday = now_et.weekday()
    h, m = now_et.hour, now_et.minute
    is_open = weekday < 5 and ((h == 9 and m >= 30) or (10 <= h < 16))
    status = "open" if is_open else "closed"
    return {
        "endpoint": "Market Status",
        "markets": [{
            "market_type": "Equity",
            "region": "United States",
            "primary_exchanges": "NYSE, NASDAQ",
            "current_status": status,
            "local_open": "09:30",
            "local_close": "16:00",
            "current_time_et": now_et.strftime("%Y-%m-%d %H:%M:%S ET"),
            "notes": "Weekdays only, excluding US market holidays."
        }]
    }

# Tool 3: Top Gainers/Losers
def get_top_gainers_losers() -> dict:
    if 'result' in _gainers_losers_cache:
        return _gainers_losers_cache['result']
    try:
        tickers_sample = ["AAPL","MSFT","NVDA","GOOGL","AMZN","META","TSLA","JPM","V","JNJ",
                          "XOM","CVX","PFE","BAC","WMT","HD","AVGO","LLY","MRK","COST"]
        data = yf.download(tickers_sample, period="1d", progress=False, auto_adjust=True)
        if data.empty:
            return {"error": "No market data available"}
        changes = {}
        for t in tickers_sample:
            try:
                o = float(data["Open"][t].iloc[-1])
                c = float(data["Close"][t].iloc[-1])
                if o > 0:
                    changes[t] = round((c - o) / o * 100, 2)
            except:
                continue
        sorted_tickers = sorted(changes.items(), key=lambda x: x[1], reverse=True)
        result = {
            "top_gainers": [{"ticker": t, "change_pct": p} for t, p in sorted_tickers[:5]],
            "top_losers": [{"ticker": t, "change_pct": p} for t, p in sorted_tickers[-5:]],
            "most_active": [{"ticker": t, "change_pct": p} for t, p in sorted_tickers[:10]],
        }
        _gainers_losers_cache['result'] = result
        return result
    except Exception as e:
        return {"error": str(e)}

# Tool 4: News Sentiment
def _simple_sentiment(title: str, summary: str) -> tuple:
    text = (title + " " + summary).lower()
    pos = ["beat", "surge", "rally", "gain", "upgrade", "buy", "bullish",
           "record", "strong", "growth", "outperform", "raise", "profit", "soar"]
    neg = ["miss", "drop", "fall", "cut", "downgrade", "sell", "bearish",
           "weak", "loss", "decline", "crash", "slash", "fear", "layoff", "warn"]
    p = sum(1 for w in pos if w in text)
    n = sum(1 for w in neg if w in text)
    if p > n:
        return "Bullish", round(min(0.5 + p * 0.1, 1.0), 3)
    elif n > p:
        return "Bearish", round(max(-0.5 - n * 0.1, -1.0), 3)
    else:
        return "Neutral", 0.0

def get_news_sentiment(ticker: str, limit: int = 5) -> dict:
    cache_key = f"{ticker}_{limit}"
    if cache_key in _news_cache:
        return _news_cache[cache_key]
    try:
        raw = yf.Ticker(ticker).news or []
        articles = []
        for n in raw[:limit]:
            c = n.get("content", {})
            title = c.get("title", "") or ""
            summary = c.get("summary", "") or ""
            source = c.get("provider", {}).get("displayName", "") or ""
            label, score = _simple_sentiment(title, summary)
            articles.append({"title": title, "source": source, "sentiment": label, "score": score})
        result = {"ticker": ticker, "articles": articles}
        _news_cache[cache_key] = result
        return result
    except Exception as e:
        return {"ticker": ticker, "articles": [], "error": str(e)}

# Tool 5: Query Local DB
def query_local_db(sql: str) -> dict:
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(sql, conn)
        conn.close()
        return {"columns": list(df.columns), "rows": df.to_dict(orient="records")}
    except Exception as e:
        return {"error": str(e)}

# Tool 6: Company Overview
def get_company_overview(ticker: str) -> dict:
    if ticker in _overview_cache:
        return _overview_cache[ticker]
    try:
        info = yf.Ticker(ticker).info
        if not info or not info.get('shortName'):
            result = {'error': f'No overview data for {ticker}'}
        else:
            pe = info.get('trailingPE') or info.get('forwardPE') or ''
            result = {
                'ticker': ticker,
                'name': info.get('shortName', ''),
                'sector': info.get('sector', ''),
                'pe_ratio': str(round(pe, 2)) if isinstance(pe, (int, float)) else str(pe),
                'eps': str(info.get('trailingEps', '')),
                'market_cap': str(info.get('marketCap', '')),
                '52w_high': str(info.get('fiftyTwoWeekHigh', '')),
                '52w_low': str(info.get('fiftyTwoWeekLow', '')),
            }
        _overview_cache[ticker] = result
        return result
    except Exception as e:
        return {'error': str(e)}

# Tool 7: Get Tickers by Sector
def get_tickers_by_sector(sector: str) -> dict:
    try:
        conn = sqlite3.connect(DB_PATH)
        query = "SELECT ticker, company, industry FROM stocks WHERE LOWER(sector) = LOWER(?)"
        df = pd.read_sql_query(query, conn, params=(sector,))
        if df.empty:
            query = "SELECT ticker, company, industry FROM stocks WHERE LOWER(sector) LIKE LOWER(?)"
            df = pd.read_sql_query(query, conn, params=(f'%{sector}%',))
        if df.empty:
            query = "SELECT ticker, company, industry FROM stocks WHERE LOWER(industry) LIKE LOWER(?)"
            df = pd.read_sql_query(query, conn, params=(f'%{sector}%',))
        conn.close()
        return {'sector': sector, 'stocks': df.to_dict(orient='records')}
    except Exception as e:
        return {'error': str(e)}

# Tool dispatch map
ALL_TOOL_FUNCTIONS = {
    "get_tickers_by_sector": get_tickers_by_sector,
    "get_price_performance": get_price_performance,
    "get_company_overview": get_company_overview,
    "get_market_status": get_market_status,
    "get_top_gainers_losers": get_top_gainers_losers,
    "get_news_sentiment": get_news_sentiment,
    "query_local_db": query_local_db,
}
