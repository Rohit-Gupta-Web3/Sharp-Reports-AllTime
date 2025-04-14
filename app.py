import os
import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- Load data ---
df = {k.strip(): v for k, v in pd.read_excel('Sharp Token.xlsx', sheet_name=None).items()}
referral_df = df['Referrals']
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

# --- Clean and prep data ---for df_ in [wallet_df, referral_df, fee_df]:
for df_ in [wallet_df, referral_df, fee_df]:
    if 'Date' in df_.columns:
        df_['Date'] = pd.to_datetime(df_['Date'], format='%Y-%m-%d', errors='coerce')
        df_.dropna(subset=['Date'], inplace=True)

referral_sources = [col for col in referral_df.columns if col != 'Date' and pd.api.types.is_numeric_dtype(referral_df[col])]
referral_df['Referrals'] = referral_df[referral_sources].sum(axis=1)

tokens_source_df = pd.read_excel("Sharp Token.xlsx", sheet_name="Tokens per source")
tokens_source_df['Date'] = pd.to_datetime(tokens_source_df['Date'], format='%m-%d-%Y', errors='coerce')
tokens_source_df.dropna(subset=['Date'], inplace=True)

# Identify token source columns here (do it early)
token_source_cols = tokens_source_df.select_dtypes(include='number').columns.tolist()

# --- Precompute Figures ---
def create_figures():
    # Token Charts
    # 1. Filter from Jan 1, 2025 onwards
    tsdf = tokens_source_df[tokens_source_df['Date'] >= '2025-01-01'].copy()
    
    # 2. Get list of source columns (excluding 'Total' if present)
    token_source_cols = tsdf.select_dtypes(include='number').columns.tolist()
    token_source_cols = [col for col in token_source_cols if col != 'Total']
    
    # 3. Resample monthly
    monthly_tokens = tsdf.resample('ME', on='Date').sum(numeric_only=True).reset_index()
    monthly_tokens['Month'] = monthly_tokens['Date'].dt.strftime('%B %Y')
    
    # 4. Use existing Total column, or calculate fallback
    if 'Total' not in monthly_tokens.columns:
        monthly_tokens['Total'] = monthly_tokens[token_source_cols].sum(axis=1)
    
    # 5. Get grand total
    total_tokens = monthly_tokens['Total'].sum()

    token_bar = px.bar(
        monthly_tokens,
        x='Month',
        y='Total',
        title=f'Monthly Token Distribution (Total: {total_tokens:,.0f})'
    )
    token_bar.update_layout(xaxis_tickangle=-45)

    token_line = px.line(
        monthly_tokens,
        x='Date',
        y='Total',
        title=f'Monthly Token Growth Over Time (Total: {total_tokens:,.0f})'
    )
    
    # Explicitly setting legend group and name for clarity
    token_line.update_traces(
        name="Total Tokens",
        legendgroup="Total Tokens"
    )
    
    # You can also ensure that the legend shows the correct label
    token_line.update_layout(
        showlegend=True,
        legend=dict(
            title="Legend",
            x=0.8,
            y=1,
            traceorder="normal",
            orientation="v"
        )
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
    tsdf = tokens_source_df.copy()
    
    # 1. Total Token by Source - Bar Chart
    total_tokens = df[token_source_cols].sum().reset_index()
    total_tokens.columns = ['Source', 'Total Tokens']

    grand_total = total_tokens['Total Tokens'].sum()
    
    token_source_bar = px.bar(
        total_tokens,
        x='Total Tokens',
        y='Source',
        orientation='h',
        color='Source',
        title=f'Total Tokens by Source (Total: {int(total_tokens["Total Tokens"].sum()):,})',
        color_discrete_sequence=px.colors.qualitative.Set3,
        text=None
    )
    
    token_source_bar.update_traces(
        text=total_tokens['Total Tokens'],
        texttemplate='%{x:,.0f}',
        insidetextanchor='middle'
    )
    
    token_source_bar.update_layout(
        showlegend = False,
        uniformtext_minsize=8,
        uniformtext_mode='hide',
        bargap=0.15,
        bargroupgap=0.1
    )

    # --- Monthly Tokens by Source (Pie Subplots) ---
    tsdf = tokens_source_df.copy()
    tsdf['Date'] = pd.to_datetime(tsdf['Date'], errors='coerce')
    tsdf = tsdf[tsdf['Date'] >= '2025-01-01'].dropna(subset=['Date'])
    
    tsdf['Month_dt'] = tsdf['Date'].dt.to_period('M').dt.to_timestamp()
    tsdf['Month'] = tsdf['Month_dt'].dt.strftime('%b %Y')
    tsdf = tsdf.sort_values('Month_dt')
    
    # Ensure consistent month order
    month_order = tsdf['Month'].unique().tolist()
    tsdf['Month'] = pd.Categorical(tsdf['Month'], categories=month_order, ordered=True)
    
    # Ensure token_source_cols is defined properly
    token_source_cols = [col for col in tsdf.columns if col not in ['Date', 'Month_dt', 'Month'] and pd.api.types.is_numeric_dtype(tsdf[col])]
    
    # Melt and group data
    melted = tsdf.melt(id_vars='Month', value_vars=token_source_cols, var_name='Source', value_name='Tokens')
    monthly_data = melted.groupby(['Month', 'Source'], observed=True).sum().reset_index()
    
    # Get ordered months and totals
    months = monthly_data['Month'].cat.categories.tolist()
    month_totals = monthly_data.groupby('Month', observed=True)['Tokens'].sum().to_dict()
    
    # Create subplot titles with line break
    subplot_titles = [f"{m}<br>Total: {int(month_totals[m]):,}" for m in months]
    
    # Create subplot titles (month only)
    subplot_titles = [f"{m}" for m in months]
    
    # Create subplot layout
    fig_pies = make_subplots(
        rows=1,
        cols=len(months),
        specs=[[{'type': 'domain'}]*len(months)],
        subplot_titles=subplot_titles
    )
    
    # Add pies and "Total" annotations
    annotations = []
    for i, month in enumerate(months):
        sub_df = monthly_data[monthly_data['Month'] == month]
        fig_pies.add_trace(
            go.Pie(
                labels=sub_df['Source'],
                values=sub_df['Tokens'],
                name=str(month),
                textinfo='percent',
                text=sub_df['Source'],
                textposition='inside',
                hovertemplate='%{label}: %{value:,.0f} tokens (%{percent})<extra></extra>'
            ),
            row=1,
            col=i+1
        )
    
        # Add small total token annotation under the title
        annotations.append(dict(
            x=(i + 0.5) / len(months),   # center under each pie chart
            y=-0.25,                     # push it well below the chart
            text=f"<span style='font-size:12px'>Total: {int(sub_df['Tokens'].sum()):,}</span>",
            showarrow=False,
            xanchor='center',
            font=dict(size=12),
            xref='paper',
            yref='paper'
        ))
    
    fig_pies.update_layout(
        title_text=f"Monthly Token Distribution by Source (Total: {int(monthly_data['Tokens'].sum()):,})",
        margin=dict(t=100, b=80),
        annotations=fig_pies.layout.annotations + tuple(annotations)
    )
    return token_bar, token_line, wallet_pie, wallet_bar, referral_bar, referral_line, fee_line, token_source_bar, fig_pies

# --- Generate charts once ---
token_bar, token_line, wallet_pie, wallet_bar, referral_bar, referral_line, fee_line, \
        token_source_bar, fig_pies = create_figures()

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
        dbc.Col(dcc.Graph(figure=fee_line), md=6),
        dbc.Col(dcc.Graph(figure=token_source_bar), md=6),
    ], className="mb-4"),
    
    dbc.Row([
        dbc.Col(dcc.Graph(figure=fig_pies), md=12),
    ], className="mb-4"),
    
], fluid=True)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 80))
    app.run(host='0.0.0.0')
