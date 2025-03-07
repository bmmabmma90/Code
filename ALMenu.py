# AL_Menu
# Streamlit menu selection and front end for AngelList

import streamlit as st
import pandas as pd
from matplotlib import pyplot as plt
import seaborn as sns
import squarify
import numpy as np # User for colour stuff
from datetime import datetime, date
from AL_Functions import (
    format_currency,
    format_currency_dollars_only,
    format_large_number,
    format_multiple,
    format_percent,
    format_st_editor_block,
    calculate_row_xirr,
    calculate_company_xirr,
    calculate_portfolio_xirr,
    process_and_summarize_data,
    show_top_X_increase_and_multiple,
    show_top_X_names_based_on_multiple_by_Lead,
    show_realised_based_on_Lead,
    extract_company_name,
    convert_date,
    has_angellist_data
)

st.set_page_config(layout="wide")
st.title("Startup Data Analyser")

# Set has no data file until one is read in correctly
if 'force_load' not in st.session_state: 
    st.session_state.force_load = False
if 'advanced_user' not in st.session_state:
    st.session_state.advanced_user = False
if 'menu_choice' not in st.session_state:
    st.session_state.menu_choice = "About"
if 'has_data_file' not in st.session_state: 
    st.session_state.has_data_file = False
if 'has_enhanced_data_file' not in st.session_state: 
    st.session_state.has_enhanced_data_file = False
if 'has_finance_data_file' not in st.session_state: 
    st.session_state.has_finance_data_file = False
if 'date_format' not in st.session_state: 
    st.session_state.date_format = "%d/%m/%y"
if 'has_angellist_data' not in st.session_state: 
    st.session_state.has_angellist_data = False

if 'df' not in st.session_state: 
    st.session_state.df = pd.DataFrame()
if 'df2' not in st.session_state: 
    st.session_state.df2 = pd.DataFrame()
if 'total_value' not in st.session_state:   
    st.session_state.total_value = 0

# Sidebar for the menu
with st.sidebar:
    st.header("Menu")
    if st.session_state.has_data_file:
        if st.session_state.advanced_user :
            option = st.selectbox(
                "Choose an option:",
                ("About", "Load Data", "Overwrite", "Stats", "Top Investments", "Top by Company", "Ask me anything", "Round", "Market", "Year", "Realized", "Lead Stats", "Leads no values", "Graphs", "Tax")
            )
        else:
            option = st.selectbox(
                "Choose an option:",
                ("About", "Load Data", "Stats", "Top Investments", "Top by Company", "Ask me anything", "Round", "Market", "Year", "Realized", "Lead Stats", "Leads no values", "Graphs")
            )
    else:
        option = st.selectbox(
            "Choose an option:",
            ("About", "Load Data") 
        )
    if st.session_state.menu_choice != option:
        st.session_state.menu_choice = option

# Perform actions based on the selected option
if st.session_state.menu_choice == "About" :
    st.subheader("About", divider=True)
    multi = '''AngelList's investor focused data analysis is somewhat limited. This program aims 
to make it easier for investors to get insight from their :red[AngelList] data and to be able to perform ad hoc 
analysis to inform their future investing decisions.

The program takes in up to two data sources in the Load menu item. The first is an export of :red[AngelList] data 
which you can generate from the :blue-background[Portfolio page] (-->select Export CSV). This is all you need to process your data.
    
**Advanced**    

The second (and optional file) is a .CSV formatted file you 
can make to store additional data that isn't stored in :red[AngelList] or that is not readily accessible in the export. The 
format of this second file must be:
    
    ! Any comments or version you want to include - this line is ignored for processing 
    Company/Fund  URL  AngelList URL   Comment   Other fields

[Further instructions](https://docs.google.com/document/d/1WldPWcaWwZNBu-X0_e7LzybXyoVedJl84KTDR-gE4fo/edit?usp=sharing) are available (please comment if issues)

v.0.0.2
'''
    st.markdown(multi)

elif st.session_state.menu_choice == "Overwrite" :
    st.subheader("Overwrite Values", divider=True)
    multi = '''The overwrite function will attempt to overwrite your primary data with data from your secondary data file. 
Once complete, all ongoing calculations will be based on this new data. 
'''
    st.markdown(multi)

    # Add Overwrite button - add the correct logic
    # Note that doesn't deal with double/triple ups - if that is the case it needs a way of overwriting just the valuation data for the right value
    if st.button("Overwrite Values", type="primary") :
        if st.session_state.has_enhanced_data_file: #Otherwise we have nothing to overwrite with
            df = st.session_state.df
            df2 = st.session_state.df2
            # Check if 'New Value' column exists in df2
            if 'New Value' in df2.columns:
                # Ensure both dataframes have 'Company/Fund' and have the right fields to match on
                if all(col in df.columns for col in ['Company/Fund', 'Invest Date']) and all(col in df2.columns for col in ['Company/Fund', 'Match Date']):
                    # Merge dataframes on 'Company/Fund' to find matching rows
                    df2['Match Date'] = df2['Match Date'].apply(convert_date)
                    merged_df = pd.merge(df, df2[['Company/Fund', 'Match Date', 'New Value']], left_on=['Company/Fund','Invest Date'], right_on=['Company/Fund','Match Date'], how='inner', suffixes=('', '_df2'))
                    # Filter out rows where 'New Value' is not None
                    rows_to_update = merged_df[merged_df['New Value'].notnull()]
                    # Create a list to store changes for display
                    changes_list = []

                    # Update 'Net Value' in df with 'New Value' from df2
                    for index, row in rows_to_update.iterrows():
                        # Find the index in df where Company/Fund matches
                        df_index = df[df['Company/Fund'] == row['Company/Fund']].index[0]
                        # Store old values
                        old_net_value = df.loc[df_index, 'Net Value']
                        old_real_multiple = 0
                        old_XIRR = 0
                        if 'Real Multiple' in df.columns :
                            old_real_multiple = df.loc[df_index, 'Real Multiple']
                        if 'XIRR' in df.columns :
                            old_xirr = df.loc[df_index, 'XIRR']
                        # Recalculate new values - but also they need to be in the right format so we probably need to do all our normalisation code - maybe put it in a separate file somewhere?
                        df.loc[df_index, 'Net Value'] = float(row['New Value'])
                        df.loc[df_index, 'Unrealized Value'] = float(row['New Value']) # If don't set this it gets overridden later when calculating everyhing from scratch
                        df.loc[df_index, 'Real Multiple'] = row['New Value']/df.loc[df_index, 'Invested']
                        df.loc[df_index, 'XIRR'] = calculate_row_xirr(df.loc[df_index], datetime.now())

                        # Record the change
                        changes_list.append({
                            'Company/Fund': df.loc[df_index, 'Company/Fund'],
                            'Invest Date' : df.loc[df_index, 'Invest Date'],
                            'Old Value': old_net_value,
                            'New Value': df.loc[df_index, 'Net Value'],
                            'Old Real Multiple' :old_real_multiple,
                            'New Real Multiple' : df.loc[df_index, 'Real Multiple'],
                            'old_xirr' : old_xirr,
                            'New XIRR' : df.loc[df_index, 'XIRR']
                        })
                    # Display the changes in a DataFrame
                    if changes_list:
                        st.write("Values Overwritten (and recalculated values) were as follows")
                        changes_df = pd.DataFrame(changes_list)
                        st.dataframe(changes_df)

                        # Run the process thing again
                            # 2. Process all the data

                        df, summary_df, num_uniques, num_leads, num_zero_value_leads, num_locked = process_and_summarize_data(df, st.session_state.date_format)

                        st.dataframe(df)
                        # Set session state values for other screens
                        st.session_state.df = df
                        st.session_state.sumdf = summary_df
                        st.session_state.num_uniques = num_uniques
                        st.session_state.num_leads = num_leads
                        st.session_state.num_zero_value_leads = num_zero_value_leads
                        st.session_state.num_locked = num_locked
                    else:
                        st.write("No changes made. No matching values found or 'New Value' is empty.")
                else:
                    st.write("Error: 'Company/Fund' column is missing in one or both DataFrames and/or no 'Invest Date' and 'Match Date' found")
            else : st.write("No 'New Value' to replace values with in the data set")
        else : st.write("No data file to replace values with")
    
elif st.session_state.menu_choice == "Load Data":
    st.subheader("(Re)Load in data file(s) for processing", divider=True)
    st.markdown("You can (re)load the data from the data file and replace any changes you have made to the data locally.")
    
    # Display if already loaded and button not pressed or where data hasn't been loaded
    # Check if already loaded
# Force load allows you to ignore the Load Data with specific data
    force_load = st.session_state.force_load

    if force_load == True:
        filepath = "/Users/deepseek/Downloads/2021.csv"  # Replace with your file path
        filepath = "/Users/deepseek/Downloads/ben-armstrong_angellist_investments_2025_02_21.csv"
        filepath = "/Users/deepseek/Downloads/2022.csv"  # Replace with your file path
        filepath = "/Users/deepseek/Downloads/Synd.csv"  # Replace with your file path

        df = pd.read_csv(filepath, header=1, skip_blank_lines=True)
   #     st.session_state.has_angellist_data = has_angellist_data(filepath)
        
        # if df is not None:
        #     print(f"Is AngelList data: {st.session_state.has_angellist_data}")
        #     print("DataFrame loaded successfully:")
        #     print(df)
        # else:
        #     print("Failed to load DataFrame.")
        # if st.session_state.has_angellist_data: 
        #     st.session_state.date_format = "%m/%d/%y" 

        st.session_state.has_data_file = True
        st.session_state.df = df
        with st.container(height=200):
            st.write(df)       
        df2 = pd.read_csv(r"/Users/deepseek/Downloads/Enhance.csv", header=1, skip_blank_lines=True)
        st.session_state.has_enhanced_data_file = True
        st.session_state.df2 = df2
        with st.container(height=200):
            st.write(df2)       
    else:
        # Action 1: Load in Data
        uploaded_file = st.file_uploader("Choose the file in a CSV [AngelList] format", type="csv")

    if force_load == False and uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file, header=1, skip_blank_lines=True)
            # st.session_state.has_angellist_data = has_angellist_data(uploaded_file)
        
            # if st.session_state.has_angellist_data: 
            #     st.session_state.date_format = "%m/%d/%y" 

            st.session_state.has_data_file = True
            st.session_state.df = df
            with st.container(height=200):
                st.write(df)
        except pd.errors.ParserError:
            st.write(f"Error: Could not parse file as a CSV file. Please ensure it's a valid CSV.")
        except Exception as e:
            st.write(f"An unexpected error occurred: {e}")

    # Optional - Load in Enhancement file if it exists
    if not force_load:
        uploaded_file2 = st.file_uploader("Choose the Enhancement file in a CSV format. The first row is ignored and the first column must be 'Company/Fund' matching exactly, followed by any other columns", type="csv")
    if not force_load and uploaded_file2 is not None:
        try:
            df2 = pd.read_csv(uploaded_file2, header=1, skip_blank_lines=True)
            st.session_state.has_enhanced_data_file = True
            st.session_state.df2 = df2
            with st.container(height=200):
                st.write(df2)               
        except pd.errors.ParserError:
            st.write("Error: Could not parse file as a CSV file. Please ensure it's a valid CSV.")
        except Exception as e:
            st.write(f"An unexpected error occurred: {e}")

    # Add a button to reset the data load
    if force_load :
        if st.button("Reload all Data", type="primary"):
            st.session_state.force_load = False
            st.session_state.has_data_file = False
            st.session_state.has_enhanced_data_file = False

    # Action 2 is all the data normalisation and analysis logic
    # Only do it if there is data in the data frame otherwise suggest load the data
    if st.session_state.has_data_file:
        # Set the df locally from the data session
        df = st.session_state.df
    
    # Do all the data processing    
    # 1. Drop the data we don't analyse for easy display / debugging - 'Round', 'Market', 'Round Size', 'Invest Date', 'Instrument'
        todrop = { 'Investment Entity', 'Invest Date_y', # This is a special value caused by the outer join - we shouldn't see it! 
                'Investment Type', 'Fund Name', 'Allocation',  
                'Valuation or Cap Type', # 'Valuation or Cap', 
                'Discount', 'Carry', 'Share Class'}
        # Get the actual column names from the DataFrame
        df_columns = df.columns
        # Convert the column names to a set for efficient comparison
        df_columns_set = set(df_columns)
        # Create a new set with only the columns that are present in the DataFrame
        todrop_filtered = {col for col in todrop if col in df_columns_set}
        # Drop the filtered columns
        df = df.drop(columns=todrop_filtered)

    # 2. Process all the data
        df, summary_df, num_uniques, num_leads, num_zero_value_leads, num_locked = process_and_summarize_data(df)

 #      st.dataframe(summary_df)
 #      print(summary_df)

        # Button
        if st.button("Proceed", type="primary"):
            st.session_state.menu_choice = "Stats"
        #   st.experimental_rerun()

        # Set session state values for other screens
        st.session_state.df = df
        st.session_state.sumdf = summary_df

        st.session_state.num_uniques = num_uniques
        st.session_state.num_leads = num_leads
        st.session_state.num_zero_value_leads = num_zero_value_leads
        st.session_state.num_locked = num_locked

elif st.session_state.menu_choice == 'Ask me anything':
    st.markdown('''You can ask a question in query format to get an answer on the dataframe.
Valid operations are on all column names and can use <,>,=   and or 'column name' == "Value"
''')
    st.markdown("Example questions include:<br>1. What are the top companies?<br>2. How much was invested in total?<br>3. Which market had the most invested in it?", unsafe_allow_html=True)

    if st.session_state.has_data_file:
        df = st.session_state.df
        query = st.text_input("Enter your query in simple terms")
        if query:
            answer = df.query(query)
            st.write(answer) 

elif st.session_state.menu_choice == "Stats":
    st.subheader("Investment Statistics", divider=True)
    st.markdown("Show statistics across the portfolio.  NB: If you have 'Locked' data (eg from AngelList' you will need to go into AngelList to get the total portfolio value which is then used to work out the value increase/decrease of all 'Locked' investments")
    # Write all the outputs to the screen

    sumdf = st.session_state.sumdf
    total_value = sumdf.loc[sumdf['Category'] == 'Totals', 'Realized'].iloc[0] + sumdf.loc[sumdf['Category'] == 'Totals', 'Unrealized'].iloc[0]
    print(st.session_state)
    if st.session_state.num_locked > 0 and st.session_state.total_value == 0 :
        total_value = st.number_input("Insert the total value from AngelList")
        st.session_state.total_value = total_value
        locked_value = total_value - sumdf.loc[sumdf['Category'] == 'Totals', 'Unrealized'].iloc[0]
        st.session_state.sumdf.loc[st.session_state.sumdf['Category'] == 'Locked', 'Unrealized'] = float(locked_value)
        st.session_state.sumdf.loc[st.session_state.sumdf['Category'] == 'Totals', 'Unrealized'] = total_value
    elif st.session_state.total_value == 0 :
        st.session_state.total_value = total_value

    a, b, f, g = st.columns(4) # Macro stats - investments + companies plus syndicate stats
    c, d, h, e = st.columns(4) # Macro valuation stats - total value, net value and invested $
#       f, g = st.columns(2) # Syndicate info

    a.metric(label="Investments", value=sumdf.loc[sumdf['Category'] == 'Totals', 'Investments'].iloc[0], border=True)
    b.metric(label="Companies", value=st.session_state.num_uniques, border=True)
    if st.session_state.total_value > 0:
        c.metric(label="Total Value $",value=format_currency_dollars_only(total_value), border=True)
        d.metric(label="Multiple (x)",value=format_multiple(sumdf.loc[sumdf['Category'] == 'Totals', 'Multiple'].iloc[0]), border=True)

        # Calculate overall XIRR
        if 'overall_XIRR' not in st.session_state :                    
            overall_XIRR = calculate_portfolio_xirr(st.session_state.df, total_value)
            st.session_state.overall_XIRR = overall_XIRR
            h.metric(label="IRR %",value=format_percent(overall_XIRR), border=True)
        else:
            h.metric(label="IRR %",value=format_percent(st.session_state.overall_XIRR), border=True)
    e.metric(label="Invested $",value=format_currency_dollars_only(sumdf.loc[sumdf['Category'] == 'Totals', 'Invested'].iloc[0]), border=True)
    f.metric(label="Syndicates Invested",value=st.session_state.num_leads, border=True)
    g.metric(label="Syndicates no value info",value=st.session_state.num_zero_value_leads, border=True)

    # Neatly format everything
    summary_styled = st.session_state.sumdf.style.format({'Percentage': format_percent, 'Invested': format_currency_dollars_only, \
            'Realized': format_currency_dollars_only, 'Unrealized': format_currency_dollars_only, \
            'Value':format_currency_dollars_only,'Multiple': format_multiple})
    st.dataframe(summary_styled, hide_index=True)

elif st.session_state.menu_choice == "Top Investments":
    st.subheader("Top Investments", divider=True)
    st.markdown('''Show selected top investments across the portfolio (by return multiple).  
                 You can use the slider to restrict the number of values shown on the screen
    ''')

    # Write all the outputs to the screen
    top_filter = st.slider("Show how many",1,50,5)   
    # Calculate the top X investments by multiple and show information for them

    # Load the data from the session state
    df = st.session_state.df
    filtered_df = df[df['Real Multiple'] > 1]
    #st.write(df)
    sorted_df = filtered_df.dropna(subset=['Real Multiple']).sort_values(by='Real Multiple', ascending=False)

    # Get ready for screen display - drop columns and format
    # Drop the filtered columns
    sorted_df = sorted_df.drop(columns=['Status','Valuation Unknown', 'Multiple', 'Round Size'])
    
    # Reorder columns to place 'Real Multiple' and 'XIRR' after 'Company/Fund'
    cols = sorted_df.columns.tolist()
    if 'Real Multiple' in cols and 'XIRR' in cols and 'Company/Fund' in cols :
        cols.remove('Real Multiple')
        cols.remove('XIRR')
        company_index = cols.index('Company/Fund')
        cols.insert(company_index + 1, 'Real Multiple')
        cols.insert(company_index + 2, 'XIRR')
        sorted_df = sorted_df[cols]
    
    # Get the top X investments
    top_X_num = sorted_df.head(top_filter)
    top_X_num.loc[:,'XIRR'] = top_X_num['XIRR']*100

    # Merge the cleaned dataset with the sample dataset using 'Company/Fund' as the key
    if st.session_state.has_enhanced_data_file:
        enhanced_df = pd.merge(top_X_num, st.session_state.df2, on='Company/Fund', how='left')
        top_X_num = enhanced_df
    
    format_st_editor_block(top_X_num)

    # Show a tree graph that looks nice
    # Calculate sizes based on Net Value
    sizes = top_X_num['Net Value']
    labels = [f"{company}\n({multiple:.1f}x)" for company, multiple in zip(top_X_num['Company/Fund'], top_X_num['Real Multiple'])]
    colors = plt.cm.viridis(np.linspace(0, 0.8, len(top_X_num)))

    # Create the plot
    plt.figure(figsize=(12, 8))
    squarify.plot(sizes=sizes, label=labels, color=colors, alpha=0.8, text_kwargs={'fontsize':10})
    plt.axis('off')
    plt.title('Investment Treemap (Size by Net Value, Labels show Multiple)', pad=20)
    plt.tight_layout()
    st.pyplot(plt)
    plt.cla()

    # Also show a Waterfall Chart of value created (which isn't limited by the data set)
    # Filter out values below the 1% threshold
    threshold = 0.01
    temp_df = df.copy()
    temp_df['Val increase'] = temp_df['Net Value'] - temp_df['Invested']
    total_increase = temp_df['Val increase'].sum()
    filtered_df = temp_df[temp_df['Val increase'] / total_increase >= threshold]

    # Group the remaining investments by 'Investment' and sum their 'Val increase'
    others_increase = temp_df[temp_df['Val increase'] / total_increase < threshold]['Val increase'].sum()

    # Create an 'Others' category
    others_category = pd.DataFrame({'Company/Fund': ['Others'], 'Val increase': [others_increase]})
    filtered_df = pd.concat([filtered_df, others_category])
    sorted_df = filtered_df.sort_values(by='Val increase', ascending=False)
    total_entries = len(sorted_df)

    # Create the waterfall chart
    fig, ax = plt.subplots(figsize=(10, 6))
    # Get the labels and values
    labels = sorted_df['Company/Fund'].tolist()
    values = sorted_df['Val increase'].tolist()
    # Plot the waterfall chart

    # Convert values to millions
    values_millions = [v / 1e6 for v in values]  # Divide each value by 1 million

    # Plot the waterfall chart
    # Calculate new ylim based on millions
    total_increase_millions = total_increase / 1e6
    others_increase_millions = others_increase / 1e6
    ax.set_ylim(0, total_increase_millions - others_increase_millions)  # Set y-axis limit for clarity

#        ax.set_ylim(0, total_increase - others_increase) # Set y-axis limit for clarity
    cmap = plt.get_cmap('coolwarm', total_entries)  # Use 'viridis' or any other colormap you like
    # Initialize the current value at 0 for the first bar
    current_value = 0
    for i, (label, value) in enumerate(zip(labels, values_millions)):
        next_value = current_value + value
        ax.bar(i, value, bottom=current_value, label=label if i == 0 else "", color=cmap(i), alpha=0.7, width=0.8) # Set label only for the first bar
        current_value = next_value
        ax.text(i, current_value*.9, f"${values[i]:,.0f}", ha='center', va='center')

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha='right')
    ax.set_ylabel("Value Increase ($ M)")
    ax.set_title("Waterfall Chart of Value Increase by Investment (Over 1%)")
    #plt.legend() # No longer needed since labels are only set for the first bar
    plt.tight_layout()
    st.pyplot(fig)  

elif st.session_state.menu_choice == "Top by Company":
    st.subheader("Top Investments aggregated by Company", divider=True)
    st.markdown('''This data will look at all the investments by company (ie aggregating multiple investments).

You can use the slider to restrict the number of values shown on the screen
    ''')

    # Write all the outputs to the screen
    top_filter = st.slider("Show how many",1,50,5)   
    # Calculate the top X investments by multiple and show information for them

    # Load the data from the session state
    df = st.session_state.df

    # Get ready for screen display - drop columns and format
    # Drop the filtered columns
    sorted_df = df.drop(columns=['Status','Valuation Unknown', 'Multiple', 'Round Size'])

    # Now aggregate all the investments by Company/Fund and then recalculate IRR and Multiples, Invested Amount, Etc
    # Gets a little tricky with XIRR but as long as have all dates and amounts it should be okay
    # Group by 'Company/Fund' and aggregate data
    if 'URL' in sorted_df.columns:
        grouped = sorted_df.groupby('Company/Fund').agg(
            Invested=('Invested', 'sum'),
            Net_Value=('Net Value', 'sum'),
            Unrealized=('Unrealized Value', 'sum'),
            Realized=('Realized Value', 'sum'),
            First_Invest_Date=('Invest Date', 'min'),  # don't use either of these values yet
            Last_Invest_Date=('Invest Date', 'max'), # this is the second not used
            URL=('URL', 'first'),
        ).reset_index()
    else:             
        grouped = sorted_df.groupby('Company/Fund').agg(
            Invested=('Invested', 'sum'),
            Net_Value=('Net Value', 'sum'),
            Unrealized=('Unrealized Value', 'sum'),
            Realized=('Realized Value', 'sum'),
            First_Invest_Date=('Invest Date', 'min'),  # don't use either of these values yet
            Last_Invest_Date=('Invest Date', 'max'), # this is the second not used
        ).reset_index()
    # Add in 'Website/URL' if it is in the df
    # if 'Website' in df.columns:
    #     grouped = pd.merge(grouped, df[['Company/Fund', 'Website']], on='Company/Fund', how='inner')
    # if 'URL' in df.columns:
    #     grouped = pd.merge(grouped, df[['Company/Fund', 'URL']], on='Company/Fund', how='inner')

    # Calculate 'Real Multiple' and 'XIRR'
    grouped['Real Multiple'] = grouped['Net_Value'] / grouped['Invested']
    # Calculate 'XIRR'

    grouped['XIRR'] = 0.0
    for index, row in grouped.iterrows():
        # Get all transactions relating to this fund
        all_transactions = df.loc[df['Company/Fund'] == row['Company/Fund']]
        # Create a dataframe to store all the transactions

     #   st.write(row['Company/Fund'])
     #   st.write(all_transactions)
        # Create a list to store all cash flows
        company_xirr = 0.0
        if all_transactions['Net Value'].iloc[0] > 0 : # If no positives then doesn't make sense
            all_cashflows = []
            for index, row in all_transactions.iterrows():
                all_cashflows.append((row['Invest Date'], -row['Invested']))
            
            # Add the sum of Net value as exit value with time as now
            total_net_value = all_transactions['Net Value'].sum()
            if pd.notna(row["Realized Date"]):
                realized_date = row["Realized Date"]
     #          st.write("Did find a realized date for the row")
                all_cashflows.append((realized_date, total_net_value))
            else:
                all_cashflows.append((datetime.now(), total_net_value))
     #      st.write(all_cashflows)
            # Calculate the xirr for this row, and store it in the overall dataframe
            try:
                # Calculate the XIRR for this company
                company_xirr = calculate_company_xirr(all_cashflows)
            except ValueError:
                company_xirr = 0.0
            # Find the correct index to update in 'grouped'
    #        st.write("Company XIRR:")
    #        st.write(company_xirr)
        company_name = all_transactions['Company/Fund'].iloc[0]  # Get the company name from all_transactions
        index_to_update = grouped.index[grouped['Company/Fund'] == company_name]
        grouped.loc[index_to_update[0], 'XIRR'] = company_xirr # Update the first match - should only be one

    # sort the values
    sorted_df = grouped.dropna(subset=['Real Multiple']).sort_values(by='Real Multiple', ascending=False)

    # Get the top X investments
    top_X_num = sorted_df.head(top_filter)
    top_X_num.loc[:,'XIRR'] = top_X_num['XIRR']*100

    # Reorder columns to place 'Real Multiple' and 'XIRR' after 'Company/Fund'
    cols = top_X_num.columns.tolist()
    if 'Real Multiple' in cols and 'XIRR' in cols and 'Company/Fund' in cols :
        cols.remove('Real Multiple')
        cols.remove('XIRR')
        company_index = cols.index('Company/Fund')
        cols.insert(company_index + 1, 'Real Multiple')
        cols.insert(company_index + 2, 'XIRR')
        top_X_num = top_X_num[cols]

    if st.session_state.has_enhanced_data_file:
        enhanced_df = pd.merge(top_X_num, st.session_state.df2, on='Company/Fund', how='left')
        top_X_num = enhanced_df

    # Display results in an editor block    
    format_st_editor_block(top_X_num)

    # Show a tree graph that looks nice
    # Calculate sizes based on Net Value
    # First remove zero numbers as they can't be plotted
    top_X_num = top_X_num[top_X_num['Net_Value'] > 0]

    sizes = top_X_num['Net_Value']

    labels = [f"{company}\n({multiple:.1f}x)" for company, multiple in zip(top_X_num['Company/Fund'], top_X_num['Real Multiple'])]
    colors = plt.cm.viridis(np.linspace(0, 0.8, len(top_X_num)))

    # Create the plot
    plt.figure(figsize=(12, 8))
    squarify.plot(sizes=sizes, label=labels, color=colors, alpha=0.8, text_kwargs={'fontsize':10})
    plt.axis('off')
    plt.title('Investment Treemap (Size by Net Value, Labels show Multiple)', pad=20)
    plt.tight_layout()
    st.pyplot(plt)
    plt.cla()

    # Also show a Waterfall Chart of value created (which isn't limited by the data set)
    # Filter out values below the 1% threshold
    threshold = 0.01
    temp_df = grouped.copy() # So we are playing with aggregated values here
    # Have to groupby again
    temp_df['Val increase'] = temp_df['Net_Value'] - temp_df['Invested']
    total_increase = temp_df['Val increase'].sum()
    filtered_df = temp_df[temp_df['Val increase'] / total_increase >= threshold]

    # Group the remaining investments by 'Investment' and sum their 'Val increase'
    others_increase = temp_df[temp_df['Val increase'] / total_increase < threshold]['Val increase'].sum()

    # Create an 'Others' category
    others_category = pd.DataFrame({'Company/Fund': ['Others'], 'Val increase': [others_increase]})
    filtered_df = pd.concat([filtered_df, others_category])
    sorted_df = filtered_df.sort_values(by='Val increase', ascending=False)
    total_entries = len(sorted_df)

    # Create the waterfall chart
    fig, ax = plt.subplots(figsize=(10, 6))
    # Get the labels and values
    labels = sorted_df['Company/Fund'].tolist()
    values = sorted_df['Val increase'].tolist()
    # Plot the waterfall chart

    # Convert values to millions
    values_millions = [v / 1e6 for v in values]  # Divide each value by 1 million

    # Plot the waterfall chart
    # Calculate new ylim based on millions
    total_increase_millions = total_increase / 1e6
    others_increase_millions = others_increase / 1e6
    ax.set_ylim(0, total_increase_millions - others_increase_millions)  # Set y-axis limit for clarity

#        ax.set_ylim(0, total_increase - others_increase) # Set y-axis limit for clarity
    cmap = plt.get_cmap('coolwarm', total_entries)  # Use 'viridis' or any other colormap you like
    # Initialize the current value at 0 for the first bar
    current_value = 0
    for i, (label, value) in enumerate(zip(labels, values_millions)):
        next_value = current_value + value
        ax.bar(i, value, bottom=current_value, label=label if i == 0 else "", color=cmap(i), alpha=0.7, width=0.8) # Set label only for the first bar
        current_value = next_value
        ax.text(i, current_value*.9, f"${values[i]:,.0f}", ha='center', va='center')

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha='right')
    ax.set_ylabel("Value Increase ($ M)")
    ax.set_title('Value Increase by Investment (showing > 1%)')
    #plt.legend() # No longer needed since labels are only set for the first bar
    plt.tight_layout()
    st.pyplot(fig)

elif st.session_state.menu_choice == "Round":
    # prompt: Create a pie graph of summarised data that is aggregated by Round and sums the Invested amount
    st.subheader("Round Stats", divider=True)
    st.markdown("Show statistics related to rounds of investment")


    # define the round order to use to reset things as required
    # could use this for filtering/sorting and display order of round data for AngelList for example but have to check that none are missing or it won't display them
    round_order = ['Preseed', 'Pre-Seed', 'Seed', 'Seed+', 'Series A', 'Series A+','Series B', 'Series B+', 'Series C', 'Other']
    # Group by 'Round' and sum 'Invested'
    temp_df = st.session_state.df.copy()
    all_rounds = temp_df['Round'].unique()

    temp_df["Increase"] = temp_df["Net Value"] - temp_df["Invested"]    
    grouped = temp_df.groupby("Round", as_index=False).agg({"Invested":"sum", "Increase":"sum"})
    grouped['Round'] = pd.Categorical(grouped['Round'], categories=round_order, ordered=True)
    grouped.sort_values('Round', inplace=True)

    invested_sum = grouped["Invested"].sum()
    value_sum = grouped[grouped["Increase"] > 0]["Increase"].sum()
    grouped["Perc by Invested"] = grouped["Invested"]/invested_sum if invested_sum !=0 else 0
    grouped["Perc by Increase"] = grouped["Increase"]/value_sum if invested_sum !=0 else 0
    # Get median data
#    median_by_round = temp_df.groupby('Round')['Valuation or Cap'].median()
#    grouped = grouped.merge(median_by_round.rename('Median Round Price'), on='Round', how='left')
    overall_median = temp_df['Valuation or Cap'].median()

    # Create a new column in the grouped dataframe to store the examples
    grouped["Examples"] = ""
    # Iterate through unique rounds and update the "Examples" column
    for round_name in temp_df["Round"].unique():
        examples = show_top_X_increase_and_multiple(temp_df, round_name, 'Round')
        grouped.loc[grouped["Round"] == round_name, "Examples"] = examples

    grouped_styled = grouped.style.format({'Perc by Invested': format_percent, 'Perc by Increase': format_percent, 'Invested': format_currency, 'Increase': format_currency, 'Median Round Price': format_large_number})
    st.dataframe(grouped_styled, hide_index=True)

    # Limited the data displayed
    sorted_df = grouped.sort_values(by='Invested', ascending=False)

    # Create the pie chart showing Invested
    plt.figure(figsize=(8, 8))
    plt.pie(sorted_df["Invested"], labels=sorted_df["Round"], autopct='%1.1f%%', startangle=90)
    plt.title('Investment Amount by Round')
    plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    st.pyplot(plt)

    # Create the pie chart showing Value
    # set all values to 0 that are negative
    grouped.loc[grouped["Increase"] < 0, "Increase"] = 0
    # Limited the data displayed
    sorted_df = grouped.sort_values(by='Increase', ascending=False)

    plt.figure(figsize=(8, 8))
    plt.pie(grouped["Increase"], labels=grouped["Round"], autopct='%1.1f%%', startangle=90)
    plt.title('Value created by Round')
    plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    st.pyplot(plt)

    # Graph the valuation material
    if 'Valuation or Cap' not in temp_df.columns or temp_df['Valuation or Cap'].isnull().all():
        st.write("Data contains no 'Valuation or Cap' data.")
    else:
        top_filter = st.slider("Show how many categories",1,20,4)  
        from matplotlib.ticker import FuncFormatter
        # Create a figure with two subplots - one for the box plot and one for the individual points
        valid_rounds = temp_df['Round'].dropna().unique()
        valid_round_order = [round_name for round_name in round_order if round_name in valid_rounds]
        valid_round_order = valid_round_order[:top_filter]

        fig, ax = plt.subplots(figsize=(12, 10))
        #gridspec_kw={'height_ratios': [2, 1]})
        # 1. First subplot: Box plot with individual points
    #    sns.boxplot(x='Round', y='Valuation or Cap', data=temp_df[temp_df['Round'].isin(valid_rounds)], order=valid_round_order,
        sns.boxplot(x='Round', y='Valuation or Cap', data=temp_df, order=valid_round_order,
                showfliers=False, ax=ax, palette='pastel')
        # Add swarm plot to show individual data points
    #    sns.swarmplot(x='Round', y='Valuation or Cap', data=temp_df[temp_df['Round'].isin(valid_rounds)], order=valid_round_order,
        sns.swarmplot(x='Round', y='Valuation or Cap', data=temp_df, order=valid_round_order,
                    size=8, color='darkblue', alpha=0.7, ax=ax)

        # Add the overall median line
        ax.axhline(y=overall_median, color='red', linestyle='--', 
                label=f'Overall Median: ${overall_median:,.0f}')

        # Format y-axis to show in millions
        def millions(x, pos):
            return f'${x/1000000:.1f}M'
        ax.yaxis.set_major_formatter(FuncFormatter(millions))
        #ax.set_xticklabels(valid_round_order)
        
        # Add title and labels
        ax.set_title('Valuation or Cap by Investment Round with Individual Data Points', fontsize=14)
        ax.set_xlabel('Investment Round', fontsize=12)
        ax.set_ylabel('Valuation or Cap', fontsize=12)
        ax.legend()

        plt.tight_layout()
        st.pyplot(fig)

        # Also print a summary of the data
        st.write("Summary of Valuation/Cap by Round:")
        # Create a summary DataFrame
        summary_data = []
        for round_name in temp_df["Round"].unique():
            round_data = temp_df[temp_df['Round'] == round_name]
            if len(round_data) > 0:
                median_val = round_data['Valuation or Cap'].median()
                min_val = round_data['Valuation or Cap'].min()
                max_val = round_data['Valuation or Cap'].max()
                if pd.isna(median_val): median_val = 0
                if pd.isna(min_val): min_val = 0
                if pd.isna(max_val): max_val = 0
                count = len(round_data)
                summary_data.append({
                    "Round": round_name,
                    "Count": count,
                    "Median": median_val,
                    "Min": min_val,
                    "Max": max_val
                })
            else:
                summary_data.append({"Round": round_name, "Count": 0, "Median": 0, "Min": 0, "Max": 0 })

        # Create a data frame with the summary data
        summary_df = pd.DataFrame(summary_data)
        overall_min = summary_df["Min"].min()
        overall_max = summary_df["Max"].max()
        total_row = pd.DataFrame([["Total", temp_df["Round"].size, overall_median, overall_min, overall_max]], columns=summary_df.columns)
        summary_df = pd.concat([summary_df, total_row], ignore_index=True)
        summary_df['Round'] = pd.Categorical(summary_df['Round'], categories=round_order + ['Total'], ordered=True)

        #summary_df.loc[len(summary_df)] = ["Total", temp_df["Round"].size, overall_median, overall_min, overall_max]
        summary_df = summary_df.sort_values("Round")
        st.dataframe(summary_df.style.format({'Median': format_large_number, 'Min': format_large_number, 'Max': format_large_number}), hide_index=True)

elif st.session_state.menu_choice == "Market":
    st.subheader("Market Stats", divider=True)
    st.markdown("Show statistics related to markets invested in")
    top_filter = st.slider("Show how many in graphs",1,50,10) 

    temp_df = st.session_state.df.copy()

    temp_df["Increase"] = temp_df["Net Value"] - temp_df["Invested"]    
    grouped = temp_df.groupby("Market", as_index=False).agg({"Invested":"sum", "Increase":"sum"})
    invested_sum = grouped["Invested"].sum()
    value_sum = grouped[grouped["Increase"] > 0]["Increase"].sum()
    grouped["Invested %"] = grouped["Invested"]/invested_sum if invested_sum !=0 else 0
    grouped["Increase %"] = grouped["Increase"]/value_sum if invested_sum !=0 else 0

    # Create a new column in the grouped dataframe to store the examples
    grouped["Examples"] = ""

    # Iterate through unique rounds and update the "Examples" column
    for round_name in temp_df["Market"].unique():
        examples = show_top_X_increase_and_multiple(temp_df, round_name, 'Market')
        grouped.loc[grouped["Market"] == round_name, "Examples"] = examples
 
    grouped_styled = grouped.style.format({'Invested %': format_percent, 'Increase %': format_percent, 'Invested': format_currency, 'Increase': format_currency})
    st.dataframe(grouped_styled, hide_index=True)

    # Limited the data displayed
    sorted_df = grouped.sort_values(by='Invested', ascending=False)
    filtered_grouped = sorted_df.head(top_filter)

    # Create the pie chart showing Invested
    plt.figure(figsize=(8, 8))
    plt.pie(filtered_grouped["Invested"], labels=filtered_grouped["Market"], autopct='%1.1f%%', startangle=90)
    plt.title('Investment Amount by Market')
    plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    st.pyplot(plt)

    # Create the pie chart showing Value
    # set all values to 0 that are negative
    grouped.loc[grouped["Increase"] < 0, "Increase"] = 0
    sorted_df = grouped.sort_values(by='Increase', ascending=False)
    filtered_grouped = sorted_df.head(top_filter)

    plt.figure(figsize=(8, 8))
    plt.pie(filtered_grouped["Increase"], labels=filtered_grouped["Market"], autopct='%1.1f%%', startangle=90)
    plt.title('Value created by Market')
    plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    st.pyplot(plt)

elif st.session_state.menu_choice == "Year":
    st.subheader("Yearly Stats", divider=True)
    st.markdown("Yearly investment statistics")

    temp_df = st.session_state.df.copy()

    # Clean 'Invest Date' column
    if 'Invest Date' in temp_df.columns:
        temp_df['Year'] = temp_df['Invest Date'].dt.year

    # Group by year
    if 'Year' in temp_df.columns:
        summary_df = temp_df.groupby('Year').agg(
            Investments=('Year', 'count'),
            Leads=('Lead', 'nunique'),
            Invested=('Invested', 'sum'),
            Value=('Net Value', 'sum'),
            Avg = ('Invested', 'mean'),
            Min=('Invested', 'min'),
            Max=('Invested', 'max')
        ).reset_index()

        summary_df['Multiple'] = summary_df['Value']/summary_df['Invested']
        formatted_summary_df = summary_df.style.format({'Multiple': format_multiple, 'Invested': format_currency, 'Value': format_currency, 'Min': format_currency, 'Max': format_currency, 'Avg': format_currency})
        st.dataframe(formatted_summary_df, hide_index=True)

        # Display a nice graph
        fig, ax1 = plt.subplots(figsize=(12, 6))
        # Bar plot for Invested Amount and Value against each other with multiple displayed
        ax1.bar(summary_df['Year'], summary_df['Value'], color='green', label='Net Value')  # Adjust alpha for visibilit
        ax1.set_xlabel('Investment Year')
        ax1.set_ylabel('Invested Amount', color='skyblue')
        ax1.tick_params(axis='y', labelcolor='skyblue')
        ax1.set_xticks(summary_df['Year']) # Set x-ticks to years
        ax1.bar(summary_df['Year'], summary_df['Invested'], color='skyblue', label='Invested Amount', alpha=0.5)
        # Add annotations for Multiple values on top of the bars
        for i, multiple in enumerate(summary_df['Multiple']):
            ax1.text(summary_df['Year'][i], summary_df['Value'][i], f'{multiple:.2f} x', ha='center', va='bottom')
        # Combine legends
        lines, labels = ax1.get_legend_handles_labels()
        #lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines, labels, loc='upper right')

        plt.title('Analysis by Year')
        st.pyplot(plt)
        
        # Show the second graph of Investments over time
        # prompt: Sort df by Invest Date. Graph invest date by amount and show it as a scatterpot using Seaborn. Also on the right hand axis show the cumulative amount invested over time as bars representing a month of time
        import matplotlib.ticker as mtick

        # Sort by Invest Date before calculating cumulative sum
        temp_df.sort_values(by='Invest Date', inplace=True)
        # Calculate cumulative investment
        temp_df['Cumulative Invested'] = temp_df['Invested'].cumsum()        
            # Create the figure and axes
        fig, ax1 = plt.subplots(figsize=(12, 6))
        # Plot the scatter plot on the first axis
        sns.scatterplot(x='Invest Date', y='Invested', data=temp_df, ax=ax1, label='Investment Amount', color="blue")
        ax1.set_xlabel('Date of Investment')
        ax1.set_ylabel('Amount Invested', color='blue')
        ax1.tick_params(axis='y', labelcolor='blue')
        # Create a second y-axis for the cumulative investment
        ax2 = ax1.twinx()
        # Calculate monthly cumulative investments
        df_monthly = temp_df.groupby(pd.Grouper(key='Invest Date', freq='ME'))['Cumulative Invested'].last().reset_index()
        # Plot the cumulative investment as bars on the second axis
        ax2.bar(df_monthly['Invest Date'], df_monthly['Cumulative Invested'], width=25, color="orange", alpha = 0.5, label='Cumulative Investment')
        ax2.set_ylabel('Cumulative Amount Invested', color='orange')
        ax2.tick_params(axis='y', labelcolor='orange')
        # Format y-axis ticks as currency
        formatter = mtick.FormatStrFormatter('$%1.0f')
        ax1.yaxis.set_major_formatter(formatter)        
        ax2.yaxis.set_major_formatter(formatter)
        # Set title and rotate x-axis labels
        plt.title('Investment amount over time')
        plt.xticks(rotation=45)
        # Add legends
        lines, labels = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        # Only show one legend
        ax1.get_legend().remove()
        ax2.legend(lines + lines2, labels + labels2, loc='upper center')
        # Improve layout
        plt.tight_layout()
        st.pyplot(fig)        
    else:
        st.write("Error: 'Invest Date' or 'Value' column not found in DataFrame.")

elif st.session_state.menu_choice == "Lead Stats":        
    st.subheader("Lead Stats", divider=True)
    st.markdown("Show statistics about the top deal leads")

    # Show the stats regarding Syndicate LEads
    top_filter = st.slider("Show how many",1,60,5)   

    # Load the data from the session state
    df = st.session_state.df

    # now group them by Lead and calculate the average multiple
    aggregated_df = df.groupby('Lead').agg(
                Investments=('Company/Fund', 'size'),
                Invested=('Invested', 'sum'),
                Unrealized=('Unrealized Value', 'sum'),
                Invested_avg=('Invested', 'mean'),
                Value=('Unrealized Value', 'sum')
    ).reset_index()

    # Exclude where no value as sum (result would be infinite)
    #aggregated_df = aggregated_df[aggregated_df["sum_value"] != 0]

    # Calculate average multiple
    aggregated_df['Multiple'] = (aggregated_df['Value'] / aggregated_df['Invested'])

    # Get the realised count
    # Filter for rows where Status is 'Realized'
    realized_df = df[df['Status'] == 'Realized']
    # Group by Lead and count the number of rows
    realized_counts = realized_df.groupby('Lead').size().reset_index(name='num_Realized')
    # Merge the realized counts back into the aggregated DataFrame
    aggregated_df = pd.merge(aggregated_df, realized_counts, on='Lead', how='left').fillna(0)

    aggregated_df['Realised %'] = aggregated_df['num_Realized']/aggregated_df['Investments']
    aggregated_df['num_Realized'] = aggregated_df['num_Realized'].astype(int)
    # Take top values
    top_X_num = aggregated_df.nlargest(top_filter, 'Multiple')

    # Shows the companies with the top multiples in 'Company (X.X)x, ...' format by matching on the Lead = mname
    # Not sure how to generalise this but if I can then can reduce file size

    # Create a new column in the grouped dataframe to store the examples
    top_X_num["Best"] = ""
    top_X_num["Worst"] = ""

    # Iterate through unique rounds and update the "Examples" column
    topX = 4
    for lead_name in top_X_num["Lead"].unique():
        examples = show_top_X_names_based_on_multiple_by_Lead(topX, df, lead_name)
        top_X_num.loc[top_X_num["Lead"] == lead_name, "Best"] = examples
        examples = show_realised_based_on_Lead(topX, df, lead_name)
        top_X_num.loc[top_X_num["Lead"] == lead_name, "Worst"] = examples

    # Reorder columns to place 'Real Multiple' and 'XIRR' after 'Company/Fund'
    cols = top_X_num.columns.tolist()
    if 'Real Multiple' in cols and 'XIRR' in cols and 'Company/Fund' in cols :
        cols.remove('Real Multiple')
        cols.remove('XIRR')
        company_index = cols.index('Company/Fund')
        cols.insert(company_index + 1, 'Real Multiple')
        cols.insert(company_index + 2, 'XIRR')
        top_X_num = top_X_num[cols]

    # Apply the formatting using Pandas Styler - this doesn't seem to work
    styled_df = top_X_num.style.format({'Realised %': format_percent, 'Invested' : format_currency, 'Unrealized': format_currency, 'Invested_avg': format_currency, 'Value': format_currency, 'Multiple': format_multiple})
    st.dataframe(styled_df, hide_index=True)

elif st.session_state.menu_choice == "Leads no values":
    st.subheader("Leads with no disclosed valuation data", divider=True)
    st.markdown("Show all the leads that aren't showing the value of their investments (or what % they aren't disclosing).")            
    
    df = st.session_state.df

    # Calculate the percentage of companies with 'Locked' in the 'Net Value' column for each deal lead and identifies the lead with the highest percentage
    # Group by Lead and aggregate investment count, average Invested, average Multiple and locked percentage
    grouped = df.groupby('Lead').agg(
        total_investments=('Company/Fund', 'size'),
        avg_invested=('Invested', 'mean'),
        sum_invested=('Invested', 'sum'),
        locked_count=('Valuation Unknown', 'sum')
    ).reset_index()

    # Add locked %
    grouped['locked_percentage'] = 100 * grouped['locked_count'] / grouped['total_investments']
    # Filter out the values that are zero
    filtered_df = grouped[grouped['locked_percentage'] > 0]

    if filtered_df.empty:
        st.write ("There are no leads with no valuation data in this dataset.")
    else:
        # Sort based on locked_percentage descending, remove excess columns and rename columns
        result = filtered_df.sort_values(by='locked_percentage', ascending=False)
        result = result.sort_values(by='locked_count', ascending=False)
        result  = result.drop(columns=['locked_count', 'locked_percentage'])
        result = result.rename(columns={"total_investments": "Investments", "avg_invested": "Avg Invested", "sum_invested" : "Sum Invested"})
        # Neatly format everything
        # Apply the formatting using Pandas Styler - this doesn't seem to work

        styled_df = result.style.format({'Avg Invested': format_currency, 'Sum Invested' : format_currency})
        st.dataframe(styled_df, hide_index=True)

elif st.session_state.menu_choice == "Realized":
    st.subheader("Realized Investments", divider=True)
    st.markdown("Show all the deals that were exited either as a full loss (Dead) or with a (partial) return of capital as recorded by AngelList")
    st.markdown("Note that IRR has not been recalculated here based on actual exit dates")
    
    # Load the data from the session state
    df = st.session_state.df

    # Find rows where 'Status' is 'Realized' or 'Dead' - note not using Dead any more
    status_realized_or_dead = df[df['Status'].isin(['Realized', 'Dead'])]

    # Calculate profit and loss and Real Multiple (can be inaccurate in AngelList)
    result_a = status_realized_or_dead.copy()
    result_a["Profit"] = result_a["Realized Value"] - result_a["Invested"]
    result_a['Real Multiple'] = result_a['Realized Value']/result_a['Invested']
    result_sorted = result_a.sort_values(by='Real Multiple', ascending=False)        

    # reorder some columns
    # insert Multiple after and remove the prior position 
    name_column_index = result_sorted.columns.get_loc('Company/Fund')
    result_sorted.insert(name_column_index+1, 'Lead', result_sorted.pop('Lead'))
    result_sorted.insert(name_column_index+1, 'XIRR', result_sorted.pop('XIRR'))
    result_sorted.insert(name_column_index+1, 'Profit', result_sorted.pop('Profit'))
    result_sorted.insert(name_column_index+1, 'Real Multiple', result_sorted.pop('Real Multiple'))
    result_sorted['XIRR']=result_sorted['XIRR']*100 # For display only

    # Put in the summary analysis to help people understand what is happening here
    #display_text = f"Successful exits: turned ${st.session_state.invested_realised_1x:,.2f} into ${st.session_state.value_realised_1x:,.2f} a {(st.session_state.value_realised_1x/st.session_state.invested_realised_1x):.1f}x multiple" 
    #st.text(display_text)
    #display_text = f"Other exits: turned ${st.session_state.invested_realised_less1x:,.2f} into ${st.session_state.value_realised_less1x:,.2f} a {(st.session_state.value_realised_less1x/st.session_state.invested_realised_less1x):.1f}x multiple" 
    #st.text(display_text)
    st.text("Note that other amounts may have been realised but those investments aren't fully realised yet - eg partial earn outs")

    if st.session_state.has_enhanced_data_file:
        enhanced_df = pd.merge(result_sorted, st.session_state.df2, on='Company/Fund', how='left')
        # enhanced needs to be resorted too
        enhanced_df.insert(name_column_index+1, 'Comment', enhanced_df.pop('Comment'))
        enhanced_df.insert(name_column_index+1, 'AngelList URL', enhanced_df.pop('AngelList URL'))
        result_sorted = enhanced_df

    # Display everything in a St editor block
    format_st_editor_block(result_sorted)

elif st.session_state.menu_choice == "Graphs":
    st.subheader("Graphs", divider=True)
    st.markdown("Shows some key graphs and analysis")

    # Load the data from the session state
    df = st.session_state.df

    # set themes and sizes - note I couldn't display it neatly
    sns.set_theme()

    # Set up the formatting and dimensions
    col1, col2 = st.columns(2)
    col3, col4 = st.columns(2)
    col5, col6 = st.columns(2)

    # 1. Distribution of Multiples > 1
    with col1:
        data_mult = df[df['Real Multiple'] > 1]['Real Multiple'].dropna()
        fig, ax = plt.subplots()
        sns.histplot(data=data_mult, bins=20, color='skyblue')
        ax.set_title('Distribution of Investment Multiples (>1x)')
        ax.set_xlabel('Multiple')            
        ax.set_ylabel('Count')    
        st.pyplot(fig)
        
    # 2. Distribution of Investment Amounts
    with col2:
        fig, ax = plt.subplots()
        sns.histplot(data=df['Invested'].dropna(), bins=20, color='salmon')
        ax.set_title('Distribution of Investment Amounts')
        ax.set_xlabel('Investment Amount ($)')
        ax.set_ylabel('Count')
        st.pyplot(fig)
        
    # 3. Investment Amount vs Multiple (for multiples > 1)
    with col3:
        scatter_df = df[(df['Real Multiple'] > 1) & (df['Invested'].notnull())]
        fig, ax = plt.subplots()
        sns.regplot(data=scatter_df, x='Invested', y='Real Multiple', color='red', scatter_kws={'color': 'purple', 'alpha': 0.6})          
        ax.set_title('Investment Amount vs Multiple')
        ax.set_xlabel('Investment Amount ($)')
        ax.set_ylabel('Multiple')
        st.pyplot(fig)

    # 4. Pie chart of Lead summary for Multiples > 2
    with col4:
        high_multiple_deals = df[df['Real Multiple'] > 2]
        lead_summary = high_multiple_deals['Lead'].value_counts()
        fig, ax = plt.subplots()          
        ax.pie(lead_summary, labels=lead_summary.index, autopct='%1.1f%%', startangle=90, colors=sns.color_palette('pastel'))
        ax.set_title('Lead Summary for Multiples > 2')
        st.pyplot(fig)

    # 5. Plot of Instrument vs Invested
    with col5:
        if 'Instrument' in df.columns :
            # Really dumb way of fudging the legends by renaming in the data
            # Calculate the percentage of total investment for each instrument
            instrument_investment_percentage = df.groupby('Instrument')['Invested'].sum() / df['Invested'].sum() * 100
            # Set up a temporary data set and rename all the Instruments to showing % so they are in the final graph
            df_temp = df.copy()
            df_temp['Instrument'] = df_temp['Instrument'].replace("debt", f"debt ({instrument_investment_percentage.get('debt', 0):.1f}%)")
            df_temp['Instrument'] = df_temp['Instrument'].replace("equity", f"equity ({instrument_investment_percentage.get('equity', 0):.1f}%)")
            df_temp['Instrument'] = df_temp['Instrument'].replace("safe", f"safe ({instrument_investment_percentage.get('safe', 0):.1f}%)")
            # Create the violin plot
            fig, ax = plt.subplots(figsize=(10, 6))  # Increase figure size
            sns.violinplot(df_temp, x='Invested', y='Instrument', hue='Instrument', inner='stick', ax=ax)
            sns.despine(top=True, right=True, bottom=True, left=True)
            ax.set_title('Instrument vs Invested')
            ax.set_xlabel('Investment Amount ($)')
            ax.set_ylabel('Instrument')
            # ax.legend(loc='upper right') - wasn't displaying clearly
            plt.tight_layout()  # Improve layout
            st.pyplot(fig)

    # 5. Plot of Round Size and Multiple
    # from scipy import stats
    # import numpy as np

    # Filter out rows with missing or unrealistic multiples
    df_filtered = df.dropna(subset=['Round Size', 'Real Multiple'])

    # Calculate correlation
    correlation = df_filtered['Round Size'].corr(df_filtered['Real Multiple'])
    st.write('Correlation coefficient between Round Size and Multiple: {:.2f}', correlation)

    # Print some key statistics
    st.write("Average Multiple (>1x): {:.2f}".format(data_mult.mean()))
    st.write("Median Multiple (>1x): {:.2f}".format(data_mult.median()))
    st.write("Average Investment Amount: ${:,.2f}".format(df['Invested'].mean()))
    st.write("Median Investment Amount: ${:,.2f}".format(df['Invested'].median()))

elif st.session_state.menu_choice == "Tax":
    st.subheader("Tax and Finance Analysis", divider=True)
    st.markdown("Look at the money flows (money into the account, out of the account). This is in preparation for tax time but also to more accurately calculate the XIRR by using exact dates of returned funds.")
    if st.session_state.has_finance_data_file:
        df3 = st.session_state.df3
    else:
        uploaded_file = st.file_uploader("Choose the AngelList finance file in a CSV format", type="csv")
    # If the uploaded_file is true
    if uploaded_file is not None :
        try:
            df3 = pd.read_csv(uploaded_file, header=0, skip_blank_lines=True)
            st.session_state.has_finance_data_file = True
            st.session_state.df3 = df3
            with st.container(height=200):
                st.write(df3)
        except pd.errors.ParserError:
            st.write(f"Error: Could not parse file as a CSV file. Please ensure it's a valid CSV.")
        except Exception as e:
            st.write(f"An unexpected error occurred: {e}")
    
    if st.session_state.has_finance_data_file :
        # Group by 'Transaction type' and sum the 'Amount'
        subtotals = df3.groupby('Transaction')['Amount'].sum()
        st.table(subtotals)

        # prompt: Create a new column called 'Company/Fund' that looks at the Transaction and Description column. It should have an empty value where 'Transaction' is a Deposit or Refill otherwise it should return the value from 'Description' but ignore words like "Closing Proceeds", "Amount Adjustment for", "Refund for", "Investment in", "Return of Capital", "Dissolution Proceeds" and also ignore anything after an initial hyphen ('-').
        # Ignore specific phrases
        phrases_to_remove = ["Closing Proceeds from", "Amount adjustment for", "Refund for", "Closing proceeds from",
                            "Investment in", "For investment in", "Return of Capital", "Dissolution Proceeds", "Holdback", "Acquisition", "acquisition.", "acquisition", "Merger", "Distribution"]
        # Escape special characters in phrases for regex
        escaped_phrases = [re.escape(phrase) for phrase in phrases_to_remove]
        # Create a regex pattern to match any of the phrases
        pattern = "|".join(escaped_phrases)
        
        # Apply the function to create the new 'Company/Fund' column
        df3['Company/Fund'] = df3.apply(lambda row: "" if row['Transaction'] in ['Deposit', 'Refill'] else extract_company_name(row['Description'], pattern), axis=1)
        df3['New Date'] = df3['Date'].apply(convert_date)

        # prompt: Show all the values where there is one or more matches on Company/Fund, sort them by Company/Fund but also by Date in reverse order. Drop the Balance column and show the Company/Fund coloumn first. Don't show any values where there isn't an entry on the Company/Fund column. Also convert the date to a date field first. As a final step only show company/Fund values where there was at least one Disbursement
        # Filter out rows where 'Company/Fund' is empty
        df_t = df3[df3['Company/Fund'] != ""]
        # Group by 'Company/Fund' and check if there's at least one disbursement
        companies_with_disbursements = df_t[df_t['Transaction'] == 'Disbursement'].groupby('Company/Fund').size().index
        # Filter the DataFrame to keep only companies with disbursements
        df_f = df_t[df_t['Company/Fund'].isin(companies_with_disbursements)]
        # Sort the DataFrame by 'Company/Fund' and 'Date' in reverse order
        df_sorted = df_f.sort_values(['Company/Fund', 'New Date'], ascending=[True, True])
        # Drop the 'Balance' column
        df_sorted = df_sorted.drop(columns=['Balance'])
        # Reorder columns to show 'Company/Fund' first
        cols = ['Company/Fund', 'New Date', 'Transaction', 'Description', 'Amount', 'Date'] # + [col for col in df_sorted.columns if col != 'Company/Fund']
        df_final = df_sorted[cols]
        # Display the final DataFrame
        st.write("These are the companies that have more than just an investment")
        st.table(df_final)
