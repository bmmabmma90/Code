# This file contains all the standalone functions used by ALMenu for reuse rather than having one monolithic file

import pandas as pd
import re
from pyxirr import xirr
from datetime import datetime

# Formats currency for Streamlit
def format_currency(amount):
    """Formats a number as currency."""
    return '${:,.2f}'.format(amount)

def format_currency_dollars_only(amount):
    """Formats a number as currency."""
    return '${:,.0f}'.format(amount)

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

def convert_date(date_str):
    """Converts a date string to a pandas datetime object so that it can be sorted and calculated on

    Args:
        date_str (str): The date string.

    Returns:
        pd.Timestamp or pd.NaT: The datetime object or NaT for invalid dates.
    """
    if pd.isna(date_str):
        return pd.NaT  # Return Not a Time value for missing dates
    try:
        return pd.to_datetime(date_str)
    except ValueError:
        try:
            return pd.to_datetime(date_str, format='%m/%d/%y')
        except ValueError:
            print(f"Could not convert date: {date_str}")
            return pd.NaT  # Return NaT for unconvertible dates
 
def calculate_row_xirr(row, now):
    """Calculates the XIRR for a single row.

    Args:
        row (pd.Series): The row containing investment data.
        now (datetime): The current datetime.

    Returns:
        float: The XIRR, or NaN if calculation fails, or 0.0 if Net Value <= 0.
    """
    if row['Net Value'] <= 0:
        return 0.0
    try:
        dates = [row['Invest Date'], now]
        amounts = [-row['Invested'], row['Net Value']]
        return xirr(dates, amounts)
    except Exception as e:
        print(f"Error calculating XIRR for row {row.name}: {e}")
        return float('nan')

# Calculate the whole portfolio's XIRR using hte XIRR function 
def calculate_portfolio_xirr(df, total_net_value):
    """Calculates the overall XIRR of the whole portfolio.
    Args:
        df: DataFrame with 'Invest Date', 'Invested' but uses total_net_value to do the total calculation.
    Returns:
        The portfolio XIRR as a float, or None if calculation fails.
    """
    try:
        # Combine all cashflows into a single list
        all_cashflows = []
        for index, row in df.iterrows():
            if pd.notna(row['Invest Date']):
                all_cashflows.append((row['Invest Date'], -row['Invested']))
        # Add the total value as at now    
        all_cashflows.append((datetime.now(), total_net_value))
        # Calculate the overall portfolio XIRR
        portfolio_xirr = xirr(all_cashflows)
        return portfolio_xirr
    except Exception as e:
        st.write(f"Error calculating portfolio XIRR: {e}")
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
    total_investments = len(df.index)
    # Get unique transactions in the Name / Description column
    unique_names = df["Company/Fund"].unique()
    num_uniques = len(unique_names)

    # 2.a. Normalize the data by converting them to numbers
    df["Realized Value"] = df["Realized Value"].replace(r'[^\d.]', '', regex=True).astype(float)   
    df["Invested"] = df["Invested"].replace(r'[^\d.]', '', regex=True).astype(float)   
    df["Multiple"] = df["Multiple"].replace(r'[^\d.]', '', regex=True).astype(float)
    if 'Round Size' in df.columns :
        df['Round Size'] = df['Round Size'].replace(r'[^\d]', '', regex=True).astype(float)
    
    # 2.b. Special treatment of Unrealized Value because we want to flag where we don't know the actual value
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
    df["Net Value"] = df["Net Value"].replace(r'[^\d.]', '', regex=True).astype(float) 
    df["Unrealized Value"] = df["Unrealized Value"].replace(r'[^\d.]', '', regex=True).astype(float) 
    df['Real Multiple'] = (df['Realized Value']+df['Unrealized Value'])/df['Invested']

    # Fix Dates
    df['Invest Date'] = df['Invest Date'].apply(convert_date)

    # Calculate basic XIRR for values - need to replace this with my proper logic I think later
    # improvement would be where some realised value to look at the financial information in AngelList and put in the other data to calculate this more clearly (overwriting this)
    now = datetime.now()
    df['XIRR'] = 0.0  # Set column to zero as a float
    df['XIRR'] = df.apply(calculate_row_xirr, axis=1, now=now)
    
    # 2.a.2 Move some columns 
    name_column_index = df.columns.get_loc('Company/Fund')
    # insert Multiple after and remove the prior position 
    df.insert(name_column_index+1, 'Multiple', df.pop('Multiple'))
    name_column_index = df.columns.get_loc('Invested')
    # insert Multiple after and remove the prior position 
    df.insert(name_column_index+1, 'Net Value', df.pop('Net Value'))

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
            filtered_df = df[(df['Status'] != 'Realized') & (df['Valuation Unknown'] == False) & (df['Real Multiple'] >= 1)]
        elif row_names[i] == 'Not Marked Up':
            filtered_df = df[(df['Status'] != 'Realized') & (df['Valuation Unknown'] == False) & (df['Real Multiple'] < 1)]

        # Calculate summary statistics
        count = len(filtered_df)
        invested_sum = filtered_df['Invested'].sum()
        realized_sum = filtered_df['Realized Value'].sum()
        unrealized_sum = filtered_df['Unrealized Value'].sum()
        multiple = (unrealized_sum + realized_sum) / invested_sum if invested_sum != 0 else 0  # Handle potential division by zero
        if row_names[i] == 'Totals': # Only do this once and can reuse this value in further calculations
            total_invested_original = invested_sum
        percentage = (invested_sum / total_invested_original) if total_invested_original !=0 else 0

        top_companies = filtered_df.sort_values(by='Real Multiple', ascending=False).head(5)
        examples = ""
        for index, row in top_companies.iterrows():
            examples += f"{row['Company/Fund']} ({row['Real Multiple']:.2f}x), "

        # Remove the trailing comma and space
        examples = examples[:-2]

        # Create a new DataFrame for the summary
        summary_data = {'Category' : [row_names[i]], 'Count': [count], 'Percentage': [percentage], 'Invested': [invested_sum],
                        'Realized': [realized_sum], 'Unrealized': [unrealized_sum], 'Multiple': [multiple], 'Examples': [examples] }
        if row_names[i] == 'Totals': # Create the table otherwise append
            summary_df = pd.DataFrame(summary_data)
        else:
            summary_df = pd.concat([summary_df, pd.DataFrame(summary_data)], ignore_index=True)

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
    return df, summary_df, num_uniques, num_leads, num_zero_value_leads, num_locked

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
