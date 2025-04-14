# sql_data.py
import os
import pandas as pd
from sqlalchemy import create_engine

def fetch_live_data():
    """
    Connects to the live SQL Server and fetches data from multiple tables.
    Returns a dictionary of DataFrames.
    """
    # Read connection parameters from environment variables
    server = os.environ.get("SQL_SERVER", "10.4.21.5")
    database = os.environ.get("SQL_DATABASE", "TRSM")
    username = os.environ.get("SQL_USERNAME", "TRSMAna")
    password = os.environ.get("SQL_PASSWORD", "chattypostgraduatecanary")

    # Create connection string for MSSQL with pyodbc
    connection_string = f"mssql+pyodbc://{username}:{password}@{server}/{database}?driver=ODBC+Driver+17+for+SQL+Server"
    engine = create_engine(connection_string)

    # Define SQL queries
    # Note: orders are filtered to have OrderStatus = 'packed', matching your sample.
    batches_query = "SELECT * FROM dbo.Batches WHERE CreatedAt >= '2020-01-01' AND CreatedAt <= GETDATE();"
    customers_query = "SELECT * FROM dbo.Customers WHERE CreatedAt >= '2020-01-01' AND CreatedAt <= GETDATE();"
    order_lines_query = "SELECT * FROM dbo.OrderLines WHERE CreatedAt >= '2020-01-01' AND CreatedAt <= GETDATE();"
    orders_query = ("SELECT * FROM dbo.Orders WHERE OrderStatus = 'packed' " 
                    "AND CreatedAt >= '2020-01-01' AND CreatedAt <= GETDATE();")
    packs_query = "SELECT * FROM dbo.Packs WHERE CreatedAt >= '2020-01-01' AND CreatedAt <= GETDATE();"
    products_query = "SELECT * FROM dbo.Products WHERE CreatedAt >= '2020-01-01' AND CreatedAt <= GETDATE();"
    purchase_order_lines_query = "SELECT * FROM dbo.PurchaseOrderLines WHERE CreatedAt >= '2020-01-01' AND CreatedAt <= GETDATE();"
    purchase_orders_query = "SELECT * FROM dbo.PurchaseOrders WHERE CreatedAt >= '2020-01-01' AND CreatedAt <= GETDATE();"
    regions_query = "SELECT * FROM dbo.Regions WHERE CreatedAt >= '2020-01-01' AND CreatedAt <= GETDATE();"
    shippers_query = "SELECT * FROM dbo.Shippers WHERE CreatedAt >= '2020-01-01' AND CreatedAt <= GETDATE();"
    shipping_methods_query = "SELECT * FROM dbo.ShippingMethods WHERE CreatedAt >= '2020-01-01' AND CreatedAt <= GETDATE();"
    suppliers_query = "SELECT * FROM dbo.Suppliers WHERE CreatedAt >= '2020-01-01' AND CreatedAt <= GETDATE();"
    units_of_measure_query = "SELECT * FROM dbo.UnitsOfMeasure"

    # Load data into DataFrames
    batches_data = pd.read_sql(batches_query, engine)
    customers_data = pd.read_sql(customers_query, engine)
    order_lines_data = pd.read_sql(order_lines_query, engine)
    orders_data = pd.read_sql(orders_query, engine)
    packs_data = pd.read_sql(packs_query, engine)
    products_data = pd.read_sql(products_query, engine)
    purchase_order_lines_data = pd.read_sql(purchase_order_lines_query, engine)
    purchase_orders_data = pd.read_sql(purchase_orders_query, engine)
    regions_data = pd.read_sql(regions_query, engine)
    shippers_data = pd.read_sql(shippers_query, engine)
    shipping_methods_data = pd.read_sql(shipping_methods_query, engine)
    suppliers_data = pd.read_sql(suppliers_query, engine)
    units_of_measure_data = pd.read_sql(units_of_measure_query, engine)

    # Merge orders with customers to include customer information.
    orders_customers = pd.merge(orders_data, customers_data, on='CustomerId', how='inner')

    # Merge orders with order_lines to include product details.
    orders_customers_lines = pd.merge(orders_customers, order_lines_data, on='OrderId', how='inner')

    # Merge with products to get product price and cost details.
    full_data = pd.merge(orders_customers_lines, products_data, on='ProductId', how='inner',
                         suffixes=('_orderlines', '_products'))

    # Merge with regions for regional analysis.
    full_data_regions = pd.merge(full_data, regions_data, on='RegionId', how='left',
                                 suffixes=('_products', '_regions'))

    # Ensure ShipperId is string and merge with shippers.
    full_data_regions['ShipperId'] = full_data_regions['ShipperId'].astype(str)
    shippers_data['ShipperId'] = shippers_data['ShipperId'].astype(str)
    full_data_shipping = pd.merge(full_data_regions, shippers_data, on='ShipperId', how='left',
                                  suffixes=('_regions', '_shippers'))

    # Ensure shipping method identifiers are strings and merge with shipping methods.
    full_data_shipping['ShippingMethodRequested'] = full_data_shipping['ShippingMethodRequested'].astype(str)
    shipping_methods_data['ShippingMethodId'] = shipping_methods_data['ShippingMethodId'].astype(str)
    full_data_shipping = pd.merge(
        full_data_shipping,
        shipping_methods_data,
        left_on='ShippingMethodRequested',
        right_on='ShippingMethodId',
        how='left',
        suffixes=('_shippers', '_methods')
    )

    # Merge with suppliers for supplier analysis.
    full_data_suppliers = pd.merge(full_data_shipping, suppliers_data, on='SupplierId', how='left',
                                   suffixes=('_methods', '_suppliers'))

    # Prepare pack values and merge into order_lines_data.
    pack_values = packs_data.groupby('PickedForOrderLine').agg({
        'WeightLb': 'sum',
        'ItemCount': 'sum'
    }).reset_index()
    order_lines_data = pd.merge(order_lines_data, pack_values, left_on='OrderLineId',
                                right_on='PickedForOrderLine', how='left')
    order_lines_data = pd.merge(order_lines_data, products_data[['ProductId', 'UnitOfBillingId']],
                                on='ProductId', how='left')

    # Calculate total sales (revenue) based on UnitOfBillingId logic.
    def calculate_revenue(row):
        # Matches your SQL: if UnitOfBillingId equals 3, use WeightLb; otherwise, use ItemCount.
        if row['UnitOfBillingId'] == 3:
            return row['WeightLb'] * row['Price']
        else:
            return row['ItemCount'] * row['Price']
    order_lines_data['TotalSales'] = order_lines_data.apply(calculate_revenue, axis=1)

    # Calculate total cost similarly.
    def calculate_total_cost(row):
        if row['UnitOfBillingId'] == 3:
            return row['WeightLb'] * row['CostPrice']
        else:
            return row['ItemCount'] * row['CostPrice']
    order_lines_data['TotalCost'] = order_lines_data.apply(calculate_total_cost, axis=1)

    # Calculate profit for order_lines.
    order_lines_data['Profit'] = order_lines_data['TotalSales'] - order_lines_data['TotalCost']

    # Merge computed columns into full_data_suppliers based on OrderLineId (if present).
    if 'OrderLineId' in full_data_suppliers.columns and 'OrderLineId' in order_lines_data.columns:
        full_data_suppliers = pd.merge(full_data_suppliers,
                                       order_lines_data[['OrderLineId', 'TotalSales', 'TotalCost', 'Profit']],
                                       on='OrderLineId', how='left')

    return {
        "batches": batches_data,
        "customers": customers_data,
        "order_lines": order_lines_data,
        "orders": orders_data,
        "packs": packs_data,
        "products": products_data,
        "purchase_order_lines": purchase_order_lines_data,
        "purchase_orders": purchase_orders_data,
        "regions": regions_data,
        "shippers": shippers_data,
        "shipping_methods": shipping_methods_data,
        "suppliers": suppliers_data,
        "units_of_measure": units_of_measure_data,
        "full_data_suppliers": full_data_suppliers
    }
