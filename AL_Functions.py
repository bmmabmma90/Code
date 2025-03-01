# This file contains all the standalone functions used by ALMenu for reuse rather than having one monolithic file

import pandas as pd
import re
from pyxirr import xirr
from datetime import datetime
import streamlit as st
import matplotlib.ticker as mtick

# Formats currency for Streamlit
def format_currency(amount):
    """Formats a number as currency."""
    return '${:,.2f}'.format(amount)

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
    if pd.isna(description):
        return ""
    # Remove anything after a hyphen
    description = re.split(r"-", description, maxsplit=1)[0]
    # Remove the brackets and anything in between
    description = re.sub(r"\(.*?\)", "", description)
    # Remove the phrases using regex substitution
    return re.sub(pattern, "", description).strip() #.strip() removes leading and trailing whitespace.

# Force convert a date from a string - not sure this works brilliantly because has 
# Create a new date called 'New Date' that is a real sortable date value
def convert_date(date_str):
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
    """Calculates the XIRR for a single row based on Invest Date, Invested, Net Value and now only"""
    if row['Net Value'] > 0:
        try:
            dates = [row['Invest Date'], now]
            amounts = [-row['Invested'], row['Net Value']]
            return xirr(dates, amounts)
        except Exception as e:
            print(f"Error calculating XIRR for row {row.name}: {e}")
            return float('nan')
    return 0.0

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
