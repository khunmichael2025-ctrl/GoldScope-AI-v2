
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path

st.set_page_config(
    page_title="GoldScope AI",
    page_icon="🪙",
    layout="wide",
)

# ---------- HEADER ----------
col1, col2 = st.columns([1, 4], vertical_alignment="center")

with col1:
    if Path("logo.png").exists():
        st.image("logo.png", width=130)

with col2:
    st.title("🪙 GoldScope AI")
    st.caption("XAU/USD · 15-minute candlestick dashboard")

# ---------- TIME ZONES ----------
TIMEZONES = {
    "UTC": "UTC",
    "ICT — Cambodia": "Asia/Phnom_Penh",
    "New York": "America/New_York",
    "London": "Europe/London",
    "Tokyo": "Asia/Tokyo",
    "Singapore": "Asia/Singapore",
    "Hong Kong": "Asia/Hong_Kong",
    "Sydney": "Australia/Sydney",
    "Dubai": "Asia/Dubai",
    "India": "Asia/Kolkata",
    "Paris": "Europe/Paris",
    "Los Angeles": "America/Los_Angeles",
}

selected_zone = st.selectbox(
    " Chart time zone",
    options=list(TIMEZONES.keys()),
    index=1,
)

zone_name = TIMEZONES[selected_zone]

st.caption(
    f"Selected time zone: {selected_zone} · "
    f"UTC offset: {datetime.now(ZoneInfo(zone_name)).strftime('%z')}"
)

# ---------- API KEY ----------
try:
    api_key = st.secrets.get("TWELVE_DATA_API_KEY", "")
except Exception:
    api_key = ""

# ---------- MARKET DATA ----------
@st.cache_data(ttl=30, show_spinner=False)
def fetch_gold(key):
    response = requests.get(
        "https://api.twelvedata.com/time_series",
        params={
            "symbol": "XAU/USD",
            "interval": "15min",
            "outputsize": 100,
            "timezone": "UTC",
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

    df["datetime"] = pd.to_datetime(
        df["datetime"], utc=True, errors="coerce"
    )

    for column in ["open", "high", "low", "close"]:
        df[column] = pd.to_numeric(
            df[column], errors="coerce"
        )

    df = df.dropna(
        subset=["datetime", "open", "high", "low", "close"]
    )
    df = df.sort_values("datetime").reset_index(drop=True)

    if df.empty:
        raise ValueError("No valid candlestick data received.")

    return df


# ---------- DASHBOARD ----------
@st.fragment(run_every="60s")
def gold_dashboard():
    if not api_key:
        st.error(
            "API key missing. Add TWELVE_DATA_API_KEY "
            "to your Streamlit Cloud Secrets."
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
            f"{change:+.2f}",
        )

        c2.metric(
            "Estimated Support",
            f"${df['low'].tail(20).min():,.2f}",
        )

        c3.metric(
            "Estimated Resistance",
            f"${df['high'].tail(20).max():,.2f}",
        )

        # Convert timestamps for the selected time zone
        chart_df = df.copy()
        chart_df["datetime"] = (
            chart_df["datetime"].dt.tz_convert(zone_name)
        )

        # Candlestick chart
        st.subheader(" XAU/USD Candlestick Chart")
        st.caption(
            "Each candle represents 15 minutes. "
            "Chart times use your selected time zone."
        )

        fig = go.Figure(
            data=[
                go.Candlestick(
                    x=chart_df["datetime"],
                    open=chart_df["open"],
                    high=chart_df["high"],
                    low=chart_df["low"],
                    close=chart_df["close"],
                    name="XAU/USD",
                    increasing_line_color="#16a34a",
                    decreasing_line_color="#ef4444",
                )
            ]
        )

        support = float(df["low"].tail(20).min())
        resistance = float(df["high"].tail(20).max())

        fig.add_hline(
            y=support,
            line_dash="dash",
            line_color="#16a34a",
            annotation_text="Estimated Support",
        )

        fig.add_hline(
            y=resistance,
            line_dash="dash",
            line_color="#ef4444",
            annotation_text="Estimated Resistance",
        )

        fig.update_layout(
            template="plotly_dark",
            height=600,
            xaxis_title=f"Time ({selected_zone})",
            yaxis_title="Gold price (USD)",
            xaxis_rangeslider_visible=False,
            margin=dict(l=20, r=20, t=35, b=20),
        )

        fig.update_xaxes(
            tickformat="%d %b %H:%M",
            showgrid=True,
        )

        fig.update_yaxes(
            tickprefix="$",
            showgrid=True,
        )

        st.plotly_chart(fig, use_container_width=True)

        # Recent candle table
        with st.expander("View recent candles"):
            table = chart_df.tail(10).copy()
            table["datetime"] = table["datetime"].dt.strftime(
                "%Y-%m-%d %H:%M %Z"
            )
            table = table.rename(
                columns={
                    "datetime": f"Time ({selected_zone})",
                    "open": "Open",
                    "high": "High",
                    "low": "Low",
                    "close": "Close",
                }
            )
            st.dataframe(
                table[
                    [
                        f"Time ({selected_zone})",
                        "Open", "High", "Low", "Close",
                    ]
                ].iloc[::-1],
                use_container_width=True,
                hide_index=True,
            )

        # Simple observation
        st.subheader("Market Observation")

        recent = df["close"].tail(5)

        if len(recent) >= 5 and recent.is_monotonic_increasing:
            st.info("Recent closing prices are trending upward.")
        elif len(recent) >= 5 and recent.is_monotonic_decreasing:
            st.info("Recent closing prices are trending downward.")
        else:
            st.info(
                "Recent prices are moving unevenly. "
                "This observation does not predict future prices."
            )

        latest_time = df["datetime"].iloc[-1].tz_convert(zone_name)

        st.caption(
            f"Latest candle: {latest_time.strftime('%Y-%m-%d %H:%M %Z')}"
        )
        st.caption(
            "Last checked: "
            + datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
        )
        st.caption(
            "Refresh checks run every 60 seconds. "
            "Actual market-data updates depend on Twelve Data."
        )

    except Exception as error:
        st.error(f"Could not update gold prices: {error}")


gold_dashboard()

st.divider()

st.subheader("About GoldScope AI")
st.write(
    "GoldScope AI displays XAU/USD candlesticks and simple "
    "support and resistance estimates. Levels are calculated "
    "from recent candles and are not guaranteed to hold."
)

st.caption(
    "For informational purposes only. Not financial advice."
)
