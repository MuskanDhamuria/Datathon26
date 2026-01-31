from __future__ import annotations
import streamlit as st
import pandas as pd
import numpy as np
import requests 
import json
from freight_api import load_data, get_risk_report

from voyage_economics import (
    run_partial_voyage,
    find_delay_threshold,
    find_bunker_price_threshold,
)

# ---------------- Page config ----------------
st.set_page_config(
    page_title="Freight Decision Assistant",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------- Title ----------------
st.markdown("## 🚢 Freight Decision Assistant")
st.caption(
    "Interactive demo for vessel–cargo assignment with bunker price sensitivity "
    "and rule-based recommendations."
)

# ---------------- Load data ----------------
DATA = load_data(".")
results_df = DATA.get("results_df")
assignments_df = DATA.get("assignments_df")

if results_df is None or results_df.empty:
    st.warning(
        "No precomputed data found (`freight_calculator_all_combinations.csv`). "
        "Run the notebook first."
    )
    st.stop()

# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("🔧 Inputs")

    vessel_list = sorted(results_df["vessel"].unique().tolist())
    cargo_list = sorted(results_df["cargo"].unique().tolist())

    vessel = st.selectbox("Vessel", vessel_list)
    cargo = st.selectbox("Cargo / Route", cargo_list)

    st.divider()

    default_vlsfo = (
        float(results_df["vlsfo_price"].median())
        if "vlsfo_price" in results_df.columns
        else 490.0
    )

    # VLSFO input
    vlsfo_price = st.number_input(
        "VLSFO Price ($/MT)",
        value=default_vlsfo,
        step=1.0,
    )

    # MGO input with session state fix
    if "mgo_price" not in st.session_state:
        st.session_state.mgo_price = float(vlsfo_price * 1.3)

    mgo_price = st.number_input(
        "MGO Price ($/MT)",
        value=st.session_state.mgo_price,
        step=1.0,
    )

    # Update session state when user edits MGO
    st.session_state.mgo_price = mgo_price

    speed_knots = st.slider(
        "Speed (knots)",
        min_value=9.0,
        max_value=16.0,
        value=12.0,
        step=0.5,
    )

    extra_days = st.number_input(
        "Extra Waiting Days",
        min_value=0.0,
        max_value=30.0,
        value=0.0,
        step=0.5,
    )

submitted = st.button("🚀 Compute Recommendation", use_container_width=True)

# ---------------- Helper ----------------
def compute_adjusted_profit(row, vlsfo_new, mgo_new):
    orig_profit = float(row.get("profit", 0))
    vlsfo_orig = float(row.get("vlsfo_price", vlsfo_new))
    mgo_orig = float(row.get("mgo_price", mgo_new))
    total_vlsfo = float(row.get("total_vlsfo_mt", 0))
    total_mgo = float(row.get("total_mgo_mt", 0))
    days = float(row.get("days", 1)) or 1.0

    delta = (vlsfo_new - vlsfo_orig) * total_vlsfo + (mgo_new - mgo_orig) * total_mgo
    adj_profit = orig_profit - delta
    adj_tce = adj_profit / days if days > 0 else 0.0

    return {
        "orig_profit": orig_profit,
        "adj_profit": adj_profit,
        "orig_tce": float(row.get("tce", 0)),
        "adj_tce": adj_tce,
        "days": days,
    }
# ---------------- Main content ----------------
# Persist 'submitted' state in session_state
if "submitted" not in st.session_state:
    st.session_state.submitted = False

if submitted:
    st.session_state.submitted = True

current_sig = (vessel, cargo, vlsfo_price, mgo_price, speed_knots, extra_days)

    # If inputs changed, clear cached results
if st.session_state.get("last_sig") != current_sig:
        st.session_state.last_sig = current_sig
        st.session_state.pop("adjusted", None)
        st.session_state.pop("selected_row", None)

if st.session_state.submitted:
    # Ensure the selected row is persisted
    if "selected_row" not in st.session_state:
        mask = (results_df["vessel"] == vessel) & (results_df["cargo"] == cargo)
        if not mask.any():
            st.error("No matching vessel–cargo combination found.")
            st.stop()
        st.session_state.selected_row = results_df[mask].iloc[0].to_dict()
    
    row = st.session_state.selected_row

    # Compute adjusted values if not already persisted
    if "adjusted" not in st.session_state:
        adjusted = run_partial_voyage(
            base_row=row,
            vlsfo_price=vlsfo_price,
            mgo_price=mgo_price,
            speed_knots=speed_knots,
            extra_days=extra_days,
        )

        # Fallback for missing keys
        if "adj_profit" not in adjusted:
            comp = compute_adjusted_profit(row, vlsfo_price, mgo_price)
            adjusted.setdefault("adj_profit", comp["adj_profit"])
            adjusted.setdefault("adj_tce", comp["adj_tce"])
            adjusted.setdefault("orig_profit", comp["orig_profit"])
            adjusted.setdefault("orig_tce", comp["orig_tce"])
            adjusted.setdefault("profit", comp["adj_profit"])
            adjusted.setdefault("tce", comp["adj_tce"])
            adjusted.setdefault("days", comp["days"])

        st.session_state.adjusted = adjusted
    else:
        adjusted = st.session_state.adjusted


    # ---------------- Tabs ----------------
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Recommendation", "📈 Top Assignments", "🧠 Risk & Context", "🤖 AI Chatbot"])

    # -------- TAB 1: Recommendation --------
    with tab1:
        c1, c2, c3 = st.columns(3)
        c1.metric("Profit", f"${adjusted.get('profit', 0):,.0f}")
        c2.metric("TCE", f"${adjusted.get('tce', 0):,.0f}")
        c3.metric("Voyage Days", f"{adjusted.get('days', 0):.1f}")

        st.divider()

        adj_profit = adjusted.get("adj_profit", 0)
        orig_profit = adjusted.get("orig_profit", 1)
        if adj_profit >= 0:
            st.success("✅ **RECOMMENDATION: ASSIGN**")
        elif adj_profit > -0.05 * max(1.0, orig_profit):
            st.warning("⚠️ **RECOMMENDATION: HEDGE / CAUTION**")
        else:
            st.error("❌ **RECOMMENDATION: DECLINE**")

    # -------- TAB 2: Top Assignments --------
    with tab2:
        st.subheader("Top 10 Assignments (Ranked by Adjusted Profit)")

        top_df = results_df.copy()

        # Compute adjusted profit & tce using all inputs
        def compute_row(row):
            adjusted = run_partial_voyage(
                base_row=row.to_dict(),
                vlsfo_price=vlsfo_price,
                mgo_price=mgo_price,
                speed_knots=speed_knots,
                extra_days=extra_days,
            )
            if adjusted:
                adj_profit = adjusted.get("adj_profit", compute_adjusted_profit(row, vlsfo_price, mgo_price)["adj_profit"])
                adj_tce = adjusted.get("adj_tce", compute_adjusted_profit(row, vlsfo_price, mgo_price)["adj_tce"])
            else:
                comp = compute_adjusted_profit(row, vlsfo_price, mgo_price)
                adj_profit = comp["adj_profit"]
                adj_tce = comp["adj_tce"]
            return pd.Series({"adj_profit": adj_profit, "adj_tce": adj_tce})

        top_df[["adj_profit", "adj_tce"]] = top_df.apply(compute_row, axis=1)

        # Add a flag for the selected vessel/cargo
        top_df["selected"] = (top_df["vessel"] == vessel) & (top_df["cargo"] == cargo)

        # Sort by selected first, then adj_profit descending
        top_df = top_df.sort_values(["selected", "adj_profit"], ascending=[False, False]).head(10)


        display_cols = ["vessel", "cargo", "adj_profit", "adj_tce", "days", "selected"]
        display_cols = [c for c in display_cols if c in top_df.columns]

        st.dataframe(
            top_df[display_cols].reset_index(drop=True),
            use_container_width=True,
            height=400,
        )


    # -------- TAB 3: Risk --------
    with tab3:
        risk_report = get_risk_report(".")
        st.json(risk_report if isinstance(risk_report, dict) else {})


    # ---- TAB 4: Chatbot ----
    with tab4:
        st.subheader("🤖 Freight Decision AI Assistant")

        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])

        # User input
        user_input = st.chat_input("Ask about voyage recommendations...")

        if user_input:
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            
            # Display user message immediately
            with st.chat_message("user"):
                st.write(user_input)

            current_rec = f"""
Current Best Recommendation:
- Vessel: {row.get('vessel', 'N/A')}
- Cargo: {row.get('cargo', 'N/A')}
- Adjusted Profit: ${adjusted.get('adj_profit', 0):,.0f}
- Adjusted TCE: ${adjusted.get('adj_tce', 0):,.0f}
- Voyage Days: {adjusted.get('days', 0):.1f}
"""

            # Query Ollama
            with st.chat_message("assistant"):
                status = st.empty()

                with st.spinner("🤖 Generating response..."):
                    try:
                        response = requests.post(
                            "http://localhost:11434/api/generate",
                            json={
                                "model": "tinyllama",
                                "prompt": f"{current_rec}\nUser Query: {user_input}",
                                "stream": False,
                            },
                            timeout=30,
                        )

                        if response.status_code == 200:
                            assistant_response = response.json().get("response", "No response generated.")
                            status.write(assistant_response)
                            st.session_state.chat_history.append(
                                {"role": "assistant", "content": assistant_response}
                            )
                        else:
                            status.error(f"Ollama error: {response.status_code}")

                    except requests.exceptions.ConnectionError:
                        status.error("⚠️ Ollama not running.")
                    except Exception as e:
                        status.error(f"Error: {str(e)}")