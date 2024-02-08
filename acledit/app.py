from dash import Dash, html, Input, Output, ALL, dcc, ctx
from acledit.config import config
import dash_bootstrap_components as dbc
from pathlib import Path

app = Dash(
    __name__,
    requests_pathname_prefix= config.prefix,
    external_stylesheets=[dbc.themes.BOOTSTRAP]
)

app.layout = html.Div([
    html.H1(children='Access Control', style={'textAlign':'center'}),
    dbc.ListGroup([], id="file-list"),
    dcc.Store(id="current_dir")
])

@app.callback(
    Output("current_dir", "data"),
    Input({"type": "file", "filename": ALL}, "n_clicks"),
)
def browse_dir(_n_clicks: int) -> str:
    if ctx.triggered_id is None:
        # This happens when the app first initializes
        return str(Path.home())
    else:
        new_path: str = ctx.triggered_id["filename"]
        if Path(new_path).is_dir():
            return new_path
        else:
            raise Exception("Not a directory")

@app.callback(
    Output("current_dir", "data", allow_duplicate=True),
    Input({"type": "dir-up"}, "n_clicks"),
    Input("current_dir", "data"),
    prevent_initial_call=True
)
def up_dir(n_clicks: int | None, current_dir: str) -> str:
    if n_clicks is not None:
        return str(Path(current_dir).parent)
    else:
        return current_dir

@app.callback(
    Output("file-list", "children"),
    Input("current_dir", "data"),
)
def populate_filelist(dir: str | None) -> list[dbc.ListGroupItem]:
    new_children = [
        dbc.ListGroupItem(children="Back", id={"type": "dir-up"}, href="#")
    ]
    if dir is None:
        dir = str(Path.home())
    for file in sorted(Path(dir).iterdir(), key=lambda path: path.name):
        new_children.append(
            dbc.ListGroupItem(children=file.name, id={"filename": str(file), "type": "file"}, href="#")
        )
    return new_children
