"""Partial voyage recalculation and scenario threshold analysis."""
import numpy as np

def run_partial_voyage(
    base_row: dict,
    vlsfo_price: float,
    mgo_price: float,
    speed_knots: float,
    extra_days: float,
    daily_hire: float = 12000,
    opex_per_day: float = 3000,
):
    """Recalculate profit & TCE for partial voyage changes."""
    base_days = float(base_row.get("days", 1))
    base_profit = float(base_row.get("profit", 0))
    base_vlsfo_mt = float(base_row.get("total_vlsfo_mt", 0))
    base_mgo_mt = float(base_row.get("total_mgo_mt", 0))
    base_speed = float(base_row.get("speed_knots", 12))

    speed_factor = base_speed / max(speed_knots, 1.0)
    sailing_days = base_days * speed_factor
    total_days = sailing_days + extra_days

    fuel_factor = (speed_knots / base_speed) ** 3
    vlsfo_mt = base_vlsfo_mt * fuel_factor
    mgo_mt = base_mgo_mt * fuel_factor

    bunker_cost = vlsfo_mt * vlsfo_price + mgo_mt * mgo_price
    time_cost = total_days * (daily_hire + opex_per_day)

    base_bunker_cost = base_vlsfo_mt * float(base_row.get("vlsfo_price", vlsfo_price)) + \
                       base_mgo_mt * float(base_row.get("mgo_price", mgo_price))
    base_time_cost = base_days * (daily_hire + opex_per_day)
    revenue = base_profit + base_bunker_cost + base_time_cost

    profit = revenue - bunker_cost - time_cost
    tce = profit / total_days if total_days > 0 else 0

    return {
        "profit": profit,
        "adj_profit": profit,
        "tce": tce,
        "adj_tce": tce,
        "days": total_days,
        "fuel": {"vlsfo_mt": vlsfo_mt, "mgo_mt": mgo_mt},
    }

# ---------------- Threshold Analysis ----------------
def find_delay_threshold(base_row, results_df, vlsfo_price, mgo_price,
                         speed_knots, extra_days_start=0.0, extra_days_end=30.0, step=0.5):
    current_vessel = base_row["vessel"]
    current_cargo = base_row["cargo"]
    base_result = run_partial_voyage(base_row, vlsfo_price, mgo_price, speed_knots, extra_days_start)
    base_profit = base_result["profit"]
    epsilon = 1e-3  # tolerance

    for delay_days in np.arange(extra_days_start, extra_days_end + step, step):
        profits = []
        for _, row in results_df.iterrows():
            result = run_partial_voyage(row.to_dict(), vlsfo_price, mgo_price, speed_knots, delay_days)
            profits.append({"vessel": row["vessel"], "cargo": row["cargo"], "profit": result["profit"]})
        top_choice = max(profits, key=lambda x: x["profit"])
        if (top_choice["vessel"] != current_vessel or top_choice["cargo"] != current_cargo) and abs(top_choice["profit"] - base_profit) > epsilon:
            return delay_days, top_choice, profits
    return None, None, None

def find_bunker_price_threshold(base_row, results_df, vlsfo_price, mgo_price,
                                speed_knots, extra_days, price_increase_start=0.0,
                                price_increase_end=200.0, step=1.0):
    current_vessel = base_row["vessel"]
    current_cargo = base_row["cargo"]
    base_result = run_partial_voyage(base_row, vlsfo_price, mgo_price, speed_knots, extra_days)
    base_profit = base_result["profit"]
    epsilon = 1e-3  # tolerance

    for pct_increase in np.arange(price_increase_start, price_increase_end + step, step):
        new_vlsfo_price = vlsfo_price * (1 + pct_increase / 100)
        profits = []
        for _, row in results_df.iterrows():
            result = run_partial_voyage(row.to_dict(), new_vlsfo_price, mgo_price, speed_knots, extra_days)
            profits.append({"vessel": row["vessel"], "cargo": row["cargo"], "profit": result["profit"]})
        top_choice = max(profits, key=lambda x: x["profit"])
        if (top_choice["vessel"] != current_vessel or top_choice["cargo"] != current_cargo) and abs(top_choice["profit"] - base_profit) > epsilon:
            return pct_increase, top_choice, profits
    return None, None, None
