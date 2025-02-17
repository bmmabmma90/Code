# Streamlit front end

import streamlit as st

lower = st.slider("Lower number",1,500,100)
upper = st.slider("Higher number",1000,3000,2000)

total_investments = 8
num_uniques = 5
num_dead = 1
num_greater_1x_multiple = 3
invested_sum = 13405.00
realized_sum = 10.55
net_sum = 14354.55

def format_currency(amount) :
    return '${:,.2f}'.format(amount)

a, b = st.columns(2)
c, d = st.columns(2)
e, f, g = st.columns(3)

a.metric(label="Investments", value=total_investments, border=True)
b.metric(label="Companies", value=num_uniques, border=True)
c.metric(label="Deceased ::dead::",value=num_dead, border=True)
d.metric(label=">1x",value=num_greater_1x_multiple, border=True)
e.metric(label="Invested $",value=format_currency(invested_sum), border=True)
f.metric(label="Net Value $",value=format_currency(realized_sum), border=True)
g.metric(label="Realised $",value=format_currency(net_sum), border=True)

#        st.metric(label="Total Investments", value=total_investments
#        st.write(f"Total dead investments: {total_investments}")
#        st.write(f"Total dead investments: {num_uniques}")
#        st.write(f"Total dead investments: {num_dead}")
#        st.write(f"Total investments > 1x: {num_greater_1x_multiple}")
#        st.write(f"The sum of the 'Invested' column is: {invested_sum}")
#        st.write(f"The sum of the 'Realized Value' column is: {realized_sum}")
#        st.write(f"The sum of the 'Net Value' column is: {net_sum}")

st.write("Processing Armstrong numbers...")
for num in range(lower, upper + 1):

   # order of number
   order = len(str(num))
    
   # initialize sum
   sum = 0

   temp = num
   while temp > 0:
       digit = temp % 10
       sum += digit ** order
       temp //= 10

   if num == sum:
       st.write(num)