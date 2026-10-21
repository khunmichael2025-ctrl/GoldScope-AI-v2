import os
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from streamlit_autorefresh import st_autorefresh
import feedparser
from openai import OpenAI

APP_TITLE = "GoldScope AI"
PRICE_URL = "https://api.goldprice.dev/v1/prices"
BARS_URL = "https://api.goldprice.dev/v1/bars"
NEWS_URL = "https://news.google.com/rss/search"

st.set_page_config(page_title=APP_TITLE, page_icon="🟡", layout="wide")

# Re-run the app every 60 seconds to request fresh market data.
st_autorefresh(interval=60 * 1000, key="gold_scope_auto_refresh")

st.markdown("""
<style>
.block-container {max-width: 1180px; padding-top: 1.6rem;}
.small-muted {color:#8792a2; font-size:0.88rem;}
</style>
""", unsafe_allow_html=True)

st.title("🟡 GoldScope AI")
st.caption("XAU/USD daily market context • News-aware chat • No trading execution")

with st.sidebar:
    st.subheader("Settings")
    st.write("Market: **XAU/USD spot gold**")
    model_name = st.text_input(
        "AI model name",
        value=os.getenv("OPENAI_MODEL", "gpt-6-astra"),
        help="Uses the model name enabled for your API account."
    )
    st.caption("This starter app uses a public price endpoint that may be delayed.")
    st.divider()
    st.markdown("**Safety**")
    st.caption("Educational market analysis only. No buy/sell orders are sent.")

def get_spot():
    r = requests.get(
        PRICE_URL,
        params={"symbol": "XAU-USD-SPOT"},
        timeout=12,
        headers={"User-Agent": "GoldScopeAI/1.0"}
    )
    r.raise_for_status()
    payload = r.json()
    rows = payload.get("symbols", [])
    if not rows:
        raise ValueError("The price service returned no XAU/USD quote.")
    return rows[0]

def get_daily_bars(days=30):
    end = datetime.now(timezone.utc)
    earliest_allowed = datetime(2026, 9, 21, tzinfo=timezone.utc)
    start = max(end - timedelta(days=days + 12), earliest_allowed)
    params = {
        "symbol": "XAU-USD-SPOT",
        "interval": "1d",
        "from": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "to": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "limit": 100,
    }
    r = requests.get(BARS_URL, params=params, timeout=15,
                     headers={"User-Agent": "GoldScopeAI/1.0"})
    r.raise_for_status()
    rows = r.json().get("bars", [])
    df = pd.DataFrame(rows)
    if df.empty or "close" not in df:
        return pd.DataFrame()
    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["date"] = pd.to_datetime(df["bar_start"], utc=True, errors="coerce")
    df = df.dropna(subset=["date", "close"]).sort_values("date")
    return df.tail(days).reset_index(drop=True)

def get_news():
    query = 'gold XAU USD Federal Reserve inflation yields'
    url = NEWS_URL
    response = requests.get(
        url,
        params={"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"},
        timeout=12,
        headers={"User-Agent": "Mozilla/5.0 GoldScopeAI/1.0"}
    )
    response.raise_for_status()
    feed = feedparser.parse(response.text)
    items = []
    for entry in feed.entries[:8]:
        published = entry.get("published", "")
        items.append({
            "title": entry.get("title", "Untitled"),
            "link": entry.get("link", ""),
            "published": published,
            "source": entry.get("source", {}).get("title", "Google News RSS")
        })
    return items

def calc_context(spot, bars, news):
    price = float(spot["price"])
    timestamp = spot.get("computed_at", "not provided")
    stale = spot.get("is_stale", None)
    result = {
        "price": price,
        "timestamp": timestamp,
        "stale": stale,
        "trend": "Not enough daily bars",
        "change_pct": None,
        "sma5": None,
        "sma20": None,
        "support_ref": None,
        "resistance_ref": None,
        "rsi14": None,
        "notes": [],
    }
    if not bars.empty:
        bars = bars.copy()
        bars["sma5"] = bars["close"].rolling(5).mean()
        bars["sma20"] = bars["close"].rolling(20).mean()
        delta = bars["close"].diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, float("nan"))
        bars["rsi14"] = 100 - (100 / (1 + rs))
        last = bars.iloc[-1]
        prev = bars.iloc[-2] if len(bars) > 1 else last
        result["sma5"] = float(last["sma5"]) if pd.notna(last["sma5"]) else None
        result["sma20"] = float(last["sma20"]) if pd.notna(last["sma20"]) else None
        result["rsi14"] = float(last["rsi14"]) if pd.notna(last["rsi14"]) else None
        result["change_pct"] = (
            (float(last["close"]) / float(prev["close"]) - 1) * 100
            if float(prev["close"]) != 0 else None
        )
        result["support_ref"] = float(bars.tail(10)["low"].min()) if bars["low"].notna().any() else None
        result["resistance_ref"] = float(bars.tail(10)["high"].max()) if bars["high"].notna().any() else None
        if result["sma5"] is not None and result["sma20"] is not None:
            if float(last["close"]) > result["sma5"] > result["sma20"]:
                result["trend"] = "Bullish daily structure"
            elif float(last["close"]) < result["sma5"] < result["sma20"]:
                result["trend"] = "Bearish daily structure"
            else:
                result["trend"] = "Mixed / sideways daily structure"
        result["notes"].append(
            "Daily bars are used for broad context, not intraday entries."
        )
    result["news"] = news
    return result

def fmt(value, digits=2):
    return "N/A" if value is None else f"{value:,.{digits}f}"

try:
    spot = get_spot()
    news = get_news()
    bars = get_daily_bars()
    context = calc_context(spot, bars, news)
    data_error = None
except Exception as e:
    spot, news, bars, context = None, [], pd.DataFrame(), None
    data_error = str(e)

if data_error:
    st.error("Could not load market data right now. Check your internet connection and try Refresh.")
    st.caption(f"Technical detail: {data_error}")
    st.stop()

price_col, change_col, trend_col, rsi_col = st.columns(4)
with price_col:
    st.metric("XAU/USD spot", f"${context['price']:,.2f}")
with change_col:
    ch = context["change_pct"]
    st.metric("Latest daily close change", "N/A" if ch is None else f"{ch:+.2f}%")
with trend_col:
    st.metric("Daily structure", context["trend"])
with rsi_col:
    st.metric("RSI (14)", fmt(context["rsi14"]))

st.caption(
    f"Quote timestamp: {context['timestamp']} • "
    + ("Feed marks quote stale" if context["stale"] is True else
       "Staleness not reported" if context["stale"] is None else "Feed does not mark quote stale")
    + " • Anonymous gold quotes may be delayed about 15 minutes."
)

left, right = st.columns([1.5, 1])
with left:
    st.subheader("Daily price history")
    if not bars.empty:
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=bars["date"], open=bars["open"], high=bars["high"],
            low=bars["low"], close=bars["close"], name="Daily gold"
        ))
        fig.update_layout(
            height=390, margin=dict(l=10, r=10, t=20, b=10),
            xaxis_rangeslider_visible=False,
            template="plotly_dark",
            legend=dict(orientation="h")
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Daily candle history isn't available from the data provider right now.")

    st.subheader("Transparent indicator notes")
    st.write(f"- **Trend rule:** {context['trend']} (based on 5-day and 20-day simple moving averages when available).")
    st.write(f"- **Recent support reference:** ${fmt(context['support_ref'])}")
    st.write(f"- **Recent resistance reference:** ${fmt(context['resistance_ref'])}")
    rsi = context["rsi14"]
    if rsi is not None:
        if rsi >= 70:
            rsi_note = "RSI is high; that can reflect strong momentum or an extended move, not an automatic sell."
        elif rsi <= 30:
            rsi_note = "RSI is low; that can reflect weak momentum or an extended move, not an automatic buy."
        else:
            rsi_note = "RSI is between 30 and 70; it does not give a strong overbought/oversold reading."
        st.write(f"- **RSI interpretation:** {rsi_note}")
    st.caption("Support/resistance are simple recent daily extremes, not guaranteed turning points.")

with right:
    st.subheader("Recent gold-related headlines")
    if news:
        for item in news:
            st.markdown(f"**[{item['title']}]({item['link']})**")
            st.caption(item["published"] or item["source"])
    else:
        st.info("No headlines returned by the RSS feed.")

    st.subheader("Today's context")
    if context["trend"] == "Bullish daily structure":
        st.info("The simple moving-average rule shows a bullish daily structure. This is context, not a trade signal.")
    elif context["trend"] == "Bearish daily structure":
        st.warning("The simple moving-average rule shows a bearish daily structure. This is context, not a trade signal.")
    else:
        st.info("The simple moving-average rule is mixed or incomplete. Waiting for clearer evidence may be more informative.")

st.divider()
st.subheader("Chat with GoldScope AI")
st.caption("Ask about the indicators or headlines. It explains scenarios, not guaranteed signals or personalized trade instructions.")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

user_question = st.chat_input("Ask: What does today's gold trend mean?")
if user_question:
    st.session_state.chat_history.append({"role": "user", "content": user_question})
    with st.chat_message("user"):
        st.markdown(user_question)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        answer = (
            "The market dashboard is running, but chat needs an OpenAI API key. "
            "Ask a parent/guardian to help set up API access and billing, then set "
            "OPENAI_API_KEY in Windows. Never paste your API key into this chat or share it."
        )
        with st.chat_message("assistant"):
            st.markdown(answer)
        st.session_state.chat_history.append({"role": "assistant", "content": answer})
    else:
        headlines = "\n".join(
            f"- {n['title']} ({n['published']}) {n['link']}" for n in news[:8]
        ) or "No headlines available."
        market_context = f"""
Current XAU/USD reference quote:
- Price: ${context['price']:.2f} per troy ounce
- Timestamp: {context['timestamp']}
- Feed stale flag: {context['stale']}
- Quote may be delayed around 15 minutes.
- Daily structure: {context['trend']}
- Latest daily close change: {fmt(context['change_pct'])}%
- SMA5: {fmt(context['sma5'])}
- SMA20: {fmt(context['sma20'])}
- RSI14: {fmt(context['rsi14'])}
- Recent 10-bar support reference: {fmt(context['support_ref'])}
- Recent 10-bar resistance reference: {fmt(context['resistance_ref'])}

Recent headlines (treat headlines as unverified summaries; don't infer facts not shown):
{headlines}
"""
        system = """
You are GoldScope AI, a cautious educational gold-market explainer.
Explain market context in simple English. Use only the provided data for current claims.
Never claim a setup is certain, never invent a live quote or economic event, and clearly
distinguish observed data from interpretation. If asked for a buy/sell signal, explain
the current evidence and alternative scenarios without giving a personalized command,
exact entry, stop-loss, or take-profit. State when data is stale, delayed, incomplete,
or daily-only. Do not execute trades, and do not ask for broker credentials.
"""
        try:
            client = OpenAI(api_key=api_key)
            messages = [{"role": "system", "content": system + "\n\nMARKET DATA:\n" + market_context}]
            for old in st.session_state.chat_history[-8:]:
                messages.append({"role": old["role"], "content": old["content"]})
            response = client.responses.create(
                model=model_name,
                input=messages
            )
            answer = response.output_text.strip()
        except Exception as e:
            answer = (
                "The AI request failed. Check your API key, model access, and billing. "
                "No trades were placed. Error details: " + str(e)
            )
        with st.chat_message("assistant"):
            st.markdown(answer)
        st.session_state.chat_history.append({"role": "assistant", "content": answer})

st.caption("GoldScope AI is an educational prototype, not financial advice. Spot data may be delayed, headlines can be incomplete, and technical indicators can be wrong. No trades are placed.")
