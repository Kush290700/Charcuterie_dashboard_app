# app.py
from dash import Dash, dcc, html, Input, Output
import plotly.graph_objects as go
import pandas as pd

# Import modules
from data_processing import df, monthly_sales, available_skus, available_years, available_months, available_regions
from forecasting import cached_forecast
from visualizations import (
    create_forecast_graph,
    create_historical_ts_graph,
    create_top_products_graph,
    create_customer_leaderboard_graph,
    create_top_reps_graph,
    create_top_shipping_methods_graph,
    create_region_trend_graph,
    create_top_skus_by_region_graph,
    create_region_contribution_graph,
    create_yoy_growth_graph,
    create_trend_graph,
    create_seasonality_graph,
    create_profit_margin_graph,
    create_yoy_profit_margin_graph
)

# ------------------ INITIALIZE DASH APP ------------------
app = Dash(__name__)
server = app.server

app.layout = html.Div([
    html.H1("🔮 Charcuterie Forecasting & Performance Dashboard",
            style={'textAlign': 'center', 'color': '#333', 'marginBottom': '10px'}),
    
    html.Div([
        # Control Panel
        html.Div([
            html.Label("Select SKU - Description:", style={'fontWeight': 'bold'}),
            dcc.Dropdown(
                id='sku-dropdown',
                options=[{'label': 'Select All', 'value': 'ALL'}] + [{'label': s, 'value': s} for s in available_skus],
                value='ALL',
                style={'marginBottom': '15px'}
            ),
            html.Label("Forecast Period (months):", style={'fontWeight': 'bold'}),
            html.Div(
                dcc.Slider(
                    id='month-slider',
                    min=1,
                    max=12,
                    step=1,
                    value=6,
                    marks={i: str(i) for i in range(1, 13)},
                    tooltip={"placement": "bottom", "always_visible": True}
                ),
                style={'marginBottom': '20px'}
            ),
            html.Label("Select Years:", style={'fontWeight': 'bold'}),
            dcc.Dropdown(
                id='year-dropdown',
                options=[{'label': 'Select All', 'value': 'ALL'}] + [{'label': str(y), 'value': y} for y in available_years],
                value='ALL',
                multi=True,
                style={'marginBottom': '15px'}
            ),
            html.Label("Select Months:", style={'fontWeight': 'bold'}),
            dcc.Dropdown(
                id='month-dropdown',
                options=[{'label': 'Select All', 'value': 'ALL'}] + [{'label': str(m), 'value': m} for m in available_months],
                value='ALL',
                multi=True,
                style={'marginBottom': '15px'}
            ),
            html.Label("Metric:", style={'fontWeight': 'bold'}),
            dcc.Dropdown(
                id='metric-dropdown',
                options=[
                    {'label': 'Shipped Lb', 'value': 'ShippedLb'},
                    {'label': 'Revenue', 'value': 'Rev'},
                    {'label': 'Cost', 'value': 'Cost'},
                    {'label': 'Base Price', 'value': 'Base'},
                    {'label': 'Profit Margin', 'value': 'ProfitMargin'}
                ],
                value='ShippedLb',
                style={'marginBottom': '15px'}
            ),
            html.Label("Select Regions for Trend:", style={'fontWeight': 'bold'}),
            dcc.Dropdown(
                id='region-dropdown',
                options=[{'label': 'Select All', 'value': 'ALL'}] + [{'label': r, 'value': r} for r in available_regions],
                value='ALL',
                multi=True,
                style={'marginBottom': '15px'}
            )
        ], style={'width': '28%', 'padding': '20px', 'backgroundColor': '#f9f9f9', 'margin': '10px'}),
        
        # Graphs Section
        html.Div([
            # Forecasting Section
            html.Div([
                html.H2("Forecasting", style={'color': '#555', 'marginBottom': '5px'}),
                dcc.Graph(id='forecast-graph', style={'height': '400px'}),
                dcc.Graph(id='historical-ts-graph', style={'height': '400px'})
            ], style={'marginBottom': '20px'}),
            
            # Performance Analysis Section
            html.Div([
                html.H2("Performance Analysis", style={'color': '#555', 'marginBottom': '5px'}),
                dcc.Graph(id='eda-top-products', style={'height': '400px'}),
                dcc.Graph(id='eda-customer-leaderboard', style={'height': '400px'}),
                dcc.Graph(id='top-reps', style={'height': '400px'}),
                dcc.Graph(id='top-shipping-methods', style={'height': '400px'})
            ], style={'marginBottom': '20px'}),
            
            # Regional Analysis Section
            html.Div([
                html.H2("Regional Analysis", style={'color': '#555', 'marginBottom': '5px'}),
                dcc.Graph(id='eda-region-trend', style={'height': '400px'}),
                dcc.Graph(id='top-skus-by-region', style={'height': '400px'}),
                dcc.Graph(id='region-contribution', style={'height': '400px'}),
                dcc.Graph(id='yoy-growth-region', style={'height': '400px'})
            ], style={'marginBottom': '20px'}),
            
            # Year-over-Year & Time-Based Trends Section
            html.Div([
                html.H2("Year-over-Year Growth", style={'color': '#555', 'marginBottom': '5px'}),
                dcc.Graph(id='yoy-growth-rep', style={'width': '100%', 'height': '400px', 'marginBottom': '20px'}),
                dcc.Graph(id='yoy-growth-customer', style={'width': '100%', 'height': '400px', 'marginBottom': '30px'}),
                dcc.Graph(id='yoy-growth-sku', style={'width': '100%', 'height': '450px'}),
                dcc.Graph(id='yoy-profit-margin', style={'width': '100%', 'height': '450px', 'marginBottom': '30px'}),
                
                html.H2("Time-Based Trends", style={'color': '#555', 'marginBottom': '5px'}),
                html.Div([
                    dcc.Graph(id='rep-trend', style={'display': 'inline-block', 'width': '50%', 'height': '400px'}),
                    dcc.Graph(id='customer-trend', style={'display': 'inline-block', 'width': '50%', 'height': '400px'})
                ], style={'marginBottom': '20px'}),
                html.Div([
                    dcc.Graph(id='seasonality', style={'display': 'inline-block', 'width': '50%', 'height': '400px'}),
                    dcc.Graph(id='profit-margin-sku', style={'display': 'inline-block', 'width': '50%', 'height': '400px'})
                ])
            ])
        ], style={'width': '70%', 'padding': '20px', 'margin': '10px'})
    ], style={'display': 'flex', 'flexWrap': 'wrap', 'justifyContent': 'center'})
])

# ------------------ CALLBACK UPDATE ------------------
@app.callback(
    [
        Output('forecast-graph', 'figure'),
        Output('historical-ts-graph', 'figure'),
        Output('eda-top-products', 'figure'),
        Output('eda-customer-leaderboard', 'figure'),
        Output('top-reps', 'figure'),
        Output('top-shipping-methods', 'figure'),
        Output('eda-region-trend', 'figure'),
        Output('top-skus-by-region', 'figure'),
        Output('region-contribution', 'figure'),
        Output('yoy-growth-region', 'figure'),
        Output('yoy-profit-margin', 'figure'),
        Output('yoy-growth-rep', 'figure'),
        Output('yoy-growth-customer', 'figure'),
        Output('yoy-growth-sku', 'figure'),
        Output('rep-trend', 'figure'),
        Output('customer-trend', 'figure'),
        Output('seasonality', 'figure'),
        Output('profit-margin-sku', 'figure')
    ],
    [
        Input('sku-dropdown', 'value'),
        Input('month-slider', 'value'),
        Input('year-dropdown', 'value'),
        Input('month-dropdown', 'value'),
        Input('metric-dropdown', 'value'),
        Input('region-dropdown', 'value')
    ]
)
def update_dashboard(sku_desc, months_ahead, selected_years, selected_months, metric, selected_regions):
    filtered_df = df.copy()
    
    # Apply Year/Month filters
    if selected_years != 'ALL':
        if isinstance(selected_years, list):
            filtered_df = filtered_df[filtered_df['DateExpected'].dt.year.isin(selected_years)]
        else:
            filtered_df = filtered_df[filtered_df['DateExpected'].dt.year == selected_years]
    if selected_months != 'ALL':
        if isinstance(selected_months, list):
            filtered_df = filtered_df[filtered_df['DateExpected'].dt.month.isin(selected_months)]
        else:
            filtered_df = filtered_df[filtered_df['DateExpected'].dt.month == selected_months]
    
    # Filter by SKU if a specific SKU is selected
    if sku_desc != 'ALL':
        filtered_df = filtered_df[filtered_df['SKU_Desc'] == sku_desc]

    # Create visualizations
    forecast_fig = create_forecast_graph(sku_desc, months_ahead, cached_forecast)
    ts_fig = create_historical_ts_graph(sku_desc)
    fig_top = create_top_products_graph(filtered_df, metric)
    fig_cust = create_customer_leaderboard_graph(filtered_df, metric)
    fig_rep = create_top_reps_graph(filtered_df, metric)
    fig_ship = create_top_shipping_methods_graph(filtered_df, metric)
    fig_region = create_region_trend_graph(filtered_df, metric, selected_regions)
    fig_region_sku = create_top_skus_by_region_graph(filtered_df, metric)
    fig_region_contrib = create_region_contribution_graph(filtered_df, metric)
    fig_yoy_region = create_yoy_growth_graph(filtered_df, 'RegionName', metric, "YoY Growth by Region (%)", '#1f77b4')
    fig_yoy_profit_margin = create_yoy_profit_margin_graph(filtered_df)
    fig_yoy_rep = create_yoy_growth_graph(filtered_df, 'Rep', metric, "YoY Growth by Rep (%)", '#2ca02c')
    fig_yoy_customer = create_yoy_growth_graph(filtered_df, 'CustomerName', metric, "YoY Growth by Customer (%)", '#ff7f0e')
    fig_yoy_sku = create_yoy_growth_graph(filtered_df, 'SKU', metric, "YoY Growth by SKU (Top 10, %)", '#9467bd')
    fig_rep_trend = create_trend_graph(filtered_df, 'Rep', metric, "Trend by Rep (Top 5)")
    fig_customer_trend = create_trend_graph(filtered_df, 'CustomerName', metric, "Trend by Customer (Top 5)")
    fig_seasonality = create_seasonality_graph(filtered_df, metric)
    fig_profit_margin = create_profit_margin_graph(filtered_df)

    return (
        forecast_fig,
        ts_fig,
        fig_top,
        fig_cust,
        fig_rep,
        fig_ship,
        fig_region,
        fig_region_sku,
        fig_region_contrib,
        fig_yoy_region,
        fig_yoy_profit_margin,
        fig_yoy_rep,
        fig_yoy_customer,
        fig_yoy_sku,
        fig_rep_trend,
        fig_customer_trend,
        fig_seasonality,
        fig_profit_margin
    )

# ------------------ RUN APP ------------------
if __name__ == '__main__':
    app.run(debug=True)
