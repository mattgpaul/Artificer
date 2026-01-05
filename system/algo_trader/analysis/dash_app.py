from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
import plotly.express as px
from dash import Dash, Input, Output, dcc, html

from infrastructure.postgres.postgres import BasePostgresClient
from system.algo_trader.adapters.timescale.store import AlgoTraderStore
from system.algo_trader.analysis.queries import AlgoTraderQueries


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def build_app() -> Dash:
    db = BasePostgresClient()
    store = AlgoTraderStore(db=db)
    store.migrate()
    q = AlgoTraderQueries(db=db)

    app = Dash(__name__)
    app.layout = html.Div(
        [
            html.H2("algo_trader analysis"),
            html.Div(
                [
                    html.Label("Symbol"),
                    dcc.Dropdown(
                        id="symbol",
                        options=[{"label": s, "value": s} for s in q.list_symbols()],
                        value=None,
                        clearable=True,
                    ),
                ],
                style={"maxWidth": "400px"},
            ),
            html.Div(
                [
                    html.Label("Lookback (days)"),
                    dcc.Slider(id="lookback_days", min=1, max=365, step=1, value=30),
                ],
                style={"maxWidth": "600px"},
            ),
            dcc.Graph(id="trade_price_chart"),
            html.H3("Trade executions"),
            html.Div(id="trade_table"),
        ],
        style={"fontFamily": "system-ui, sans-serif", "margin": "24px"},
    )

    @app.callback(
        Output("trade_price_chart", "figure"),
        Output("trade_table", "children"),
        Input("symbol", "value"),
        Input("lookback_days", "value"),
    )
    def _update(symbol: str | None, lookback_days: int):
        since = _utc_now() - timedelta(days=int(lookback_days))
        df = q.list_trade_executions(symbol=symbol, since=since, limit=5000)
        if df.empty:
            fig = px.scatter(title="No trade executions found (yet)")
            return fig, html.Div("No rows.")

        df["ts"] = pd.to_datetime(df["ts"])
        fig = px.scatter(
            df,
            x="ts",
            y="price",
            color="side",
            hover_data=["symbol", "qty", "run_id"],
            title="Trade executions (price over time)",
        )

        table = html.Table(
            [
                html.Thead(
                    html.Tr(
                        [html.Th(c) for c in ["ts", "symbol", "side", "qty", "price", "run_id"]]
                    )
                ),
                html.Tbody(
                    [
                        html.Tr(
                            [
                                html.Td(str(row.get("ts"))),
                                html.Td(row.get("symbol")),
                                html.Td(row.get("side")),
                                html.Td(str(row.get("qty"))),
                                html.Td(str(row.get("price"))),
                                html.Td(row.get("run_id") or ""),
                            ]
                        )
                        for row in df.tail(200).to_dict("records")
                    ]
                ),
            ],
            style={"borderCollapse": "collapse", "width": "100%"},
        )
        return fig, table

    return app


def main() -> None:
    app = build_app()
    app.run_server(debug=True, host="0.0.0.0", port=8050)


if __name__ == "__main__":
    main()
