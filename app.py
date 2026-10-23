import streamlit as st
import streamlit.components.v1 as components
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
import base64

st.set_page_config(
    page_title="GoldScope AI",
    page_icon="🪙",
    layout="wide",
)

# ---------- SESSION STATE ----------
if "gold_started" not in st.session_state:
    st.session_state.gold_started = False

if "gold_alerts_seen" not in st.session_state:
    st.session_state.gold_alerts_seen = set()


# ---------- STARTUP SCREEN ----------
def show_startup_screen():
    st.markdown(
        """
        <style>
        .stApp {
            background: #000000;
        }

        [data-testid="stHeader"] {
            background: transparent;
        }

        .startup-title {
            text-align: center;
            color: #f5d991;
            font-size: clamp(28px, 5vw, 44px);
            font-weight: 800;
            letter-spacing: 2px;
            margin-top: 22px;
            margin-bottom: 8px;
        }

        .startup-subtitle {
            text-align: center;
            color: #a9b9cd;
            font-size: 12px;
            letter-spacing: 3px;
            margin-bottom: 20px;
        }

        div.stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #f5d991, #b88632);
            color: #10131b;
            border: none;
            border-radius: 12px;
            min-height: 52px;
            font-size: 17px;
            font-weight: 750;
        }

        div.stButton > button[kind="primary"]:hover {
            background: #ffe7a1;
            color: #10131b;
            border: none;
        }

        .startup-footer {
            text-align: center;
            color: #77869b;
            font-size: 11px;
            margin-top: 14px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Add startup_hands.png beside this Python file.
    if Path("startup_hands.png").exists():
        image_base64 = base64.b64encode(
            Path("startup_hands.png").read_bytes()
        ).decode("utf-8")

        components.html(
            f"""
            <!DOCTYPE html>
            <html>
            <head>
            <meta name="viewport"
                  content="width=device-width, initial-scale=1">
            <style>
                * {{ box-sizing: border-box; }}

                body {{
                    margin: 0;
                    padding: 0;
                    background: #000;
                    overflow: hidden;
                }}

                .banner {{
                    position: relative;
                    width: 100%;
                    background: #000;
                    overflow: hidden;
                }}

                .banner img {{
                    display: block;
                    width: 100%;
                    height: auto;
                }}

                .coin-position {{
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    perspective: 600px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    width: clamp(48px, 10vw, 100px);
                    aspect-ratio: 1;
                    background: #000;
                    border-radius: 50%;
                }}

                .coin {{
                    display: inline-block;
                    font-family: "Apple Color Emoji",
                                 "Segoe UI Emoji", sans-serif;
                    font-size: clamp(38px, 8vw, 76px);
                    line-height: 1;
                    transform-style: preserve-3d;
                    filter:
                        drop-shadow(0 0 7px #ffd45b)
                        drop-shadow(0 0 18px rgba(255, 180, 30, .65));
                    animation: coin-spin 3s linear infinite;
                }}

                @keyframes coin-spin {{
                    from {{ transform: rotateY(0deg); }}
                    to {{ transform: rotateY(360deg); }}
                }}

                @media (prefers-reduced-motion: reduce) {{
                    .coin {{ animation: none; }}
                }}
            </style>
            </head>
            <body>
                <div class="banner">
                    <img
                        src="data:image/png;base64,{image_base64}"
                        alt="Two hands reaching toward each other"
                    >
                    <div class="coin-position">
                        <span class="coin">🪙</span>
                    </div>
                </div>
            </body>
            </html>
            """,
            height=300,
            scrolling=False,
        )
    else:
        st.warning(
            "Upload startup_hands.png beside streamlit_app.py "
            "to show the hands artwork."
        )

    st.markdown(
        """
        <div class="startup-title">🪙 GoldScope AI</div>
        <div class="startup-subtitle">
            PRECISION · CLARITY · DISCIPLINE
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div style="
            text-align:center;
            color:#bac7d7;
            font-size:14px;
            line-height:1.8;
            margin:0 auto 28px auto;
            max-width:460px;
        ">
            Explore XAU/USD market data, technical indicators,
            and experimental trading setups in one dashboard.
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, center, _ = st.columns([1, 2, 1])

    with center:
        if st.button(
            "🪙 Continue",
            type="primary",
            use_container_width=True,
        ):
            st.session_state.gold_started = True
            st.rerun()

    st.markdown(
        """
        <div class="startup-footer">
            EDUCATIONAL MARKET ANALYSIS · TRADE RESPONSIBLY
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------- HEADER ----------
def show_header():
    col1, col2 = st.columns(
        [1, 4],
        vertical_alignment="center",
    )

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

    # Only use completed 15-minute candles.
    now = pd.Timestamp.now(tz="UTC")
    candle_end = data["datetime"] + pd.Timedelta(minutes=15)
    data = data.loc[candle_end <= now].copy()
    data = data.sort_values("datetime").reset_index(drop=True)

    if len(data) < 60:
        return None

    # EMA 20 and EMA 50.
    data["ema20"] = data["close"].ewm(
        span=20, adjust=False
    ).mean()

    data["ema50"] = data["close"].ewm(
        span=50, adjust=False
    ).mean()

    # RSI 14.
    delta = data["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1 / 14, min_periods=14, adjust=False
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / 14, min_periods=14, adjust=False
    ).mean()

    rs = avg_gain / avg_loss
    data["rsi"] = 100 - (100 / (1 + rs))

    # ATR 14.
    previous_close = data["close"].shift(1)

    true_range = pd.concat(
        [
            data["high"] - data["low"],
            (data["high"] - previous_close).abs(),
            (data["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    data["atr"] = true_range.ewm(
        alpha=1 / 14, min_periods=14, adjust=False
    ).mean()

    last = data.iloc[-1]
    prev = data.iloc[-2]

    if (
        pd.isna(last["rsi"])
        or pd.isna(last["atr"])
        or last["atr"] <= 0
    ):
        return None

    bullish = last["close"] > last["open"]
    bearish = last["close"] < last["open"]

    # Experimental BUY conditions.
    buy = (
        last["ema20"] > last["ema50"]
        and last["close"] > last["ema20"]
        and bullish
        and 50 < last["rsi"] < 68
        and prev["close"] <= prev["ema20"]
    )

    # Experimental SELL conditions.
    sell = (
        last["ema20"] < last["ema50"]
        and last["close"] < last["ema20"]
        and bearish
        and 32 < last["rsi"] < 50
        and prev["close"] >= prev["ema20"]
    )

    entry = float(last["close"])
    atr = float(last["atr"])

    # Illustrative ATR-based TP/SL.
    sl_distance = atr
    tp_distance = atr * 2

    if buy:
        signal = "BUY"
        reason = (
            "Bullish trend, candle confirmation, "
            "and RSI momentum."
        )
        sl = entry - sl_distance
        tp = entry + tp_distance

    elif sell:
        signal = "SELL"
        reason = (
            "Bearish trend, candle confirmation, "
            "and RSI momentum."
        )
        sl = entry + sl_distance
        tp = entry - tp_distance

    else:
        signal = "WAIT"
        reason = "No confirmed setup under the current rules."
        sl = None
        tp = None

    return {
        "signal": signal,
        "reason": reason,
        "price": entry,
        "rsi": float(last["rsi"]),
        "ema20": float(last["ema20"]),
        "ema50": float(last["ema50"]),
        "atr": atr,
        "entry": entry if signal != "WAIT" else None,
        "sl": sl,
        "tp": tp,
        "risk_reward": 2.0 if signal != "WAIT" else None,
        "time": last["datetime"],
    }


# ---------- SIGNAL DISPLAY ----------
def show_signal(result, zone_name):
    st.divider()
    st.subheader("GoldScope AI Signal")

    if result is None:
        st.warning(
            "Not enough completed candles to calculate indicators."
        )
        return

    signal = result["signal"]

    if signal == "BUY":
        st.success("BUY SETUP DETECTED")
    elif signal == "SELL":
        st.error("SELL SETUP DETECTED")
    else:
        st.info("WAIT - No confirmed setup")

    st.write(result["reason"])

    c1, c2, c3 = st.columns(3)
    c1.metric("Signal candle close", f'${result["price"]:,.2f}')
    c2.metric("RSI (14)", f'{result["rsi"]:.2f}')
    c3.metric("ATR (14)", f'${result["atr"]:,.2f}')

    st.caption(
        f'EMA 20: ${result["ema20"]:,.2f} | '
        f'EMA 50: ${result["ema50"]:,.2f}'
    )

    if signal in ("BUY", "SELL"):
        st.markdown("### Trade Plan")

        a, b, c, d = st.columns(4)
        a.metric("Entry reference", f'${result["entry"]:,.2f}')
        b.metric("Take Profit (TP)", f'${result["tp"]:,.2f}')
        c.metric("Stop Loss (SL)", f'${result["sl"]:,.2f}')
        d.metric("Risk / Reward", "1 : 2")

        st.caption(
            f'Risk distance: '
            f'${abs(result["entry"] - result["sl"]):,.2f}'
            f' | Target distance: '
            f'${abs(result["tp"] - result["entry"]):,.2f}'
        )

        st.warning(
            "TP and SL are illustrative levels, not guaranteed "
            "execution prices. Spread, slippage, gaps, and "
            "market conditions can change outcomes."
        )
    else:
        st.caption("No TP/SL levels while the signal is WAIT.")

    display_time = result["time"].tz_convert(zone_name)
    st.caption(
        "Signal candle: "
        + display_time.strftime("%Y-%m-%d %H:%M %Z")
    )

    # Notify once per direction and candle in this session.
    if signal in ("BUY", "SELL"):
        alert_id = f'{signal}_{result["time"].isoformat()}'

        if alert_id not in st.session_state.gold_alerts_seen:
            st.toast(f"GoldScope AI: {signal} setup detected!")
            st.session_state.gold_alerts_seen.add(alert_id)

    st.caption(
        "Experimental signals. Accuracy is not verified. "
        "No automatic trading."
    )


# ---------- MAIN DASHBOARD ----------
@st.fragment(run_every="60s")
def gold_dashboard(zone_name):
    if not api_key:
        st.error(
            "API key missing. Add TWELVE_DATA_API_KEY "
            "to your Streamlit Cloud Secrets."
        )
        return

    try:
        df = fetch_gold(api_key)

        latest = float(df["close"].iloc[-1])
        previous = float(df["close"].iloc[-2]) if len(df) > 1 else latest
        change = latest - previous

        support = float(df["low"].tail(20).min())
        resistance = float(df["high"].tail(20).max())

        c1, c2, c3 = st.columns(3)
        c1.metric("Gold (XAU/USD)", f"${latest:,.2f}", f"{change:+.2f}")
        c2.metric("Estimated Support", f"${support:,.2f}")
        c3.metric("Estimated Resistance", f"${resistance:,.2f}")

        result = calculate_gold_signal(df)
        show_signal(result, zone_name)

        # Candlestick chart.
        chart_df = df.copy()
        chart_df["datetime"] = chart_df["datetime"].dt.tz_convert(zone_name)

        st.subheader("XAU/USD Candlestick Chart")
        st.caption(
            "Each candle represents 15 minutes. "
            "Times use the selected time zone."
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
            xaxis_title=f"Time ({zone_name})",
            yaxis_title="Gold price (USD)",
            xaxis_rangeslider_visible=False,
            margin=dict(l=20, r=20, t=35, b=20),
        )

        fig.update_xaxes(tickformat="%d %b %H:%M", showgrid=True)
        fig.update_yaxes(tickprefix="$", showgrid=True)
        st.plotly_chart(fig, use_container_width=True)

        # Recent candles.
        with st.expander("View recent candles"):
            table = chart_df.tail(10).copy()
            table["datetime"] = table["datetime"].dt.strftime(
                "%Y-%m-%d %H:%M %Z"
            )

            table = table.rename(
                columns={
                    "datetime": f"Time ({zone_name})",
                    "open": "Open",
                    "high": "High",
                    "low": "Low",
                    "close": "Close",
                }
            )

            st.dataframe(
                table[
                    [
                        f"Time ({zone_name})",
                        "Open",
                        "High",
                        "Low",
                        "Close",
                    ]
                ].iloc[::-1],
                use_container_width=True,
                hide_index=True,
            )

        # Market observation.
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
            "Latest candle received: "
            + latest_time.strftime("%Y-%m-%d %H:%M %Z")
        )
        st.caption(
            "Last checked: "
            + datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
        )
        st.caption(
            "Refresh checks run every 60 seconds. "
            "Data updates depend on Twelve Data."
        )

    except Exception as error:
        st.error(f"Could not update gold prices: {error}")


# ---------- APP ROUTING ----------
if not st.session_state.gold_started:
    show_startup_screen()

else:
    show_header()

    selected_zone = st.selectbox(
        "Chart time zone",
        options=list(TIMEZONES.keys()),
        index=1,
    )

    zone_name = TIMEZONES[selected_zone]

    st.caption(
        f"Selected time zone: {selected_zone} | "
        f"UTC offset: "
        f"{datetime.now(ZoneInfo(zone_name)).strftime('%z')}"
    )

    gold_dashboard(zone_name)

    st.divider()
    st.subheader("About GoldScope AI")

    st.write(
        "GoldScope AI displays XAU/USD candlesticks, "
        "experimental indicator setups, and estimated "
        "support and resistance. TP and SL are illustrative "
        "levels calculated using ATR."
    )

    st.caption(
        "For educational purposes only. "
        "No automatic trading. Accuracy is not verified."
    )

    if st.button("Return to startup screen"):
        st.session_state.gold_started = False
        st.rerun()
