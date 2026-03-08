# Finlify MVP

Finlify MVP is a Streamlit-based investment decision dashboard.

Features:

- Market overview with ranking scores
- Asset detail page with price history and moving averages
- Watchlist comparison with normalized returns

## Tech Stack

- Streamlit
- Pandas
- Plotly

## Run Locally

Install dependencies:

pip install -r requirements.txt

Run the app:

streamlit run app/finlify_streamlit_mvp_app.py

## Deployment

This app is designed to deploy on Streamlit Community Cloud.

Deployment settings:

Repository: this repo
Branch: main
Main file path:

app/finlify_streamlit_mvp_app.py

## Recommended Git Scope

For a clean deployable MVP commit, include only:

- app/
- data/mart/investment/top_ranked_assets.csv
- data/visualization/investment/price_history_for_pbi.csv
- requirements.txt
- README.md
