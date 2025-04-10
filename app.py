import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html
import dash_bootstrap_components as dbc

# --- Load data ---
df = {k.strip(): v for k, v in pd.read_excel('Sharp Token.xlsx', sheet_name=None).items()}
referral_df = df['Referrals']
token_df = df['Tokens distributed per day']
wallet_df = df['Wallets Created']
fee_df = df['POL Data']

# --- Clean and prep data ---for df_ in [token_df, wallet_df, referral_df, fee_df]:
for df_ in [token_df, wallet_df, referral_df, fee_df]:
    if 'Date' in df_.columns:
        df_['Date'] = pd.to_datetime(df_['Date'], errors='coerce')
        df_.dropna(subset=['Date'], inplace=True)

referral_sources = referral_df.columns.difference(['Date'])
referral_df['Referrals'] = referral_df[referral_sources].sum(axis=1)

# --- Precompute Figures ---
def create_figures():
    # Token Charts
    monthly_tokens = token_df.resample('ME', on='Date').sum().reset_index()
    monthly_tokens['Month'] = monthly_tokens['Date'].dt.strftime('%B %Y')
    total_tokens = token_df['Amount'].sum()

    token_bar = px.bar(
        monthly_tokens,
        x='Month',
        y='Amount',
        title=f'Monthly Token Distribution (Total: {total_tokens:,.0f})'
    )
    token_bar.update_layout(xaxis_tickangle=-45)

    token_line = px.line(
        monthly_tokens,
        x='Date',
        y='Amount',
        title=f'Monthly Token Growth Over Time (Total: {total_tokens:,.0f})'
    )

    # Wallet Charts
    platform_totals = wallet_df[['Android', 'iOS']].sum().astype(int)

    wallet_pie = px.pie(
        names=platform_totals.index,
        values=platform_totals.values,
        title=(
            f'Wallet Platform Distribution<br>'
            f'Total: {platform_totals.sum():,} | Android: {platform_totals["Android"]:,} | iOS: {platform_totals["iOS"]:,}'
        )
    )

    monthly_wallets = wallet_df.resample('ME', on='Date')[['Android', 'iOS']].sum().reset_index()
    monthly_wallets['Month'] = monthly_wallets['Date'].dt.strftime('%B %Y')
    wallets_melted = monthly_wallets.melt(
        id_vars='Month',
        value_vars=['Android', 'iOS'],
        var_name='Platform',
        value_name='Count'
    )

    wallet_bar = px.bar(
        wallets_melted,
        x='Month',
        y='Count',
        color='Platform',
        barmode='group',
        title=(
            f'Monthly Wallet Creation by Platform<br>'
            f'Total: {platform_totals.sum():,} | Android: {platform_totals["Android"]:,} | iOS: {platform_totals["iOS"]:,}'
        )
    )
    wallet_bar.update_layout(xaxis_tickangle=-45)

    # Referrals (from Jan 2025 only)
    rdf = referral_df[referral_df['Date'] >= '2025-01-01']
    referral_monthly = rdf.copy()
    referral_monthly['Month'] = referral_monthly['Date'].dt.to_period('M').dt.to_timestamp()
    referral_by_source = referral_monthly.groupby('Month')[referral_sources].sum().reset_index()
    referral_totals = referral_by_source[referral_sources].sum().astype(int)

    referral_bar = px.bar(
        referral_by_source,
        x='Month',
        y=referral_sources,
        title=f"Monthly Referrals by Source (Total: {referral_totals.sum():,})",
        barmode='stack'
    )

    referral_by_source['Total'] = referral_by_source[referral_sources].sum(axis=1)
    referral_line = px.line(
        referral_by_source,
        x='Month',
        y='Total',
        title='Monthly Total Referrals Over Time (From Jan 2025)',
        markers=True
    )

    # Fee Chart
    fdf = fee_df.copy()
    fdf['Month'] = fdf['Date'].dt.to_period('M').dt.to_timestamp()
    monthly_fee = fdf.groupby('Month')['TxnFee(MATIC)'].sum().reset_index()
    total_fee = int(monthly_fee['TxnFee(MATIC)'].sum())

    fee_line = px.line(
        monthly_fee,
        x='Month',
        y='TxnFee(MATIC)',
        title=f'Transaction Fee Trends by Month (Total: {total_fee:,} MATIC)',
        markers=True
    )

    return token_bar, token_line, wallet_pie, wallet_bar, referral_bar, referral_line, fee_line

# --- Generate charts once ---
token_bar, token_line, wallet_pie, wallet_bar, referral_bar, referral_line, fee_line = create_figures()

# --- Dash App ---
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = 'Sharp Token Dashboard'

app.layout = dbc.Container([
    html.H2("Sharp Token Dashboard"),
    dbc.Row([
        dbc.Col(dcc.Graph(figure=token_bar), md=6),
        dbc.Col(dcc.Graph(figure=token_line), md=6),
    ]),
    dbc.Row([
        dbc.Col(dcc.Graph(figure=wallet_pie), md=6),
        dbc.Col(dcc.Graph(figure=wallet_bar), md=6),
    ]),
    dbc.Row([
        dbc.Col(dcc.Graph(figure=referral_bar), md=6),
        dbc.Col(dcc.Graph(figure=referral_line), md=6),
    ]),
    dbc.Row([
        dbc.Col(dcc.Graph(figure=fee_line), md=12),
    ])
], fluid=True)

if __name__ == '__main__':
    app.run(debug=True)
