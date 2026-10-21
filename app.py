
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
st.caption("Gold market dashboard · Automatic data refresh")

st.sidebar.header("Settings")
api_key = st.sidebar.text_input(
    "Twelve Data API key",
    type="password",
    help="Enter your API key here. Do not share it publicly."
)

@st.cache_data(ttl=5, show_spinner=False)
def get_gold_data(key):
    response = requests.get(
        "https://api.twelvedata.com/time_series",
        params={
            "symbol": "XAU/USD",
            "interval": "1min",
            "outputsize": 30,
            "apikey": key,
        },
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()

    if "values" not in data:
        raise ValueError(
            data.get("message", "No gold-price data returned.")
        )

    df = pd.DataFrame(data["values"])
    df["datetime"] = pd.to_datetime(df["datetime"])
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna(subset=["close"]).sort_values("datetime")

    if df.empty:
        raise ValueError("The provider returned no valid prices.")

    return df

@st.fragment(run_every="10s")
def live_gold_panel():
    if not api_key:
        st.info(
            "Enter your Twelve Data API key in the sidebar "
            "to load gold prices."
        )
        return

    try:
        df = get_gold_data(api_key)
        latest = df.iloc[-1]
        previous = df.iloc[-2] if len(df) > 1 else latest

        price = float(latest["close"])
        change = price - float(previous["close"])

        col1, col2, col3 = st.columns(3)
        col1.metric("Latest XAU/USD", f"${price:,.2f}",
                    f"{change:+.2f}")
        col2.metric("Data points", len(df))
        col3.metric(
            "Latest data timestamp",
            str(latest["datetime"])
        )

        st.line_chart(
            df.set_index("datetime")["close"],
            y_label="Price (provider units)",
        )

        if len(df) >= 5:
            recent = df["close"].tail(5)
            if recent.is_monotonic_increasing:
                st.info("Short-term observation: recent prices are rising.")
            elif recent.is_monotonic_decreasing:
                st.info("Short-term observation: recent prices are falling.")
            else:
                st.info("Short-term observation: mixed price movement.")

        st.caption(
            "Last checked: " +
            datetime.now(timezone.utc).strftime("%H:%M:%S UTC") +
            " · Provider updates may be delayed."
        )

    except Exception as error:
        st.error(f"Unable to update gold data: {error}")

live_gold_panel()

st.divider()
st.subheader("Market notes")
st.write(
    "This dashboard displays provider data and simple observations. "
    "It does not guarantee future prices or provide guaranteed signals."
)
