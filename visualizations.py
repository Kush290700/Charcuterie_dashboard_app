# visualizations.py
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from utils import compute_yoy_growth

def create_forecast_graph(sku_desc, months_ahead, cached_forecast_func):
    """
    Plots the forecast line (starting from the last historical date) for the given SKU.
    """
    forecast_fig = go.Figure()
    
    if sku_desc == 'ALL':
        forecast_fig.update_layout(
            title="Select a SKU to show forecast",
            template='plotly_white'
        )
        return forecast_fig

    # Extract monthly data for the SKU
    # (Note: monthly_sales is imported globally in the forecasting function)
    from data_processing import monthly_sales
    forecast_data = monthly_sales[monthly_sales['SKU_Desc'] == sku_desc].copy().sort_values('ds')
    if forecast_data.empty:
        forecast_fig.update_layout(
            title="No data for selected SKU",
            template='plotly_white'
        )
        return forecast_fig

    forecast = cached_forecast_func(sku_desc, months_ahead)
    forecast = forecast.head(months_ahead)

    forecast_fig.add_trace(go.Scatter(
        x=forecast.index,
        y=forecast['yhat'],
        name='Forecast',
        mode='lines+markers',
        line=dict(color='#ff7f0e', shape='spline')
    ))
    forecast_fig.update_layout(
        title=f"Sales Forecast for {sku_desc}",
        xaxis_title="Date",
        yaxis_title="Shipped Lb",
        yaxis_tickformat=".2f",
        template='plotly_white',
        legend=dict(x=0, y=1.1, orientation="h"),
        margin=dict(t=100)
    )
    return forecast_fig

def create_historical_ts_graph(sku_desc):
    """
    Plots historical monthly sums of ShippedLb for the selected SKU.
    """
    from data_processing import monthly_sales
    if sku_desc == 'ALL':
        return go.Figure().update_layout(
            title="Select a SKU to show historical sales",
            template='plotly_white'
        )
    
    ts_data = monthly_sales[monthly_sales['SKU_Desc'] == sku_desc].copy().sort_values('ds')
    if ts_data.empty:
        return go.Figure().update_layout(
            title="No data to display for this SKU",
            template='plotly_white'
        )
    
    ts_fig = px.line(
        ts_data, x='ds', y='y',
        title=f"Historical Sales for {sku_desc} (Monthly Sums)",
        markers=True, color_discrete_sequence=['#1f77b4']
    )
    ts_fig.update_layout(
        yaxis_tickformat=".2f",
        template='plotly_white',
        xaxis_title="Date",
        yaxis_title="Shipped Lb"
    )
    return ts_fig

def create_top_products_graph(filtered_df, metric):
    product_data = filtered_df.groupby(['SKU', 'Description'])[metric].sum().nlargest(10).reset_index()
    product_data['SKU'] = product_data['SKU'].astype(str).str.replace(r'\.', '', regex=True)
    product_data = product_data.sort_values(metric, ascending=False)
    fig = px.bar(
        product_data, x='SKU', y=metric,
        title=f"Top 10 Products by {metric}",
        color='SKU', custom_data=['Description']
    )
    fig.update_traces(
        hovertemplate='<b>SKU</b>: %{x}<br><b>' + metric + ':</b> %{y:.2f}<br><b>Description</b>: %{customdata[0]}'
    )
    fig.update_layout(
        xaxis_tickangle=45, yaxis_tickformat=".2f",
        template='plotly_white', xaxis_title="SKU", yaxis_title=metric,
        showlegend=False
    )
    return fig

def create_customer_leaderboard_graph(filtered_df, metric):
    customer_data = filtered_df.groupby('CustomerName')[metric].sum().nlargest(10).reset_index()
    fig = px.bar(
        customer_data, x='CustomerName', y=metric,
        title=f"Top 10 Customers by {metric}",
        color_discrete_sequence=['#ff7f0e']
    )
    fig.update_layout(
        yaxis_tickformat=".2f", template='plotly_white',
        xaxis_title="Customer", yaxis_title=metric, xaxis_tickangle=45
    )
    return fig

def create_top_reps_graph(filtered_df, metric):
    rep_data = filtered_df.groupby('Rep')[metric].sum().nlargest(10).reset_index()
    fig = px.bar(
        rep_data, x='Rep', y=metric,
        title=f"Top 10 Reps by {metric}",
        color_discrete_sequence=['#2ca02c']
    )
    fig.update_layout(
        yaxis_tickformat=".2f", template='plotly_white',
        xaxis_title="Rep", yaxis_title=metric, xaxis_tickangle=45
    )
    return fig

def create_top_shipping_methods_graph(filtered_df, metric):
    ship_data = filtered_df.groupby('ShippingMethodRequested')[metric].sum().nlargest(10).reset_index()
    fig = px.bar(
        ship_data, x='ShippingMethodRequested', y=metric,
        title=f"Top 10 Shipping Methods by {metric}",
        color_discrete_sequence=['#d62728']
    )
    fig.update_layout(
        yaxis_tickformat=".2f", template='plotly_white',
        xaxis_title="Shipping Method", yaxis_title=metric, xaxis_tickangle=45
    )
    return fig

def create_region_trend_graph(filtered_df, metric, selected_regions):
    region_data = filtered_df.groupby([pd.Grouper(key='DateExpected', freq='M'), 'RegionName'])[metric].sum().reset_index()
    region_data['Smoothed'] = region_data.groupby('RegionName')[metric].transform(lambda x: x.rolling(3, min_periods=1).mean())
    if selected_regions == 'ALL':
        top_regions = region_data.groupby('RegionName')[metric].sum().nlargest(5).index.tolist()
    else:
        top_regions = selected_regions
    region_data = region_data[region_data['RegionName'].isin(top_regions)]
    fig = px.line(
        region_data, x='DateExpected', y='Smoothed', color='RegionName',
        title=f"Region Trend by {metric} (Top 5 Regions, Smoothed)",
        markers=True, color_discrete_sequence=px.colors.qualitative.Pastel
    )
    for region in top_regions:
        region_subset = region_data[region_data['RegionName'] == region]
        mean_val = region_subset['Smoothed'].mean()
        std_val = region_subset['Smoothed'].std()
        threshold = mean_val + 2 * std_val
        peaks = region_subset[region_subset['Smoothed'] > threshold]
        for _, peak in peaks.iterrows():
            fig.add_annotation(
                x=peak['DateExpected'], y=peak['Smoothed'],
                text="Peak", showarrow=True, arrowhead=1, ax=20, ay=-30
            )
    fig.update_traces(
        hovertemplate="<b>Region</b>: %{fullData.name}<br><b>Date</b>: %{x}<br><b>" + metric + ":</b> %{y:.2f}"
    )
    fig.update_layout(
        yaxis_tickformat=".2f", template='plotly_white',
        xaxis_title="Date", yaxis_title=metric,
        xaxis_rangeslider_visible=True, legend_title_text='Region',
        legend=dict(yanchor="top", y=1.2, xanchor="left", x=0, orientation="h")
    )
    return fig

def create_top_skus_by_region_graph(filtered_df, metric):
    region_sku_data = filtered_df.groupby(['RegionName', 'SKU_Desc'])[metric].sum().reset_index()
    region_totals = region_sku_data.groupby('RegionName')[metric].sum().nlargest(20).index
    region_sku_data = region_sku_data[region_sku_data['RegionName'].isin(region_totals)]
    sku_totals = region_sku_data.groupby('SKU_Desc')[metric].sum().nlargest(10).index
    region_sku_data = region_sku_data[region_sku_data['SKU_Desc'].isin(sku_totals)]
    
    top_region_sku = region_sku_data.groupby('RegionName').apply(lambda x: x.nlargest(3, metric)).reset_index(drop=True)
    top_region_sku['DisplaySKU'] = top_region_sku['SKU_Desc'].apply(lambda x: x if len(x) <= 20 else x[:17] + '...')
    top_region_sku['DisplayRegion'] = top_region_sku['RegionName'].apply(lambda x: x if len(x) <= 15 else x[:12] + '...')
    
    fig = px.bar(
        top_region_sku, 
        x='DisplayRegion', 
        y=metric, 
        color='DisplaySKU',
        title=f"Top 3 SKUs by Region ({metric}) - Top 20 Regions, Top 3 SKUs (Stacked)",
        custom_data=['SKU_Desc', 'RegionName'],
        barmode='stack',
        color_discrete_sequence=px.colors.qualitative.Bold
    )
    fig.update_traces(
        hovertemplate=(
            "<b>Region</b>: %{customdata[1]}<br>"
            "<b>SKU</b>: %{customdata[0]}<br>"
            "<b>" + metric + "</b>: %{y:.2f}<br>"
            "<extra></extra>"
        ),
        opacity=1.0
    )
    fig.update_layout(
        autosize=True,
        margin=dict(l=50, r=50, t=50, b=50),
        template='plotly_white',
        xaxis_title="Region",
        yaxis_title=metric,
        xaxis_tickangle=45,
        legend=dict(
            title="SKU (Click to Filter)",
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.02,
            bgcolor="rgba(255, 255, 255, 0.8)",
            bordercolor="gray",
            borderwidth=1,
            font=dict(size=10),
            tracegroupgap=5
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(200, 200, 200, 0.5)",
            automargin=True
        ),
        xaxis=dict(
            showgrid=False,
            automargin=True
        ),
        title=dict(
            x=0.5,
            font=dict(size=16, color="#333", family="Arial")
        ),
        font=dict(size=12, color="#333", family="Arial")
    )
    fig.update_traces(
        selector=dict(type='bar'),
        showlegend=True,
        legendgroup='DisplaySKU'
    )
    return fig

def create_region_contribution_graph(filtered_df, metric):
    region_contrib = filtered_df.groupby('RegionName')[metric].sum().reset_index().sort_values(by=metric, ascending=False)
    top_10 = region_contrib.head(10).copy()
    others = region_contrib.iloc[10:].copy()
    if len(others) > 0:
        others_val = others[metric].sum()
        top_10 = pd.concat([top_10, pd.DataFrame({'RegionName': ['Others'], metric: [others_val]})], ignore_index=True)
    
    fig = px.pie(
        top_10,
        names='RegionName',
        values=metric,
        title=f"Region Contribution to {metric}",
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    fig.update_traces(
        hovertemplate='%{label}: %{value} (%{percent})',
        textinfo='label+percent'
    )
    fig.update_layout(
        template='plotly_white',
        legend_title_text='Region',
        margin=dict(l=50, r=50, t=50, b=50)
    )
    return fig

def create_yoy_growth_graph(filtered_df, group_col, metric, title,
                            pos_color='#2ca02c', neg_color='#d62728',
                            clip_lower=-200, clip_upper=200):
    yoy_data = compute_yoy_growth(filtered_df, group_col, metric)
    if group_col == 'SKU':
        yoy_data = yoy_data.nlargest(10, 'YoY_Growth')
    elif group_col == 'CustomerName':
        yoy_data = yoy_data.nlargest(25, 'YoY_Growth')
    
    yoy_data = yoy_data.sort_values('YoY_Growth', ascending=False).reset_index(drop=True)
    if yoy_data.empty:
        return go.Figure().update_layout(title=f"No YoY Growth Data for {title}", template='plotly_white')
    
    yoy_data['YoY_Growth'] = np.clip(yoy_data['YoY_Growth'], clip_lower, clip_upper)
    yoy_data['ShortLabel'] = yoy_data[group_col].apply(lambda x: x if len(str(x)) <= 12 else str(x)[:9] + '...')
    yoy_data['BarColor'] = yoy_data['YoY_Growth'].apply(lambda val: pos_color if val > 0 else neg_color if val < 0 else '#7f7f7f')
    
    fig = go.Figure([
        go.Bar(
            x=yoy_data['ShortLabel'],
            y=yoy_data['YoY_Growth'],
            marker_color=yoy_data['BarColor'],
            customdata=yoy_data[[group_col]],
            hovertemplate=f"<b>%{{customdata[0]}}</b><br>YoY Growth: %{{y:.2f}}%<extra></extra>"
        )
    ])
    fig.add_shape(
        type="line",
        x0=-0.5, x1=len(yoy_data)-0.5,
        y0=0, y1=0,
        line=dict(color="black", dash="dash"),
        xref='x', yref='y'
    )
    yoy_mean = yoy_data['YoY_Growth'].mean()
    fig.add_shape(
        type="line",
        xref='paper', yref='y',
        x0=0, x1=1,
        y0=yoy_mean, y1=yoy_mean,
        line=dict(color='blue', dash='dash')
    )
    fig.add_annotation(
        x=1, y=yoy_mean,
        xref='paper', yref='y',
        text=f"Avg {yoy_mean:.2f}%",
        showarrow=False,
        font=dict(color='blue')
    )
    fig.update_layout(
        title=title,
        template='plotly_white',
        xaxis_title=group_col,
        yaxis_title="YoY Growth (%)",
        xaxis_tickangle=45,
        bargap=0.3,
        margin=dict(l=50, r=50, t=80, b=50),
        showlegend=False
    )
    fig.update_yaxes(tickformat=".2f")
    fig.update_traces(texttemplate='%{y:.2f}%', textposition='outside')
    return fig

def create_trend_graph(filtered_df, group_col, metric, title):
    trend_data = (filtered_df
                  .groupby([pd.Grouper(key='DateExpected', freq='M'), group_col])[metric]
                  .sum().reset_index().sort_values('DateExpected'))
    top_groups = trend_data.groupby(group_col)[metric].sum().nlargest(5).index.tolist()
    trend_data = trend_data[trend_data[group_col].isin(top_groups)].copy()
    trend_data['Smoothed'] = trend_data.groupby(group_col)[metric].transform(lambda x: x.rolling(3, min_periods=1).sum())
    trend_data['DateStr'] = trend_data['DateExpected'].dt.strftime('%Y-%m-%d')
    trend_data['hover_text'] = trend_data.apply(lambda row: f"<b>{row[group_col]}</b><br>Date: {row['DateStr']}<br>Smoothed {metric}: {row['Smoothed']:.2f}<br>Raw {metric}: {row[metric]:.2f}", axis=1)
    
    fig = px.line(
        trend_data,
        x='DateExpected',
        y='Smoothed',
        color=group_col,
        title=title,
        markers=False,
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    for trace in fig.data:
        group_name = trace.name
        subset = trend_data[trend_data[group_col] == group_name]
        trace.text = subset['hover_text']
        trace.hovertemplate = "%{text}<extra></extra>"
    
    fig.update_layout(
        yaxis_tickformat=".2f",
        template='plotly_white',
        xaxis_title="Date",
        yaxis_title=metric,
        xaxis_rangeslider_visible=True
    )
    return fig

def create_seasonality_graph(filtered_df, metric):
    month_map = {1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'}
    seasonality_data = filtered_df.copy()
    seasonality_data['Month'] = seasonality_data['DateExpected'].dt.month
    monthly_averages = seasonality_data.groupby('Month')[metric].sum().reset_index()
    monthly_averages['MonthName'] = monthly_averages['Month'].map(month_map)
    
    fig = px.line(
        monthly_averages,
        x='MonthName',
        y=metric,
        title="Average Monthly Seasonality",
        markers=True,
        color_discrete_sequence=['#1f77b4']
    )
    fig.update_traces(
        line=dict(width=3),
        marker=dict(size=8),
        hovertemplate="Month: %{x}<br>Avg: %{y:.2f}<extra></extra>"
    )
    overall_avg = monthly_averages[metric].mean()
    fig.add_shape(
        type="line",
        xref="paper", yref="y",
        x0=0, x1=1,
        y0=overall_avg, y1=overall_avg,
        line=dict(color="red", dash="dash"),
        name="Overall Avg"
    )
    min_idx = monthly_averages[metric].idxmin()
    max_idx = monthly_averages[metric].idxmax()
    min_month = monthly_averages.loc[min_idx, 'MonthName']
    max_month = monthly_averages.loc[max_idx, 'MonthName']
    min_value = monthly_averages.loc[min_idx, metric]
    max_value = monthly_averages.loc[max_idx, metric]
    fig.add_annotation(x=min_month, y=min_value, text=f"Min: {min_value:.2f}", showarrow=True, arrowhead=1, ax=20, ay=-30, arrowcolor="#d62728", font=dict(color="#d62728"))
    fig.add_annotation(x=max_month, y=max_value, text=f"Max: {max_value:.2f}", showarrow=True, arrowhead=1, ax=20, ay=-30, arrowcolor="#2ca02c", font=dict(color="#2ca02c"))
    fig.update_layout(
        yaxis_tickformat=".2f",
        template='plotly_white',
        xaxis_title="Month",
        yaxis_title=f"Average {metric}",
        margin=dict(l=60, r=40, t=80, b=60)
    )
    return fig

def create_profit_margin_graph(filtered_df):
    profit_margin_sku = filtered_df.groupby('SKU')['ProfitMargin'].mean().reset_index()
    profit_margin_sku = profit_margin_sku.nlargest(10, 'ProfitMargin')
    profit_margin_sku = profit_margin_sku.sort_values('ProfitMargin', ascending=False)
    
    fig = px.bar(
        profit_margin_sku,
        x='SKU', 
        y='ProfitMargin',
        title="Top 10 SKUs by Profit Margin",
        color='ProfitMargin',
        color_continuous_scale=['#e8e0f2', '#9467bd'],
        text='ProfitMargin'
    )
    fig.update_traces(
        hovertemplate='SKU: %{x}<br>Margin: %{y:.1%}<extra></extra>',
        texttemplate='%{text:.1%}',
        textposition='outside'
    )
    overall_margin = filtered_df['ProfitMargin'].mean()
    fig.add_shape(
        type='line',
        xref='paper', yref='y',
        x0=0, x1=1,
        y0=overall_margin, y1=overall_margin,
        line=dict(color='red', dash='dash')
    )
    fig.add_annotation(
        x=1, y=overall_margin,
        xref='paper', yref='y',
        text=f"Avg {overall_margin:.1%}",
        showarrow=False,
        font=dict(color='red')
    )
    fig.update_layout(
        coloraxis_showscale=False,
        template='plotly_white',
        xaxis_title="SKU",
        yaxis_title="Profit Margin",
        xaxis_tickangle=45,
        margin=dict(l=60, r=60, t=80, b=60)
    )
    fig.update_yaxes(tickformat=".1%")
    return fig

def create_yoy_profit_margin_graph(filtered_df):
    """
    Creates a bar graph that shows the Year-over-Year profit margin change.
    If the 'ProfitMargin' column is not present in filtered_df, it computes it using:
      ProfitMargin = (Rev - Cost) / Rev.
    """
    # Work on a copy so as not to alter the original DataFrame.
    df_year = filtered_df.copy()

    # If ProfitMargin column does not exist, try to compute it from Rev and Cost.
    if 'ProfitMargin' not in df_year.columns:
        if 'Rev' in df_year.columns and 'Cost' in df_year.columns:
            df_year['ProfitMargin'] = (df_year['Rev'] - df_year['Cost']) / df_year['Rev'].replace(0, np.nan)
        else:
            df_year['ProfitMargin'] = np.nan

    # Ensure the DateExpected column is datetime and then extract the year.
    if not pd.api.types.is_datetime64_any_dtype(df_year['DateExpected']):
        df_year['DateExpected'] = pd.to_datetime(df_year['DateExpected'])
    df_year['Year'] = df_year['DateExpected'].dt.year

    # Group by Year and compute the mean profit margin.
    yearly_pm = df_year.groupby('Year')['ProfitMargin'].mean().reset_index().sort_values('Year')

    # Compute YoY percentage change.
    yearly_pm['YoY_PM'] = yearly_pm['ProfitMargin'].pct_change() * 100
    # Drop first row (or any rows with NaN in YoY_PM)
    yearly_pm = yearly_pm.dropna(subset=['YoY_PM'])

    if yearly_pm.empty:
        return go.Figure().update_layout(title="Insufficient Profit Margin Data", template='plotly_white')

    # Create a bar graph using Plotly Express.
    fig = px.bar(yearly_pm, x='Year', y='YoY_PM', title="YoY Profit Margin Change (%)",
                 color='YoY_PM', color_continuous_scale=['red', 'green'])
    fig.update_traces(
        hovertemplate="Year: %{x}<br>YoY Profit Margin Change: %{y:.2f}%<extra></extra>",
        texttemplate='%{y:.1f}%', textposition='outside'
    )
    fig.update_layout(
        template='plotly_white',
        xaxis_title="Year",
        yaxis_title="Profit Margin Change (%)",
        yaxis_tickformat=".2f"
    )

    return fig