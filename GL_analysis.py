import streamlit as st
import pandas as pd

# Format numbers in Indian format without decimals
def format_indian(x):
    return f"{int(x):,}".replace(",", "_").replace("_", ",").replace(",000", ",000").replace(",00", ",00")

st.set_page_config(page_title="GL Analysis Dashboard", layout="wide")
st.title("📊 GL Analysis Dashboard")

uploaded_file = st.file_uploader("Upload GL Excel File", type=["xlsx"])

@st.cache_data
def load_data(file):
    xls = pd.ExcelFile(file)
    st.write("Sheets available:", xls.sheet_names)

    if "GL" not in xls.sheet_names:
        st.error("The uploaded file does not contain a 'GL' sheet.")
        return None, None

    df = pd.read_excel(file, sheet_name="GL")
    df["Posting Date"] = pd.to_datetime(df["Posting Date"], errors='coerce')
    df["Month"] = df["Posting Date"].dt.strftime("%b-%y")  # Format: Apr-25

    # Define Financial Year (April–March)
    def get_fin_year(date):
        if pd.isna(date):
            return None
        year = date.year
        if date.month < 4:
            return f"{year-1}-{str(year)[-2:]}"
        else:
            return f"{year}-{str(year+1)[-2:]}"
    df["Financial Year"] = df["Posting Date"].apply(get_fin_year)

    if "DimensionLookup" in xls.sheet_names:
        name_map = pd.read_excel(file, sheet_name="DimensionLookup")
        expected_cols = ["DimensionCode", "DimensionName"]
        if not all(col in name_map.columns for col in expected_cols):
            st.warning(f"DimensionLookup sheet missing expected columns. Found columns: {list(name_map.columns)}")
            name_map = pd.DataFrame(columns=expected_cols)
    else:
        st.warning("Sheet 'DimensionLookup' not found. Using empty mapping.")
        name_map = pd.DataFrame(columns=["DimensionCode", "DimensionName"])

    return df, name_map

if uploaded_file:
    df, name_map = load_data(uploaded_file)
    if df is None:
        st.stop()

    code_to_name = dict(zip(name_map["DimensionCode"], name_map["DimensionName"])) if not name_map.empty else {}
    dimension_cols = [col for col in df.columns if "Dimension" in col]

    # Sidebar Filters
    with st.sidebar:
        st.header("📅 Filter by Date")
        sel_fys = st.multiselect(
            "Financial Year",
            sorted(df["Financial Year"].dropna().unique()),
            default=sorted(df["Financial Year"].dropna().unique())
        )
        month_options = df[df["Financial Year"].isin(sel_fys)]["Month"].dropna().unique()
        sel_months = st.multiselect("Month", sorted(month_options))
        df = df[df["Financial Year"].isin(sel_fys)]
        if sel_months:
            df = df[df["Month"].isin(sel_months)]

    # 📌 Key Insights
    st.subheader("📌 Key Insights")
    total_amount = df["Amount (LCY)"].sum()
    unique_gls = df["G/L Account Name"].nunique()
    selected_months = df["Month"].nunique()
    top_gl = (
        df.groupby("G/L Account Name")["Amount (LCY)"]
        .sum().reset_index()
        .sort_values("Amount (LCY)", ascending=False).head(1)
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("💰 Total Amount (LCY)", f"₹{format_indian(total_amount)}")
    col2.metric("🧾 Unique G/L Accounts", unique_gls)
    col3.metric("📅 Selected Months", selected_months)
    if not top_gl.empty:
        col4.metric("📈 Top G/L Account", f"{top_gl.iloc[0]['G/L Account Name']}", f"₹{format_indian(top_gl.iloc[0]['Amount (LCY)'])}")
    else:
        col4.metric("📈 Top G/L Account", "-", "-")

    # 1️⃣ G/L-wise Dimension Pivot
    st.subheader("1️⃣ G/L Account-wise Dimension Breakdown (Pivot)")
    selected_dim1 = st.selectbox("Select Dimension", dimension_cols, key="pivot_dim")
    if selected_dim1:
        df["_DimName"] = df[selected_dim1].map(code_to_name).fillna(df[selected_dim1])
        pivot_df = df.pivot_table(
            index="_DimName",
            columns="G/L Account Name",
            values="Amount (LCY)",
            aggfunc="sum",
            fill_value=0
        )
        pivot_df.loc["Total"] = pivot_df.sum()
        pivot_df = pivot_df.astype(int).applymap(format_indian)
        st.dataframe(pivot_df, use_container_width=True)

    # 2️⃣ G/L Account Dimension Breakdown
    st.subheader("2️⃣ Select a G/L Account to Breakdown by Dimension")
    gl_names = df["G/L Account Name"].dropna().unique()
    sel_gl = st.selectbox("Select G/L Account Name", sorted(gl_names), key="gl_select")
    if sel_gl:
        glf = df[df["G/L Account Name"] == sel_gl]
        dimb = st.selectbox("Select Dimension to Breakdown", dimension_cols, key="break_dim")
        if dimb:
            glf["_DimName"] = glf[dimb].map(code_to_name).fillna(glf[dimb])
            breakdown = (
                glf.groupby("_DimName")["Amount (LCY)"]
                .sum().reset_index()
                .sort_values("Amount (LCY)", ascending=False)
            )
            breakdown["Amount (LCY)"] = breakdown["Amount (LCY)"].astype(int).map(format_indian)
            st.dataframe(breakdown, use_container_width=True)
            st.markdown(f"**Total for {sel_gl}: ₹{format_indian(glf['Amount (LCY)'].sum())}**")

    # 3️⃣ Filtered G/L Summary with Search
    st.subheader("3️⃣ Filtered G/L Summary Based on Above Selection")
    search_term = st.text_input("🔍 Search G/L Account Name or Number")
    filtered_df = df[df["G/L Account Name"] == sel_gl] if sel_gl else df

    gl_summary = (
        filtered_df.groupby(["G/L Account No.", "G/L Account Name"])["Amount (LCY)"]
        .sum().reset_index()
        .sort_values("Amount (LCY)", ascending=False)
    )
    if search_term:
        mask = (
            gl_summary["G/L Account Name"].str.contains(search_term, case=False, na=False)
            | gl_summary["G/L Account No."].astype(str).str.contains(search_term, case=False, na=False)
        )
        gl_summary = gl_summary[mask]

    gl_summary["Amount (LCY)"] = gl_summary["Amount (LCY)"].astype(int).map(format_indian)
    st.dataframe(gl_summary, use_container_width=True)

else:
    st.info("📁 Please upload a GL Excel file to begin.")
