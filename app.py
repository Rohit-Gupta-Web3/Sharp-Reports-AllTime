import os
import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

# --- Load data ---
df = {k.strip(): v for k, v in pd.read_excel("Sharp Token.xlsx", sheet_name=None).items()}
referral_df = df["Referrals"]
wallet_df = df["Wallets Created"]
fee_df = df["POL Data"]

tokens_source_df = pd.read_excel("Sharp Token.xlsx", sheet_name="Tokens per source")
tokens_source_df["Date"] = pd.to_datetime(tokens_source_df["Date"], format="%m-%d-%Y", errors="coerce")
tokens_source_df.dropna(subset=["Date"], inplace=True)
tokens_source_df["Date"] = tokens_source_df["Date"].dt.date
tokens_source_df["Date"] = pd.to_datetime(tokens_source_df["Date"])

# --- Clean and prep data ---
for df_ in [wallet_df, referral_df, fee_df]:
    if "Date" in df_.columns:
        df_["Date"] = pd.to_datetime(df_["Date"], format="%Y-%m-%d", errors="coerce")
        df_.dropna(subset=["Date"], inplace=True)

referral_sources = [col for col in referral_df.columns if col != "Date" and pd.api.types.is_numeric_dtype(referral_df[col])]
referral_df["Referrals"] = referral_df[referral_sources].sum(axis=1)

# --- Precompute Figures ---
def create_figures():
    # --- Token Charts ---
    tsdf = tokens_source_df.copy()
    token_source_cols = [col for col in tsdf.select_dtypes(include="number").columns if col != "Total"]
    monthly_tokens = tsdf.resample("MS", on="Date").sum(numeric_only=True).reset_index()
    monthly_tokens["Month"] = monthly_tokens["Date"]
    monthly_tokens["MonthLabel"] = monthly_tokens["Date"].dt.strftime("%B %Y")
    if "Total" not in monthly_tokens.columns:
        monthly_tokens["Total"] = monthly_tokens[token_source_cols].sum(axis=1)
    total_tokens = monthly_tokens["Total"].sum()

    token_bar = px.bar(monthly_tokens, x="Month", y="Total", title=f"Monthly Token Distribution (Total: {total_tokens:,.0f})", text="Total")
    token_bar.update_traces(texttemplate="%{text:,.0f}", textposition="auto")
    token_bar.update_layout(xaxis_tickangle=-45)

    token_line = px.line(monthly_tokens, x="Month", y="Total", title=f"Monthly Token Growth Over Time (Total: {total_tokens:,.0f})", markers=True)

    # --- Wallet Charts ---
    wallet_df["Month"] = wallet_df["Date"].dt.to_period("M").dt.to_timestamp()
    monthly_wallets = wallet_df.groupby("Month")[["Android", "iOS", "Web"]].sum().reset_index()
    platform_totals = monthly_wallets[["Android", "iOS", "Web"]].sum().astype(int)

    wallets_melted = monthly_wallets.melt(id_vars="Month", value_vars=["Android", "iOS", "Web"], var_name="Platform", value_name="Count")
    wallet_bar = px.bar(wallets_melted, x="Month", y="Count", color="Platform", barmode="group",
                        title=f"Monthly Wallet Creation by Platform<br>Total: {platform_totals.sum():,}")

    wallet_pie = px.pie(names=platform_totals.index, values=platform_totals.values, hole=0.4,
                        title=f"Wallet Platform Distribution<br>Total: {platform_totals.sum():,}")

    # --- Referrals ---
    rdf = referral_df.copy()
    rdf["Month"] = rdf["Date"].dt.to_period("M").dt.to_timestamp()
    referral_by_source = rdf.groupby("Month")[referral_sources].sum().reset_index()
    referral_totals = referral_by_source[referral_sources].sum().astype(int)

    referral_melted = referral_by_source.melt(id_vars="Month", value_vars=referral_sources, var_name="Campaign", value_name="Referrals")
    referral_bar = px.bar(referral_melted, x="Month", y="Referrals", color="Campaign", barmode="stack",
                          title=f"Monthly Referrals by Source (Total: {referral_totals.sum():,})")

    referral_totals_by_month = referral_melted.groupby("Month")["Referrals"].sum().reset_index()
    referral_bar.add_trace(go.Scatter(
        x=referral_totals_by_month["Month"], y=referral_totals_by_month["Referrals"],
        text=referral_totals_by_month["Referrals"].apply(lambda x: f"{int(x):,}"),
        mode="text", textposition="top center", showlegend=False
    ))

    referral_by_source["Total"] = referral_by_source[referral_sources].sum(axis=1)
    referral_line = px.line(referral_by_source, x="Month", y="Total", title="Monthly Total Referrals Over Time", markers=True)

    # --- Fee Chart ---
    fdf = fee_df.copy()
    fdf["Month"] = fdf["Date"].dt.to_period("M").dt.to_timestamp()
    monthly_fee = fdf.groupby("Month")["TxnFee(POL)"].sum().reset_index()
    total_fee = int(monthly_fee["TxnFee(POL)"].sum())
    fee_line = px.line(monthly_fee, x="Month", y="TxnFee(POL)", title=f"Transaction Fee Trends by Month (Total: {total_fee:,} POL)", markers=True)

    # --- Token Source Total ---
    total_tokens_source = tokens_source_df[token_source_cols].sum().reset_index()
    total_tokens_source.columns = ["Source", "Total Tokens"]
    token_source_bar = px.bar(total_tokens_source, x="Total Tokens", y="Source", orientation="h", color="Source",
                               title=f"Total Tokens by Source (Total: {int(total_tokens_source['Total Tokens'].sum()):,})")

    # --- Monthly Pie Charts: 6 per row ---
    tsdf["Month_dt"] = tsdf["Date"].dt.to_period("M").dt.to_timestamp()
    tsdf["Month"] = tsdf["Month_dt"].dt.strftime("%b %Y")
    tsdf = tsdf.sort_values("Month_dt")
    melted = tsdf.melt(id_vars="Month", value_vars=token_source_cols, var_name="Source", value_name="Tokens")
    monthly_data = melted.groupby(["Month", "Source"], observed=True).sum().reset_index()
    months = monthly_data["Month"].unique().tolist()

    figs_pie = []
    row = []
    for i, m in enumerate(months):
        sub_df = monthly_data[monthly_data["Month"] == m]
        fig = px.pie(sub_df, names="Source", values="Tokens", title=f"{m} Token Distribution", hole=0.4)
        row.append(dbc.Col(dcc.Graph(figure=fig), width=2))
        if (i + 1) % 6 == 0:
            figs_pie.append(dbc.Row(row, className="mb-4"))
            row = []
    if row:
        figs_pie.append(dbc.Row(row, className="mb-4"))

    return token_bar, token_line, wallet_pie, wallet_bar, referral_bar, referral_line, fee_line, token_source_bar, figs_pie

# --- Generate all charts ---
token_bar, token_line, wallet_pie, wallet_bar, referral_bar, referral_line, fee_line, token_source_bar, figs_pie = create_figures()

# --- Dash App Layout ---
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Sharp Token Dashboard All Time"

app.layout = dbc.Container([
    html.H2("Sharp Token Dashboard All Time", className="my-4 text-center"),
    dbc.Row([dbc.Col(dcc.Graph(figure=token_bar), width=12)], className="mb-4"),
    dbc.Row([dbc.Col(dcc.Graph(figure=token_line), width=12)], className="mb-4"),
    dbc.Row([
        dbc.Col(dcc.Graph(figure=wallet_pie), md=6),
        dbc.Col(dcc.Graph(figure=token_source_bar), md=6),
    ], className="mb-4"),
    dbc.Row([dbc.Col(dcc.Graph(figure=wallet_bar), width=12)], className="mb-4"),
    dbc.Row([dbc.Col(dcc.Graph(figure=referral_bar), width=12)], className="mb-4"),
    dbc.Row([dbc.Col(dcc.Graph(figure=referral_line), width=12)], className="mb-4"),
    dbc.Row([dbc.Col(dcc.Graph(figure=fee_line), width=12)], className="mb-4"),
] + figs_pie)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 80))
    app.run(host='0.0.0.0')
