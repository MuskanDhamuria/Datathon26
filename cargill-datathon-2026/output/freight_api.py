"""
Please have these
- `freight_calculator_all_combinations.csv`
- `freight_calculator_assignments.csv`
- `freight_calculator_scenarios.csv`
"""
from __future__ import annotations
import os
import json
from typing import Optional, Dict, Any, List
import pandas as pd
import numpy as np


def _read_csv_if_exists(path: str) -> Optional[pd.DataFrame]:
    try:
        if os.path.exists(path):
            return pd.read_csv(path)
    except Exception:
        pass
    return None


def load_data(base_path: str = '.') -> Dict[str, Optional[pd.DataFrame]]:
    results = _read_csv_if_exists(os.path.join(base_path, 'freight_calculator_all_combinations.csv'))
    assignments = _read_csv_if_exists(os.path.join(base_path, 'freight_calculator_assignments.csv'))
    scenarios = _read_csv_if_exists(os.path.join(base_path, 'freight_calculator_scenarios.csv'))
    return {
        'results_df': results,
        'assignments_df': assignments,
        'scenarios_df': scenarios
    }


def _df_to_records(df: pd.DataFrame, n: Optional[int] = None) -> List[Dict[str, Any]]:
    if df is None:
        return []
    if n is not None:
        df = df.head(n)
    return json.loads(df.to_json(orient='records'))


def get_top5(base_path: str = '.', n: int = 5) -> List[Dict[str, Any]]:
    data = load_data(base_path)
    results = data.get('results_df')
    if results is None or results.empty:
        assignments = data.get('assignments_df')
        if assignments is None or assignments.empty:
            return []
        df = assignments
    else:
        df = results

    if 'tce' in df.columns:
        top = df.nlargest(n, 'tce')
    elif 'profit' in df.columns:
        top = df.nlargest(n, 'profit')
    else:
        top = df.head(n)

    fields = [c for c in ['vessel', 'cargo', 'profit', 'tce', 'days'] if c in top.columns]
    return json.loads(top[fields].to_json(orient='records'))


def get_comparison(base_path: str = '.') -> Dict[str, Any]:
    data = load_data(base_path)
    assignments = data.get('assignments_df')
    if assignments is None or assignments.empty:
        return {'error': 'assignments CSV not found'}

    total_profit = float(assignments['profit'].sum()) if 'profit' in assignments.columns else None
    avg_tce = float(assignments['tce'].mean()) if 'tce' in assignments.columns else None
    total_days = float(assignments['days'].sum()) if 'days' in assignments.columns else None
    return {
        'algorithm': 'greedy_tce (from CSV)',
        'total_profit': total_profit,
        'avg_tce': avg_tce,
        'total_days': total_days,
        'assignments': len(assignments)
    }


def get_report(base_path: str = '.', algorithm_name: str = 'greedy_tce') -> Dict[str, Any]:
    data = load_data(base_path)
    assign = data.get('assignments_df')
    results = data.get('results_df')

    if assign is None or assign.empty:
        return {'error': 'assignments CSV not found'}

    report = {
        'total_assignments': int(len(assign)),
        'vessels_utilized': int(assign['vessel'].nunique()) if 'vessel' in assign.columns else None,
        'cargoes_assigned': int(assign['cargo'].nunique()) if 'cargo' in assign.columns else None,
        'total_gross_revenue': float(assign['gross_revenue'].sum()) if 'gross_revenue' in assign.columns else None,
        'total_net_revenue': float(assign['net_revenue'].sum()) if 'net_revenue' in assign.columns else None,
        'total_bunker_cost': float(assign['bunker_cost'].sum()) if 'bunker_cost' in assign.columns else None,
        'total_hire_cost': float(assign['hire_cost'].sum()) if 'hire_cost' in assign.columns else None,
        'total_operating_costs': float(assign['total_costs'].sum()) if 'total_costs' in assign.columns else None,
        'total_profit': float(assign['profit'].sum()) if 'profit' in assign.columns else None,
        'avg_tce': float(assign['tce'].mean()) if 'tce' in assign.columns else None,
        'avg_profit_margin_pct': float(assign['profit_margin_pct'].mean()) if 'profit_margin_pct' in assign.columns else None,
        'top5': get_top5(base_path, n=5)
    }
    scenarios = data.get('scenarios_df')
    if scenarios is not None and 'total_profit' in scenarios.columns:
        report['scenarios_summary'] = {
            'min_profit': float(scenarios['total_profit'].min()),
            'median_profit': float(scenarios['total_profit'].median()),
            'max_profit': float(scenarios['total_profit'].max())
        }

    return report


def get_risk_report(base_path: str = '.') -> Dict[str, Any]:
    data = load_data(base_path)
    scenarios = data.get('scenarios_df')
    if scenarios is None or 'total_profit' not in scenarios.columns:
        return {'error': 'scenarios CSV not found or missing total_profit'}

    profits = scenarios['total_profit'].dropna().astype(float)
    arr = profits.to_numpy()
    mean = float(arr.mean())
    std = float(arr.std())
    var_5 = float(np.percentile(arr, 5))
    cvar_5 = float(arr[arr <= var_5].mean()) if np.any(arr <= var_5) else var_5
    return {
        'mc_mean_profit': mean,
        'mc_std_profit': std,
        'mc_var_5': var_5,
        'mc_cvar_5': cvar_5,
        'n_samples': int(len(arr))
    }


def run_all(base_path: str = '.') -> Dict[str, Any]:
    data = load_data(base_path)
    report = get_report(base_path)
    comparison = get_comparison(base_path)
    risk = get_risk_report(base_path)

    return {
        'report': report,
        'comparison': comparison,
        'risk_report': risk,
        'top5': report.get('top5', [])
    }


if __name__ == '__main__':
    ctx = run_all('.')
    print(json.dumps(ctx, indent=2))