from dash import Dash, html, Input, Output, ALL, dcc, ctx
from acledit.config import config
import dash_bootstrap_components as dbc
from acledit.components.browser import FileBrowser
from acledit.components.editor import AclEditorModal
from acledit.components.share import AclShareModal

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
                    sm=8,
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
        # The path of the file we're currently editing ACLs for
        dcc.Store(id="edit_file", data=None),
        dcc.Store(id="current_acl", data=None),
        AclEditorModal(id="acl_editor"),
        AclShareModal(id="acl_share"),
    ],
    className="justify-content-center",
)


# The edit button should trigger the ACL editor modal
@app.callback(
    Output(AclEditorModal.current_file("acl_editor"), "data"),
    Input(FileBrowser.edit(aio_id="file-browser", filename = ALL), "n_clicks"),
    prevent_initial_call=True
)
def edit_file(n_clicks: list[int]):
    if ctx.triggered_id is None or not any(n_clicks):
        return None

    return ctx.triggered_id["filename"]

# The share button should trigger the ACL share modal
@app.callback(
    Output(AclShareModal.current_file("acl_share"), "data"),
    Input(FileBrowser.share(aio_id="file-browser", filename = ALL), "n_clicks"),
    prevent_initial_call=True
)
def share_file(n_clicks: list[int]):
    if ctx.triggered_id is None or not any(n_clicks):
        return None

    return ctx.triggered_id["filename"]
