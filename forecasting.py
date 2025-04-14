# forecasting.py
from functools import lru_cache
import pandas as pd
from prophet import Prophet
import plotly.graph_objects as go
from data_processing import monthly_sales

@lru_cache(maxsize=128)
def cached_forecast(sku_desc, periods, interval_width=0.95):
    """
    Optimized forecasting function that produces realistic forecast values
    using raw monthly sums from the global monthly_sales.
    
    - Uses multiplicative seasonality for SKUs with sufficient data.
    - Adjusts Prophet parameters for better trend and seasonality capture.
    - interval_width sets the confidence interval for forecast uncertainty (default 95%).
    
    Returns a DataFrame with forecast columns: yhat, yhat_lower, and yhat_upper.
    """
    sku_df = monthly_sales[monthly_sales['SKU_Desc'] == sku_desc][['ds', 'y']].copy()
    sku_df = sku_df[sku_df['y'] > 0].sort_values('ds')

    # Handle SKUs with fewer than 2 data points
    if len(sku_df) < 2:
        future_dates = pd.date_range(start=sku_df['ds'].max(), periods=periods+1, freq='M')[1:]
        print(f"[DEBUG] Not enough data for {sku_desc}. Returning zeros for forecast.")
        return pd.DataFrame({
            'ds': future_dates,
            'yhat': [0] * periods,
            'yhat_lower': [0] * periods,
            'yhat_upper': [0] * periods
        }).set_index('ds')

    # Handle short history (2-6 data points) with a simple trend extrapolation
    if len(sku_df) <= 6:
        if len(sku_df) >= 2:
            last_two = sku_df.tail(2)
            trend_slope = last_two['y'].iloc[-1] - last_two['y'].iloc[-2]  # Monthly difference
            last_value = last_two['y'].iloc[-1]
            future_dates = pd.date_range(start=sku_df['ds'].max(), periods=periods+1, freq='M')[1:]
            forecast_values = [max(0, last_value + trend_slope * i) for i in range(1, periods+1)]
            print(f"[DEBUG] Short history for {sku_desc}. Using linear extrapolation with slope {trend_slope:.2f}.")
            return pd.DataFrame({
                'ds': future_dates,
                'yhat': forecast_values,
                'yhat_lower': forecast_values,  # No uncertainty for simple extrapolation
                'yhat_upper': forecast_values
            }).set_index('ds')
        else:
            last_value = sku_df['y'].iloc[-1]
            future_dates = pd.date_range(start=sku_df['ds'].max(), periods=periods+1, freq='M')[1:]
            print(f"[DEBUG] Only one data point for {sku_desc}. Repeating the last value for forecast.")
            return pd.DataFrame({
                'ds': future_dates,
                'yhat': [last_value] * periods,
                'yhat_lower': [last_value] * periods,
                'yhat_upper': [last_value] * periods
            }).set_index('ds')

    # Initialize Prophet model for SKUs with sufficient data.
    model = Prophet(
        seasonality_mode='multiplicative',  # Force multiplicative for better scaling
        yearly_seasonality=len(sku_df) >= 12,
        weekly_seasonality=False,
        daily_seasonality=False,
        changepoint_prior_scale=0.8,          # More flexible trend changes
        seasonality_prior_scale=15.0,         # Stronger seasonality effects
        growth='linear',
        interval_width=interval_width         # Set custom uncertainty interval (e.g., 0.95 for 95%)
    )
    # Add monthly seasonality
    model.add_seasonality(name='monthly', period=30.5, fourier_order=5)

    sku_df['floor'] = 0
    model.fit(sku_df)
    
    # Generate future dates from the last historical date
    future = model.make_future_dataframe(periods=periods, freq='M', include_history=False)
    future['floor'] = 0
    forecast = model.predict(future)

    # Ensure non-negative forecasts
    forecast['yhat'] = forecast['yhat'].clip(lower=0)
    forecast['yhat_lower'] = forecast['yhat_lower'].clip(lower=0)
    forecast['yhat_upper'] = forecast['yhat_upper'].clip(lower=0)

    # Debug: Print forecast sample with upper and lower intervals
    print(f"[DEBUG] Forecast for {sku_desc} (first 5 rows):")
    print(forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].head())
    
    return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].set_index('ds')

def create_forecast_graph(sku_desc, months_ahead):
    """
    Generates a Plotly graph displaying the forecast (yhat) along with its confidence interval
    (using yhat_lower and yhat_upper) from the Prophet forecast.
    """
    forecast_fig = go.Figure()

    # If 'ALL', user hasn't picked a specific SKU -> return an empty figure.
    if sku_desc == 'ALL':
        forecast_fig.update_layout(
            title="Select a SKU to show forecast",
            template='plotly_white'
        )
        return forecast_fig

    # Ensure there is forecast data for the selected SKU.
    forecast_data = monthly_sales[monthly_sales['SKU_Desc'] == sku_desc].copy().sort_values('ds')
    if forecast_data.empty:
        forecast_fig.update_layout(
            title="No data for selected SKU",
            template='plotly_white'
        )
        return forecast_fig

    # Generate forecast via the cached_forecast function
    forecast = cached_forecast(sku_desc, months_ahead)
    forecast = forecast.head(months_ahead)

    # Plot the upper bound trace (invisible line) to use for area filling.
    forecast_fig.add_trace(go.Scatter(
        x=forecast.index,
        y=forecast['yhat_upper'],
        mode='lines',
        line=dict(color='rgba(255,127,14,0)'),  # Invisible
        hoverinfo='skip',
        showlegend=False,
        name='Upper Bound'
    ))

    # Plot the lower bound trace with fill set to 'tonexty' to fill the area between lower and upper bounds.
    forecast_fig.add_trace(go.Scatter(
        x=forecast.index,
        y=forecast['yhat_lower'],
        mode='lines',
        line=dict(color='rgba(255,127,14,0)'),  # Invisible
        fill='tonexty',  # Fill area to previous trace
        fillcolor='rgba(255,127,14,0.2)',     # Semi-transparent fill
        hoverinfo='skip',
        showlegend=True,
        name='Confidence Interval'
    ))

    # Plot the main forecast (yhat) as a line with markers.
    forecast_fig.add_trace(go.Scatter(
        x=forecast.index,
        y=forecast['yhat'],
        mode='lines+markers',
        line=dict(color='#ff7f0e', shape='spline'),
        name='Forecast'
    ))

    # Update layout settings
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
