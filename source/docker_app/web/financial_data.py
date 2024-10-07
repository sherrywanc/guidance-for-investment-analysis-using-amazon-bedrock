import streamlit as st
import pandas as pd

def render():
    st.subheader("Financial Data")
    if 'parsed_data' in st.session_state and st.session_state['parsed_data']:
        parsed_data = st.session_state['parsed_data']

        # Create the DataFrame and extract year from the columns
        df = pd.DataFrame(parsed_data)
        df = df.melt(id_vars=["Metric"], var_name="Year", value_name="Value")

        sub_tab1, sub_tab2, sub_tab3, sub_tab4, sub_tab5 = st.tabs(
            ["Combined Chart", "Charts", "JSON Data", "Table Data", "Source Data"]
        )

        with sub_tab1:
            combined_data = df[df["Metric"].str.contains("Total Revenue|Total Expenses|Gross Profit", case=False)]
            combined_data = combined_data.pivot(index='Year', columns='Metric', values='Value')
            st.bar_chart(combined_data)

        with sub_tab2:
            if not df.empty:
                revenue_data = df[df["Metric"].str.contains("Total Revenue", case=False)]
                expense_data = df[df["Metric"].str.contains("Total Expenses", case=False)]
                income_data = df[df["Metric"].str.contains("Gross Profit", case=False)]

                st.subheader("Financial Charts")
                chart_tab1, chart_tab2, chart_tab3 = st.tabs(["Revenue Chart", "Expense Chart", "Profit Chart"])

                with chart_tab1:
                    st.line_chart(revenue_data.pivot(index='Year', columns='Metric', values='Value'))

                with chart_tab2:
                    st.line_chart(expense_data.pivot(index='Year', columns='Metric', values='Value'))

                with chart_tab3:
                    st.line_chart(income_data.pivot(index='Year', columns='Metric', values='Value'))

        with sub_tab3:
            st.json(parsed_data)

        with sub_tab4:
            st.dataframe(df.pivot(index='Metric', columns='Year', values='Value'), use_container_width=True)

        with sub_tab5:
            st.write("Download the raw financial data for further analysis.")
            st.download_button(
                label="Download data as CSV",
                data=df.to_csv().encode('utf-8'),
                file_name=f'{st.session_state["ticker"]}_financial_data.csv',
                mime='text/csv'
            )
    else:
        st.write("Please perform an analysis in the 'Fundamental Analysis' tab first.")
    st.markdown("---")  # Horizontal line for separation
