# GoldScope AI

Educational XAU/USD market-context dashboard with news-aware chat. It does not execute trades.

## Run locally

```bash
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

The dashboard reruns every 60 seconds. This requests updated data, but actual freshness depends on the market-data provider, API limits, and any caching in the app.

For public deployment on Streamlit Community Cloud, set `OPENAI_API_KEY` and optionally `OPENAI_MODEL` in the app's Secrets settings. Never put API keys in this repository. Ensure the model name is one enabled for your API account.

Educational use only, not financial advice. Quotes may be delayed or unavailable.
