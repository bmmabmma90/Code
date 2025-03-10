# This file contains all the standalone functions used by ALMenu for reuse rather than having one monolithic file

import pandas as pd
import re
import csv
import io
from pyxirr import xirr
from datetime import datetime
import streamlit as st

# Formats currency for Streamlit
def format_currency(amount):
    """Formats a number as currency."""
    return '${:,.2f}'.format(amount)

def format_currency_dollars_only(amount):
    """Formats a number as currency."""
    return '${:,.0f}'.format(amount)

def format_large_number(number):
    """
    Formats a large number with one decimal place, using 'M' for millions or 'K' for thousands.

    Args:
        number (float): The number to format.

    Returns:
        str: The formatted number.
    """
    if number >= 1_000_000:
        return f"${number / 1_000_000:.2f}M"  # Millions
    elif number >= 1_000:
        return f"${number / 1_000:.2f}K"  # Thousands
    else:
        return f"${number:.2f}"  # Numbers less than 1,000


def format_date(date):
    """Formats a date to DD MM YY format for the screen"""
    return date.strftime("%d %m %y")

# Format for multiple in Streamlit
def format_multiple(amount):
    """Formats a number as a multiple (e.g., 2.5x)."""
    return '{:.2f}x'.format(amount)

def format_percent(amount):
    """Formats a number as a percentage."""
    return '{:.1%}'.format(amount)

# Formats percentage for Streamlit
def format_percentage(val): return "{:.2%}".format(val*100) # Formats to 2 decimal places 

# For removing European values etc
def replace_two_or_more_decimal_points(value):
    if isinstance(value, str) and value.count('.') >= 2:
        return value.replace('.', ',', value.count('.') - 1)
    return value

# Formats a St Editor block using our global variables - note this is a display specific function
def format_st_editor_block(df_t):

    # Set formatting for the data editor for Streamlit so we can easily change the formatting if we want
    stformatnumber = "$%.0f"
    stformatmult = "%.2f x"
    stformatpercent = "%.1f %%"
    stformatdate = "DD/MM/YYYY"

    # Apply the formatting using Pandas Styler - this doesn't seem to work
    styled_df = df_t.style.format({'XIRR': format_percent, 'Invested' : format_currency, 'Real Multiple': format_multiple})
    #         styled_df = enhanced_df

    # This should include all columns and presumably formatting on a column that doesn't exist is just ignored
    st.data_editor(
            styled_df, 
            column_config= {
                "Invest Date": st.column_config.DateColumn("Invest Date", format=stformatdate, help="The date of the investment"), 
                "First_Invest_Date": st.column_config.DateColumn("First Date", format=stformatdate, help="The date of the first investment"),
                "Last_Invest_Date": st.column_config.DateColumn("Last Date", format=stformatdate, help="The date of the last investment"), 
                "Realized Date": st.column_config.DateColumn("Realized Date", format=stformatdate, help="The date of exit of the investment"), 
                "Real Multiple": st.column_config.NumberColumn("Multiple",  format=stformatmult, help="Multiple expressed as total value / invested amount"),
                "Multiple": st.column_config.NumberColumn("Old Multiple", format=stformatmult, help="Multiple as originally recorded in the data supplied"),
                "Invested": st.column_config.NumberColumn("Invested", format=stformatnumber, help="Dollars invested (rounded to nearest whole number)"), 
                "Net Value": st.column_config.NumberColumn("Net Value", format=stformatnumber, help="Total value including realised and unrealized (rounded to nearest whole number)"),
                "Unrealized Value": st.column_config.NumberColumn("Unreal $", format=stformatnumber, help="Unrealized value of the investment as reported by the deal lead (rounded to nearest whole number)"), 
                "Realized Value": st.column_config.NumberColumn("$ Received", format=stformatnumber, help="Realized value as reported by AngelList (rounded to nearest whole number)"), 
                "Profit": st.column_config.NumberColumn("Profit", format=stformatnumber, help="Realized value less Invested Value"),
                "XIRR": st.column_config.NumberColumn("IRR", format=stformatpercent, help="IRR for this investment"), 
                "URL": st.column_config.LinkColumn("Website", help="The link to the website for the company"),
                "AngelList URL": st.column_config.LinkColumn("Website", help="The link to your AngelList investment record", display_text="AL Link")
            },
            hide_index=True,
    )  



# Tries to extract a company name from an AngelList description in tax data that is a bit messy and not clear
def extract_company_name(description, pattern):
    """Extracts a company name from a description string.

    Args:
        description (str): The description string.
        pattern (str): The regex pattern to remove.

    Returns:
        str: The extracted company name.
    """
    if pd.isna(description):
        return ""
    # Remove anything after a hyphen
    description = re.split(r"-", description, maxsplit=1)[0]
    # Remove the brackets and anything in between
    description = re.sub(r"\(.*?\)", "", description)
    # Remove the phrases using regex substitution
    return re.sub(pattern, "", description).strip() #.strip() removes leading and trailing whitespace.

def convert_date_two(date_str, is_us_format=True):
    """
    Convert a date string to a pandas datetime object.

    Parameters:
    - date_str (str): The date string to convert.
    - is_us_format (bool): Whether the date is in US format (MM/DD/YYYY). 
                           If False, assumes DD/MM/YYYY format.

    Returns:
    - pd.Timestamp or None: The converted datetime object, or None if conversion fails.
    """
    try:
        if is_us_format:
            # Use US format (MM/DD/YYYY)
            date_format = '%m/%d/%Y'
        else:
            # Use non-US format (DD/MM/YYYY)
            date_format = '%d/%m/%Y'
        
        # Convert the string to a datetime object
        datetime_obj = pd.to_datetime(date_str, format=date_format, errors='coerce')
        
        # Check if the conversion was successful
        if pd.isna(datetime_obj):
            return None
        else:
            return datetime_obj
    except Exception as e:
        # Handle any unexpected errors
        print(f"An error occurred: {e}")
        return None




def convert_date(date_str, is_US_date=True):
    """Converts a date string to a pandas datetime object so that it can be sorted and calculated on
    Also takes is it US format date (is angellList date)

    Args:
        date_str (str): The date string.
        is_US_date: The default is it will look for it in the US format which is '%m/%d/%y', 
        if false it is assumed to be '%d/%m/%y"

    Returns:
        pd.Timestamp or pd.NaT: The datetime object or NaT for invalid dates.
    """
    if pd.isna(date_str):
        return pd.NaT  # Return Not a Time value for missing dates
    try:
        if is_US_date:
            return pd.to_datetime(date_str, format="%m/%d/%y")
        else:
            return pd.to_datetime(date_str, format="%d/%m/%y", dayfirst=True)

    except ValueError:
        try:
            if is_US_date:
                return pd.to_datetime(date_str)
            else:
                st.write(f"Could not convert date: {date_str}")
                return pd.NaT  # Return NaT for unconvertible dates
        except ValueError:
            st.write(f"Could not convert date: {date_str}")
            return pd.NaT  # Return NaT for unconvertible dates

 
def calculate_row_xirr(row, now):
    """Calculates the XIRR for a single row from the df with its normal set up 
        will also process the Realized Date if it is present

    Args:
        row (pd.Series): The row containing investment data.
        now (datetime): The current datetime.

    Returns:
        float: The XIRR, or NaN if calculation fails, or 0.0 if Net Value <= 0.
    """
    if row['Net Value'] <= 0:
        return 0.0
    try:
        # Check if there is a column called 'Realized Date' and if so use that as the second date rather than now
        if 'Realized Date' in row and pd.notna(row['Realized Date']):
            dates = [row['Invest Date'], row['Realized Date']]
        else:
            dates = [row['Invest Date'], now]     
        amounts = [-row['Invested'], row['Net Value']]
        return xirr(dates, amounts)
    except Exception as e:
        print(f"Error calculating XIRR for row {row.name}: {e}")
        return float('nan')

def calculate_xirr(all_cashflows):
    """
    This function takes a list of cashflow tuples (date, amount)
    and calculates the XIRR based on those cashflows.

    Args:
        all_cashflows: A list of tuples, where each tuple is (date, amount).
                       'date' should be a datetime object, and 'amount' is a float.

    Returns:
        float: The XIRR value for the company, or None if calculation fails.
    """
    try:
        # Ensure the cashflows list is not empty
        if not all_cashflows:
            print("Warning: Empty cashflows list passed to calculate_xirr.")
            return 0.0  # Or None, depending on how you want to handle empty cashflows
        
        # Separate dates and amounts
        dates, amounts = zip(*all_cashflows)

        # Calculate the XIRR for this company
        the_xirr = xirr(dates, amounts)
        return the_xirr
    except Exception as e:
        print(f"Error calculating company XIRR: {e}")
        return 0.0  # Or None, depending on how you want to handle errors

# Calculate the whole portfolio's XIRR using the XIRR function
def calculate_portfolio_xirr(df, has_realized_dates, total_unrealized_value):
    """Calculates the overall XIRR of the whole portfolio.
    Args:
        df: DataFrame with 'Invest Date', 'Invested', possibly a 'Realized Date' but uses 
        total_net_value (this should exclude realised value) to do the total calculation.
    Returns:
        The portfolio XIRR as a float, or None if calculation fails.
    """
    try:
        # Combine all cashflows into a single list
        all_cashflows = []
        for index, row in df.iterrows():
            # Do the investment amount
            if pd.notna(row['Invest Date']):
                all_cashflows.append((row['Invest Date'], -row['Invested']))
            # Add any realized amount (if present)
            if has_realized_dates and pd.notna(row['Realized Date']):
                all_cashflows.append((row['Realized Date'], row['Realized Value']))
        # Add the total unrealized value as of now 
        all_cashflows.append((datetime.now(), total_unrealized_value)) 
   
        # Calculate the overall portfolio XIRR
        portfolio_xirr = xirr(all_cashflows)
        return portfolio_xirr
    except Exception as e:
        print(f"Error calculating portfolio XIRR: {e}")
        return None
    
def process_and_summarize_data(df):
    """
    Processes the DataFrame, normalizes data, and creates summary statistics.

    Args:
        df (pd.DataFrame): The input DataFrame.

    Returns:
        tuple: A tuple containing the processed DataFrame (df), the summary DataFrame (summary_df),
               the number of unique companies (num_uniques), the number of leads (num_leads),
               the number of leads with no value info (num_zero_value_leads), and number of locked values (num_locked).
    """
    # 2. Collect stats
    # Total rows in the dataframe (ie investments)
    # total_investments = len(df.index)
    # Get unique transactions in the Name / Description column
    unique_names = df["Company/Fund"].unique()
    num_uniques = len(unique_names)

    # 2.a. Replace non numeric values with 0 so the calculations that follow work
    df["Realized Value"] = df["Realized Value"].fillna(0)
    df["Multiple"] = df["Multiple"].fillna(0)

    # 2.b. Normalize the data by converting them to numbers
    df["Realized Value"] = df["Realized Value"].replace(r'[^\d.]', '', regex=True).astype(float)   
    df["Invested"] = df["Invested"].replace(r'[^\d.]', '', regex=True).astype(float)   
    df["Multiple"] = df["Multiple"].replace(r'[^\d.]', '', regex=True).astype(float)
    if 'Round Size' in df.columns :
        df['Round Size'] = df['Round Size'].replace(r'[^\d]', '', regex=True).astype(float)
    if 'Valuation or Cap' in df.columns:
        # First remove the european decimals before forcing to a float
        df['Valuation or Cap'] = df['Valuation or Cap'].apply(replace_two_or_more_decimal_points)  
        df['Valuation or Cap'] = df['Valuation or Cap'].replace(r'[^\d.]', '', regex=True).astype(float)
    
    # 2.c. Special treatment of Unrealized Value because we want to flag where we don't know the actual value
    # We'll iterate through and force "Unrealized" and "Net Value" to zero AFTER we have made a note that the
    #.   value isn't known in a new column called "Unknown Value"
    # insert in a specific order for ease of reference
    if 'Valuation Unknown' not in df.columns :
        df.insert(3, "Valuation Unknown", False)

    num_locked = 0
    invested_locked = 0
    for index, row in df.iterrows():
        original_value = row['Unrealized Value']
        if original_value == "Locked" :
            df.loc[index, "Valuation Unknown"] = True
            df.loc[index, "Unrealized Value"] = 0
            df.loc[index, "Net Value"] = 0
            num_locked += 1
            invested_locked += df.loc[index, "Invested"]
   
    # Now convert whole columns for Unrealized Value and Net Value now that have gathered which are locked (Forcing
    # Locked to zero
    df['Net Value'] = df['Net Value'].apply(replace_two_or_more_decimal_points)  
    df["Net Value"] = df["Net Value"].replace(r'[^\d.]', '', regex=True).astype(float) 
    df["Unrealized Value"] = df["Unrealized Value"].replace(r'[^\d.]', '', regex=True).astype(float) 
    df["Real Multiple"] = (df["Realized Value"]+df["Unrealized Value"])/df["Invested"]

    # Fix Dates
    df['Invest Date'] = df['Invest Date'].apply(convert_date_two, is_us_format=st.session_state.has_angellist_data)
    has_realized_date = False
    if 'Realized Date' in df.columns :
        has_realized_date = True
        df['Realized Date'] = df['Realized Date'].apply(convert_date_two, is_us_format=st.session_state.has_angellist_data)

    # Calculate basic XIRR for values - need to replace this with my proper logic I think later
    # improvement would be where some realised value to look at the financial information in AngelList and put in the other data to calculate this more clearly (overwriting this)
    now = datetime.now()
    df['XIRR'] = 0.0  # Set column to zero as a float
    df['XIRR'] = df.apply(calculate_row_xirr, axis=1, now=now)
    
    # 2.a.2 Move some columns 
    name_column_index = df.columns.get_loc('Company/Fund')
    # insert Multiple after and remove the prior position 
    df.insert(name_column_index+1, 'Real Multiple', df.pop('Real Multiple'))
    name_column_index = df.columns.get_loc('Invested')
    # insert Multiple after and remove the prior position 
    df.insert(name_column_index+1, 'Net Value', df.pop('Net Value'))

    #st.table(df) #debug
    #2.c. Calculate all the summary values
    # prompt: Filter the results to show only where Multiple > 1 and then create a completely new dataframe with a row called 'Multiple > 1' and as columns 'Count', 'Invested', 'Realized', 'UnRealized', 'Multiple', 'Percentage' have values that are the count of the number of results, the sum of the amount invested, the sum of the Realized, the sum of the Unrealized, the ratio of (UnRealised + Realised)/Invested, and a % that represents the ratio of the amount invested divided by the total sum of invested capital before the filter was applied
    # Output: Count, %, Invested, Realized, UnRealized, Multiple
    # We want to create the following slices of data:
    # Totals - no Filter
    # Realized at >=1x- Filtered: Status is Realized and Real Multiple >= 1
    # Realized at <1x - Filtered: Status is Realized and Real Multiple <1
    # Locked:         - Filtered: Valuation Unknown = True
    # Marked Up:      - Filtered: Valuation Unknown is not True and Real Multiple >=1
    # Not marked up:  - Filtered: Valuation Unknown is not True and Real Multiple < 1
    # Check that sum of all but Totals = Totals
    row_names = ['Totals', 'Realized >=1x', 'Realized <1x', 'Locked', 'Marked Up', 'Not Marked Up']
    top_X_cut = 5
    # iterate over the row names and run the searches
    for i in range(len(row_names)):
        if row_names[i] == 'Totals':
            filtered_df = df
        elif row_names[i] == 'Realized >=1x':
            filtered_df = df[(df['Status'] == 'Realized') & (df['Real Multiple'] >= 1)]
        elif row_names[i] == 'Realized <1x':
            filtered_df = df[(df['Status'] == 'Realized') & (df['Real Multiple'] < 1)]
        elif row_names[i] == 'Locked':
            filtered_df = df[(df['Status'] != 'Realized') & (df['Valuation Unknown'] == True)]
        elif row_names[i] == 'Marked Up':
            filtered_df = df[(df['Status'] != 'Realized') & (df['Valuation Unknown'] == False) & (df['Real Multiple'] > 1)]
        elif row_names[i] == 'Not Marked Up':
            filtered_df = df[(df['Status'] != 'Realized') & (df['Valuation Unknown'] == False) & (df['Real Multiple'] <= 1)]

        # Calculate summary statistics
        count = len(filtered_df)
        count_uniques = len(filtered_df['Company/Fund'].unique())
        invested_sum = filtered_df['Invested'].sum()
        realized_sum = filtered_df['Realized Value'].sum()
        unrealized_sum = filtered_df['Unrealized Value'].sum()
        value_sum = realized_sum + unrealized_sum
        multiple = (unrealized_sum + realized_sum) / invested_sum if invested_sum != 0 else 0  # Handle potential division by zero
        if row_names[i] == 'Totals': # Only do this once and can reuse this value in further calculations
            total_invested_original = invested_sum
        percentage = (invested_sum / total_invested_original) if total_invested_original !=0 else 0

        top_companies = filtered_df.sort_values(by='Real Multiple', ascending=False).head(top_X_cut)
        examples = ""
        for index, row in top_companies.iterrows():
            examples += f"{row['Company/Fund']} ({row['Real Multiple']:.2f}x), "

        # Remove the trailing comma and space
        examples = examples[:-2]

        # Create a new DataFrame for the summary
        summary_data = {'Category' : [row_names[i]], 'Investments': [count], 'Companies': [count_uniques],
                        'Percentage': [percentage], 'Invested': [invested_sum],
                        'Realized': [realized_sum], 'Unrealized': [unrealized_sum], 'Value': [value_sum],
                        'Multiple': [multiple], 'Examples': [examples] }
        if row_names[i] == 'Totals': # Create the table otherwise append
            summary_df = pd.DataFrame(summary_data)
        else:
            summary_df = pd.concat([summary_df, pd.DataFrame(summary_data)], ignore_index=True)
    #st.write(summary_df)
    # 2.d Calculate lead statistics by aggregating data
    aggregated_df = df.groupby('Lead').agg(
        total_investments=('Company/Fund', 'size'),
        sum_value=('Unrealized Value', 'sum')
    ).reset_index()
    num_leads = len(aggregated_df)
    # Exclude where no value as sum (result would be infinite)
    aggregated_df = aggregated_df[aggregated_df["sum_value"] != 0]
    # Calculate how many there are
    num_zero_value_leads = num_leads - len(aggregated_df)
    return df, summary_df, num_uniques, num_leads, num_zero_value_leads, num_locked, has_realized_date

def show_top_X_increase_and_multiple(df, round_name, type):
    """Shows the top X companies in a particular category.
    Args:
        df: DataFrame to show info about.
        round_name: the name of the category.
        type: either Market or Round.
    Returns:
        A list of strings showing company (x)
    """
    round_df = df[df[type] == round_name].sort_values(by="Increase", ascending=False)
    topX = 5
    # Create a list to store the formatted strings
    top_X_examples_list = []
    for index, row in round_df.head(topX).iterrows():
        company_fund = row["Company/Fund"]
        real_multiple = row["Real Multiple"]
        formatted_string = f"{company_fund} ({real_multiple:.2f}x)"
        top_X_examples_list.append(formatted_string)

    # Join the formatted strings with commas
    top_X_examples = ", ".join(top_X_examples_list)
    return top_X_examples

def show_top_X_names_based_on_multiple_by_Lead(top_values, df, mname):
    """Shows the companies with the top multiples in 'Company (X.X)x, ...' format by matching on the Lead = mname.
    Args:
        top_values: The number of companies to show
        df: The main data frame
        mname: The name of the Lead to filter by
    Returns:
        A list of strings showing company (x)
    """
    temp_df = df[df["Lead"] == mname].sort_values(by="Real Multiple", ascending=False)
    # Create a list to store the formatted strings
    top_X_examples_list = []
    for index, row in temp_df.head(top_values).iterrows():
                company_fund = row["Company/Fund"]
                real_multiple = row["Real Multiple"]
                formatted_string = f"{company_fund} ({real_multiple:.2f}x)"
                top_X_examples_list.append(formatted_string)
    # Join the formatted strings with commas
    top_X_examples = ", ".join(top_X_examples_list)
    return top_X_examples

def show_realised_based_on_Lead(top_values, df, mname):
    """Shows the realised companies in 'Company (X.X)x, ...' format by matching on the Lead = mname.
        Args:
            top_values: The number of companies to show
            df: The main data frame
            mname: The name of the Lead to filter by
        Returns:
            A list of strings showing company (x)
    """
    filtered_df = df[df['Status'] == 'Realized']
    temp_df = filtered_df[filtered_df["Lead"] == mname].sort_values(by="Real Multiple", ascending=True)
    # Create a list to store the formatted strings
    top_X_examples_list = []
    for index, row in temp_df.head(top_values).iterrows():
                company_fund = row["Company/Fund"]
                real_multiple = row["Real Multiple"]
                formatted_string = f"{company_fund} ({real_multiple:.2f}x)"
                top_X_examples_list.append(formatted_string)
    # Join the formatted strings with commas
    top_X_examples = ", ".join(top_X_examples_list)
    return top_X_examples

def has_angellist_data(file_or_filepath):
    """
    Checks if a CSV file (either a filepath or a file-like object from st.file_uploader)
    contains 'AngelList' in its header row.

    Args:
        file_or_filepath: Either a filepath (str) or an UploadedFile object from st.file_uploader.

    Returns:
        bool: True if 'AngelList' is in the header, False otherwise.
    """
    try:
        if isinstance(file_or_filepath, str):
            # It's a filepath
            with open(file_or_filepath, 'r', newline='', encoding='utf-8') as file:
                reader = csv.reader(file)
                header_row = next(reader, None)
        else:
            # It's a file-like object (st.file_uploader)
            # Using getvalue
            bytes_data = file_or_filepath.getvalue()
            # Create a BytesIO object
            buffer = io.TextIOWrapper(io.BytesIO(bytes_data), encoding='utf-8')
            reader = csv.reader(buffer)
            header_row = next(reader, None)

        if header_row is None:
            return False

        is_angellist_data = any("AngelList" in item for item in header_row)
        return is_angellist_data

    except FileNotFoundError:
        print(f"Error: File not found.")
        return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False
    