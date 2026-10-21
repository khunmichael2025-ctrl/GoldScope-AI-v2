
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timezone

st.set_page_config(
    page_title="GoldScope AI",
    page_icon="🪙",
    layout="wide"
)

# Logo and website header
col1, col2 = st.columns(
    [1, 4],
    vertical_alignment="center"
)

with col1:
    st.image("logo.png", width=150)

with col2:
    st.title("GoldScope AI")
    st.caption("XAU/USD · Smarter Gold Trading · 15m")

# API key stored securely in Streamlit Cloud Secrets
api_key = st.secrets.get("TWELVE_DATA_API_KEY", "")


@st.cache_data(ttl=30, show_spinner=False)
def fetch_gold(key):
    response = requests.get(
        "https://api.twelvedata.com/time_series",
        params={
            "symbol": "XAU/USD",
            "interval": "15min",
            "outputsize": 100,
            "apikey": key,
            "timezone": "UTC",
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

    df["datetime"] = pd.to_datetime(
        df["datetime"], utc=True, errors="coerce"
    )

    for column in ["open", "high", "low", "close"]:
        df[column] = pd.to_numeric(
            df[column], errors="coerce"
        )

    df = (
        df.dropna(
            subset=[
                "datetime", "open", "high",
                "low", "close"
            ]
        )
        .sort_values("datetime")
        .reset_index(drop=True)
    )

    if df.empty:
        raise ValueError("No valid candle data received.")

    return df


@st.fragment(run_every="60s")
def gold_dashboard():

    if not api_key:
        st.error(
            "API key missing. Add TWELVE_DATA_API_KEY "
            "under your Streamlit Cloud Secrets."
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

        # Price cards
        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Gold (XAU/USD)",
            f"${latest:,.2f}",
            f"{change:+.2f} vs previous 15m candle"
        )

        c2.metric(
            "Estimated Support",
            f"${df['low'].min():,.2f}"
        )

        c3.metric(
            "Estimated Resistance",
            f"${df['high'].max():,.2f}"
        )

        # 15-minute candlestick chart
        st.subheader("🕯️ Gold Candlestick Chart")
        st.caption(
            "Timeframe: 15 minutes · Latest 100 candles · UTC"
        )

        fig = go.Figure(
            data=[
                go.Candlestick(
                    x=df["datetime"],
                    open=df["open"],
                    high=df["high"],
                    low=df["low"],
                    close=df["close"],
                    name="XAU/USD",
                    increasing_line_color="#00C087",
                    increasing_fillcolor="#00C087",
                    decreasing_line_color="#FF4D4F",
                    decreasing_fillcolor="#FF4D4F",
                    hovertemplate=(
                        "Time: %{x}<br>"
                        "Open: %{open:.2f}<br>"
                        "High: %{high:.2f}<br>"
                        "Low: %{low:.2f}<br>"
                        "Close: %{close:.2f}"
                        "<extra></extra>"
                    ),
                )
            ]
        )

        fig.update_layout(
            template="plotly_dark",
            height=600,
            xaxis_title="Time (UTC)",
            yaxis_title="Gold price (USD)",
            xaxis_rangeslider_visible=False,
            margin=dict(l=15, r=15, t=25, b=15),
            hovermode="x unified",
        )

        fig.update_xaxes(
            showgrid=True,
            rangeslider_visible=False,
        )

        fig.update_yaxes(showgrid=True)

        st.plotly_chart(
            fig,
            width="stretch",
            key="gold_15m_candlestick",
        )

        # Market observation
        st.subheader("Market Observation")

        if len(df) >= 5:
            recent = df["close"].tail(5)

            if recent.is_monotonic_increasing and (
                recent.iloc[-1] > recent.iloc[0]
            ):
                st.info(
                    "Recent 15m closes are generally rising."
                )

            elif recent.is_monotonic_decreasing and (
                recent.iloc[-1] < recent.iloc[0]
            ):
                st.info(
                    "Recent 15m closes are generally falling."
                )

            else:
                st.info(
                    "Recent 15m closes are moving unevenly."
                )

        else:
            st.info(
                "Not enough candles for a trend observation."
            )

        st.caption(
            "Latest returned candle: "
            + df["datetime"].iloc[-1].strftime(
                "%Y-%m-%d %H:%M UTC"
            )
        )

        st.caption(
            "Last checked: "
            + datetime.now(timezone.utc).strftime(
                "%H:%M:%S UTC"
            )
        )

        st.caption(
            "The dashboard checks for updates every 60 seconds. "
            "The data provider may delay updates. "
            "The latest candle may still be forming."
        )

    except Exception as error:
        st.error(f"Could not update gold prices: {error}")


gold_dashboard()

st.divider()

st.subheader("About GoldScope AI")

st.write(
    "GoldScope AI displays XAU/USD 15-minute candlesticks "
    "and estimated support/resistance based on the returned "
    "history. These levels are not guaranteed, and market "
    "observations cannot predict future prices."
)

st.caption(
    "For informational purposes only. Not financial advice."
)
