import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

# Set random seed for reproducible data
np.random.seed(42)
random.seed(42)

# Generate sample customer IDs for consistent merging
customer_ids = [f"CUST{str(i).zfill(4)}" for i in range(1001, 1051)]  # 50 customers

# Template 1: Sales Data Files
def create_sales_template_1():
    """Create sales data with columns: Customer_ID, Product, Quantity, Unit_Price, Sale_Date"""
    products = ['Laptop', 'Mouse', 'Keyboard', 'Monitor', 'Headphones', 'Webcam', 'Tablet', 'Phone']
    
    data = []
    for _ in range(30):  # 30 records per file
        customer_id = random.choice(customer_ids)
        product = random.choice(products)
        quantity = random.randint(1, 5)
        unit_price = round(random.uniform(50, 1500), 2)
        sale_date = datetime.now() - timedelta(days=random.randint(1, 365))
        
        data.append({
            'Customer_ID': customer_id,
            'Product': product,
            'Quantity': quantity,
            'Unit_Price': unit_price,
            'Sale_Date': sale_date.strftime('%Y-%m-%d')
        })
    
    return pd.DataFrame(data)

def create_sales_template_2():
    """Create sales data with slightly different product mix"""
    products = ['Desktop', 'Speaker', 'Printer', 'Scanner', 'Router', 'Camera', 'Smartwatch', 'Charger']
    
    data = []
    for _ in range(25):  # 25 records per file
        customer_id = random.choice(customer_ids)
        product = random.choice(products)
        quantity = random.randint(1, 3)
        unit_price = round(random.uniform(25, 800), 2)
        sale_date = datetime.now() - timedelta(days=random.randint(1, 180))
        
        data.append({
            'Customer_ID': customer_id,
            'Product': product,
            'Quantity': quantity,
            'Unit_Price': unit_price,
            'Sale_Date': sale_date.strftime('%Y-%m-%d')
        })
    
    return pd.DataFrame(data)

# Template 2: Customer Data Files
def create_customer_template_1():
    """Create customer data with columns: Customer_ID, Company_Name, Industry, Country, Registration_Date"""
    companies = ['Tech Solutions Inc', 'Digital Dynamics', 'Innovation Corp', 'Future Systems', 'Smart Tech Ltd',
                'Global Solutions', 'Advanced Computing', 'NextGen Technologies', 'Digital Pioneers', 'Tech Innovators']
    industries = ['Technology', 'Healthcare', 'Finance', 'Education', 'Manufacturing', 'Retail', 'Consulting']
    countries = ['USA', 'Canada', 'UK', 'Germany', 'France', 'Japan', 'Australia', 'Singapore']
    
    # Use first 25 customer IDs
    selected_customers = customer_ids[:25]
    
    data = []
    for customer_id in selected_customers:
        company = f"{random.choice(companies)} {random.randint(1, 999)}"
        industry = random.choice(industries)
        country = random.choice(countries)
        reg_date = datetime.now() - timedelta(days=random.randint(365, 1095))
        
        data.append({
            'Customer_ID': customer_id,
            'Company_Name': company,
            'Industry': industry,
            'Country': country,
            'Registration_Date': reg_date.strftime('%Y-%m-%d')
        })
    
    return pd.DataFrame(data)

def create_customer_template_2():
    """Create customer data for different set of customers"""
    companies = ['Business Partners', 'Enterprise Solutions', 'Corporate Services', 'Professional Systems',
                'Strategic Consulting', 'Optimal Performance', 'Excellence Group', 'Premier Solutions']
    industries = ['Telecommunications', 'Energy', 'Transportation', 'Real Estate', 'Media', 'Government']
    countries = ['Brazil', 'India', 'China', 'South Korea', 'Netherlands', 'Sweden', 'Switzerland']
    
    # Use next 25 customer IDs (some overlap with first set for merging)
    selected_customers = customer_ids[15:40]  # 10 overlapping customers
    
    data = []
    for customer_id in selected_customers:
        company = f"{random.choice(companies)} {random.randint(100, 999)}"
        industry = random.choice(industries)
        country = random.choice(countries)
        reg_date = datetime.now() - timedelta(days=random.randint(200, 800))
        
        data.append({
            'Customer_ID': customer_id,
            'Company_Name': company,
            'Industry': industry,
            'Country': country,
            'Registration_Date': reg_date.strftime('%Y-%m-%d')
        })
    
    return pd.DataFrame(data)

# Create all files
print("Generating test files...")

# Sales Template Files (Group 1)
sales_df_1 = create_sales_template_1()
sales_df_2 = create_sales_template_2()

# Customer Template Files (Group 2)
customer_df_1 = create_customer_template_1()
customer_df_2 = create_customer_template_2()

# Save files to Excel
with pd.ExcelWriter('sales_data_q1.xlsx', engine='openpyxl') as writer:
    # Add some header rows for testing header row parameter
    pd.DataFrame([['Sales Report Q1 2024'], ['Generated on: ' + datetime.now().strftime('%Y-%m-%d')], ['']]).to_excel(
        writer, sheet_name='Sales_Data', header=False, index=False)
    sales_df_1.to_excel(writer, sheet_name='Sales_Data', startrow=3, index=False)

with pd.ExcelWriter('sales_data_q2.xlsx', engine='openpyxl') as writer:
    pd.DataFrame([['Sales Report Q2 2024'], ['Generated on: ' + datetime.now().strftime('%Y-%m-%d')], ['']]).to_excel(
        writer, sheet_name='Sales_Data', header=False, index=False)
    sales_df_2.to_excel(writer, sheet_name='Sales_Data', startrow=3, index=False)

with pd.ExcelWriter('customer_info_batch1.xlsx', engine='openpyxl') as writer:
    # Add some empty columns for testing header column parameter
    temp_df = pd.DataFrame([['']] * 2)  # 2 empty rows
    temp_df.to_excel(writer, sheet_name='Customer_Info', header=False, index=False)
    
    # Add customer data starting from column B (index 1)
    customer_df_1.to_excel(writer, sheet_name='Customer_Info', startrow=2, startcol=1, index=False)

with pd.ExcelWriter('customer_info_batch2.xlsx', engine='openpyxl') as writer:
    temp_df = pd.DataFrame([['']] * 2)  # 2 empty rows
    temp_df.to_excel(writer, sheet_name='Customer_Info', header=False, index=False)
    
    customer_df_2.to_excel(writer, sheet_name='Customer_Info', startrow=2, startcol=1, index=False)

print("✅ Test files generated successfully!")
print("\n📁 Files created:")
print("1. sales_data_q1.xlsx (Template 1 - Sales)")
print("2. sales_data_q2.xlsx (Template 1 - Sales)")  
print("3. customer_info_batch1.xlsx (Template 2 - Customer)")
print("4. customer_info_batch2.xlsx (Template 2 - Customer)")

print("\n🔧 Configuration for testing:")
print("\nSales Group (Template 1):")
print("- Sheet Name: Sales_Data")
print("- Header Row: 4 (data starts at row 4)")
print("- Header Column: 1")
print("- Key Column: Customer_ID")

print("\nCustomer Group (Template 2):")
print("- Sheet Name: Customer_Info") 
print("- Header Row: 3 (data starts at row 3)")
print("- Header Column: 2 (data starts at column B)")
print("- Key Column: Customer_ID")

print("\n🔗 Merge Instructions:")
print("- Both groups have 'Customer_ID' as the common key")
print("- You can merge Sales data with Customer data using Customer_ID")
print("- Some customers appear in both groups for successful merging")

print("\n📊 Data Summary:")
print(f"- Sales Q1: {len(sales_df_1)} records")
print(f"- Sales Q2: {len(sales_df_2)} records")
print(f"- Customer Batch 1: {len(customer_df_1)} records")
print(f"- Customer Batch 2: {len(customer_df_2)} records")
print(f"- Total unique customers: {len(set(customer_ids))}")

# Show sample data
print("\n👀 Sample Sales Data:")
print(sales_df_1.head(3))
print("\n👀 Sample Customer Data:")
print(customer_df_1.head(3))