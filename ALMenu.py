# AL_Menu
# Streamlit menu selection and front end for AngelList
# Needs to handle a range of things better

import streamlit as st
import pandas as pd
from matplotlib import pyplot as plt
import seaborn as sns
import squarify
import numpy as np

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
            ("About", "Load Data", "Stats", "Top Investments", "Realized", "Lead Stats", "Leads no markups", "Graphs")
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
    force_load = False
    if force_load == True:
        df = pd.read_csv(r"/Users/deepseek/Downloads/ben-armstrong_angellist_investments_2025_02_21.csv", header=1, skip_blank_lines=True)
        st.session_state.has_data_file = True
        st.session_state.df = df
        with st.container(height=200):
            st.write(df)       
        df2 = pd.read_csv(r"/Users/deepseek/Downloads/Enhance-2.csv", header=1, skip_blank_lines=True)
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
    # 1. Drop the data we don't analyse for easy display / debugging
        todrop = { 'Invest Date', 'Investment Entity',
                'Investment Type', 'Round', 'Market', 'Fund Name', 'Allocation',
                'Instrument', 'Round Size', 'Valuation or Cap Type', 'Valuation or Cap',
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
        
        # 2.b. Special treatment of Unrealized Value because we want to flag where we don't know the actual value
        # We'll iterate through and force "Unrealized" and "Net Value" to zero AFTER we have made a note that the
        #.   value isn't known in a new column called "Unknown Value"
        # insert in a specific order for ease of reference
        df.insert(3, "Valuation Unknown", False)

        num_locked = 0
        invested_locked = 0
        for index, row in df.iterrows():
            original_value = row['Unrealized Value']
            if original_value == "Locked" :
                df.loc[index, "Valuation Unknown"] = True
                df.loc[index, "Unrealized Value"] = 0
                df.loc[index, "Net Value"] = 0
                df.loc[index, "Multiple"] = 0
                num_locked += 1
                invested_locked += df.loc[index, "Invested"]
       
        # Now convert whole columns for Unrealized Value and Net Value now that have gathered which are locked (Forcing
        # Locked to zero

        df["Net Value"] = df["Net Value"].replace(r'[^\d.]', '', regex=True).astype(float) 
        df["Unrealized Value"] = df["Unrealized Value"].replace(r'[^\d.]', '', regex=True).astype(float) 

        # 2.a.2 Move some columns 
        name_column_index = df.columns.get_loc('Company/Fund')
        # insert Multiple after and remove the prior position 
        df.insert(name_column_index+1, 'Multiple', df.pop('Multiple'))
        name_column_index = df.columns.get_loc('Invested')
        # insert Multiple after and remove the prior position 
        df.insert(name_column_index+1, 'Net Value', df.pop('Net Value'))

        # 2.c. Calculate all the values for realised and marked up investments
        invested_realised_1x = 0
        invested_realised_less1x = 0
        invested_non_realised = 0  # Note the sum of these 3 things should be total_invested
        value_realised_1x = 0
        value_realised_less1x = 0  # Note the sum of these 2 things should be total_realised
    #   invested_locked = 0
        invested_showing = 0 # Note the sum of these 2 should be total_invested_live
        value_markup = 0
        value_not_markedup = 0
        value_locked = 0 # Note the sum of these 3 should be total_value
        num_greater_1x_multiple = 0

        # 2.d Calculate the profit and Real Multiple along with some results about realisations
        df["Profit"] = df["Realized Value"] - df["Invested"]
        df['Real Multiple'] = df['Realized Value']/df['Invested']

        # 2.e Calculate the grand totals 
        total_invested = df["Invested"].sum()
        total_realized = df["Realized Value"].sum()
        total_invested_live = total_invested - total_realized

        # 2.c.1. Do realized calculations of invested and values
        filtered_df = df[(df['Status'] == 'Realized') & (df['Real Multiple'] >= 1)]
        invested_realised_1x = filtered_df['Invested'].sum()
        value_realised_1x = filtered_df['Realized Value'].sum()

        filtered_df = df[(df['Status'] == 'Realized') & (df['Real Multiple'] < 1)]
        invested_realised_less1x = filtered_df['Invested'].sum()
        value_realised_less1x = filtered_df['Realized Value'].sum()
        num_realised = filtered_df['Company/Fund'].count()# nunique()  Count uniques

        invested_non_realised = total_invested - invested_realised_1x - invested_realised_less1x
        invested_showing = total_invested_live - invested_locked

        # Switch up real multiple to use it in a different context here
        df['Real Multiple'] = df['Unrealized Value']/df['Invested']
        value_markup = df[(df['Status'] != 'Realized') & (df['Valuation Unknown'] == False) & (df['Real Multiple'] >= 1)]['Unrealized Value'].sum()
        value_not_markedup = df[(df['Status'] != 'Realized') & (df['Valuation Unknown'] == False) & (df['Real Multiple'] < 1)]['Unrealized Value'].sum()
        invested_markup = df[(df['Status'] != 'Realized') & (df['Valuation Unknown'] == False) & (df['Real Multiple'] >= 1)]['Invested'].sum()
        invested_not_markedup = df[(df['Status'] != 'Realized') & (df['Valuation Unknown'] == False) & (df['Real Multiple'] < 1)]['Invested'].sum()

        # Sum the numbers of marked up for curiousity
        for index, row in df.iterrows():
#            if (row['Unrealized Value'] == 0) and (row['Valuation Unknown'] == False):
#                df.loc[index, "Status"] = "Dead"
#                num_realised=num_realised+1
            if (row['Multiple']) > 1:
                num_greater_1x_multiple = num_greater_1x_multiple + 1

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
        st.session_state.invested_realised_1x = invested_realised_1x
        st.session_state.invested_realised_less1x = invested_realised_less1x
        st.session_state.invested_non_realised = invested_non_realised
        st.session_state.total_invested = total_invested

        st.session_state.value_realised_1x = value_realised_1x
        st.session_state.value_realised_less1x = value_realised_less1x
        st.session_state.total_realised = total_realized
        st.session_state.invested_locked = invested_locked
        st.session_state.invested_showing = invested_showing
        st.session_state.total_invested_live = total_invested_live

        st.session_state.value_markup = value_markup
        st.session_state.value_not_markedup = value_not_markedup
        st.session_state.invested_markup = invested_markup
        st.session_state.invested_not_markedup = invested_not_markedup
        st.session_state.value_locked = value_locked

        st.session_state.num_realised = num_realised
        st.session_state.num_greater_1x_multiple = num_greater_1x_multiple
        st.session_state.num_uniques = num_uniques
        st.session_state.total_investments = total_investments
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
        t, h, i, j = st.columns(4) # Realized Information
        u, k, l, m = st.columns(4) # Locked Information
        v, n, o, p = st.columns(4) # <=1x Information
        w, q, r, s = st.columns(4) # >1x Information

        with t:
            st.write("Realised:")
            st.write(f"{(st.session_state.num_realised*100/st.session_state.total_investments):.0f} %")
        with u:
            st.write("Locked:")
            st.write(f"{(st.session_state.num_locked*100/st.session_state.total_investments):.0f} %")
        with v:
            st.write("<1x")
            st.write("")
        with w:
            st.write("1x+")
            st.write(f"{(st.session_state.num_greater_1x_multiple*100/st.session_state.total_investments):.0f} %")
        a.metric(label="Investments", value=st.session_state.total_investments, border=True)
        b.metric(label="Companies", value=st.session_state.num_uniques, border=True)
        if total_value > 0:
            st.session_state.total_value = total_value
            st.session_state.value_locked = total_value - st.session_state.value_markup - st.session_state.value_not_markedup
            c.metric(label="Total Value $",value=format_currency(total_value), border=True)
            d.metric(label="Multiple (x)",value=format_multiple(st.session_state.total_value/st.session_state.total_invested), border=True)
        e.metric(label="Invested $",value=format_currency(st.session_state.total_invested), border=True)
        f.metric(label="Syndicates Invested",value=st.session_state.num_leads, border=True)
        g.metric(label="Syndicates no value info",value=st.session_state.num_zero_value_leads, border=True)

        # Realized no. --> Realized Invested $ --> Realized Value
        h.metric(label="Realized #",value=st.session_state.num_realised, border=True)
        i.metric(label="Realized Invested $", value=format_currency(st.session_state.invested_realised_1x+st.session_state.invested_realised_less1x), border=True)
        j.metric(label="Realised Value $",value=format_currency(st.session_state.total_realised), border=True)

        # Locked no. --> Locked Invested $ --> Locked Value $
        k.metric(label="Locked #",value=st.session_state.num_locked, border=True)
        l.metric(label="Locked Invested $",value=format_currency(st.session_state.invested_locked), border=True)
        m.metric(label="Locked Value $",value=format_currency(st.session_state.value_locked), border=True)
     
        # <= 1x Information
        n.metric(label=" <1x #",value=(st.session_state.total_investments - st.session_state.num_locked - st.session_state.num_greater_1x_multiple - st.session_state.num_realised), border=True)        
        o.metric(label=" <1x Invested $",value=format_currency(st.session_state.invested_not_markedup), border=True)        
        p.metric(label=" <1x Value $",value=format_currency(st.session_state.value_not_markedup), border=True)

        # > 1x Information (marked up)
        q.metric(label=" 1x+",value=st.session_state.num_greater_1x_multiple, border=True)    
        r.metric(label=" 1x+ Invested $",value=format_currency(st.session_state.invested_markup), border=True)        
        s.metric(label=" 1x+ Value $",value=format_currency(st.session_state.value_markup), border=True)
 
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
        sorted_df = sorted_df.drop(columns=['Status','Valuation Unknown', 'Profit', 'Real Multiple'])
        # Get the top X investments
        top_X_num = sorted_df.head(top_filter)

        # Merge the cleaned dataset with the sample dataset using 'Company/Fund' as the key
        if st.session_state.has_enhanced_data_file:
            enhanced_df = pd.merge(top_X_num, st.session_state.df2, on='Company/Fund', how='left')
            st.data_editor(
                enhanced_df, 
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
    else:
        st.write("Please Load Data file first before proceeding")  

elif option == "Lead Stats":        
    st.subheader("Lead Stats", divider=True)
    st.markdown("Show statistics about the top deal leads")
    if st.session_state.has_data_file:
        # Show the stats regarding Syndicate LEads
        top_filter = st.slider("Show how many",1,50,5)   

        # Load the data from the session state
        df = st.session_state.df

        # now group them by Lead and calculate the average multiple
        aggregated_df = df.groupby('Lead').agg(
            total_investments=('Company/Fund', 'size'),
            sum_invested=('Invested', 'sum'),
            avg_invested=('Invested', 'mean'),
            sum_value=('Unrealized Value', 'sum')
        ).reset_index()
        # Exclude where no value as sum (result would be infinite)
        aggregated_df = aggregated_df[aggregated_df["sum_value"] != 0]
        # Calculate average multiple
        aggregated_df['Av Multiple'] = (aggregated_df['sum_value'] / aggregated_df['sum_invested'])
        # Take top values
        top_X_num = aggregated_df.nlargest(top_filter, 'Av Multiple')
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
        display_text = f"Successful exits: turned ${st.session_state.invested_realised_1x:,.2f} into ${st.session_state.value_realised_1x:,.2f} a {(st.session_state.value_realised_1x/st.session_state.invested_realised_1x):.1f}x multiple" 
        st.text(display_text)
        display_text = f"Other exits: turned ${st.session_state.invested_realised_less1x:,.2f} into ${st.session_state.value_realised_less1x:,.2f} a {(st.session_state.value_realised_less1x/st.session_state.invested_realised_less1x):.1f}x multiple" 
        st.text(display_text)
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
        data_mult = df[df['Multiple'] > 1]['Multiple'].dropna()
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

        # 3. Investment Amount vs Multiple (for multiples > 1)
        scatter_df = df[(df['Multiple'] > 1) & (df['Invested'].notnull())]
        plt = sns.scatterplot(data=scatter_df, x='Invested', y='Multiple', color='purple', alpha=0.6)
        plt.set_title('Investment Amount vs Multiple')
        plt.set_xlabel('Investment Amount ($)')
        plt.set_ylabel('Multiple')
        st.pyplot(plt.get_figure())

        # 4. Pie chart of Lead summary for Multiples > 2
        high_multiple_deals = df[df['Multiple'] > 2]
        lead_summary = high_multiple_deals['Lead'].value_counts()
        plt.pie(lead_summary, labels=lead_summary.index, autopct='%1.1f%%', startangle=90, colors=sns.color_palette('pastel'))
        plt.set_title('Lead Summary for Multiples > 2')
        st.pyplot(plt.get_figure())

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
