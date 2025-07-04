import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, html, dcc

# Initialize app
app = Dash(__name__)
server = app.server

# Load and prepare data
df = pd.read_excel("Sharp Token.xlsx", sheet_name=None)
referral_df = df["Referrals"]
wallet_df = df["Wallets Created"]
fee_df = df["POL Data"]
tokens_df = df["Tokens per source"].copy()

# Preprocess date filtering
tokens_df["Date"] = pd.to_datetime(tokens_df["Date"], errors="coerce")
tokens_df.dropna(subset=["Date"], inplace=True)
tokens_df = tokens_df[tokens_df["Date"] < "2025-07-01"].copy()
tokens_df["Month"] = tokens_df["Date"].dt.to_period("M").dt.to_timestamp()

for df_ in [wallet_df, referral_df, fee_df]:
    df_["Date"] = pd.to_datetime(df_["Date"], errors="coerce")
    df_.dropna(subset=["Date"], inplace=True)
    df_.drop(df_.index[df_["Date"] >= "2025-07-01"], inplace=True)
    df_["Month"] = df_["Date"].dt.to_period("M").dt.to_timestamp()

# --- Graphs ---
# Token Distribution Over Time
token_sources = [col for col in tokens_df.columns if col not in ["Date", "Month", "Total"] and pd.api.types.is_numeric_dtype(tokens_df[col])]
token_monthly = tokens_df.groupby("Month")[token_sources].sum().reset_index()
token_monthly["Total"] = token_monthly[token_sources].sum(axis=1)
token_monthly["MonthStr"] = token_monthly["Month"].dt.strftime("%b %Y")
total_tokens = int(token_monthly["Total"].sum())

fig1 = px.bar(token_monthly, x="MonthStr", y="Total", text="Total", title=f"Monthly Token Distribution (Total: {total_tokens:,})", height=500)
fig1.update_traces(texttemplate="%{text:,.0f}", textposition="outside")

fig2 = px.line(token_monthly, x="MonthStr", y="Total", markers=True, title="Token Growth Over Time", height=500)

# Wallets Created
wallet_sources = [col for col in wallet_df.columns if col not in ["Date", "Month"] and pd.api.types.is_numeric_dtype(wallet_df[col])]
wallet_monthly = wallet_df.groupby("Month")[wallet_sources].sum().reset_index()
wallet_monthly["Total"] = wallet_monthly[wallet_sources].sum(axis=1)
wallet_monthly["MonthStr"] = wallet_monthly["Month"].dt.strftime("%b %Y")
platform_totals = wallet_monthly[wallet_sources].sum()

fig3 = px.bar(wallet_monthly, x="MonthStr", y="Total", text="Total", title="Monthly Wallets Created", height=500)
fig3.update_traces(texttemplate="%{text:,.0f}", textposition="outside")

fig4 = px.pie(names=platform_totals.index, values=platform_totals.values, hole=0.4, title="Wallet Platform Distribution", height=500)

# Monthly wallet creation by platform
fig9 = px.bar(wallet_monthly, x="MonthStr", y=wallet_sources, title="Monthly Wallet Creation by Platform", height=500)

# Referrals
referral_sources = [col for col in referral_df.columns if col not in ["Date", "Month"] and pd.api.types.is_numeric_dtype(referral_df[col])]
referral_df["Referrals_Total"] = referral_df[referral_sources].sum(axis=1)
referral_monthly = referral_df.groupby("Month")[referral_sources + ["Referrals_Total"]].sum().reset_index()
referral_monthly["MonthStr"] = referral_monthly["Month"].dt.strftime("%b %Y")
melted_referrals = referral_monthly.melt(id_vars="MonthStr", value_vars=referral_sources, var_name="Campaign", value_name="Referrals_Count")

fig5 = px.bar(melted_referrals, x="MonthStr", y="Referrals_Count", color="Campaign", barmode="stack", title="Monthly Referrals by Source", height=500, color_discrete_sequence=px.colors.qualitative.Bold)
fig6 = px.line(referral_monthly, x="MonthStr", y="Referrals_Total", markers=True, title="Total Monthly Referrals", height=500)

# POL Fee Chart
monthly_fee = fee_df.groupby("Month")["TxnFee(POL)"].sum().reset_index()
monthly_fee["MonthStr"] = monthly_fee["Month"].dt.strftime("%b %Y")
fig7 = px.line(monthly_fee, x="MonthStr", y="TxnFee(POL)", markers=True, title="Monthly POL Fees", height=500)

# Token Source Totals
token_source_totals = tokens_df[token_sources].sum().reset_index()
token_source_totals.columns = ["Source", "Total Tokens"]
fig8 = px.bar(token_source_totals, x="Total Tokens", y="Source", orientation="h", title="Total Tokens by Source", height=500, color="Source", color_discrete_sequence=px.colors.qualitative.Vivid)
fig8.update_traces(texttemplate="%{x:,.0f}")

# Monthly Token Distribution by Source
monthly_token_pie_data = tokens_df.copy()
monthly_token_pie_data["MonthStr"] = monthly_token_pie_data["Month"].dt.strftime("%b %Y")
melted = monthly_token_pie_data.melt(id_vars="MonthStr", value_vars=token_sources, var_name="Source", value_name="Tokens")

fig10 = px.sunburst(melted, path=["MonthStr", "Source"], values="Tokens", title="Monthly Token Distributed by Source")

# Layout
app.layout = html.Div([
    html.H1("Sharp Token Dashboard"),
    dcc.Graph(figure=fig1),
    dcc.Graph(figure=fig2),
    dcc.Graph(figure=fig3),
    dcc.Graph(figure=fig4),
    dcc.Graph(figure=fig5),
    dcc.Graph(figure=fig6),
    dcc.Graph(figure=fig7),
    dcc.Graph(figure=fig8),
    dcc.Graph(figure=fig9),
    dcc.Graph(figure=fig10)
])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 80))
    app.run(host='0.0.0.0')
