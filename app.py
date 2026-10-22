
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
    "Chart time zone",
    options=list(TIMEZONES.keys()),
    index=1,
)

zone_name = TIMEZONES[selected_zone]

st.caption(
    f"Selected time zone: {selected_zone} · "
    f"UTC offset: "
    f"{datetime.now(ZoneInfo(zone_name)).strftime('%z')}"
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


# ---------- SIGNAL ENGINE ----------
def calculate_gold_signal(df):
    data = df.copy()

    # Only use completed 15-minute candles
    now = pd.Timestamp.now(tz="UTC")

    candle_end = data["datetime"] + pd.Timedelta(minutes=15)

    data = data.loc[candle_end <= now].copy()
    data = data.sort_values("datetime").reset_index(drop=True)

    if len(data) < 60:
        return None

    # EMA indicators
    data["ema20"] = data["close"].ewm(
        span=20, adjust=False
    ).mean()

    data["ema50"] = data["close"].ewm(
        span=50, adjust=False
    ).mean()

    # RSI 14 using Wilder-style exponential smoothing
    delta = data["close"].diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1 / 14,
        min_periods=14,
        adjust=False,
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / 14,
        min_periods=14,
        adjust=False,
    ).mean()

    rs = avg_gain / avg_loss

    data["rsi"] = 100 - (100 / (1 + rs))

    # Previous completed candle
    prev = data.iloc[-2]
    last = data.iloc[-1]

    if pd.isna(last["rsi"]):
        return None

    bullish = last["close"] > last["open"]
    bearish = last["close"] < last["open"]

    # BUY setup
    buy = (
        last["ema20"] > last["ema50"]
        and last["close"] > last["ema20"]
        and bullish
        and 50 < last["rsi"] < 68
        and prev["close"] <= prev["ema20"]
    )

    # SELL setup
    sell = (
        last["ema20"] < last["ema50"]
        and last["close"] < last["ema20"]
        and bearish
        and 32 < last["rsi"] < 50
        and prev["close"] >= prev["ema20"]
    )

    if buy:
        signal = "BUY"
        reason = (
            "Bullish trend, pullback and candle confirmation. "
            "RSI supports momentum."
        )

    elif sell:
        signal = "SELL"
        reason = (
            "Bearish trend, pullback and candle confirmation. "
            "RSI supports momentum."
        )

    else:
        signal = "WAIT"
        reason = "No confirmed setup under these rules."

    return {
        "signal": signal,
        "reason": reason,
        "price": float(last["close"]),
        "rsi": float(last["rsi"]),
        "ema20": float(last["ema20"]),
        "ema50": float(last["ema50"]),
        "time": last["datetime"],
    }


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

        # ---------- PRICE CARDS ----------
        latest = float(df["close"].iloc[-1])

        previous = (
            float(df["close"].iloc[-2])
            if len(df) > 1 else latest
        )

        change = latest - previous

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Gold (XAU/USD)",
            f"${latest:,.2f}",
            f"{change:+.2f}",
        )

        support = float(df["low"].tail(20).min())
        resistance = float(df["high"].tail(20).max())

        c2.metric("Estimated Support", f"${support:,.2f}")
        c3.metric("Estimated Resistance", f"${resistance:,.2f}")

        # ---------- SIGNAL ----------
        st.divider()
        st.subheader("🤖 GoldScope AI Signal")

        result = calculate_gold_signal(df)

        if result is None:
            st.warning(
                "Not enough completed candles to calculate "
                "a reliable indicator reading."
            )

        else:
            signal = result["signal"]

            if signal == "BUY":
                st.success("🟢 BUY SETUP DETECTED")

            elif signal == "SELL":
                st.error("🔴 SELL SETUP DETECTED")

            else:
                st.info("⏳ WAIT — No confirmed setup")

            st.write(result["reason"])

            s1, s2, s3 = st.columns(3)

            s1.metric("Signal candle close", f'${result["price"]:,.2f}')
            s2.metric("RSI (14)", f'{result["rsi"]:.2f}')
            s3.metric("EMA 20", f'${result["ema20"]:,.2f}')

            st.caption(
                f'EMA 50: ${result["ema50"]:,.2f}'
            )

            signal_time = result["time"]

            display_signal_time = signal_time.tz_convert(zone_name)

            st.caption(
                "Signal candle: "
                + display_signal_time.strftime(
                    "%Y-%m-%d %H:%M %Z"
                )
            )

            # ---------- NEW SIGNAL NOTIFICATION ----------
            # Once per signal direction per candle per session.
            # Streamlit toast is an in-app notification only.
            if "gold_alerts_seen" not in st.session_state:
                st.session_state.gold_alerts_seen = set()

            if signal in ("BUY", "SELL"):
                alert_id = (
                    f"{signal}_{signal_time.isoformat()}"
                )

                if alert_id not in st.session_state.gold_alerts_seen:

                    st.toast(
                        f"GoldScope AI: {signal} setup detected!",
                        icon="🔔",
                    )

                    st.session_state.gold_alerts_seen.add(alert_id)

        st.caption(
            "Signal rules are experimental. "
            "Not verified at 60% accuracy."
        )

        st.caption(
            "BUY/SELL labels are educational setups, "
            "not instructions to trade."
        )

        # ---------- CHART TIME ZONE ----------
        chart_df = df.copy()

        chart_df["datetime"] = (
            chart_df["datetime"].dt.tz_convert(zone_name)
        )

        # ---------- CANDLESTICK CHART ----------
        st.subheader("XAU/USD Candlestick Chart")

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

        st.plotly_chart(
            fig,
            use_container_width=True,
        )

        # ---------- RECENT CANDLES ----------
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
                        "Open",
                        "High",
                        "Low",
                        "Close",
                    ]
                ].iloc[::-1],
                use_container_width=True,
                hide_index=True,
            )

        # ---------- MARKET OBSERVATION ----------
        st.subheader("Market Observation")

        recent = df["close"].tail(5)

        if (
            len(recent) >= 5
            and recent.is_monotonic_increasing
        ):
            st.info(
                "Recent closing prices are trending upward."
            )

        elif (
            len(recent) >= 5
            and recent.is_monotonic_decreasing
        ):
            st.info(
                "Recent closing prices are trending downward."
            )

        else:
            st.info(
                "Recent prices are moving unevenly. "
                "This observation does not predict future prices."
            )

        # ---------- UPDATE STATUS ----------
        latest_time = df["datetime"].iloc[-1].tz_convert(zone_name)

        st.caption(
            "Latest candle received: "
            + latest_time.strftime("%Y-%m-%d %H:%M %Z")
        )

        st.caption(
            "Last checked: "
            + datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
        )

        st.caption(
            "Refresh checks run every 60 seconds. "
            "Actual updates depend on Twelve Data."
        )

    except Exception as error:
        st.error(f"Could not update gold prices: {error}")


gold_dashboard()

# ---------- ABOUT ----------
st.divider()

st.subheader("About GoldScope AI")

st.write(
    "GoldScope AI displays XAU/USD candlesticks, "
    "experimental indicator setups, and estimated "
    "support and resistance. Levels are not guaranteed "
    "to hold. Signals may be wrong."
)

st.caption(
    "For educational purposes only. "
    "Not financial advice. No automatic trading."
)
