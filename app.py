
import streamlit as st
import streamlit.components.v1 as components
import requests
import pandas as pd
import plotly.graph_objects as go

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="GoldScope AI",
    page_icon="🪙",
    layout="wide",
)

APP_DIR = Path(__file__).parent

NAVY = "#081426"
GOLD = "#E7B84B"
LIGHT_GOLD = "#FFE6A0"


# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

if "gold_started" not in st.session_state:
    st.session_state.gold_started = False

if "gold_alerts_seen" not in st.session_state:
    st.session_state.gold_alerts_seen = set()


# --------------------------------------------------
# TIMEZONES
# --------------------------------------------------

TIMEZONES = {
    "UTC": "UTC",
    "ICT - Cambodia": "Asia/Phnom_Penh",
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


# --------------------------------------------------
# 3D GOLD COIN STARTUP SCREEN
# --------------------------------------------------

def show_startup_screen():
    st.markdown(
        f"""
        <style>
        .startup-panel {{
            background:
                radial-gradient(
                    circle at 50% 35%,
                    #172b48 0%,
                    {NAVY} 65%,
                    #040914 100%
                );
            border: 1px solid #b88b2d;
            border-radius: 22px;
            padding: 42px 20px 35px;
            text-align: center;
            overflow: hidden;
            box-shadow: 0 15px 50px #00000035;
        }}

        .coin-scene {{
            width: 180px;
            height: 180px;
            margin: 0 auto 18px;
            perspective: 900px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .gold-coin {{
            position: relative;
            width: 130px;
            height: 130px;
            transform-style: preserve-3d;
            animation: coin-spin 5s linear infinite;
        }}

        .coin-face {{
            position: absolute;
            inset: 0;
            border-radius: 50%;
            border: 5px solid #ffdf7d;
            background:
                radial-gradient(
                    circle at 28% 23%,
                    #fffbd0 0%,
                    #f8dc76 12%,
                    #e9b839 35%,
                    #b77812 68%,
                    #68400b 100%
                );
            box-shadow:
                inset 0 0 0 3px #c38b20,
                inset 0 0 0 7px #f4d36b,
                inset 0 0 15px #81500b,
                0 0 22px #dba52a55;
            display: flex;
            align-items: center;
            justify-content: center;
            backface-visibility: hidden;
        }}

        .coin-face::before {{
            content: "";
            position: absolute;
            inset: 10px;
            border-radius: 50%;
            border: 2px solid #9a6815;
            box-shadow: inset 0 0 0 2px #f9dc7d;
        }}

        .coin-letter {{
            position: relative;
            font-family: Georgia, serif;
            font-size: 72px;
            font-weight: 900;
            line-height: 1;
            color: #83520b;
            text-shadow:
                2px 2px 0 #ffed9c,
                4px 4px 0 #bd831b,
                -1px -1px 0 #fff6bf;
            transform: translateZ(2px);
        }}

        .coin-front {{
            transform: translateZ(7px);
        }}

        .coin-back {{
            transform: rotateY(180deg) translateZ(7px);
        }}

        .coin-edge {{
            position: absolute;
            inset: 0;
            border-radius: 50%;
            border: 7px solid #c08a20;
            background:
                repeating-linear-gradient(
                    90deg,
                    #8a5a12 0px,
                    #ffe17b 3px,
                    #b47a16 6px,
                    #f4d05c 9px
                );
            transform: translateZ(0);
        }}

        @keyframes coin-spin {{
            from {{
                transform: rotateY(0deg) rotateX(-8deg);
            }}
            to {{
                transform: rotateY(360deg) rotateX(-8deg);
            }}
        }}

        .startup-title {{
            color: #f5cd66;
            font-size: clamp(30px, 5vw, 45px);
            font-weight: 800;
            letter-spacing: 1px;
            margin: 5px 0 8px;
        }}

        .startup-subtitle {{
            color: #d4deed;
            font-size: 15px;
            margin-bottom: 14px;
        }}

        .startup-status {{
            color: #e6bd57;
            font-size: 12px;
            letter-spacing: 3px;
            text-transform: uppercase;
        }}

        @media (prefers-reduced-motion: reduce) {{
            .gold-coin {{
                animation-duration: 15s;
            }}
        }}
        </style>

        <div class="startup-panel">
            <div class="coin-scene">
                <div class="gold-coin">
                    <div class="coin-edge"></div>

                    <div class="coin-face coin-front">
                        <span class="coin-letter">G</span>
                    </div>

                    <div class="coin-face coin-back">
                        <span class="coin-letter">G</span>
                    </div>
                </div>
            </div>

            <div class="startup-title">GoldScope AI</div>

            <div class="startup-subtitle">
                XAU/USD · Smarter Gold Market Analysis
            </div>

            <div class="startup-status">
                Market Intelligence Dashboard
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")

    _, center, _ = st.columns([1, 2, 1])

    with center:
        if st.button(
            "Enter GoldScope AI",
            type="primary",
            use_container_width=True,
        ):
            st.session_state.gold_started = True
            st.rerun()


# --------------------------------------------------
# WEBSITE HEADER
# --------------------------------------------------

def show_header():
    logo_path = APP_DIR / "logo.png"

    col1, col2 = st.columns([1, 5])

    with col1:
        if logo_path.exists():
            st.image(str(logo_path), width=115)

    with col2:
        st.title("🪙 GoldScope AI")
        st.caption("XAU/USD · Smarter Gold Market Analysis")

    st.divider()


# --------------------------------------------------
# GET API KEY
# --------------------------------------------------

def get_api_key():
    try:
        secret_key = st.secrets.get(
            "TWELVE_DATA_API_KEY",
            "",
        )
    except Exception:
        secret_key = ""

    with st.sidebar:
        st.header("Settings")

        if secret_key:
            st.success("API key loaded from app secrets")
            api_key = secret_key
        else:
            st.info(
                "Enter your Twelve Data API key to load "
                "gold market data."
            )

            api_key = st.text_input(
                "Twelve Data API key",
                type="password",
                help=(
                    "Your key is used to request market data. "
                    "Do not share it publicly."
                ),
            )

        st.caption(
            "Market data availability depends on your "
            "Twelve Data plan and API limits."
        )

    return api_key.strip()


# --------------------------------------------------
# FETCH GOLD CANDLES
# --------------------------------------------------

@st.cache_data(ttl=30, show_spinner=False)
def fetch_gold(api_key):
    if not api_key:
        return pd.DataFrame(), "Enter your API key."

    url = "https://api.twelvedata.com/time_series"

    params = {
        "symbol": "XAU/USD",
        "interval": "15min",
        "outputsize": 100,
        "timezone": "UTC",
        "apikey": api_key,
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()

        if "values" not in data:
            message = data.get(
                "message",
                data.get("status", "Unknown API error"),
            )
            return pd.DataFrame(), str(message)

        df = pd.DataFrame(data["values"])

        required = [
            "datetime",
            "open",
            "high",
            "low",
            "close",
        ]

        if not all(column in df.columns for column in required):
            return pd.DataFrame(), "The API returned incomplete candle data."

        df = df[required].copy()

        df["datetime"] = pd.to_datetime(
            df["datetime"],
            utc=True,
            errors="coerce",
        )

        for column in ["open", "high", "low", "close"]:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

        df = df.dropna()
        df = df.sort_values("datetime")
        df = df.drop_duplicates(
            subset=["datetime"],
            keep="last",
        )
        df = df.reset_index(drop=True)

        if df.empty:
            return pd.DataFrame(), "No usable candle data was returned."

        return df, None

    except requests.RequestException as exc:
        return pd.DataFrame(), f"Network/API request failed: {exc}"

    except Exception as exc:
        return pd.DataFrame(), f"Could not process market data: {exc}"


# --------------------------------------------------
# INDICATORS AND SIGNAL CALCULATION
# --------------------------------------------------

def add_indicators(df):
    df = df.copy()

    df["ema20"] = df["close"].ewm(
        span=20,
        adjust=False,
    ).mean()

    df["ema50"] = df["close"].ewm(
        span=50,
        adjust=False,
    ).mean()

    delta = df["close"].diff()

    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)

    avg_gain = gains.ewm(
        alpha=1 / 14,
        min_periods=14,
        adjust=False,
    ).mean()

    avg_loss = losses.ewm(
        alpha=1 / 14,
        min_periods=14,
        adjust=False,
    ).mean()

    relative_strength = avg_gain / avg_loss.replace(0, float("nan"))

    df["rsi"] = 100 - (
        100 / (1 + relative_strength)
    )

    df["rsi"] = df["rsi"].fillna(50)

    previous_close = df["close"].shift(1)

    true_range = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - previous_close).abs(),
            (df["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    df["atr"] = true_range.ewm(
        alpha=1 / 14,
        min_periods=14,
        adjust=False,
    ).mean()

    return df


def completed_candles(df):
    if df.empty:
        return df.copy()

    now = pd.Timestamp.now(tz="UTC")

    candle_end = (
        df["datetime"] + pd.Timedelta(minutes=15)
    )

    result = df.loc[candle_end <= now].copy()

    return result.reset_index(drop=True)


def calculate_gold_signal(df):
    result = {
        "signal": "WAIT",
        "reason": "Waiting for enough completed candles.",
        "entry": None,
        "stop_loss": None,
        "take_profit": None,
        "rsi": None,
        "ema20": None,
        "ema50": None,
        "atr": None,
        "candle_time": None,
    }

    if len(df) < 60:
        result["reason"] = (
            "At least 60 completed 15-minute candles "
            "are needed for this analysis."
        )
        return result

    data = add_indicators(df)

    current = data.iloc[-1]
    previous = data.iloc[-2]

    entry = float(current["close"])
    ema20 = float(current["ema20"])
    ema50 = float(current["ema50"])
    rsi = float(current["rsi"])
    atr = float(current["atr"])

    result.update(
        {
            "entry": entry,
            "rsi": rsi,
            "ema20": ema20,
            "ema50": ema50,
            "atr": atr,
            "candle_time": current["datetime"],
        }
    )

    if pd.isna(atr) or atr <= 0:
        result["reason"] = "ATR is not ready for analysis."
        return result

    bullish_candle = current["close"] > current["open"]
    bearish_candle = current["close"] < current["open"]

    crossed_above_ema20 = (
        previous["close"] <= previous["ema20"]
        and current["close"] > current["ema20"]
    )

    crossed_below_ema20 = (
        previous["close"] >= previous["ema20"]
        and current["close"] < current["ema20"]
    )

    buy_setup = (
        ema20 > ema50
        and current["close"] > ema20
        and bullish_candle
        and 50 <= rsi <= 68
        and crossed_above_ema20
    )

    sell_setup = (
        ema20 < ema50
        and current["close"] < ema20
        and bearish_candle
        and 32 <= rsi <= 50
        and crossed_below_ema20
    )

    if buy_setup:
        result["signal"] = "BUY"
        result["reason"] = (
            "The EMA trend, candle direction, RSI, "
            "and EMA20 crossover meet the buy rules."
        )

        result["stop_loss"] = entry - atr
        result["take_profit"] = entry + (2 * atr)

    elif sell_setup:
        result["signal"] = "SELL"
        result["reason"] = (
            "The EMA trend, candle direction, RSI, "
            "and EMA20 crossover meet the sell rules."
        )

        result["stop_loss"] = entry + atr
        result["take_profit"] = entry - (2 * atr)

    else:
        result["reason"] = (
            "The full entry rules are not met. "
            "Wait for a clearer setup."
        )

    return result


# --------------------------------------------------
# SUPPORT AND RESISTANCE
# --------------------------------------------------

def calculate_support_resistance(df):
    if df.empty:
        return None, None

    recent = df.tail(50)

    support = float(recent["low"].min())
    resistance = float(recent["high"].max())

    return support, resistance


# --------------------------------------------------
# SIGNAL DISPLAY AND ALERTS
# --------------------------------------------------

def show_signal(signal_data):
    signal = signal_data["signal"]

    st.subheader("Market Signal")

    if signal == "BUY":
        st.success("BUY setup detected")

    elif signal == "SELL":
        st.error("SELL setup detected")

    else:
        st.info("WAIT — no complete entry setup")

    st.write(signal_data["reason"])

    if signal_data["entry"] is not None:
        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Analysis Entry Price",
            f"${signal_data['entry']:,.2f}",
        )

        if signal_data["stop_loss"] is not None:
            col2.metric(
                "Theoretical Stop Loss",
                f"${signal_data['stop_loss']:,.2f}",
            )

            col3.metric(
                "Theoretical Take Profit",
                f"${signal_data['take_profit']:,.2f}",
            )

            st.caption(
                "Illustrative ATR-based levels, using a 1:2 "
                "risk-to-reward ratio. These are not guaranteed "
                "execution prices or personalized financial advice."
            )

    candle_time = signal_data.get("candle_time")

    if signal in ("BUY", "SELL") and candle_time is not None:
        alert_id = f"{signal}_{candle_time.isoformat()}"

        if alert_id not in st.session_state.gold_alerts_seen:
            st.session_state.gold_alerts_seen.add(alert_id)

            st.toast(
                f"{signal} setup detected on a completed 15-minute candle.",
                icon="🪙",
            )

    if signal_data["rsi"] is not None:
        a, b, c = st.columns(3)

        a.metric("RSI (14)", f"{signal_data['rsi']:.2f}")
        b.metric("EMA 20", f"${signal_data['ema20']:,.2f}")
        c.metric("EMA 50", f"${signal_data['ema50']:,.2f}")


# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------

@st.fragment(run_every="60s")
def gold_dashboard(api_key, zone_name):
    df, error = fetch_gold(api_key)

    if error:
        st.error(f"Could not load gold data: {error}")
        st.info(
            "Check your API key, internet connection, "
            "and Twelve Data plan."
        )
        return

    if df.empty:
        st.warning("No gold candle data is available yet.")
        return

    complete_df = completed_candles(df)

    if complete_df.empty:
        st.warning(
            "Waiting for the first completed 15-minute candle."
        )
        return

    latest = complete_df.iloc[-1]

    support, resistance = calculate_support_resistance(
        complete_df
    )

    current_price = float(latest["close"])

    st.subheader("Live Gold Market")

    price_col, support_col, resistance_col = st.columns(3)

    price_col.metric(
        "Latest Completed Candle",
        f"${current_price:,.2f}",
    )

    support_col.metric(
        "Support (last 50 candles)",
        f"${support:,.2f}",
    )

    resistance_col.metric(
        "Resistance (last 50 candles)",
        f"${resistance:,.2f}",
    )

    st.caption(
        "Price and levels are based on the latest completed "
        "15-minute candle and recent candle ranges."
    )

    st.divider()

    signal_data = calculate_gold_signal(complete_df)
    show_signal(signal_data)

    st.divider()

    # ----------------------------------------------
    # CANDLESTICK CHART
    # ----------------------------------------------

    st.subheader("XAU/USD 15-Minute Candlestick Chart")

    chart_df = add_indicators(complete_df.tail(100).copy())

    chart_df["display_time"] = (
        chart_df["datetime"]
        .dt.tz_convert(ZoneInfo(zone_name))
    )

    fig = go.Figure()

    fig.add_trace(
        go.Candlestick(
            x=chart_df["display_time"],
            open=chart_df["open"],
            high=chart_df["high"],
            low=chart_df["low"],
            close=chart_df["close"],
            name="XAU/USD",
            increasing_line_color="#20B486",
            decreasing_line_color="#E05260",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=chart_df["display_time"],
            y=chart_df["ema20"],
            mode="lines",
            name="EMA 20",
            line=dict(color="#E7B84B", width=1.5),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=chart_df["display_time"],
            y=chart_df["ema50"],
            mode="lines",
            name="EMA 50",
            line=dict(color="#5CA9FF", width=1.5),
        )
    )

    fig.add_hline(
        y=support,
        line_dash="dash",
        line_color="#20B486",
        annotation_text="Support",
    )

    fig.add_hline(
        y=resistance,
        line_dash="dash",
        line_color="#E05260",
        annotation_text="Resistance",
    )

    fig.update_layout(
        template="plotly_dark",
        height=600,
        xaxis_title=f"Time ({zone_name})",
        yaxis_title="Gold Price (USD)",
        xaxis_rangeslider_visible=False,
        margin=dict(l=10, r=10, t=35, b=10),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
        ),
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

    # ----------------------------------------------
    # RECENT CANDLES
    # ----------------------------------------------

    with st.expander("View Recent 15-Minute Candles"):
        recent = complete_df.tail(15).copy()

        recent["Time"] = (
            recent["datetime"]
            .dt.tz_convert(ZoneInfo(zone_name))
            .dt.strftime("%Y-%m-%d %H:%M:%S")
        )

        recent = recent[
            ["Time", "open", "high", "low", "close"]
        ].sort_values("Time", ascending=False)

        recent = recent.rename(
            columns={
                "open": "Open",
                "high": "High",
                "low": "Low",
                "close": "Close",
            }
        )

        st.dataframe(
            recent,
            use_container_width=True,
            hide_index=True,
        )

    # ----------------------------------------------
    # MARKET OBSERVATION
    # ----------------------------------------------

    st.subheader("Market Observation")

    latest_indicators = add_indicators(
        complete_df
    ).iloc[-1]

    if latest_indicators["ema20"] > latest_indicators["ema50"]:
        st.write(
            "The EMA20 is above EMA50, indicating an upward "
            "trend condition in this indicator."
        )

    elif latest_indicators["ema20"] < latest_indicators["ema50"]:
        st.write(
            "The EMA20 is below EMA50, indicating a downward "
            "trend condition in this indicator."
        )

    else:
        st.write(
            "The EMAs are close together. Trend direction "
            "may be unclear."
        )

    last_update = datetime.now(
        timezone.utc
    ).astimezone(
        ZoneInfo(zone_name)
    )

    st.caption(
        f"Dashboard checked: {last_update:%Y-%m-%d %H:%M:%S} "
        f"({zone_name})."
    )

    st.caption(
        "Data refreshes approximately every 60 seconds. "
        "The data provider may delay updates or enforce API limits."
    )


# --------------------------------------------------
# MAIN APP
# --------------------------------------------------

if not st.session_state.gold_started:
    show_startup_screen()

else:
    show_header()

    api_key = get_api_key()

    selected_timezone = st.selectbox(
        "Display time zone",
        options=list(TIMEZONES.keys()),
        index=0,
    )

    zone_name = TIMEZONES[selected_timezone]

    if api_key:
        gold_dashboard(api_key, zone_name)
    else:
        st.info(
            "Enter your Twelve Data API key in the sidebar "
            "to load the dashboard."
        )

    st.divider()

    with st.expander("About GoldScope AI"):
        st.write(
            "GoldScope AI is an educational gold-market dashboard. "
            "It displays XAU/USD candle data, technical indicators, "
            "support and resistance estimates, and rule-based "
            "BUY, SELL, or WAIT setups."
        )

        st.write(
            "Signals are not guaranteed to be accurate. This app "
            "does not place trades or connect to a broker to execute "
            "orders. Always verify market data and test any strategy "
            "carefully before making financial decisions."
        )

    if st.button("Return to Startup Screen"):
        st.session_state.gold_started = False
        st.rerun()
