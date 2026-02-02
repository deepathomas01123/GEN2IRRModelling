import streamlit as st
import pandas as pd

st.set_page_config(page_title="Harvest Data Viewer", layout="wide")
st.title("🌱 Harvest Data Explorer")

# =========================
# FILE UPLOAD
# =========================
uploaded_file = st.file_uploader(
    "Upload your dataset (CSV or Excel)",
    type=["csv", "xlsx"]
)

if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    df.columns = df.columns.str.strip()
    st.success("File uploaded successfully!")

    # Ensure Pick Date is datetime
    df["Pick Date"] = pd.to_datetime(df["Pick Date"]).dt.date
    
    # Create Fiscal Year if not present (July–June FY)
    if "Fiscal Year" not in df.columns:
        df["Fiscal Year"] = df["Pick Date"].apply(
            lambda x: f"FY{str(x.year + 1)[-2:]}" if x.month >= 7 else f"FY{str(x.year)[-2:]}"
        )


    required_columns = [
        "Pick Date",
        "Fiscal Week No",
        "Yield Kg",
        "Variety Area (ha)",
        "Cost Per Kg - Total Harvest Cost",
        "Plant",
        "Variety"
    ]

    missing_cols = [c for c in required_columns if c not in df.columns]
    if missing_cols:
        st.error(f"Missing columns in dataset: {missing_cols}")
        st.stop()

    # =========================
    # 🔧 INPUT PARAMETERS
    # =========================
    st.sidebar.header("🔧 Harvest Inputs")

    harvest_speed = st.sidebar.number_input(
        "Harvest speed (Ha / Hour)",
        value=0.10,
        step=0.01
    )

    num_machines = st.sidebar.number_input(
        "Number of Machines",
        value=10,
        step=1
    )

    session_length = st.sidebar.number_input(
        "Harvest Session Length (Hours)",
        value=8.0,
        step=0.5
    )

    lost_damaged_pct = st.sidebar.number_input(
        "Lost / damaged harvest (Above traditional) %",
        value=15.0,
        step=1.0
    ) / 100

    opportunity_cost = st.sidebar.number_input(
        "Opportunity cost (Margins ex farming) – FNQ ($)",
        value=10.0,
        step=1.0
    )

    margin_reduction_factor = st.sidebar.number_input(
        "Margin reduction factor %",
        value=100.0,
        step=5.0
    ) / 100

    machine_to_staff = st.sidebar.number_input(
        "Machine to staff Ratio",
        value=5.0,
        step=1.0
    )

    staff_wages = st.sidebar.number_input(
        "Staff Wages",
        value=32.0,
        step=1.0
    )

    max_available_hours = num_machines * session_length

    # =========================
    # 🔍 FILTERS
    # =========================
    st.sidebar.header("🔍 Filters")

    # =========================
    # 🔍 TIME FILTERS
    # =========================
    st.sidebar.subheader("📅 Time Filters")
    
    fiscal_year_list = sorted(df["Fiscal Year"].dropna().unique())
    selected_fiscal_years = st.sidebar.multiselect(
        "Select Fiscal Year(s)",
        options=fiscal_year_list,
        default=fiscal_year_list
    )
    
    filtered_by_year = df[df["Fiscal Year"].isin(selected_fiscal_years)]
    
    fiscal_week_list = sorted(
        filtered_by_year["Fiscal Week No"].dropna().unique()
    )
    
    selected_fiscal_weeks = st.sidebar.multiselect(
        "Select Fiscal Week(s)",
        options=fiscal_week_list,
        default=fiscal_week_list
    )
    
    filtered_by_time = filtered_by_year[
        filtered_by_year["Fiscal Week No"].isin(selected_fiscal_weeks)
    ]


    plant_list = sorted(filtered_by_time["Plant"].dropna().unique())


    selected_plants = st.sidebar.multiselect(
        "Select Plant(s)",
        options=plant_list,
        default=plant_list[:1]  # select first plant by default
    )


    filtered_varieties = sorted(
        filtered_by_time[
            filtered_by_time["Plant"].isin(selected_plants)
        ]["Variety"].dropna().unique()
    )

    
    selected_varieties = st.sidebar.multiselect(
        "Select Variety(s)",
        options=filtered_varieties,
        default=filtered_varieties[:1]
    )


    filtered_df = filtered_by_time[
        (filtered_by_time["Plant"].isin(selected_plants)) &
        (filtered_by_time["Variety"].isin(selected_varieties))
    ].copy()



    # =========================
    # 🧮 CALCULATED COLUMNS
    # =========================

    # Yield per hectare
    filtered_df["Yield/Ha"] = (
        filtered_df["Yield Kg"] / filtered_df["Variety Area (ha)"]
    )

    # Excel IF logic (capacity-capped hours)
    filtered_df["Combined Platform Run time"] = (
        filtered_df["Variety Area (ha)"] / harvest_speed
    ).clip(upper=max_available_hours)

    

    # NEW 2️⃣ Area harvested
    filtered_df["Area_Harvested"] = (
        filtered_df["Combined Platform Run time"] * harvest_speed
    )

    # NEW 1️⃣ Yield harvested after losses
    filtered_df["Yield_Harvested"] = (
    (1 - lost_damaged_pct) *
    filtered_df["Yield/Ha"] *
    filtered_df["Area_Harvested"]
    )

    filtered_df["Yield_Lost"] = (
    lost_damaged_pct *
    filtered_df["Yield/Ha"] *
    filtered_df["Area_Harvested"]
    )

    filtered_df["Simple Lost Yield Cost"] = (
    opportunity_cost* filtered_df["Yield_Lost"]

    )

    filtered_df["Platform Kg/hour"] = (
    filtered_df['Yield_Harvested']/filtered_df['Combined Platform Run time']

    )
    
    filtered_df["Platform cost/kg"] = (
    (staff_wages/machine_to_staff)/filtered_df['Platform Kg/hour']
    )

    filtered_df["Daily harvest savings"] = (
    filtered_df['Yield_Harvested']*(filtered_df['Cost Per Kg - Total Harvest Cost']-filtered_df['Platform cost/kg'])
    )

    filtered_df["Savings - Yield loss cost"] = (
        filtered_df["Daily harvest savings"]
        - (
            filtered_df["Yield_Lost"]
            * opportunity_cost
            * margin_reduction_factor
        )
    ).clip(lower=0)

    # =========================
    # 📊 DISPLAY
    # =========================
    tab_data, tab_dictionary = st.tabs(["📊 Data", "📘 Data Dictionary"])

    with tab_data:

        st.dataframe(
            filtered_df[
                [
                    "Pick Date",
                    "Fiscal Week No",
                    "Yield Kg",
                    "Variety Area (ha)",
                    "Cost Per Kg - Total Harvest Cost",
                    "Yield/Ha",
                    "Combined Platform Run time",
                    "Area_Harvested",
                    "Yield_Harvested",
                    "Yield_Lost",
                    "Simple Lost Yield Cost",
                    "Platform Kg/hour",
                    "Platform cost/kg",
                    "Daily harvest savings",
                    'Savings - Yield loss cost'
                   
                ]
            ],
            use_container_width=True
        )
    
        # =========================
        # 📈 SUMMARY
        # =========================
        grouped_summary = (
            filtered_df
            .groupby(["Plant", "Variety"], as_index=False)
            .agg({
                "Yield Kg": "sum",
                "Area_Harvested": "sum",
                "Yield_Harvested": "sum",
                "Yield_Lost": "sum",
                "Daily harvest savings": "sum",
                "Savings - Yield loss cost": "sum"
            })
        )
        total_row = pd.DataFrame({
            "Plant": ["TOTAL"],
            "Variety": [""],
            "Yield Kg": [grouped_summary["Yield Kg"].sum()],
            "Area_Harvested": [grouped_summary["Area_Harvested"].sum()],
            "Yield_Harvested": [grouped_summary["Yield_Harvested"].sum()],
            "Yield_Lost": [grouped_summary["Yield_Lost"].sum()],
            "Daily harvest savings": [grouped_summary["Daily harvest savings"].sum()],
            "Savings - Yield loss cost": [grouped_summary["Savings - Yield loss cost"].sum()]
        })
    
        grouped_summary_with_total = pd.concat(
            [grouped_summary, total_row],
            ignore_index=True
        )
    
        st.subheader("📊 Combined Summary (Grouped)")
        st.dataframe(grouped_summary_with_total, use_container_width=True)

    with tab_dictionary:

        st.subheader("📘 Harvest Calculations – Data Dictionary")
    
        data_dictionary = pd.DataFrame([
            {
                "Column Name": "Yield/Ha",
                "Description": "Yield produced per hectare",
                "Formula": "Yield Kg / Variety Area (ha)",
                "Units": "kg/ha",
                "Notes": "Base productivity metric"
            },
            {
                "Column Name": "Combined Platform Run time",
                "Description": "Harvest hours required, capped by machine availability",
                "Formula": "MIN(Area / Harvest Speed, Machines × Session Length)",
                "Units": "hours",
                "Notes": "Capacity-constrained runtime"
            },
            {
                "Column Name": "Area_Harvested",
                "Description": "Actual area harvested by platform",
                "Formula": "Run Time × Harvest Speed",
                "Units": "hectares",
                "Notes": "Will not exceed available area"
            },
            {
                "Column Name": "Yield_Harvested",
                "Description": "Harvested yield after loss adjustment",
                "Formula": "(1 − Loss %) × Yield/Ha × Area Harvested",
                "Units": "kg",
                "Notes": "Accounts for damage/loss above traditional"
            },
            {
                "Column Name": "Yield_Lost",
                "Description": "Yield lost due to damage",
                "Formula": "Loss % × Yield/Ha × Area Harvested",
                "Units": "kg",
                "Notes": "Used for opportunity cost calculation"
            },
            {
                "Column Name": "Simple Lost Yield Cost",
                "Description": "Cost of lost yield",
                "Formula": "Yield Lost × Opportunity Cost",
                "Units": "$",
                "Notes": "Excludes margin reduction factor"
            },
            {
                "Column Name": "Platform Kg/hour",
                "Description": "Harvest productivity of platform",
                "Formula": "Yield Harvested / Run Time",
                "Units": "kg/hour",
                "Notes": "Efficiency metric"
            },
            {
                "Column Name": "Platform cost/kg",
                "Description": "Labour cost per kg using platform",
                "Formula": "(Staff Wages ÷ Machine-to-Staff Ratio) ÷ Kg/hour",
                "Units": "$/kg",
                "Notes": "Platform operating cost"
            },
            {
                "Column Name": "Daily harvest savings",
                "Description": "Cost savings vs traditional harvesting",
                "Formula": "Yield Harvested × (Traditional Cost − Platform Cost)",
                "Units": "$",
            },
            {
                "Column Name": "Savings - Yield loss cost",
                "Description": "Net savings after accounting for yield loss",
                "Formula": "Daily Savings − (Yield Lost × Opportunity Cost × Margin Factor)",
                "Units": "$",
                "Notes": "Floored at zero"
            }
        ])
    
        st.dataframe(data_dictionary, use_container_width=True)

        



