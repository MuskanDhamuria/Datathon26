"""Interactive Streamlit UI for the freight calculator chatbot demo.

Accepts user inputs (vessel, cargo, bunker price) and displays
voyage recommendations interactively. Uses `freight_api.py` to
load notebook-produced CSVs and computes adjusted profits when
the user changes bunker prices.

Run:
    pip install streamlit pandas numpy
    streamlit run app_streamlit.py

Open http://localhost:8501 in your browser.
"""
from __future__ import annotations
import streamlit as st
import pandas as pd
import numpy as np
from freight_api import load_data, get_risk_report

st.set_page_config(page_title="Freight Chatbot Demo UI", layout="wide")

st.title("Freight Chatbot Demo — Interactive Recommendation UI")
st.write(
    "Use the controls on the left to choose a vessel, cargo and override bunker prices. "
    "The app shows adjusted profit/TCE and a simple recommendation based on the inputs."
)

DATA = load_data('.')
results_df = DATA.get('results_df')
assignments_df = DATA.get('assignments_df')

if results_df is None or results_df.empty:
    st.warning('No `freight_calculator_all_combinations.csv` found. Run the notebook first and export CSVs.')

with st.sidebar.form('inputs'):
    st.header('User Inputs')
    vessel_list = sorted(results_df['vessel'].unique().tolist()) if results_df is not None else []
    vessel = st.selectbox('Vessel', ['-- select --'] + vessel_list)
    cargo_list = sorted(results_df['cargo'].unique().tolist()) if results_df is not None else []
    cargo = st.selectbox('Cargo / Route', ['-- select --'] + cargo_list)

    # default bunker price: try to use median from results_df vlsfo_price column
    default_vlsfo = None
    if results_df is not None and 'vlsfo_price' in results_df.columns:
        default_vlsfo = float(results_df['vlsfo_price'].median())
    default_vlsfo = default_vlsfo or 490.0
    vlsfo_price = st.number_input('VLSFO Price ($/MT)', value=float(default_vlsfo), step=1.0)
    mgo_price = st.number_input('MGO Price ($/MT) (optional)', value=float(vlsfo_price * 1.3))

    st.markdown('---')
    st.write('Risk & context')
    risk_report = get_risk_report('.')
    st.write(risk_report if isinstance(risk_report, dict) else {})

    submitted = st.form_submit_button('Compute Recommendation')

col1, col2 = st.columns([2, 3])

def compute_adjusted_profit(row, vlsfo_new, mgo_new):
    # Expected columns: profit, total_vlsfo_mt, total_mgo_mt, vlsfo_price, mgo_price, days
    try:
        orig_profit = float(row.get('profit', 0))
        vlsfo_orig = float(row.get('vlsfo_price', vlsfo_new))
        mgo_orig = float(row.get('mgo_price', mgo_new))
        total_vlsfo = float(row.get('total_vlsfo_mt', 0))
        total_mgo = float(row.get('total_mgo_mt', 0))
        days = float(row.get('days', 1)) if row.get('days', 0) else 1.0

        delta = (vlsfo_new - vlsfo_orig) * total_vlsfo + (mgo_new - mgo_orig) * total_mgo
        adj_profit = orig_profit - delta
        adj_tce = adj_profit / days if days > 0 else 0.0
        return {
            'orig_profit': orig_profit,
            'adj_profit': adj_profit,
            'orig_tce': float(row.get('tce', 0)),
            'adj_tce': adj_tce,
            'days': days,
            'total_vlsfo_mt': total_vlsfo,
            'total_mgo_mt': total_mgo
        }
    except Exception as e:
        return {'error': str(e)}


if submitted:
    if vessel == '-- select --' or cargo == '-- select --':
        st.error('Please select both a vessel and a cargo.')
    else:
        # find matching row in results
        mask = (results_df['vessel'] == vessel) & (results_df['cargo'] == cargo)
        if not mask.any():
            st.error('No precomputed combination found for selected vessel+cargo. Please run the notebook to compute combinations.')
        else:
            row = results_df[mask].iloc[0].to_dict()
            adjusted = compute_adjusted_profit(row, float(vlsfo_price), float(mgo_price))

            with col1:
                st.subheader('Selected Combination')
                st.write({'vessel': vessel, 'cargo': cargo})
                st.metric('Original Profit', f"${adjusted['orig_profit']:,.0f}")
                st.metric('Adjusted Profit', f"${adjusted['adj_profit']:,.0f}")
                st.metric('Original TCE', f"${adjusted['orig_tce']:,.0f}")
                st.metric('Adjusted TCE', f"${adjusted['adj_tce']:,.0f}")

            with col2:
                st.subheader('Simple Recommendation')
                # simple rule-based recommendation
                if adjusted['adj_profit'] >= 0:
                    action = 'assign'
                    reasons = [
                        'Adjusted profit is positive under provided bunker prices.',
                        'TCE remains attractive relative to expected operating costs.'
                    ]
                elif adjusted['adj_profit'] > -0.05 * max(1.0, adjusted['orig_profit']):
                    action = 'hedge'
                    reasons = [
                        'Profit turned slightly negative; consider hedging bunker exposure.',
                        'Monitor market and re-evaluate with updated FFA quotes.'
                    ]
                else:
                    action = 'decline'
                    reasons = [
                        'Adjusted profit materially negative — do not proceed without better rates.',
                        'Consider re-pricing or waiting for improved market conditions.'
                    ]

                st.write(f"**Recommendation:** {action.upper()}")
                for r in reasons:
                    st.write('- ' + r)

            # show top-5 for given bunker price
            st.markdown('---')
            st.subheader('Top 5 Assignments at Provided Bunker Price')

            df = results_df.copy()
            # compute adjusted profit for all
            def _safe_adjusted(r):
                return compute_adjusted_profit(r, float(vlsfo_price), float(mgo_price))['adj_profit']

            df['_adj_profit'] = df.apply(lambda r: _safe_adjusted(r.to_dict()), axis=1)
            topk = df.sort_values('_adj_profit', ascending=False).head(5)
            display_cols = [c for c in ['vessel', 'cargo', 'profit', 'tce', 'days', 'total_vlsfo_mt', 'total_mgo_mt', '_adj_profit'] if c in topk.columns]
            if len(display_cols) > 0:
                topk_display = topk[display_cols].copy()
                topk_display['profit'] = topk_display['profit'].apply(lambda x: f"${x:,.0f}") if 'profit' in topk_display.columns else None
                topk_display['_adj_profit'] = topk_display['_adj_profit'].apply(lambda x: f"${x:,.0f}")
                st.table(topk_display.reset_index(drop=True))

            # allow export
            csv = topk.to_csv(index=False)
            st.download_button('Download top-5 CSV', data=csv, file_name='top5_adjusted.csv')

st.markdown('---')
st.write('Notes: This demo adjusts precomputed profits by scaling bunker costs. For on-demand full recalculation use direct voyage economics functions integrated into a Python module.')