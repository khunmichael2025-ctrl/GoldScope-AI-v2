
import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timezone

st.set_page_config(
    page_title="GoldScope AI",
    page_icon="🟡",
    layout="wide"
)

st.title("🟡 GoldScope AI")
st.caption("XAU/USD · Gold market dashboard")

# Read API key securely from Streamlit Secrets
api_key = st.secrets.get("TWELVE_DATA_API_KEY", "")

@st.cache_data(ttl=5, show_spinner=False)
def fetch_gold(key):
    response = requests.get(
        "https://api.twelvedata.com/time_series",
        params={
            "symbol": "XAU/USD",
            "interval": "1min",
            "outputsize": 100,
            "apikey": key,
        },
        timeout=20,
    )
    response.raise_for_status()
    result = response.json()

    if "values" not in result:
        raise ValueError(
            result.get("message", "Gold data is unavailable.")
        )

    df = pd.DataFrame(result["values"])
    df["datetime"] = pd.to_datetime(df["datetime"])
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna(subset=["close"])
    df = df.sort_values("datetime").reset_index(drop=True)

    if df.empty:
        raise ValueError("No valid price data received.")

    return df

@st.fragment(run_every="10s")
def gold_dashboard():
    if not api_key:
        st.error(
            "API key missing. Add TWELVE_DATA_API_KEY "
            "under your app's Streamlit Cloud Secrets."
        )
        return

    try:
        df = fetch_gold(api_key)
        latest = float(df["close"].iloc[-1])
        previous = (
            float(df["close"].iloc[-2])
            if len(df) > 1 else latest
        )

        change = latest - previous

        c1, c2, c3 = st.columns(3)
        c1.metric("Gold (XAU/USD)", f"${latest:,.2f}",
                  f"{change:+.2f}")
        c2.metric("Estimated Support", f"${df['close'].min():,.2f}")
        c3.metric("Estimated Resistance", f"${df['close'].max():,.2f}")

        st.subheader("Gold Price Chart")

        chart = df.set_index("datetime")[["close"]].copy()
        chart["Support"] = df["close"].min()
        chart["Resistance"] = df["close"].max()
        st.line_chart(chart)

        st.subheader("Market Observation")

        if len(df) >= 5:
            recent = df["close"].tail(5)
            if recent.is_monotonic_increasing:
                st.info("Recent prices are trending upward.")
            elif recent.is_monotonic_decreasing:
                st.info("Recent prices are trending downward.")
            else:
                st.info("Recent prices are moving unevenly.")
        else:
            st.info("Not enough price history for a trend observation.")

        st.caption(
            "Latest candle: " + str(df["datetime"].iloc[-1])
        )
        st.caption(
            "Last checked: "
            + datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
        )
        st.caption(
            "Refresh checks run every 10 seconds. "
            "Provider updates may be delayed."
        )

    except Exception as error:
        st.error(f"Could not update gold prices: {error}")

gold_dashboard()

st.divider()
st.subheader("About this dashboard")
st.write(
    "Support and resistance are estimated from the lowest and "
    "highest closing prices in the returned data window. "
    "They are not confirmed trading levels. Trend observations "
    "are descriptive and do not guarantee future price movements."
)
