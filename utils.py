# utils.py
import pandas as pd

def compute_yoy_growth(df, group_col, value_col, date_col='DateExpected'):
    """
    Compute Year-over-Year growth for a given group.
    Returns a DataFrame with the YoY percentage change.
    """
    if df.empty:
        return pd.DataFrame({group_col: [], 'YoY_Growth': []})
    
    df = df.copy()
    df['Year'] = df[date_col].dt.year
    yearly = df.groupby([group_col, 'Year'])[value_col].sum().reset_index()
    pivot_df = yearly.pivot(index=group_col, columns='Year', values=value_col).fillna(0)
    if pivot_df.shape[1] < 2:
        return pd.DataFrame({group_col: pivot_df.index, 'YoY_Growth': [0] * len(pivot_df)})
    yoy = pivot_df.pct_change(axis=1).iloc[:, -1] * 100
    yoy_df = pd.DataFrame({group_col: pivot_df.index, 'YoY_Growth': yoy.values})
    return yoy_df
