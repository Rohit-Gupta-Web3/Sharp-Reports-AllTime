import os
import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta, date
import uuid

# --- Timesheet helpers ---
TASKS_FILE = "tasks.csv"

def load_tasks():
    if os.path.exists(TASKS_FILE):
        df = pd.read_csv(TASKS_FILE, parse_dates=["date", "created_at"])
    else:
        df = pd.DataFrame(
            columns=[
                "id",
                "name",
                "date",
                "start",
                "end",
                "duration",
                "description",
                "completed",
                "created_at",
            ]
        )
    # ensure expected columns exist
    for col in [
        "id",
        "name",
        "date",
        "start",
        "end",
        "duration",
        "description",
        "completed",
        "created_at",
    ]:
        if col not in df.columns:
            df[col] = None
    if "completed" not in df.columns:
        df["completed"] = True
    return df


def save_tasks(df):
    df.to_csv(TASKS_FILE, index=False)

# --- Load data ---
df = {k.strip(): v for k, v in pd.read_excel("Sharp Token.xlsx", sheet_name=None).items()}

referral_df = df["Referrals"]
wallet_df = df["Wallets Created"]
fee_df = df["POL Data"]

tokens_source_df = pd.read_excel("Sharp Token.xlsx", sheet_name="Tokens per source")
tokens_source_df["Date"] = pd.to_datetime(tokens_source_df["Date"], errors="coerce")
tokens_source_df.dropna(subset=["Date"], inplace=True)
tokens_source_df["Date"] = tokens_source_df["Date"].dt.date
tokens_source_df["Date"] = pd.to_datetime(tokens_source_df["Date"])

# Load tasks data
tasks_df = load_tasks()

# --- Clean and prep data ---
for df_ in [wallet_df, referral_df, fee_df]:
    if "Date" in df_.columns:
        df_["Date"] = pd.to_datetime(df_["Date"], errors="coerce")
        df_.dropna(subset=["Date"], inplace=True)

referral_sources = [col for col in referral_df.columns if col != "Date" and pd.api.types.is_numeric_dtype(referral_df[col])]
referral_df["Referrals"] = referral_df[referral_sources].sum(axis=1)

# --- Precompute Figures ---
def create_figures():
    # Token Charts
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
    token_line.update_traces(name="Total Tokens", legendgroup="Total Tokens")
    token_line.update_layout(showlegend=True, legend=dict(title="Legend", x=0.8, y=1, traceorder="normal", orientation="v"))

    # Wallet Charts
    wallet_df["Month"] = wallet_df["Date"].dt.to_period("M").dt.to_timestamp()
    monthly_wallets = wallet_df.groupby("Month")[["Android", "iOS", "Web"]].sum().reset_index()
    platform_totals = monthly_wallets[["Android", "iOS", "Web"]].sum().astype(int)

    wallets_melted = monthly_wallets.melt(id_vars="Month", value_vars=["Android", "iOS", "Web"], var_name="Platform", value_name="Count")

    wallet_bar = px.bar(wallets_melted, x="Month", y="Count", color="Platform", barmode="group", title=(f"Monthly Wallet Creation by Platform<br>"
        f"Total: {platform_totals.sum():,} | Android: {platform_totals['Android']:,} | iOS: {platform_totals['iOS']:,} | Web: {platform_totals['Web']:,}"))
    wallet_bar.update_layout(xaxis_tickangle=-45)

    wallet_pie = px.pie(names=platform_totals.index, values=platform_totals.values, hole=0.4,
        title=(f"Wallet Platform Distribution<br>Total: {platform_totals.sum():,} | Android: {platform_totals['Android']:,} | iOS: {platform_totals['iOS']:,} | Web: {platform_totals['Web']:,}"))

    # Referrals
    referral_df["Month"] = referral_df["Date"].dt.to_period("M").dt.to_timestamp()
    referral_by_source = referral_df.groupby("Month")[referral_sources].sum().reset_index()
    referral_totals = referral_by_source[referral_sources].sum().astype(int)

    referral_melted = referral_by_source.melt(id_vars="Month", value_vars=referral_sources, var_name="Campaign", value_name="Referrals")
    referral_bar = px.bar(referral_melted, x="Month", y="Referrals", color="Campaign", title=f"Monthly Referrals by Source (Total: {referral_totals.sum():,})", barmode="stack", color_discrete_sequence=px.colors.qualitative.Vivid)

    referral_totals_by_month = referral_melted.groupby("Month")["Referrals"].sum().reset_index()
    referral_bar.add_trace(go.Scatter(x=referral_totals_by_month["Month"], y=referral_totals_by_month["Referrals"],
        text=referral_totals_by_month["Referrals"].apply(lambda x: f"{int(x):,}"), mode="text", textposition="top center", showlegend=False))

    referral_by_source["Total"] = referral_by_source[referral_sources].sum(axis=1)
    referral_line = px.line(referral_by_source, x="Month", y="Total", title="Monthly Total Referrals Over Time", markers=True)

    # Fee Chart
    fee_df["Month"] = fee_df["Date"].dt.to_period("M").dt.to_timestamp()
    monthly_fee = fee_df.groupby("Month")["TxnFee(POL)"].sum().reset_index()
    total_fee = int(monthly_fee["TxnFee(POL)"].sum())

    fee_line = px.line(monthly_fee, x="Month", y="TxnFee(POL)", title=f"Transaction Fee Trends by Month (Total: {total_fee:,} POL)", markers=True)

    # Total Tokens by Source
    total_tokens_df = tokens_source_df[token_source_cols].sum().reset_index()
    total_tokens_df.columns = ["Source", "Total Tokens"]
    token_source_bar = px.bar(total_tokens_df, x="Total Tokens", y="Source", orientation="h", color="Source",
        title=f'Total Tokens by Source (Total: {int(total_tokens_df["Total Tokens"].sum()):,})',
        color_discrete_sequence=px.colors.qualitative.Set3)
    token_source_bar.update_traces(text=total_tokens_df["Total Tokens"], texttemplate="%{x:,.0f}", insidetextanchor="middle")
    token_source_bar.update_layout(showlegend=False, uniformtext_minsize=8, uniformtext_mode="hide", bargap=0.15, bargroupgap=0.1)

    # Monthly Tokens by Source Pie Subplots
    tsdf = tokens_source_df.copy()
    tsdf["Month_dt"] = tsdf["Date"].dt.to_period("M").dt.to_timestamp()
    tsdf["Month"] = tsdf["Month_dt"].dt.strftime("%b %Y")
    tsdf = tsdf.sort_values("Month_dt")
    month_order = tsdf["Month"].unique().tolist()
    tsdf["Month"] = pd.Categorical(tsdf["Month"], categories=month_order, ordered=True)

    melted = tsdf.melt(id_vars="Month", value_vars=token_source_cols, var_name="Source", value_name="Tokens")
    monthly_data = melted.groupby(["Month", "Source"], observed=True).sum().reset_index()
    
    months = monthly_data["Month"].cat.categories.tolist()
    n_cols = 6  # max 6 pies per row
    n_rows = (len(months) + n_cols - 1) // n_cols
    subplot_titles = [f"{m}" for m in months]

    fig_pies = make_subplots(
        rows=n_rows,
        cols=n_cols,
        specs=[[{"type": "domain"}] * n_cols for _ in range(n_rows)],
        subplot_titles=subplot_titles,
    )
    annotations = []
    for idx, month in enumerate(months):
        row = idx // n_cols + 1
        col = idx % n_cols + 1
        sub_df = monthly_data[monthly_data["Month"] == month]
        fig_pies.add_trace(
            go.Pie(
                labels=sub_df["Source"],
                values=sub_df["Tokens"],
                name=str(month),
                textinfo="percent",
                text=sub_df["Source"],
                textposition="inside",
                hovertemplate="%{label}: %{value:,.0f} tokens (%{percent})",
                marker=dict(colors=px.colors.qualitative.Pastel),
            ),
            row=row,
            col=col,
        )
        annotations.append(
            dict(
                x=((col - 0.5) / n_cols),
                y=1 - (row / (n_rows + 0.5)),
                text=f"<b style='font-size:14px'>Total: {int(sub_df['Tokens'].sum()):,}</b>",
                showarrow=False,
                xanchor="center",
                font=dict(size=14),
                xref="paper",
                yref="paper",
            )
        )

    fig_pies.update_layout(
        title_text=f"Monthly Token Distribution by Source (Total: {int(monthly_data['Tokens'].sum()):,})",
        margin=dict(t=80, b=60),
        annotations=fig_pies.layout.annotations + tuple(annotations),
        height=400 * n_rows,
    )
    
    return token_bar, token_line, wallet_bar, wallet_pie, referral_bar, referral_line, fee_line, token_source_bar, fig_pies

# --- Generate charts once ---
token_bar, token_line, wallet_bar, wallet_pie, referral_bar, referral_line, fee_line, token_source_bar, fig_pies = create_figures()

dashboard_layout = dbc.Container([
    html.H2("Sharp Token Dashboard", className="my-4 text-center"),
    dbc.Row([dbc.Col(dcc.Graph(figure=token_bar), width=12)], className="mb-4"),
    dbc.Row([dbc.Col(dcc.Graph(figure=token_line), width=12)], className="mb-4"),
    dbc.Row([dbc.Col(dcc.Graph(figure=wallet_bar), width=12)], className="mb-4"),
    dbc.Row([
        dbc.Col(dcc.Graph(figure=wallet_pie), md=6),
        dbc.Col(dcc.Graph(figure=token_source_bar), md=6)
    ], className="mb-4"),
    dbc.Row([dbc.Col(dcc.Graph(figure=referral_bar), width=12)], className="mb-4"),
    dbc.Row([dbc.Col(dcc.Graph(figure=referral_line), width=12)], className="mb-4"),
    dbc.Row([dbc.Col(dcc.Graph(figure=fee_line), width=12)], className="mb-4"),
    dbc.Row([dbc.Col(dcc.Graph(figure=fig_pies), width=12)], className="mb-4"),
], fluid=False)

# --- Dash App ---
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}])
app.title = "Sharp Token Dashboard"

def timesheet_layout():
    unique_names = sorted(tasks_df["name"].dropna().unique().tolist())
    name_options = [{"label": n, "value": n} for n in unique_names]
    return dbc.Container([
        html.H4("Timesheet", className="my-3"),
        dbc.Row([
            dbc.Col([
                html.Label("Name"),
                dcc.Input(id="ts-name", type="text", className="form-control"),
            ], md=2),
            dbc.Col([
                html.Label("Date"),
                dcc.DatePickerSingle(id="ts-date", date=date.today()),
            ], md=2),
            dbc.Col([
                html.Label("Start Time"),
                dcc.Input(id="ts-start", type="time", className="form-control"),
            ], md=2),
            dbc.Col([
                html.Label("End Time"),
                dcc.Input(id="ts-end", type="time", className="form-control"),
            ], md=2),
            dbc.Col([
                html.Label("Duration (hh:mm)"),
                dcc.Input(id="ts-duration", type="text", placeholder="0:30", className="form-control"),
            ], md=2),
            dbc.Col([
                html.Label("Completed"),
                dbc.Checkbox(id="ts-completed", value=True),
            ], md=1),
            dbc.Col([
                html.Label("Description"),
                dcc.Textarea(id="ts-desc", className="form-control"),
            ], md=2),
            dbc.Col([
                html.Br(),
                dbc.Button("Add Task", id="add-task", color="primary", className="mt-1"),
            ], md=1),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([
                html.Label("Filter by Name"),
                dcc.Dropdown(options=name_options, id="filter-name", placeholder="All"),
            ], md=3),
            dbc.Col([
                html.Label("Filter by Day"),
                dcc.DatePickerSingle(id="filter-day"),
            ], md=3),
        ], className="mb-3"),
        dash_table.DataTable(
            id="tasks-table",
            columns=[
                {"name": "ID", "id": "id", "hideable": True},
                {"name": "Name", "id": "name"},
                {"name": "Date", "id": "date"},
                {"name": "Start", "id": "start"},
                {"name": "End", "id": "end"},
                {"name": "Duration", "id": "duration"},
                {"name": "Description", "id": "description"},
                {"name": "Completed", "id": "completed"},
            ],
            style_cell={"whiteSpace": "pre-line"},
            row_selectable="single",
            editable=True,
        ),
        dbc.Button("Save Changes", id="save-task", color="secondary", className="my-2"),
        html.Div(id="summary", className="mt-3"),
        dcc.Store(id="tasks-store", data=tasks_df.to_dict("records")),
    ], fluid=False)

app.layout = html.Div([
    dcc.Tabs([
        dcc.Tab(label="Dashboard", children=dashboard_layout),
        dcc.Tab(label="Timesheet", children=timesheet_layout()),
    ])
])

# --- Callbacks ---

@app.callback(Output("ts-end", "value"), Input("ts-start", "value"))
def update_end_time(start):
    if start:
        try:
            t = datetime.strptime(start, "%H:%M") + timedelta(minutes=15)
            return t.strftime("%H:%M")
        except Exception:
            pass
    return None


@app.callback(
    Output("tasks-store", "data"),
    Output("tasks-table", "data"),
    Input("add-task", "n_clicks"),
    State("ts-name", "value"),
    State("ts-date", "date"),
    State("ts-start", "value"),
    State("ts-end", "value"),
    State("ts-duration", "value"),
    State("ts-completed", "value"),
    State("ts-desc", "value"),
    State("tasks-store", "data"),
    prevent_initial_call=True,
)
def add_task(n, name, date_value, start, end, duration_inp, completed, desc, data):
    records = data or []
    if not (name and date_value):
        return records, records

    dur_td = None
    if start:
        if end:
            start_dt = datetime.strptime(f"{date_value} {start}", "%Y-%m-%d %H:%M")
            end_dt = datetime.strptime(f"{date_value} {end}", "%Y-%m-%d %H:%M")
            dur_td = end_dt - start_dt
        elif duration_inp:
            try:
                h, m = map(int, duration_inp.split(":"))
                dur_td = timedelta(hours=h, minutes=m)
                end_dt = datetime.strptime(start, "%H:%M") + dur_td
                end = end_dt.strftime("%H:%M")
            except Exception:
                return records, records
        else:
            return records, records
    elif duration_inp:
        try:
            h, m = map(int, duration_inp.split(":"))
            dur_td = timedelta(hours=h, minutes=m)
        except Exception:
            return records, records
    else:
        return records, records

    if dur_td is None:
        return records, records

    duration_str = f"{dur_td.seconds//3600}h {dur_td.seconds%3600//60}m"
    record = {
        "id": str(uuid.uuid4()),
        "name": name,
        "date": date_value,
        "start": start,
        "end": end,
        "duration": duration_str,
        "description": desc or "",
        "completed": bool(completed),
        "created_at": datetime.utcnow().isoformat(),
    }
    records.append(record)
    pd.DataFrame(records).to_csv(TASKS_FILE, index=False)
    return records, records


@app.callback(
    Output("tasks-table", "data"),
    Input("tasks-store", "data"),
    Input("filter-name", "value"),
    Input("filter-day", "date"),
)
def filter_tasks(data, name, day):
    df = pd.DataFrame(data)
    if name:
        df = df[df["name"] == name]
    if day:
        df = df[df["date"] == day]
    return df.to_dict("records")


@app.callback(Output("summary", "children"), Input("tasks-table", "data"))
def update_summary(data):
    if not data:
        return ""
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    df["duration_minutes"] = df["duration"].str.extract(r"(\d+)h (\d+)m").astype(int).mul([60, 1]).sum(axis=1)
    summary_lines = []
    for name, group in df.groupby("name"):
        daily = group.groupby(group["date"].dt.date)["duration_minutes"].sum()
        weekly_total = daily.sum()
        for d, mins in daily.items():
            status = "OK" if mins >= 480 else "<b>Less than 8h</b>"
            summary_lines.append(f"{name} {d}: {mins/60:.1f}h {status}")
        summary_lines.append(f"{name} weekly total: {weekly_total/60:.1f}h {'OK' if weekly_total >= 2400 else '<b>Less than 40h</b>'}")
    return html.Ul([html.Li(html.Span(d, style={"whiteSpace": "pre"})) for d in summary_lines])


@app.callback(
    Output("tasks-store", "data"),
    Output("tasks-table", "data"),
    Input("save-task", "n_clicks"),
    State("tasks-table", "data"),
    State("tasks-table", "selected_rows"),
    State("tasks-store", "data"),
    prevent_initial_call=True,
)
def save_edit(n, table_data, selected, store_data):
    if not selected:
        return store_data, table_data
    row = table_data[selected[0]]
    df = pd.DataFrame(store_data)
    idx = df.index[df["id"] == row["id"]]
    if idx.empty:
        return store_data, table_data
    created_at = pd.to_datetime(df.loc[idx[0], "created_at"])
    if datetime.utcnow() - created_at > timedelta(hours=24):
        return store_data, table_data
    df.loc[idx[0]] = row
    df.to_csv(TASKS_FILE, index=False)
    new_data = df.to_dict("records")
    return new_data, new_data

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 80))
    app.run(host='0.0.0.0')
