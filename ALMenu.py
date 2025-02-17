# AL_Menu
# Streamlit menu selection and front end for AngelList
# Needs to handle a range of things better

import streamlit as st
import pandas as pd

st.title("AngelList Startup Data Analyser")

# Sidebar for the menu
with st.sidebar:
    st.header("Menu")
    option = st.selectbox(
        "Choose an option:",
        ("About", "Load Data", "Stats", "Top Investments", "Realized", "Lead Stats", "Leads no markups", "Graphs")
    )

# st.header("Output")
# Set has no data file until one is read in correctly

if 'has_data_file' not in st.session_state: 
    st.session_state.has_data_file = False
if 'has_enhanced_data_file' not in st.session_state: 
    st.session_state.has_enhanced_data_file = False
if 'df' not in st.session_state: 
    st.session_state.df = pd.DataFrame()
if 'df2' not in st.session_state: 
    st.session_state.df2 = pd.DataFrame()
if 'net_sum' not in st.session_state:   
    st.session_state.net_sum = 0

# Perform actions based on the selected option
if option == "About" :
    st.subheader("About", divider=True)
    multi = '''AngelList's investor focused data analysis is somewhat limited. This program aims 
    to make it easier for investors to get insight from their :red[AngelList] data and to be able to perform ad hoc 
    analysis to inform their future investing decisions.

    The program takes in up to two data sources in the Load menu item. The first is an export of :red[AngelList] data 
    which you can generate from the Portfolio page (-->select Export CSV). This is all you need to process your data.

    **Advanced**
    
    The second (and optional file) is a .CSV formatted file you 
    can make to store additional data that isn't stored in :red[AngelList] or that is not readily accessible in the export. The 
    of this second file must be:

    ! Any comments or version you want to include - [this first line is ignored] 
    Company/Fund  URL  AngelList URL   Comment   Other fields
    '''
    st.markdown(multi)

elif option == "Load Data":
    st.subheader("Load in data file(s) for processing", divider=True)
    
    # Display if already loaded and button not pressed or where data hasn't been loaded
    # Check if already loaded - 
 #   st.session_state.has_data_file == True :
 #       st.button("Reload Data")
#else:
    # Action 1: Load in Data
    uploaded_file = st.file_uploader("Choose the AngelList file in a CSV format", type="csv")

    if uploaded_file is not None:
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
    uploaded_file2 = st.file_uploader("Choose the Enhancement file in a CSV format. The first row is ignored and the first column must be 'Company/Fund' matching exactly, followed by any other columns", type="csv")
    if uploaded_file2 is not None:
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

        # 2.a. Special treatment of Unrealized Value because we want to flag where we don't know the actual value
        # We'll iterate through and force "Unrealized" and "Net Value" to zero AFTER we have made a note that the
        #.   value isn't known in a new column called "Unknown Value"
        # insert in a specific order for ease of reference
        df.insert(3, "Valuation Unknown", False)
        for index, row in df.iterrows():
            original_value = row['Unrealized Value']
            if original_value == "Locked" :
                df.loc[index, "Unrealized Value"] = 0
                df.loc[index, "Valuation Unknown"] = True
                df.loc[index, "Net Value"] = 0
                df.loc[index, "Multiple"] = 0

        # 2.a.2 Move some columns 
        name_column_index = df.columns.get_loc('Company/Fund')
        # insert Multiple after and remove the prior position 
        df.insert(name_column_index+1, 'Multiple', df.pop('Multiple'))
        name_column_index = df.columns.get_loc('Invested')
        # insert Multiple after and remove the prior position 
        df.insert(name_column_index+1, 'Net Value', df.pop('Net Value'))
 
        # 2.b. Normalize the data by converting the to numbers
        df["Realized Value"] = df["Realized Value"].replace("[\$,]", "", regex=True).astype(float)
        df["Unrealized Value"] = df["Unrealized Value"].replace("[\$,]", "", regex=True).astype(float)
        df["Invested"] = df["Invested"].replace("[\$,]", "", regex=True).astype(float)
        df["Net Value"] = df["Net Value"].replace("[\$,]", "", regex=True).astype(float)
        df["Multiple"] = df["Multiple"].replace("[\$,]", "", regex=True).astype(float)

        # 2.c. Check if the company is actually dead ie Valuation Unknown is not True but Net Value = 0
        # Also count the number where multiple > 1
        num_dead = 0
        num_greater_1x_multiple = 0

        for index, row in df.iterrows():
            if (row['Unrealized Value'] == 0) and (row['Valuation Unknown'] == False):
                df.loc[index, "Status"] = "Dead"
                num_dead=num_dead+1
            if (row['Multiple']) > 1:
                num_greater_1x_multiple = num_greater_1x_multiple + 1

        # 2.d. Calculate the sum of the 'Invested' column and the 'Net Value' column
        try:
            invested_sum = df["Invested"].sum()
            realized_sum = df["Realized Value"].sum()
            net_sum = df["Net Value"].sum()
        except KeyError:
            st.error("Error: 'Invested' column not found in the DataFrame.")
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")

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
        st.session_state.invested_sum = invested_sum
        st.session_state.realized_sum = realized_sum
        st.session_state.net_sum = net_sum
        st.session_state.num_dead = num_dead
        st.session_state.num_greater_1x_multiple = num_greater_1x_multiple
        st.session_state.num_uniques = num_uniques
        st.session_state.total_investments = total_investments
        st.session_state.num_leads = num_leads
        st.session_state.num_zero_value_leads = num_zero_value_leads

elif option == "Stats":
    st.subheader("Investment Statistics", divider=True)
    st.markdown("Show statistics across the portfolio")

    if st.session_state.has_data_file:
          # Write all the outputs to the screen
        def format_currency(amount) :
            return '${:,.2f}'.format(amount)

        a, b = st.columns(2)
        c, d = st.columns(2)
        e, f, g = st.columns(3)
        h, i = st.columns(2)

        a.metric(label="Investments", value=st.session_state.total_investments, border=True)
        b.metric(label="Companies", value=st.session_state.num_uniques, border=True)
        c.metric(label="Deceased",value=st.session_state.num_dead, border=True)
        d.metric(label=" >1x",value=st.session_state.num_greater_1x_multiple, border=True)
        e.metric(label="Invested $",value=format_currency(st.session_state.invested_sum), border=True)
        f.metric(label="Net Value $",value=format_currency(st.session_state.net_sum), border=True)
        g.metric(label="Realised $",value=format_currency(st.session_state.realized_sum), border=True)
        h.metric(label="Syndicates Invested",value=st.session_state.num_leads, border=True)
        i.metric(label="Syndicates no value info",value=st.session_state.num_zero_value_leads, border=True)
    else:
        st.write("Please Load Data file first before proceeding")  
#        screen_display = {
#            "Description": ["**Total Investments**", "**Total unique investments**", "Dead Investments", "> 1x Investments", "Total Invested ($)", "Net Value ($)", "Realised ($)" ],
#            "Values": [total_investments, num_uniques, num_dead, num_greater_1x_multiple, invested_sum, net_sum, realized_sum]
#        }
#        st.metric(label="Total Investments", value=total_investments
#        st.write(f"Total dead investments: {total_investments}")
#        st.write(f"Total dead investments: {num_uniques}")
#        st.write(f"Total dead investments: {num_dead}")
#        st.write(f"Total investments > 1x: {num_greater_1x_multiple}")
#        st.write(f"The sum of the 'Invested' column is: {invested_sum}")
#        st.write(f"The sum of the 'Realized Value' column is: {realized_sum}")
#        st.write(f"The sum of the 'Net Value' column is: {net_sum}")
#        st.table(screen_display)
 
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
        sorted_df = sorted_df.drop(columns=['Status','Valuation Unknown'])
        # Get the top X investments
        top_X_num = sorted_df.head(top_filter)

        # Merge the cleaned dataset with the sample dataset using 'Company/Fund' as the key
        if st.session_state.has_enhanced_data_file:
            enhanced_df = pd.merge(top_X_num, st.session_state.df2, on='Company/Fund', how='left')
#           st.write(enhanced_df)
            
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
        else :
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

        # Display the top X investments
#        with st.container(height=300):
#            st.write(top_X_num)
    else:
        st.write("Please Load Data file first before proceeding")  

elif option == "Leads no markups":
    st.subheader("Leads with no markups", divider=True)
    st.markdown("Show all the leads that have no markups recorded in AngelList")
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

        # prompt: Using dataframe df: Write code that finds all the values in df that have Realized Value > 0 or that have Status = Realized or Status == Dead
        # Find rows where 'Realized Value' is greater than 0
        realized_value_gt_0 = df[df['Realized Value'] > 0]
        # Find rows where 'Status' is 'Realized' or 'Dead'
        status_realized_or_dead = df[df['Status'].isin(['Realized', 'Dead'])]
        # Combine the two sets of rows using concatenation
        combined_df = pd.concat([realized_value_gt_0, status_realized_or_dead])
        # Drop duplicate rows to avoid redundancy
        result_df = combined_df.drop_duplicates()
        # Calculate profit and loss and Real Multiple (can be inaccurate in AngelList)
        result_a = result_df.copy()
        result_a["Profit"] = result_a["Realized Value"] - result_a["Invested"]
        result_a['Real Multiple'] = result_a['Realized Value']/result_a['Invested']
        result_sorted = result_a.sort_values(by='Real Multiple', ascending=False)

        # reorder some columns
        # insert Multiple after and remove the prior position 
        name_column_index = result_sorted.columns.get_loc('Company/Fund')
        result_sorted.insert(name_column_index+1, 'Lead', result_sorted.pop('Lead'))
        result_sorted.insert(name_column_index+1, 'Profit', result_sorted.pop('Profit'))
        result_sorted.insert(name_column_index+1, 'Real Multiple', result_sorted.pop('Real Multiple'))

       # Neatly format everything
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
#        with st.container(height=300):
#            st.write(result)
    else:
        st.write("Please Load Data file first before proceeding")
elif option == "Graphs":
    st.subheader("Graphs", divider=True)
    st.markdown("Shows some key graphs and analysis")
    if st.session_state.has_data_file:
        # Load the data from the session state
        df = st.session_state.df

        from matplotlib import pyplot as plt
        import seaborn as sns

        # Grab our data
        df = st.session_state.df

        # set themes and sizes - note I couldn't display it neatly
        sns.set_theme()

        # 1. Distribution of Multiples > 1
        data_mult = df[df['Multiple'] > 1]['Multiple'].dropna()
        plot = sns.histplot(data=data_mult, bins=20, color='skyblue')
        plot.set_title('Distribution of Investment Multiples (>1x)')
        plot.set_xlabel('Multiple')
        plot.set_ylabel('Count')
        st.pyplot(plot.get_figure())

        # 2. Distribution of Investment Amounts
        plot = sns.histplot(data=df['Invested'].dropna(), bins=20, color='salmon')
        plot.set_title('Distribution of Investment Amounts')
        plot.set_xlabel('Investment Amount ($)')
        plot.set_ylabel('Count')
        st.pyplot(plot.get_figure())

        # 3. Investment Amount vs Multiple (for multiples > 1)
        scatter_df = df[(df['Multiple'] > 1) & (df['Invested'].notnull())]
        plot = sns.scatterplot(data=scatter_df, x='Invested', y='Multiple', color='purple', alpha=0.6)
        plot.set_title('Investment Amount vs Multiple')
        plot.set_xlabel('Investment Amount ($)')
        plot.set_ylabel('Multiple')
        st.pyplot(plot.get_figure())

        # 4. Pie chart of Lead summary for Multiples > 2
        high_multiple_deals = df[df['Multiple'] > 2]
        lead_summary = high_multiple_deals['Lead'].value_counts()
        plot.pie(lead_summary, labels=lead_summary.index, autopct='%1.1f%%', startangle=90, colors=sns.color_palette('pastel'))
        plot.set_title('Lead Summary for Multiples > 2')
        st.pyplot(plot.get_figure())

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
