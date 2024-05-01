from typing import Literal
from dash import Dash, html, Input, Output, ALL, dcc, ctx, State, MATCH, callback
from dash.development.base_component import Component
import dash_bootstrap_components as dbc
from acledit.components.utils import declare_child, real_event
from dash.exceptions import PreventUpdate
from acledit.acl import AclSet, grant_user, get_or_create_entry, can_read_recursive, execute_share
from acledit.config import config
from pathlib import Path
from getpass import getuser
import posix1e as acl
import os
import pwd

class AclShareModal(html.Div):
    """
    The high-level share and status modal, that pops up when you click "Share"
    """
    # Public
    current_file = declare_child("current_file")

    # Private
    _title = declare_child("title")
    _modal = declare_child("modal")
    _close = declare_child("close")
    _share = declare_child("share")
    _status = declare_child("status")
    _username = declare_child("username")
    _alerts = declare_child("alerts")
    _default = declare_child("default")
    _recursive = declare_child("recursive")
    _editable = declare_child("editable")
    _advanced = declare_child("advanced")

    def __init__(self, id: str, **kwargs):
        super().__init__(
            [
                dbc.Modal(
                    [
                        dbc.ModalHeader(
                            dbc.ModalTitle(
                                ["Share ", html.Code(id=AclShareModal._title(id))]
                            )
                        ),
                        dbc.ModalBody(
                            dbc.Stack(
                                gap=1,
                                children=[
                                    dbc.InputGroup(
                                        [
                                            dbc.InputGroupText("Username"),
                                            dbc.Input(id=AclShareModal._username(id)),
                                        ]
                                    ),
                                    dbc.Checkbox(
                                        id=self._editable(id),
                                        label=html.Div(
                                            [
                                                html.Strong("Grant Edit."),
                                                " Allow the user to edit this file or directory.",
                                                config.hints.edit,
                                            ]
                                        ),
                                        value=False,
                                    ),
                                    dbc.Accordion(
                                        id=self._advanced(id),
                                        flush=True,
                                        start_collapsed=True,
                                        children=dbc.AccordionItem(
                                            title="Show Advanced Settings",
                                            children=[
                                                dbc.Stack(
                                                    children=[
                                                        dbc.Checkbox(
                                                            id=self._recursive(id),
                                                            label=html.Div(
                                                                [
                                                                    html.Strong(
                                                                        "Recursive."
                                                                    ),
                                                                    " Also share all files and directories inside this directory.",
                                                                    config.hints.recursive,
                                                                ]
                                                            ),
                                                            value=False,
                                                        ),
                                                        dbc.Checkbox(
                                                            id=self._default(id),
                                                            label=html.Div(
                                                                [
                                                                    html.Strong(
                                                                        "Inherit."
                                                                    ),
                                                                    " Future files in this directory will inherit these sharing settings.",
                                                                    config.hints.default,
                                                                ]
                                                            ),
                                                            value=False,
                                                        ),
                                                    ],
                                                )
                                            ],
                                        ),
                                    ),
                                    dbc.Alert(
                                        "Disclaimer: even if you share a specific file with another user, they may be able to access all files within the VAST area if they know their exact filenames. The user will not be able to list files in VAST spaces they have not been explicitly given access to, however.",
                                        color="warning",
                                    ),
                                    html.Div(id=AclShareModal._alerts(id)),
                                ],
                            )
                        ),
                        dbc.ModalFooter(
                            [
                                dbc.Button(
                                    "Status",
                                    id=AclShareModal._status(id),
                                ),
                                dbc.Button(
                                    "Share",
                                    id=AclShareModal._share(id),
                                ),
                                dbc.Button(
                                    "Close",
                                    id=AclShareModal._close(id),
                                    n_clicks=0,
                                ),
                            ]
                        ),
                    ],
                    is_open=False,
                    id=AclShareModal._modal(id),
                ),
                dcc.Store(id=AclShareModal.current_file(id)),
            ]
        )


@callback(
    Output(AclShareModal._modal(MATCH), "is_open"),
    Output(AclShareModal._title(MATCH), "children"),
    Output(AclShareModal._alerts(MATCH), "children", allow_duplicate=True),
    Output(AclShareModal._editable(MATCH), "label", allow_duplicate=True),
    Output(AclShareModal._advanced(MATCH), "style", allow_duplicate=True),
    Input(AclShareModal.current_file(MATCH), "data"),
    prevent_initial_call=True,
)
def open_modal(filename: str | None) -> tuple[Literal[True], str, list, list, dict]:
    """
    Open the modal, set its title, and clear alerts
    At this point we modify parts of the modal depending on if we're sharing a file or directory
    """
    if filename is None:
        raise PreventUpdate()

    modal_open = True
    title = Path(filename).name
    alerts = []
    
    if Path(filename).is_dir():
        style = {"visible": True}
        editable_description = [
            html.Strong("Grant Edit."),
            " Allow the user to create and delete files in this directory"
        ]
    else:
        style = {"display": "none"}
        editable_description = [
            html.Strong("Grant Edit."),
            " Allow the user to edit or delete this file"
        ]

    return modal_open, title, alerts, editable_description, style


@callback(
    Output(AclShareModal._modal(MATCH), "is_open", allow_duplicate=True),
    Input(AclShareModal._close(MATCH), "n_clicks"),
    prevent_initial_call=True,
)
def close_modal(_n_clicks: int) -> bool:
    return False

@callback(
    Output(AclShareModal._alerts(MATCH), "children", allow_duplicate=True),
    Input(AclShareModal._share(MATCH), "n_clicks"),
    State(AclShareModal.current_file(MATCH), "data"),
    State(AclShareModal._username(MATCH), "value"),
    State(AclShareModal._editable(MATCH), "value"),
    State(AclShareModal._recursive(MATCH), "value"),
    State(AclShareModal._default(MATCH), "value"),
    prevent_initial_call=True,
)
def on_share(
    _n_clicks: int,
    current_file: str,
    share_user: str,
    editable: bool,
    recursive: bool,
    default: bool,
) -> list:
    """
    Perform the share, and generate any status alerts
    """
    try:
        execute_share(current_file, share_user, editable, recursive, default)
    except Exception as e:
        return [
            dbc.Alert(
                str(e),
                dismissable=True,
                color="danger",
            )
        ]

    return [
        dbc.Alert(f"File successfully shared!", dismissable=True, color="success")
    ]

@callback(
    Output(AclShareModal._alerts(MATCH), "children"),
    Input(AclShareModal._status(MATCH), "n_clicks"),
    State(AclShareModal._username(MATCH), "value"),
    State(AclShareModal.current_file(MATCH), "data"),
)
def on_calculate(_n_clicks: int, user: str, path: str) -> list[dbc.Alert]:
    """
    Triggers when the user clicks "status".
    Generates various status alerts relating to the validity of the user,
    the path, and the user's access to the path
    """
    if not real_event():
        raise PreventUpdate()
    if not Path(path).exists():
        return [
            dbc.Alert(
                f'The path "{path}" does not exist!',
                dismissable=False,
                color="danger",
            )
        ]
    try:
        pwd.getpwnam(user)
    except KeyError:
        return [
            dbc.Alert(
                f'The user "{user}" does not exist!',
                dismissable=False,
                color="danger",
            )
        ]

    if can_read_recursive(user, Path(path)):
        return [
            dbc.Alert(
                f"{user} CAN access {path}",
                dismissable=False,
                color="success",
            )
        ]

    return [
        dbc.Alert(
            f"{user} CANNOT access {path}",
            dismissable=False,
            color="danger",
        )
    ]
