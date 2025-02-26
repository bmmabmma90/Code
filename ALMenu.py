# AL_Menu
# Streamlit menu selection and front end for AngelList
# Needs to handle a range of things better

import streamlit as st
import pandas as pd
from matplotlib import pyplot as plt
import seaborn as sns
import squarify
import numpy as np
from pyxirr import xirr
from datetime import datetime

st.set_page_config(layout="wide")
st.title("AngelList Startup Data Analyser")

# Set has no data file until one is read in correctly
if 'has_data_file' not in st.session_state: 
    st.session_state.has_data_file = False
if 'has_enhanced_data_file' not in st.session_state: 
    st.session_state.has_enhanced_data_file = False
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
        option = st.selectbox(
            "Choose an option:",
            ("About", "Load Data", "Stats", "Top Investments", "Round", "Market", "Year", "Realized", "Lead Stats", "Leads no markups", "Graphs")
        )
    else:
        option = st.selectbox(
            "Choose an option:",
            ("About", "Load Data")
        )
        
# Perform actions based on the selected option
if option == "About" :
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
'''
    st.markdown(multi)

elif option == "Load Data":
    st.subheader("Load in data file(s) for processing", divider=True)
    
    # Display if already loaded and button not pressed or where data hasn't been loaded
    # Check if already loaded
# Force load allows you to ignore the Load Data with specific data
    force_load = True
    if force_load == True:
        df = pd.read_csv(r"/Users/deepseek/Downloads/ben-armstrong_angellist_investments_2025_02_21.csv", header=1, skip_blank_lines=True)
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
        uploaded_file = st.file_uploader("Choose the AngelList file in a CSV format", type="csv")

    if force_load == False and uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file, header=1, skip_blank_lines=True)
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
    
        # Action 2 is all the data normalisation and analysis logic
    # Only do it if there is data in the data frame otherwise suggest load the data
    if st.session_state.has_data_file:
        # Set the df locally from the data session
        df = st.session_state.df
    
    # Do all the data processing    
    # 1. Drop the data we don't analyse for easy display / debugging - 'Round', 'Market', 'Round Size', 'Invest Date'
        todrop = { 'Investment Entity',
                'Investment Type', 'Fund Name', 'Allocation',  
                'Instrument', 'Valuation or Cap Type', 'Valuation or Cap', 
                'Discount', 'Carry', 'Share Class'}
        # Get the actual column names from the DataFrame
        df_columns = df.columns
        # Convert the column names to a set for efficient comparison
        df_columns_set = set(df_columns)
        # Create a new set with only the columns that are present in the DataFrame
        todrop_filtered = {col for col in todrop if col in df_columns_set}
        # Drop the filtered columns
        df = df.drop(columns=todrop_filtered)

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

        # Calculate basic XIRR for values 
        # improvement would be where some realised value to look at the financial information in AngelList and put in the other data to calculate this more clearly (overwriting this)
        now = datetime.now()
        df['XIRR'] = 0.0  # Set column to zero as a float
        for index, row in df.iterrows():
            if row['Net Value'] > 0: # Ignore calculating if net value is 0, ie leave XIRR as 0.0 for these
                try:
                    dates = [row['Invest Date'], now]
                    amounts = [-row['Invested'], row['Net Value']]
                    df.loc[index, 'XIRR'] = xirr(dates, amounts)
                except Exception as e:
                    print(f"Error calculating XIRR for row {index}: {e}")
                    df.loc[index, 'XIRR'] = float('nan')  # or some other appropriate value
        
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
            percentage = (invested_sum / total_invested_original) * 100 if total_invested_original !=0 else 0

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

        # Set session state values for other screens
        st.session_state.df = df
        st.session_state.sumdf = summary_df

        st.session_state.num_uniques = num_uniques
#       st.session_state.total_investments = total_investments
        st.session_state.num_leads = num_leads
        st.session_state.num_zero_value_leads = num_zero_value_leads
        st.session_state.num_locked = num_locked

elif option == "Stats":
    st.subheader("Investment Statistics", divider=True)
    st.markdown("Show statistics across the portfolio.  NB: You will need to go into AngelList to get the total portfolio value which is then used to work out the value increase/decrease of all 'Locked' investments")
    # Write all the outputs to the screen
    total_value = st.number_input("Insert the total value from AngelList")
        
    if st.session_state.has_data_file:
        # Write all the outputs to the screen
        def format_currency(amount) :
            return '${:,.2f}'.format(amount)
        def format_multiple(amount) :
            return '{:.2f}x'.format(amount)
        # Calculate the total value using an estimate

        a, b, f, g = st.columns(4) # Macro stats - investments + companies plus syndicate stats
        c, d, e = st.columns(3) # Macro valuation stats - total value, net value and invested $
#       f, g = st.columns(2) # Syndicate info

        sumdf = st.session_state.sumdf
        a.metric(label="Investments", value=sumdf.loc[sumdf['Category'] == 'Totals', 'Count'].iloc[0], border=True)
        b.metric(label="Companies", value=st.session_state.num_uniques, border=True)
        if total_value > 0:
            st.session_state.total_value = total_value
            locked_value = total_value - sumdf.loc[sumdf['Category'] == 'Totals', 'Unrealized'].iloc[0]
            st.session_state.sumdf.loc[st.session_state.sumdf['Category'] == 'Locked', 'Unrealized'] = locked_value
            st.session_state.sumdf.loc[st.session_state.sumdf['Category'] == 'Totals', 'Unrealized'] = total_value
            c.metric(label="Total Value $",value=format_currency(total_value), border=True)
            d.metric(label="Multiple (x)",value=format_multiple(st.session_state.total_value/sumdf.loc[sumdf['Category'] == 'Totals', 'Invested'].iloc[0]), border=True)
        e.metric(label="Invested $",value=format_currency(sumdf.loc[sumdf['Category'] == 'Totals', 'Invested'].iloc[0]), border=True)
        f.metric(label="Syndicates Invested",value=st.session_state.num_leads, border=True)
        g.metric(label="Syndicates no value info",value=st.session_state.num_zero_value_leads, border=True)

        # Neatly format everything
        st.data_editor(
            st.session_state.sumdf,
                    column_config= {
                    "Percentage": st.column_config.NumberColumn(
                        "Percentage", help="Percentage of all invested capital", format="%.1f"
                    ),
                    "Multiple": st.column_config.NumberColumn(
                        "Multiple", help="Multiple expressed as total value (realised and unrealised) / invested amount", format="%.2f x"
                    )
                    },
            hide_index=True,
        )

elif option == "Top Investments":
    st.subheader("Top Investments", divider=True)
    st.markdown('''Show selected top investments across the portfolio (by return multiple).  
                 You can use the slider to restrict the number of values shown on the screen
    ''')
    if st.session_state.has_data_file:
        # Write all the outputs to the screen
        top_filter = st.slider("Show how many",1,50,5)   
        # Calculate the top X investments by multiple and show information for them

        # Load the data from the session state
        df = st.session_state.df
        filtered_df = df[df['Multiple'] > 1]
        sorted_df = filtered_df.dropna(subset=['Multiple']).sort_values(by='Multiple', ascending=False)

        # Get ready for screen display - drop columns and format
        # Drop the filtered columns
        sorted_df = sorted_df.drop(columns=['Status','Valuation Unknown', 'Real Multiple'])
        # Get the top X investments
        top_X_num = sorted_df.head(top_filter)

        # Merge the cleaned dataset with the sample dataset using 'Company/Fund' as the key
        if st.session_state.has_enhanced_data_file:
            enhanced_df = pd.merge(top_X_num, st.session_state.df2, on='Company/Fund', how='left')
        
            # format it nicely
            def format_percentage(val): return "{:.2%}".format(val*100) # Formats to 2 decimal places 
            # Apply the formatting using Pandas Styler 
            styled_df = enhanced_df.style.format({'XIRR': format_percentage})

            st.data_editor(
                styled_df, 
                column_config= {
                    "URL": st.column_config.LinkColumn(
                        "Website", help="The link to the website for the company"
                    ),
                    "AngelList URL": st.column_config.LinkColumn(
                        "Website", help="The link to your AngelList investment record", display_text="AL Link"
                    ),
                    "Multiple": st.column_config.NumberColumn(
                        "Multiple", help="Multiple expressed as total value / invested amount", format="%.2f x"
                    ),
                    "Invested": st.column_config.NumberColumn(
                        "Invested", help="Dollars invested (rounded to nearest whole number)", format="$%.0f"
                    ), 
                    "Net Value": st.column_config.NumberColumn(
                        "Net Value", help="Total value including realised and unrealized (rounded to nearest whole number)", format="$%.0f"
                    ),
                    "Unrealized Value": st.column_config.NumberColumn(
                        "Unreal $", help="Unrealized value of the investment as reported by the deal lead (rounded to nearest whole number)", format="$%.0f"
                    ), 
                    "Realized Value": st.column_config.NumberColumn(
                        "$ Received", help="Realized value as reported by AngelList (rounded to nearest whole number)", format="$%.0f"
                    ) 
                },
                hide_index=True,
            )
        else :
            # Data structure and interactive data
            st.data_editor(
                top_X_num, 
                column_config= {
                    "Multiple": st.column_config.NumberColumn(
                        "Multiple", help="Multiple expressed as total value / invested amount", format="%.1f x"
                    ),
                    "Invested": st.column_config.NumberColumn(
                        "Invested", help="Dollars invested (rounded to nearest whole number)", format="$%.0f"
                    ), 
                    "Net Value": st.column_config.NumberColumn(
                        "Net Value", help="Total value including realised and unrealized (rounded to nearest whole number)", format="$%.0f"
                    ),
                    "Unrealized Value": st.column_config.NumberColumn(
                        "Unreal $", help="Unrealized value of the investment as reported by the deal lead (rounded to nearest whole number)", format="$%.0f"
                    ), 
                    "Realized Value": st.column_config.NumberColumn(
                        "$ Received", help="Realized value as reported by AngelList (rounded to nearest whole number)", format="$%.0f"
                    ) 
                },
                hide_index=True,
            )
        # Show a tree graph that looks nice
        # Calculate sizes based on Net Value
        sizes = top_X_num['Net Value']
        labels = [f"{company}\n({multiple:.1f}x)" for company, multiple in zip(top_X_num['Company/Fund'], top_X_num['Multiple'])]
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
        ax.set_ylim(0, total_increase - others_increase) # Set y-axis limit for clarity
        cmap = plt.get_cmap('coolwarm', total_entries)  # Use 'viridis' or any other colormap you like
        # Initialize the current value at 0 for the first bar
        current_value = 0
        for i, (label, value) in enumerate(zip(labels, values)):
            next_value = current_value + value
            ax.bar(i, value, bottom=current_value, label=label if i == 0 else "", color=cmap(i), alpha=0.7, width=0.8) # Set label only for the first bar
            current_value = next_value
            ax.text(i, current_value*.9, f"{value:.0f}", ha='center', va='center')

        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha='right')
        ax.set_ylabel("Value Increase")
        ax.set_title("Waterfall Chart of Value Increase by Investment (Over 1%)")
        #plt.legend() # No longer needed since labels are only set for the first bar
        plt.tight_layout()
        st.pyplot(plt)

    else:
        st.write("Please Load Data file first before proceeding")  

elif option == "Round":
    # prompt: Create a pie graph of summarised data that is aggregated by Round and sums the Invested amount
    st.subheader("Round Stats", divider=True)
    st.markdown("Show statistics related to rounds of investment")
    top_filter = st.slider("Show how many in graphs",1,50,10) 

    # Group by 'Round' and sum 'Invested'
    temp_df = st.session_state.df.copy()

    temp_df["Increase"] = temp_df["Net Value"] - temp_df["Invested"]
    grouped = temp_df.groupby("Round", as_index=False).agg({"Invested":"sum", "Increase":"sum"})
    invested_sum = grouped["Invested"].sum()
    value_sum = grouped[grouped["Increase"] > 0]["Increase"].sum()
    grouped["Perc by Invested"] = grouped["Invested"]/invested_sum * 100 if invested_sum !=0 else 0
    grouped["Perc by Increase"] = grouped["Increase"]/value_sum * 100 if invested_sum !=0 else 0

    def show_top_X_increase_and_multiple(df, round_name):
        round_df = df[df["Round"] == round_name].sort_values(by="Increase", ascending=False)
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

    # Create a new column in the grouped dataframe to store the examples
    grouped["Examples"] = ""

    # Iterate through unique rounds and update the "Examples" column
    for round_name in temp_df["Round"].unique():
        examples = show_top_X_increase_and_multiple(temp_df, round_name)
        grouped.loc[grouped["Round"] == round_name, "Examples"] = examples
 
    st.write(grouped)

    # Limited the data displayed
    sorted_df = grouped.sort_values(by='Invested', ascending=False)
    filtered_grouped = sorted_df.head(top_filter)

    # Create the pie chart showing Invested
    plt.figure(figsize=(8, 8))
    plt.pie(filtered_grouped["Invested"], labels=filtered_grouped["Round"], autopct='%1.1f%%', startangle=90)
    plt.title('Investment Amount by Round')
    plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    st.pyplot(plt)

    # Create the pie chart showing Value
    # set all values to 0 that are negative
    grouped.loc[grouped["Increase"] < 0, "Increase"] = 0
    # Limited the data displayed
    sorted_df = grouped.sort_values(by='Increase', ascending=False)
    filtered_grouped = sorted_df.head(top_filter)

    plt.figure(figsize=(8, 8))
    plt.pie(grouped["Increase"], labels=grouped["Round"], autopct='%1.1f%%', startangle=90)
    plt.title('Value created by Round')
    plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    st.pyplot(plt)

elif option == "Market":
    st.subheader("Market Stats", divider=True)
    st.markdown("Show statistics related to markets invested in")
    top_filter = st.slider("Show how many in graphs",1,50,10) 

    temp_df = st.session_state.df.copy()

    temp_df["Increase"] = temp_df["Net Value"] - temp_df["Invested"]
    grouped = temp_df.groupby("Market", as_index=False).agg({"Invested":"sum", "Increase":"sum"})
    invested_sum = grouped["Invested"].sum()
    value_sum = grouped[grouped["Increase"] > 0]["Increase"].sum()
    grouped["Perc by Invested"] = grouped["Invested"]/invested_sum * 100 if invested_sum !=0 else 0
    grouped["Perc by Increase"] = grouped["Increase"]/value_sum * 100 if invested_sum !=0 else 0

    def show_top_X_increase_and_multiple(df, round_name):
        round_df = df[df["Market"] == round_name].sort_values(by="Increase", ascending=False)
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

    # Create a new column in the grouped dataframe to store the examples
    grouped["Examples"] = ""

    # Iterate through unique rounds and update the "Examples" column
    for round_name in temp_df["Market"].unique():
        examples = show_top_X_increase_and_multiple(temp_df, round_name)
        grouped.loc[grouped["Market"] == round_name, "Examples"] = examples
 
    st.write(grouped)

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

elif option == "Year":
    st.subheader("Yearly Stats", divider=True)
    st.markdown("Show statistics related to investments by year")

    temp_df = st.session_state.df.copy()

    # Clean 'Invest Date' column
    if 'Invest Date' in temp_df.columns:
        temp_df['Invest Date'] = pd.to_datetime(temp_df['Invest Date'], errors='coerce')
        temp_df['Invest Year'] = temp_df['Invest Date'].dt.year

    # Group by year
    if 'Invest Year' in temp_df.columns:
        summary_df = temp_df.groupby('Invest Year').agg(
            Num_Investments=('Invest Year', 'count'),
            Invest_Value=('Invested', 'sum'),
            Min=('Invested', 'min'),
            Max=('Invested', 'max'),
            Total_Value=('Net Value', 'sum'),
            Leads=('Lead', 'nunique')
        ).reset_index()
        
        summary_df['Multiple'] = summary_df['Total_Value']/summary_df['Invest_Value']
    #pct_change() * 100
                # Neatly format everything
        st.data_editor(
            summary_df, 
            column_config= {
                "Invest Year": st.column_config.NumberColumn(
                    "Year", help="The year in which the investment was made", format="%d"
                ),
                "Num_investments": st.column_config.NumberColumn(
                    "#", help="Number of investments", format="%d"
                ),
                "Invest_Value": st.column_config.NumberColumn(
                    "Invested", help="Total invested that year", format="$%.0f"
                ), 
                "Min": st.column_config.NumberColumn(
                    "Min", help="Smallest investment that year", format="$%.0f"
                ),
                "Max": st.column_config.NumberColumn(
                    "Max", help="Biggest investment that year", format="$%.0f"
                ),
                "Total_Value": st.column_config.NumberColumn(
                    "Value", help="Total value of investments made that year", format="$%.0f"
                ), 
                "Multiple": st.column_config.NumberColumn(
                    "Multiple", help="The total multiple for that year", format="%.2f x"
                ) 
            },
            hide_index=True,
        )

        # Display a nice graph
        fig, ax1 = plt.subplots(figsize=(12, 6))

        # Bar plot for Invested Amount
        ax1.bar(summary_df['Invest Year'], summary_df['Total_Value'], color='green', label='Net Value')  # Adjust alpha for visibilit

        ax1.set_xlabel('Investment Year')
        ax1.set_ylabel('Invested Amount', color='skyblue')
        ax1.tick_params(axis='y', labelcolor='skyblue')
        ax1.set_xticks(summary_df['Invest Year']) # Set x-ticks to years
        ax1.bar(summary_df['Invest Year'], summary_df['Invest_Value'], color='skyblue', label='Invested Amount', alpha=0.5)

        # Add annotations for Multiple values on top of the bars
        for i, multiple in enumerate(summary_df['Multiple']):
            ax1.text(summary_df['Invest Year'][i], summary_df['Invest_Value'][i], f'{multiple:.2f} x', ha='center', va='bottom')

        # Combine legends
        lines, labels = ax1.get_legend_handles_labels()
        #lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines, labels, loc='upper right')

        plt.title('Analysis by Year')
        st.pyplot(plt)

    else:
        st.write("Error: 'Invest Date' or 'Value' column not found in DataFrame.")


elif option == "Lead Stats":        
    st.subheader("Lead Stats", divider=True)
    st.markdown("Show statistics about the top deal leads")
    if st.session_state.has_data_file:
        # Show the stats regarding Syndicate LEads
        top_filter = st.slider("Show how many",1,60,5)   

        # Load the data from the session state
        df = st.session_state.df

        # now group them by Lead and calculate the average multiple
        aggregated_df = df.groupby('Lead').agg(
                    num_investments=('Company/Fund', 'size'),
                    sum_invested=('Invested', 'sum'),
                    unrealized=('Unrealized Value', 'sum'),
                    avg_invested=('Invested', 'mean'),
                    sum_value=('Unrealized Value', 'sum')
        ).reset_index()

        # Exclude where no value as sum (result would be infinite)
        #aggregated_df = aggregated_df[aggregated_df["sum_value"] != 0]
        # Calculate average multiple
        aggregated_df['Av Multiple'] = (aggregated_df['sum_value'] / aggregated_df['sum_invested'])

        # Get the realised count
        # Filter for rows where Status is 'Realized'
        realized_df = df[df['Status'] == 'Realized']
        # Group by Lead and count the number of rows
        realized_counts = realized_df.groupby('Lead').size().reset_index(name='num_Realized')
        # Merge the realized counts back into the aggregated DataFrame
        aggregated_df = pd.merge(aggregated_df, realized_counts, on='Lead', how='left').fillna(0)

        aggregated_df['Percent Realised'] = aggregated_df['num_Realized']/aggregated_df['num_investments'] * 100
        # Take top values
        top_X_num = aggregated_df.nlargest(top_filter, 'Av Multiple')

        # Shows the companies with the top multiples in 'Company (X.X)x, ...' format by matching on the Lead = mname
        # Not sure how to generalise this but if I can then can reduce file size
        def show_top_X_names_based_on_multiple_by_Lead(top_values, df, mname):
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

        # Create a new column in the grouped dataframe to store the examples
        top_X_num["Best"] = ""
        top_X_num["Worst"] = ""

        # Iterate through unique rounds and update the "Examples" column
        topX = 4
        for lead_name in top_X_num["Lead"].unique():
            examples = show_top_X_names_based_on_multiple_by_Lead(4, df, lead_name)
            top_X_num.loc[top_X_num["Lead"] == lead_name, "Best"] = examples
            examples = show_realised_based_on_Lead(4, df, lead_name)
            top_X_num.loc[top_X_num["Lead"] == lead_name, "Worst"] = examples

        # Neatly format everything
        st.data_editor(
            top_X_num, 
            column_config= {
                "total_investments": st.column_config.NumberColumn(
                    "Investments", help="The total number of investments", format="%d"
                ),
                "avg_invested": st.column_config.NumberColumn(
                    "Avg", help="Average invested into syndicates by this lead", format="$%.0f"
                ),
                "sum_invested": st.column_config.NumberColumn(
                    "Sum", help="Total invested into this syndicate", format="$%.0f"
                ), 
                "sum_value": st.column_config.NumberColumn(
                    "Value", help="Total value including realised and unrealized (rounded to nearest whole number)", format="$%.0f"
                ),
                "Av multiple": st.column_config.NumberColumn(
                    "Multiple", help="The average multiple return into this syndicate (as reported by AngelList)", format="$%.1f x"
                ) 
            },
            hide_index=True,
        )
#        with st.container(height=300):
#            st.write(top_X_num)
    else:
        st.write("Please Load Data file first before proceeding")  

elif option == "Leads no markups":
    st.subheader("Leads with no disclosed markups", divider=True)
    st.markdown("Show all the leads that have no markups recorded in AngelList")            
    
    # Show the stats regarding Syndicate LEads
#    top_filter = st.slider("Show how many",1,50,5)   
    if st.session_state.has_data_file:
        # Load the data from the session state
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
        # Sort based on locked_percentage descending
        result = filtered_df.sort_values(by='locked_percentage', ascending=False)
        result = result.sort_values(by='locked_count', ascending=False)
        
 #       # Take top values
 #       result = result.nlargest(top_filter, 'Lead')      
        # drop superfluous columns
        result  = result.drop(columns=['locked_count', 'locked_percentage'])
        # Neatly format everything
        st.data_editor(
            result, 
            column_config= {
                "total_investments": st.column_config.NumberColumn(
                    "Investments", help="The total number of investments", format="%d"
                ),
                "avg_invested": st.column_config.NumberColumn(
                    "Avg", help="Average invested into syndicates by this lead", format="$%.0f"
                ),
                "sum_invested": st.column_config.NumberColumn(
                    "Sum", help="Total invested into this syndicate", format="$%.0f"
                ) 
            },
            hide_index=True,
        )
#        with st.container(height=300):
#            st.write(result)
    else:
        st.write("Please Load Data file first before proceeding")

elif option == "Realized":
    st.subheader("Realized Investments", divider=True)
    st.markdown("Show all the deals that were exited either as a full loss (Dead) or with a (partial) return of capital as recorded by AngelList")
    if st.session_state.has_data_file:
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
        result_sorted.insert(name_column_index+1, 'Profit', result_sorted.pop('Profit'))
        result_sorted.insert(name_column_index+1, 'Real Multiple', result_sorted.pop('Real Multiple'))

        # Put in the summary analysis to help people understand what is happening here
        #display_text = f"Successful exits: turned ${st.session_state.invested_realised_1x:,.2f} into ${st.session_state.value_realised_1x:,.2f} a {(st.session_state.value_realised_1x/st.session_state.invested_realised_1x):.1f}x multiple" 
        #st.text(display_text)
        #display_text = f"Other exits: turned ${st.session_state.invested_realised_less1x:,.2f} into ${st.session_state.value_realised_less1x:,.2f} a {(st.session_state.value_realised_less1x/st.session_state.invested_realised_less1x):.1f}x multiple" 
        #st.text(display_text)
        st.text("Note that other amounts may have been realised but those investments aren't fully realised yet - eg partial earn outs")
        
        # Neatly format everything
        if st.session_state.has_enhanced_data_file:
            enhanced_df = pd.merge(result_sorted, st.session_state.df2, on='Company/Fund', how='left')
            # enhanced needs to be resorted too
            enhanced_df.insert(name_column_index+1, 'Comment', enhanced_df.pop('Comment'))
            enhanced_df.insert(name_column_index+1, 'AngelList URL', enhanced_df.pop('AngelList URL'))

            st.data_editor(
                enhanced_df, 
                column_config= {
                    "URL": st.column_config.LinkColumn(
                        "Website", help="The link to the website for the company"
                    ),
                    "AngelList URL": st.column_config.LinkColumn(
                        "Website", help="The link to your AngelList investment record", display_text="AL Link"
                    ),
                    "Real Multiple": st.column_config.NumberColumn(
                        "Multiple", help="Multiple expressed as Realized value / invested amount", format="%.2f x"
                    ), 
                    "Multiple": st.column_config.NumberColumn(
                        "AL Multiple", help="Multiple as originally recored by AngelList system", format="%.2f x"
                    ),
                    "Invested": st.column_config.NumberColumn(
                        "Invested", help="Dollars invested (rounded to nearest whole number)", format="$%.0f"
                    ), 
                    "Net Value": st.column_config.NumberColumn(
                        "Net Value", help="Total value including realised and unrealized (rounded to nearest whole number)", format="$%.0f"
                    ),
                    "Proft": st.column_config.NumberColumn(
                        "Profit", help="Realized value less Invested Value", format="$%.0f"
                    ), 
                    "Unrealized Value": st.column_config.NumberColumn(
                        "Unreal $", help="Unrealized value of the investment as reported by the deal lead (rounded to nearest whole number)", format="$%.0f"
                    ), 
                    "Realized Value": st.column_config.NumberColumn(
                        "$ Received", help="Realized value as reported by AngelList (rounded to nearest whole number)", format="$%.0f"
                    ) 
                },
                hide_index=True,
            )
        else :
            # Data structure and interactive data
            st.data_editor(
                result_sorted, 
                column_config= {
                    "Real Multiple": st.column_config.NumberColumn(
                        "Multiple", help="Multiple expressed as Realized value / invested amount", format="%.2f x"
                    ), 
                    "Multiple": st.column_config.NumberColumn(
                        "AL Multiple", help="Multiple as originally recored by AngelList system", format="%.2f x"
                    ),
                    "Invested": st.column_config.NumberColumn(
                        "Invested", help="Dollars invested (rounded to nearest whole number)", format="$%.0f"
                    ), 
                    "Net Value": st.column_config.NumberColumn(
                        "Net Value", help="Total value including realised and unrealized (rounded to nearest whole number)", format="$%.0f"
                    ),
                    "Proft": st.column_config.NumberColumn(
                        "Profit", help="Realized value less Invested Value", format="$%.0f"
                    ), 
                    "Unrealized Value": st.column_config.NumberColumn(
                        "Unreal $", help="Unrealized value of the investment as reported by the deal lead (rounded to nearest whole number)", format="$%.0f"
                    ), 
                    "Realized Value": st.column_config.NumberColumn(
                        "$ Received", help="Realized value as reported by AngelList (rounded to nearest whole number)", format="$%.0f"
                    ) 
                },
                hide_index=True,
            )
    else:
        st.write("Please Load Data file first before proceeding")
elif option == "Graphs":
    st.subheader("Graphs", divider=True)
    st.markdown("Shows some key graphs and analysis")
    if st.session_state.has_data_file:
        # Load the data from the session state
        df = st.session_state.df
  
        # set themes and sizes - note I couldn't display it neatly
        sns.set_theme()
        # Set up the formatting and dimensions
        # a, b = st.columns(2)
        # width = 3
        # height = 2

        # 1. Distribution of Multiples > 1
        data_mult = df[df['Real Multiple'] > 1]['Real Multiple'].dropna()
        plt = sns.histplot(data=data_mult, bins=20, color='skyblue')
#        fig, ax = plt.subp.subplots(figsize=(width, height))
        plt.set_title('Distribution of Investment Multiples (>1x)')
        plt.set_xlabel('Multiple')
        plt.set_ylabel('Count')    
        st.pyplot(plt.get_figure())

        # 2. Distribution of Investment Amounts
        plt = sns.histplot(data=df['Invested'].dropna(), bins=20, color='salmon')
 #       fig, ax = plt.subplots(figsize=(width, height))
        plt.set_title('Distribution of Investment Amounts')
        plt.set_xlabel('Investment Amount ($)')
        plt.set_ylabel('Count')
        st.pyplot(plt.get_figure())
        plt.cla()

        # 3. Investment Amount vs Multiple (for multiples > 1)
        scatter_df = df[(df['Real Multiple'] > 1) & (df['Invested'].notnull())]
        plt = sns.scatterplot(data=scatter_df, x='Invested', y='Real Multiple', color='purple', alpha=0.6)
        plt.set_title('Investment Amount vs Multiple')
        plt.set_xlabel('Investment Amount ($)')
        plt.set_ylabel('Multiple')
        st.pyplot(plt.get_figure())
        plt.cla()

        # 4. Pie chart of Lead summary for Multiples > 2
        high_multiple_deals = df[df['Real Multiple'] > 2]
        lead_summary = high_multiple_deals['Lead'].value_counts()
        plt.pie(lead_summary, labels=lead_summary.index, autopct='%1.1f%%', startangle=90, colors=sns.color_palette('pastel'))
        plt.set_title('Lead Summary for Multiples > 2')
        st.pyplot(plt.get_figure())
        plt.cla()

        # 5. Plot of Round Size and Multiple
        # from scipy import stats
        # import numpy as np

        # Filter out rows with missing or unrealistic multiples
        df_filtered = df.dropna(subset=['Round Size', 'Real Multiple'])

        # # Plot scatter plot
        # #fig = plt.figure(figsize=(12,8))
        # sns.scatterplot(data=df_filtered, x='Round Size', y='Real Multiple', alpha=0.6)
        # plt.set_xlabel('Round Size ($)')
        # plt.set_ylabel('Multiple (x)')
        # plt.set_title('Relationship between Round Size and Multiple')
        # plt.grid(True)

        # # Trend line
        # mask = ~df_filtered['Round Size'].isna() & ~df_filtered['Real Multiple'].isna()
        # slope, intercept, r_value, p_value, std_err = stats.linregress(df_filtered['Round Size'][mask], df_filtered['Real Multiple'][mask])
        # line_x = np.linspace(df_filtered['Round Size'][mask].min(), df_filtered['Round Size'][mask].max(), 100)
        # line_y = slope * line_x + intercept
        # plt.plot(line_x, line_y, color='red', label='Trend line')
        # plt.legend()
        # st.pyplot(plt.get_figure())

        # Calculate correlation
        correlation = df_filtered['Round Size'].corr(df_filtered['Real Multiple'])
        st.write('Correlation coefficient between Round Size and Multiple: {:.2f}', correlation)

        # Print some key statistics
        st.write("Average Multiple (>1x): {:.2f}".format(data_mult.mean()))
        st.write("Median Multiple (>1x): {:.2f}".format(data_mult.median()))
        st.write("Average Investment Amount: ${:,.2f}".format(df['Invested'].mean()))
        st.write("Median Investment Amount: ${:,.2f}".format(df['Invested'].median()))
    else:
        st.write("Please Load Data file first before proceeding")

## Optional: Add a button to reset the selection
#if st.button("Reset Selection"):
#    option = None
#    st.write("Selection reset. Please choose an option again.")
