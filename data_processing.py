import pandas as pd
import numpy as np
import warnings

warnings.filterwarnings("ignore")

def replace_zero_cost_with_average(df):
    """
    Replaces zero values in the 'Cost' column with the average cost for that SKU.
    If no non-zero cost exists for a given SKU, the value remains 0.
    Returns the updated DataFrame.
    """
    if 'Cost' in df.columns:
        avg_cost_per_sku = df.loc[df['Cost'] != 0].groupby('SKU')['Cost'].mean()
        df.loc[df['Cost'] == 0, 'Cost'] = df.loc[df['Cost'] == 0, 'SKU'].map(avg_cost_per_sku).fillna(0)
    return df

def load_and_clean_data(filepath):
    # Load the Excel file
    df = pd.read_excel(filepath)
    df['DateExpected'] = pd.to_datetime(df['DateExpected'])
    df = df[df['DateExpected'] >= '2020-01-01'].dropna(subset=['SKU', 'ShippedLb'])
    
    # Clip negative values in numerical columns
    numerical_cols = ['ShippedLb', 'Price', 'Rev', 'Cost', 'Base']
    for col in numerical_cols:
        df[col] = df[col].clip(lower=0)
    
    # Remove outliers using the IQR method
    def remove_outliers(df, column):
        Q1 = df[column].quantile(0.25)
        Q3 = df[column].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        return df[(df[column] >= lower_bound) & (df[column] <= upper_bound)]
    
    for col in numerical_cols:
        df = remove_outliers(df, col)
    
    # Keep only latest description for each SKU
    latest_desc = df.sort_values('DateExpected').groupby('SKU')['Description'].last().reset_index()
    df = df.drop(columns=['Description']).merge(latest_desc, on='SKU', how='left')
    
    # Clean the SKU column: Convert to float then int to remove decimals, then to string
    df['SKU'] = df['SKU'].astype(float).astype(int).astype(str)
    df['SKU_Desc'] = df['SKU'] + ' - ' + df['Description']
    
    # --- New function call: Replace 0 Cost with SKU's average Cost ---
    df = replace_zero_cost_with_average(df)
    
    # Compute Profit Margin
    df['ProfitMargin'] = (df['Rev'] - df['Cost']) / df['Rev'].replace(0, np.nan)
    
    return df

def compute_monthly_sales(df):
    """
    Precomputes monthly sales (using the sums across regions) and 
    renames columns to suit Prophet conventions.
    """
    monthly_sales = df.groupby([
        pd.Grouper(key='DateExpected', freq='M'),
        'SKU', 'SKU_Desc'
    ])[['ShippedLb', 'Rev', 'Cost', 'Base']].sum().reset_index()
    monthly_sales.rename(columns={'DateExpected': 'ds', 'ShippedLb': 'y'}, inplace=True)
    return monthly_sales

# ------------------ INITIAL LOAD ------------------
# Modify the path as needed
DATA_FILEPATH = r"C:\Users\Kush\Downloads\Sales_Charcuterie.xlsx"
df = load_and_clean_data(DATA_FILEPATH)
monthly_sales = compute_monthly_sales(df)

# Debug: Print historical data for a specific SKU
sku_to_debug = '58122113 - Charcuterie Coppa Fresh TRSM'
debug_data = monthly_sales[monthly_sales['SKU_Desc'] == sku_to_debug][['ds', 'y']].sort_values('ds')
print(f"Debug - Historical Data for {sku_to_debug}:\n", debug_data)

# Precompute valid SKUs having at least 2 data points (if needed)
valid_skus = monthly_sales.groupby('SKU_Desc').filter(lambda x: x['y'].count() >= 2)['SKU_Desc'].unique()

# Prepare filter options (to be imported in app.py later)
available_skus = sorted(df['SKU_Desc'].unique())
available_years = sorted(df['DateExpected'].dt.year.unique())
available_months = sorted(df['DateExpected'].dt.month.unique())
available_regions = sorted(df['RegionName'].unique())
