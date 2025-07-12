import streamlit as st
import pandas as pd

# Set page configuration
st.set_page_config(page_title="Roll Weight Dashboard", layout="wide")
st.markdown("## 📏 **Roll Weight Dashboard**")

# Week number input textbox
week_no = st.text_input("Enter Week No.", "")
if week_no.strip():
    st.markdown(f"### 📅 Week No.: {week_no.strip()}")

@st.cache_data
def load_data(file):
    df = pd.read_excel(file, sheet_name="Sheet1", header=1)
    df.columns = df.columns.str.strip()
    required_cols = ["FG Description", "Roll No", "Actual Roll Wt", "Theoretical Roll Wt (Incl Toller)", "Diff"]
    for col in required_cols:
        if col not in df.columns:
            st.error(f"Missing required column: {col}")
            return pd.DataFrame()
    df = df.dropna(subset=["FG Description"])
    return df

uploaded_file = st.file_uploader("### 📂 Upload Roll Weight Excel File", type=["xlsx"])

if uploaded_file:
    df = load_data(uploaded_file)
    if not df.empty:
        st.sidebar.header("🔍 Filter Options")
        fg_list = sorted(df["FG Description"].dropna().unique().tolist())
        fg_all = st.sidebar.checkbox("Select All FG Descriptions", value=True)
        if fg_all:
            selected_fg = fg_list
        else:
            selected_fg = st.sidebar.multiselect("FG Description", fg_list, default=fg_list[:5])

        filtered_df = df[df["FG Description"].isin(selected_fg)].copy()

        # Reset index and start from 1 (will show as row numbers in table)
        filtered_df = filtered_df.reset_index(drop=True)
        filtered_df.index = filtered_df.index + 1

        # Numeric columns to format
        numeric_cols = ["Actual Roll Wt", "Theoretical Roll Wt (Incl Toller)", "Diff"]
        # Add these two columns if they exist in data
        for col in ['BOM per SQM- PY & OY', 'Sqm Woven- Theoretical']:
            if col in filtered_df.columns:
                numeric_cols.append(col)

        filtered_df[numeric_cols] = filtered_df[numeric_cols].round(2)

        def color_diff(val):
            if -5 <= val <= 5:
                return 'background-color: #d4f4dd'  # light green
            elif -20 <= val <= 20:
                return 'background-color: #fff9d4'  # light yellow
            else:
                return 'background-color: #f8d7da'  # light red

        def highlight_diff_column(df):
            styles = pd.DataFrame('', index=df.index, columns=df.columns)
            styles.loc[:, 'Diff'] = df['Diff'].apply(color_diff)
            return styles

        styled_df = (
            filtered_df.style
            .apply(highlight_diff_column, axis=None)
            .set_table_styles([{'selector': 'th', 'props': [('font-weight', 'bold')]}])
            .format({col: "{:,.2f}" for col in numeric_cols})
        )

        st.markdown("### 📋 **Filtered Data Preview**")
        st.dataframe(styled_df, height=400)

    else:
        st.warning("Uploaded file has no usable data.")
else:
    st.info("Please upload a Roll Weight Excel file to begin.")
