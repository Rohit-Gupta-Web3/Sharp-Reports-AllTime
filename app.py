# Sharp Token Dashboard - Jupyter Notebook Version

import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from IPython.display import display

# --- Load data ---
df = {k.strip(): v for k, v in pd.read_excel("Sharp Token.xlsx", sheet_name=None).items()}

referral_df = df["Referrals"]
wallet_df = df["Wallets Created"]
fee_df = df["POL Data"]
tokens_source_df = df["Tokens per source"]

# --- Clean and prep data ---
tokens_source_df["Date"] = pd.to_datetime(tokens_source_df["Date"], errors="coerce")
tokens_source_df.dropna(subset=["Date"], inplace=True)
tokens_source_df = tokens_source_df[tokens_source_df["Date"] < "2025-07-01"]
tokens_source_df["Date"] = tokens_source_df["Date"].dt.to_period("M").dt.to_timestamp()

for df_ in [wallet_df, referral_df, fee_df]:
    if "Date" in df_.columns:
        df_["Date"] = pd.to_datetime(df_["Date"], errors="coerce")
        df_.dropna(subset=["Date"], inplace=True)
        df_.drop(df_.index[df_["Date"] >= "2025-07-01"], inplace=True)
        df_["Month"] = df_["Date"].dt.to_period("M").dt.to_timestamp()

referral_sources = [col for col in referral_df.columns if col not in ["Date", "Month"] and pd.api.types.is_numeric_dtype(referral_df[col])]
referral_df["Referrals_Total"] = referral_df[referral_sources].sum(axis=1)

# --- Token Charts ---
token_sources = [col for col in tokens_source_df.columns if col not in ["Date", "Total"] and pd.api.types.is_numeric_dtype(tokens_source_df[col])]
token_monthly = tokens_source_df.groupby("Date")[token_sources].sum().reset_index()
token_monthly["Total"] = token_monthly[token_sources].sum(axis=1)
total_tokens = int(token_monthly["Total"].sum())

token_monthly["Month"] = token_monthly["Date"].dt.strftime("%b %Y")
fig1 = px.bar(token_monthly, x="Month", y="Total", text="Total", title=f"Monthly Token Distribution (Total: {total_tokens:,})", height=500)
fig1.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
fig1.update_xaxes(tickmode="array", tickvals=token_monthly["Month"], ticktext=token_monthly["Month"])
fig1.show()

fig2 = px.line(token_monthly, x="Month", y="Total", markers=True, title=f"Token Growth Over Time (Total: {total_tokens:,})", height=500)
fig2.update_xaxes(tickmode="array", tickvals=token_monthly["Month"], ticktext=token_monthly["Month"])
fig2.show()

# --- Wallet Charts ---
wallet_sources = [col for col in wallet_df.columns if col not in ["Date", "Month"] and pd.api.types.is_numeric_dtype(wallet_df[col])]
wallet_monthly = wallet_df.groupby("Month")[wallet_sources].sum().reset_index()
wallet_monthly["Total"] = wallet_monthly[wallet_sources].sum(axis=1)
platform_totals = wallet_monthly[wallet_sources].sum()
wallet_monthly["MonthStr"] = wallet_monthly["Month"].dt.strftime("%b %Y")

fig3 = px.bar(wallet_monthly, x="MonthStr", y="Total", text="Total", title=f"Monthly Wallets Created (Total: {int(wallet_monthly['Total'].sum()):,})", height=500)
fig3.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
fig3.update_xaxes(tickmode="array", tickvals=wallet_monthly["MonthStr"], ticktext=wallet_monthly["MonthStr"])
fig3.show()

fig4 = px.pie(names=platform_totals.index, values=platform_totals.values, hole=0.4, title="Wallet Platform Distribution", height=500)
fig4.show()

# --- Referrals ---
referral_monthly = referral_df.groupby("Month")[referral_sources + ["Referrals_Total"]].sum().reset_index()
referral_monthly["MonthStr"] = referral_monthly["Month"].dt.strftime("%b %Y")
melted_referrals = referral_monthly.melt(id_vars="MonthStr", value_vars=referral_sources, var_name="Campaign", value_name="Referrals_Count")

fig5 = px.bar(melted_referrals, x="MonthStr", y="Referrals_Count", color="Campaign", barmode="stack", title="Monthly Referrals by Source", height=500, color_discrete_sequence=px.colors.qualitative.Bold)
fig5.update_xaxes(tickmode="array", tickvals=referral_monthly["MonthStr"], ticktext=referral_monthly["MonthStr"])
fig5.show()

fig6 = px.line(referral_monthly, x="MonthStr", y="Referrals_Total", markers=True, title="Total Monthly Referrals", height=500)
fig6.update_xaxes(tickmode="array", tickvals=referral_monthly["MonthStr"], ticktext=referral_monthly["MonthStr"])
fig6.show()

# --- Fee Chart ---
monthly_fee = fee_df.groupby("Month")["TxnFee(POL)"].sum().reset_index()
monthly_fee["MonthStr"] = monthly_fee["Month"].dt.strftime("%b %Y")
total_fee = int(monthly_fee["TxnFee(POL)"].sum())

fig7 = px.line(monthly_fee, x="MonthStr", y="TxnFee(POL)", markers=True, title=f"Monthly POL Fees (Total: {total_fee:,})", height=500)
fig7.update_xaxes(tickmode="array", tickvals=monthly_fee["MonthStr"], ticktext=monthly_fee["MonthStr"])
fig7.show()

# --- Token Source Total ---
token_source_totals = tokens_source_df[token_sources].sum().reset_index()
token_source_totals.columns = ["Source", "Total Tokens"]
fig8 = px.bar(token_source_totals, x="Total Tokens", y="Source", orientation="h", title="Total Tokens by Source", height=500, color="Source", color_discrete_sequence=px.colors.qualitative.Vivid)
fig8.update_traces(texttemplate="%{x:,.0f}")
fig8.show()
