import streamlit as st
import pandas as pd

st.set_page_config(
    layout="wide"
)
# ============================================================
# PAGE CONFIG
# ============================================================
tab_results, tab_dictionary = st.tabs(
    ["📊 Harvest Results", "📘 Data Dictionary"]
)

with tab_results:
    
    st.title("🌱 Harvest Data Explorer")
             
    
    # ============================================================
    # LOAD SALES BUDGET (NUMERIC FISCAL YEAR)
    # ============================================================
    @st.cache_data

    def load_sales_budget():
        FILE_PATH = "data/SalesBudget.xlsx"
        # Header row usually NOT first row in finance files
        df = pd.read_excel(FILE_PATH, header=0)
    
        # Clean column names
        df.columns = (
            df.columns.astype(str)
            .str.replace("\xa0", " ", regex=False)
            .str.replace("\n", " ", regex=False)
            .str.strip()
        )
    
        # Fiscal Week
        df["Fiscal Week No"] = (
            df["Week"]
            .astype(str)
            .str.extract(r"(\d+)", expand=False)
            .astype(int)
        )
    
        # BX Budget Return (Kg) → numeric
        df["Budget Sales Price($)"] = (
            df["BX Budget Return (Kg)"]
            .astype(str)
            .str.replace(r"[^\d.]", "", regex=True)
            .astype(float)
        )
    
        # CY26 → 2026
        df["Fiscal Year"] = (
            df["CY"]
            .astype(str)
            .str.replace("CY", "")
            .astype(int)
            + 2000
        )
    
        return df[
            ["Fiscal Year", "Fiscal Week No", "Budget Sales Price($)"]
        ].dropna()
    
    
    budget_lookup = load_sales_budget()
    
    # ============================================================
    # PROCESS HARVEST DATA
    # ============================================================
    df = pd.read_excel("data/Actuals.xlsx")    
    df.columns = df.columns.str.strip()
    st.success("Harvest file uploaded successfully!")

    # Required columns
    required_columns = [
        "Costa Fiscal Year",
        "Pick Date",
        "Fiscal Week No",
        "Plant",
        "Product Variety",
        "Yield Kg",
        "Variety Area (ha)",
        "Cost Per Kg - Total Harvest Cost"
    ]

    missing = [c for c in required_columns if c not in df.columns]
    if missing:
        st.error(f"Missing columns: {missing}")
        st.stop()

    # Ensure correct types
    df["Fiscal Year"] = (
        df["Costa Fiscal Year"]
        .astype(str)
        .str.extract(r"(\d{4})", expand=False)
        .astype(int)
    )

    df["Fiscal Week No"] = df["Fiscal Week No"].astype(int)
    df["Pick Date"] = pd.to_datetime(df["Pick Date"])

    # ============================================================
    # SIDEBAR INPUTS
    # ============================================================
    st.sidebar.header("🔧 Harvest Inputs")

    st.sidebar.subheader("📦 Harvest Speed Configuration")
    
    # ---- initialise state (only once) ----
    if "minutes_per_100m" not in st.session_state:
        st.session_state.minutes_per_100m = 8.5
    
    if "time_per_cycle" not in st.session_state:
        st.session_state.time_per_cycle = st.session_state.minutes_per_100m * 60 / 33
    
    
    # ---- callbacks ----
    def update_time_per_cycle():
        st.session_state.time_per_cycle = (
            st.session_state.minutes_per_100m * 60 / 33
        )
    
    def update_minutes_per_100m():
        st.session_state.minutes_per_100m = (
            st.session_state.time_per_cycle * 33 / 60
        )
    
    
    with st.sidebar.container():
    
        st.number_input(
            "Harvest speed (minutes / 100m)",
            key="minutes_per_100m",
            step=0.1,
            on_change=update_time_per_cycle
        )
    
        st.number_input(
            "Time per cycle (sec / cycle)",
            key="time_per_cycle",
            step=0.1,
            on_change=update_minutes_per_100m
        )
    
        # ---- final calculated harvest speed ----
        harvest_speed = (
            (100 * 8.5 / 3)
            / (st.session_state.minutes_per_100m / 60)
            / 10000
        )
    
        st.markdown(
            f"""
            **Calculated Harvest Speed:**  
            🌱 `{harvest_speed:.4f} Ha / Hour`
            """
        )
    

    num_machines = st.sidebar.number_input(
        "Number of Machines",
        value=10,
        step=1
    )

    session_length = st.sidebar.number_input(
        "Session Length (Hours)",
        value=8.0,
        step=0.5
    )

    lost_damaged_pct = st.sidebar.number_input(
        "Lost / Damaged %",
        value=15.0,
        step=1.0
    ) / 100

    # margin_reduction_factor = st.sidebar.number_input(
    #     "Margin Reduction %",
    #     value=100.0,
    #     step=5.0
    # ) / 100

    machine_to_staff = st.sidebar.number_input(
        "Machine to Staff Ratio",
        value=5.0,
        step=1.0
    )

    staff_wages = st.sidebar.number_input(
        "Staff Wages ($/hr)",
        value=32.0,
        step=1.0
    )

    max_available_hours = num_machines * session_length

        # ============================================================
    # ADDITIONAL COST & EFFICIENCY INPUTS
    # ============================================================
    
    seconds_efficiency = st.sidebar.number_input(
        "Seconds Efficiency (%)",
        value=90.0,
        step=1.0
    ) / 100
    
    packaging_cost_per_kg = st.sidebar.number_input(
        "Packaging Cost ($/kg)",
        value=4.0,
        step=0.5
    )
    
    overhead_pct = st.sidebar.number_input(
        "Overhead Cost (%)",
        value=19.0,
        step=1.0
    ) / 100


    # ============================================================
    # FILTERS (TIME → PLANT → VARIETY)
    # ============================================================
    st.sidebar.subheader("📅 Time Filters")

    fy_list = sorted(
        df["Fiscal Year"]
        .isin([2025, 2026])
    )
    
    fy_options = sorted(df.loc[fy_list, "Fiscal Year"].unique())
    
    selected_fy = st.sidebar.selectbox(
        "Fiscal Year",
        options=fy_options,
        index=len(fy_options) - 1
    )
    
    df_time = df[df["Fiscal Year"] == selected_fy]

    fw_list = sorted(df_time["Fiscal Week No"].unique())
    selected_fw = st.sidebar.multiselect(
        "Fiscal Week",
        options=fw_list,
        default=fw_list
    )

    df_time = df_time[df_time["Fiscal Week No"].isin(selected_fw)]

    # Plant
    st.sidebar.subheader("🌱 Plant Filter")
    plant_list = sorted(df_time["Plant"].dropna().unique())
    selected_plants = st.sidebar.multiselect(
        "Plant",
        options=plant_list,
        default=plant_list[:1] if plant_list else []
    )

    df_plant = df_time[df_time["Plant"].isin(selected_plants)]

    # Variety
    st.sidebar.subheader("🌿 Variety Filter")
    variety_list = sorted(df_plant["Product Variety"].dropna().unique())

    # Add Select All option
    variety_options = ["Select All"] + variety_list
    
    selected_varieties = st.sidebar.multiselect(
        "Variety",
        options=variety_options,
        default=["Select All"]
    )
    
    # Handle Select All logic
    if "Select All" in selected_varieties:
        selected_varieties = variety_list
    
    filtered_df = df_plant[
        df_plant["Product Variety"].isin(selected_varieties)
    ].copy()


    # ============================================================
    # MERGE OPPORTUNITY COST
    # ============================================================
    filtered_df = filtered_df.merge(
        budget_lookup,
        on=["Fiscal Year", "Fiscal Week No"],
        how="left"
    )

    if filtered_df["Budget Sales Price($)"].isna().any():
        st.warning("⚠️ Some Fiscal Year / Week combinations missing budget mapping")

    # ============================================================
    # CALCULATIONS
    # ============================================================
    filtered_df["Yield/Ha"] = (
        filtered_df["Yield Kg"] / filtered_df["Variety Area (ha)"]
    )

    filtered_df["Combined Platform Run time"] = (
        filtered_df["Variety Area (ha)"] / harvest_speed
    ).clip(upper=max_available_hours)

    filtered_df["Area_Harvested"] = (
        filtered_df["Combined Platform Run time"] * harvest_speed
    )

    filtered_df["Yield_Harvested"] = (
        (1 - lost_damaged_pct)
        * filtered_df["Yield/Ha"]
        * filtered_df["Area_Harvested"]
    )

    filtered_df["Yield_Lost"] = (
        lost_damaged_pct
        * filtered_df["Yield/Ha"]
        * filtered_df["Area_Harvested"]
    )


    filtered_df["Opportunity Cost"] = (
        filtered_df["Budget Sales Price($)"] * filtered_df["Yield_Lost"]* seconds_efficiency
        - (
            overhead_pct * filtered_df["Cost Per Kg - Total Harvest Cost"] * filtered_df["Yield_Lost"]
            + packaging_cost_per_kg * filtered_df["Yield_Lost"] *seconds_efficiency
        )
    ).clip(lower=0)


    filtered_df["Platform Kg/hour"] = (
        filtered_df["Yield_Harvested"]
        / filtered_df["Combined Platform Run time"].replace(0, pd.NA)
    )

    filtered_df["Platform cost/kg"] = (
        (staff_wages / machine_to_staff)
        / filtered_df["Platform Kg/hour"]
    )

    filtered_df["Daily harvest savings"] = (
        filtered_df["Yield_Harvested"]
        * (
            filtered_df["Cost Per Kg - Total Harvest Cost"]
            - filtered_df["Platform cost/kg"]
        )
    )

    filtered_df["Savings - Yield loss cost"] = (
        filtered_df["Daily harvest savings"]
        - filtered_df["Opportunity Cost"]
    )

    filtered_df["Pick Date"] = pd.to_datetime(filtered_df["Pick Date"]).dt.date

    st.subheader("📊 Harvest Results")
    st.dataframe(filtered_df, use_container_width=True)

    # ============================================================
    # SUMMARY + TOTAL ROW
    # ============================================================
    grouped_summary = (
        filtered_df
        .groupby(["Plant", "Product Variety"], as_index=False)
        .agg(
            Yield_Kg=("Yield Kg", "sum"),
            Area_Harvested=("Area_Harvested", "sum"),
            Yield_Harvested=("Yield_Harvested", "sum"),
            Yield_Lost=("Yield_Lost", "sum"),
            Daily_harvest_savings=("Daily harvest savings", "sum"),
            Savings_Yield_loss_cost=(
                "Savings - Yield loss cost",
                lambda x: x[x > 0].sum()
            )
        )
    )

    total_row = pd.DataFrame({
        "Plant": ["TOTAL"],
        "Product Variety": [""],
        "Yield_Kg": [grouped_summary["Yield_Kg"].sum()],
        "Area_Harvested": [grouped_summary["Area_Harvested"].sum()],
        "Yield_Harvested": [grouped_summary["Yield_Harvested"].sum()],
        "Yield_Lost": [grouped_summary["Yield_Lost"].sum()],
        "Daily_harvest_savings": [grouped_summary["Daily_harvest_savings"].sum()],
        "Savings_Yield_loss_cost": [grouped_summary["Savings_Yield_loss_cost"].sum()]
    })


    grouped_summary = pd.concat(
        [grouped_summary, total_row],
        ignore_index=True
    )

    plant_savings = (
        filtered_df
        .groupby("Plant", as_index=False)
        .agg(
            Net_Savings=("Savings - Yield loss cost", "sum")
        )
        .sort_values("Net_Savings", ascending=False)
    )


    currency_cols = [
        "Daily_harvest_savings",
        "Savings_Yield_loss_cost"
    ]
    
    styled_summary = grouped_summary.style.format({
        col: "${:,.0f}" for col in currency_cols
    })

    st.subheader("📊 Combined Summary (Grouped)")
    st.dataframe(styled_summary, use_container_width=True)

    total_days = filtered_df.shape[0]
    positive_days = (
        filtered_df["Savings - Yield loss cost"] > 0
    ).sum()

    pct_positive_days = (
        positive_days / total_days * 100
        if total_days > 0 else 0
    )

    st.metric(
        label="📈 % Days with Positive Net Savings",
        value=f"{pct_positive_days:.1f}%",
        help="Percentage of harvest days where Savings – Yield loss cost was greater than zero"
    )

    st.subheader("📈 Net Savings by Plant (Selected Period)")
    
    st.bar_chart(
        plant_savings.set_index("Plant")["Net_Savings"],
        use_container_width=True
    )

    





with tab_dictionary:

    st.subheader("📘 Harvest Model – Data Dictionary")
    st.markdown(
        """
        This table documents **all calculated fields**, their formulas,
        and the business assumptions used in the Harvest Data Explorer.
        """
    )

    data_dictionary = pd.DataFrame([
        {
            "Field Name": "Yield/Ha",
            "Description": "Yield density per hectare for the selected plant and variety",
            "Formula / Logic": "Yield Kg ÷ Variety Area (ha)",
            "Key Assumptions": "Yield is evenly distributed across the planted area"
        },
        {
            "Field Name": "Combined Platform Run time",
            "Description": "Total platform runtime required to harvest the variety area",
            "Formula / Logic": "Variety Area (ha) ÷ Harvest Speed (ha/hr), capped at max available hours",
            "Key Assumptions": "Machines operate continuously up to the available session hours"
        },
        {
            "Field Name": "Area_Harvested",
            "Description": "Total area harvested by the platform during the session",
            "Formula / Logic": "Combined Platform Run time × Harvest Speed",
            "Key Assumptions": "No downtime or inefficiency beyond the runtime cap"
        },
        {
            "Field Name": "Yield_Harvested",
            "Description": "Net harvested yield after accounting for damage and losses",
            "Formula / Logic": "(1 − Lost/Damaged %) × Yield/Ha × Area_Harvested",
            "Key Assumptions": "Loss percentage applies uniformly across harvested area"
        },
        {
            "Field Name": "Yield_Lost",
            "Description": "Yield lost due to damage, inefficiency, or handling",
            "Formula / Logic": "Lost/Damaged % × Yield/Ha × Area_Harvested",
            "Key Assumptions": "Lost yield cannot be recovered for sale"
        },
        {
            "Field Name": "Seconds Efficiency",
            "Description": "Proportion of lost yield that becomes true waste",
            "Formula / Logic": "User input (default 90%)",
            "Key Assumptions": "Remaining percentage is recovered as seconds-grade fruit"
        },
        {
            "Field Name": "Budget Sales Price($)",
            "Description": "Budgeted sales price per kg for the given fiscal year and week",
            "Formula / Logic": "Lookup from Sales Budget table by Fiscal Year & Fiscal Week",
            "Key Assumptions": "Budget price reflects expected market value"
        },
        {
            "Field Name": "Opportunity Cost",
            "Description": "Net revenue lost due to damaged or unharvested fruit",
            "Formula / Logic": (
                "(Budget Sales Price × Yield_Lost × Seconds Efficiency) − "
                "(Overhead % × Cost Per Kg × Yield_Lost + Packaging Cost × Yield_Lost × Seconds Efficiency)"
            ),
            "Key Assumptions": "Lost yield incurs avoided costs (packaging & overhead)"
        },
        {
            "Field Name": "Platform Kg/hour",
            "Description": "Harvest productivity rate of the platform",
            "Formula / Logic": "Yield_Harvested ÷ Combined Platform Run time",
            "Key Assumptions": "Productivity is stable across the harvesting session"
        },
        {
            "Field Name": "Platform cost/kg",
            "Description": "Labour cost per kg using platform harvesting",
            "Formula / Logic": "(Staff Wages ÷ Machine-to-Staff Ratio) ÷ Platform Kg/hour",
            "Key Assumptions": "Staff are evenly distributed across machines"
        },
        {
            "Field Name": "Daily harvest savings",
            "Description": "Cost savings achieved by platform harvesting versus baseline",
            "Formula / Logic": "Yield_Harvested × (Baseline Cost/kg − Platform cost/kg)",
            "Key Assumptions": "Baseline cost reflects traditional harvesting"
        },
        {
            "Field Name": "Savings - Yield loss cost",
            "Description": "Net economic benefit after accounting for lost yield",
            "Formula / Logic": "Daily harvest savings − Opportunity Cost",
            "Key Assumptions": "Negative savings are clipped to zero"
        },
        {
            "Field Name": "Pick Date",
            "Description": "Date on which harvesting occurred",
            "Formula / Logic": "Converted to date format (YYYY-MM-DD)",
            "Key Assumptions": "Time of day is not analytically relevant"
        }
    ])


    st.dataframe(
        data_dictionary,
        use_container_width=True,
        hide_index=True
    )

    st.info(
        "ℹ️ All percentages, costs, and efficiencies are user-adjustable "
        "to support scenario testing and sensitivity analysis."
    )

