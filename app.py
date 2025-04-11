import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- Load data ---
df = {k.strip(): v for k, v in pd.read_excel('Sharp Token.xlsx', sheet_name=None).items()}
referral_df = df['Referrals']
token_df = df['Tokens distributed per day']
wallet_df = df['Wallets Created']
fee_df = df['POL Data']

tokens_source_df = pd.read_excel("Sharp Token.xlsx", sheet_name="Tokens per source")
tokens_source_df['Date'] = pd.to_datetime(tokens_source_df['Date'], format='%m-%d-%Y', errors='coerce')
tokens_source_df.dropna(subset=['Date'], inplace=True)
tokens_source_df['Date'] = tokens_source_df['Date'].dt.date  # strip time
tokens_source_df['Date'] = pd.to_datetime(tokens_source_df['Date'])  # convert back to datetime

# Use this cleaned version in the charts
df = tokens_source_df.copy()

# Identify numeric source columns
token_source_cols = df.select_dtypes(include='number').columns.tolist()

# --- Clean and prep data ---for df_ in [token_df, wallet_df, referral_df, fee_df]:
for df_ in [token_df, wallet_df, referral_df, fee_df]:
    if 'Date' in df_.columns:
        df_['Date'] = pd.to_datetime(df_['Date'], format='%Y-%m-%d', errors='coerce')
        df_.dropna(subset=['Date'], inplace=True)

referral_sources = [col for col in referral_df.columns if col != 'Date' and pd.api.types.is_numeric_dtype(referral_df[col])]
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
    platform_totals = wallet_df[['Android', 'iOS', 'Web']].sum().astype(int)
    
    wallet_pie = px.pie(
        names=platform_totals.index,
        values=platform_totals.values,
        title=(
            f'Wallet Platform Distribution<br>'
            f'Total: {platform_totals.sum():,} | '
            f'Android: {platform_totals["Android"]:,} | '
            f'iOS: {platform_totals["iOS"]:,} | '
            f'Web: {platform_totals["Web"]:,}'
        )
    )
    
    monthly_wallets = wallet_df.resample('ME', on='Date')[['Android', 'iOS', 'Web']].sum().reset_index()
    monthly_wallets['Month'] = monthly_wallets['Date'].dt.strftime('%B %Y')
    
    wallets_melted = monthly_wallets.melt(
        id_vars='Month',
        value_vars=['Android', 'iOS', 'Web'],
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
            f'Total: {platform_totals.sum():,} | '
            f'Android: {platform_totals["Android"]:,} | '
            f'iOS: {platform_totals["iOS"]:,} | '
            f'Web: {platform_totals["Web"]:,}'
        )
    )
    wallet_bar.update_layout(xaxis_tickangle=-45)

    # Referrals (from Jan 2025 only)
    rdf = referral_df[referral_df['Date'] >= '2025-01-01']
    referral_monthly = rdf.copy()
    referral_monthly['Month'] = referral_monthly['Date'].dt.to_period('M').dt.to_timestamp()
    referral_by_source = referral_monthly.groupby('Month')[referral_sources].sum().reset_index()
    referral_totals = referral_by_source[referral_sources].sum().astype(int)

    # Melt the dataframe to long format for proper legend labels
    referral_melted = referral_by_source.melt(
        id_vars='Month',
        value_vars=referral_sources,
        var_name='Campaign',
        value_name='Referrals'
    )
    
    # Grouped or stacked bar chart by campaign
    referral_bar = px.bar(
        referral_melted,
        x='Month',
        y='Referrals',
        color='Campaign',
        title=f"Monthly Referrals by Source (Total: {referral_totals.sum():,})",
        barmode='stack'  # or 'group' if you prefer side-by-side bars
    )
    
    # Line chart for total referrals over time
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

        # -------- TOKENS PER SOURCE --------
    tokens_source_df['Date'] = pd.to_datetime(tokens_source_df['Date'], errors='coerce').dt.date
    #tsdf = tokens_source_df[tokens_source_df['Date'] >= '2025-01-01'].copy()
    tsdf = tokens_source_df.copy()
    
    # 1. Total Token by Source - Bar Chart
    total_tokens = df[token_source_cols].sum().reset_index()
    total_tokens.columns = ['Source', 'Total Tokens']
    token_source_bar = px.bar(
        total_tokens,
        x='Source',
        y='Total Tokens',
        color='Source',  # color by source to get different colors
        title='Total Tokens by Source',
        color_discrete_sequence=px.colors.qualitative.Set3  # or try Plotly, Pastel, Bold etc.
    )
    
    # 2. Stacked Bar Chart - Tokens per Source Over Time
    # Prepare Monthly Tokens by Source
    df_stacked = df.copy()
    df_stacked['Month'] = df_stacked['Date'].astype(str).str[:7]  # e.g., '2025-04'
    
    # Group by Month and Sum Tokens per Source
    monthly_source_sum = df_stacked.groupby('Month')[token_source_cols].sum().reset_index()
    
    # Define rows and columns
    months = pd.to_datetime(monthly_source_sum['Month'], format="%Y-%m").dt.strftime('%b %Y')
    cols = 3
    rows = (len(months) + cols - 1) // cols
    
    # Create subplot grid for pies
    token_source_pie_grid = make_subplots(
        rows=rows,
        cols=cols,
        specs=[[{'type': 'domain'}]*cols]*rows,
        subplot_titles=[''] * len(months)  # Hide subplot titles
    )

    # Add each pie chart to the grid
    for i, row in monthly_source_sum.iterrows():
        r, c = divmod(i, cols)
        token_source_pie_grid.add_trace(
            go.Pie(
                labels=token_source_cols,
                values=row[token_source_cols],
                name='',
                marker=dict(colors=px.colors.qualitative.Safe),
                showlegend=(i == 0)  # Only show legend once
            ),
            row=r+1, col=c+1
        )
    
    # Update layout
    token_source_pie_grid.update_layout(
        title='Monthly Token Distribution by Source',
        showlegend=True,
        legend=dict(
            orientation='h',
            x=0.5,
            xanchor='center',
            y=-0.1
        )
    )

    return token_bar, token_line, wallet_pie, wallet_bar, referral_bar, referral_line, fee_line, \
       token_source_bar, token_source_pie_grid

# --- Generate charts once ---
token_bar, token_line, wallet_pie, wallet_bar, referral_bar, referral_line, fee_line, \
        token_source_bar, token_source_pie_grid = create_figures()

# --- Dash App ---
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}]
)

app.title = 'Sharp Token Dashboard'

app.layout = dbc.Container([
    html.H2("Sharp Token Dashboard", className="my-4 text-center"),

    # Token Metrics
    dbc.Row([
        dbc.Col(dcc.Graph(figure=token_bar), md=6),
        dbc.Col(dcc.Graph(figure=token_line), md=6),
    ], className="mb-4"),

    # Wallets
    dbc.Row([
        dbc.Col(dcc.Graph(figure=wallet_pie), md=6),
        dbc.Col(dcc.Graph(figure=wallet_bar), md=6),
    ], className="mb-4"),

    # Referrals
    dbc.Row([
        dbc.Col(dcc.Graph(figure=referral_bar), md=6),
        dbc.Col(dcc.Graph(figure=referral_line), md=6),
    ], className="mb-4"),

    # Fees
    dbc.Row([
        dbc.Col(dcc.Graph(figure=fee_line), md=12),
    ], className="mb-4"),

    # Tokens per Source
    dbc.Row([
        dbc.Col(dcc.Graph(figure=token_source_bar), md=6),        
        dbc.Col(dcc.Graph(figure=token_source_pie_grid), md=6),
    ], className="mb-4"),
    
], fluid=True)

import os

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 80))
    app.run(host='0.0.0.0')
