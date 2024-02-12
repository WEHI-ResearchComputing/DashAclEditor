from dash import Dash, html, Input, Output, ALL, dcc, ctx, State
from acledit.config import config
import dash_bootstrap_components as dbc
from pathlib import Path
from acledit.acl import AclSet
from dash.exceptions import PreventUpdate
from acledit.components.icon import FontAwesomeIcon
from acledit.components.browser import FileBrowser

app = Dash(
    __name__,
    requests_pathname_prefix=config.prefix,
    external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME],
)

app.layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(
                    sm=6,
                    children=[
                        html.H1(
                            children="Access Control", style={"textAlign": "center"}
                        ),
                        FileBrowser(id="file-browser")
                    ],
                )
            ],
            className="justify-content-center",
        ),
        # The path we're at in the file browser
        dcc.Store(id="current_dir", data=str(config.start_dir)),
        # The path of the file we're currently editing ACLs for
        dcc.Store(id="edit_file", data=None),
        dcc.Store(id="current_acl", data=None),
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle("Header", id="editor_modal_title")),
                dbc.ModalBody(
                    dbc.Form(
                        [
                            dbc.Table(
                                [
                                    html.Thead(
                                        html.Tr(
                                            [
                                                html.Th("Type"),
                                                html.Th("Qualifier"),
                                                html.Th("Read"),
                                                html.Th("Write"),
                                                html.Th("Execute"),
                                            ]
                                        )
                                    ),
                                    html.Tbody(id="editor_tbody"),
                                ]
                            )
                        ]
                    )
                ),
                dbc.ModalFooter(
                    dbc.Button("Close", id="close", className="ms-auto", n_clicks=0)
                ),
            ],
            id="acl_editor_modal",
            is_open=False,
        ),
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle("Header", id="share_modal_title")),
                dbc.ModalBody(
                    dbc.Form(
                        [
                            html.Div(
                                [
                                    dbc.Label("Email", html_for="example-email"),
                                    dbc.Input(
                                        type="email",
                                        id="example-email",
                                        placeholder="Enter email",
                                    ),
                                    dbc.FormText(
                                        "Are you on email? You simply have to be these days",
                                        color="secondary",
                                    ),
                                ],
                                className="mb-3",
                            )
                        ]
                    )
                ),
                dbc.ModalFooter(
                    dbc.Button("Close", id="close", className="ms-auto", n_clicks=0)
                ),
            ],
            id="acl_editor_modal",
            is_open=False,
        ),
    ],
    className="justify-content-center",
)


@app.callback(
    Output("current_dir", "data"),
    Input({"type": "dir-browse", "filename": ALL}, "n_clicks"),
)
def browse_dir(_n_clicks: int) -> str:
    if ctx.triggered_id is None:
        # This happens when the app first initializes
        return str(config.start_dir)
    else:
        new_path: str = ctx.triggered_id["filename"]
        if Path(new_path).is_dir():
            return new_path
        else:
            raise Exception("Not a directory")


@app.callback(
    Output({
        "id": "file-edit",
        "child": ""
    }, "data", allow_duplicate=True),
    Input({"type": "dir-up"}, "n_clicks"),
    Input("current_dir", "data"),
    prevent_initial_call=True,
)
def up_dir(n_clicks: int | None, current_dir: str) -> str:
    if n_clicks is not None:
        return str(Path(current_dir).parent)
    else:
        return current_dir

@app.callback(
    Output("edit_file", "data"),
    Input({"type": "share-button", "filename": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def edit_file(n_clicks: list[int]):
    if ctx.triggered_id is None or not any(n_clicks):
        return None

    return ctx.triggered_id["filename"]


@app.callback(
    Output("modal", "is_open"),
    Output("modal_title", "children"),
    Input("edit_file", "data"),
    prevent_initial_call=True,
)
def open_modal(filename: str | None):
    if filename is None:
        raise PreventUpdate()
    return True, filename


@app.callback(
    Output("acl_tbody", "children"),
    Input("current_acl", "data"),
    prevent_initial_call=True,
)
def update_acl_editor(current_acl: AclSet) -> list[html.Tr]:
    ret = []
    # for acl in current_acl
    return ret


@app.callback(
    Output("current_acl", "data"),
    Input("edit_file", "data"),
    State("current_dir", "data"),
    prevent_initial_call=True,
)
def get_acl(filename: str | None, current_dir: str) -> list[dict] | None:
    if filename is None:
        return None
    full_path = Path(current_dir) / filename
    acls = AclSet.from_file(str(full_path))
    return acls.model_dump()
