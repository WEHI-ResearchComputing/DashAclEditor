from typing import Literal
from dash import Dash, html, Input, Output, ALL, dcc, ctx, State, MATCH, callback
from dash.development.base_component import Component
import dash_bootstrap_components as dbc
from acledit.components.utils import declare_child
from dash.exceptions import PreventUpdate
from acledit.acl import AclSet, grant_user, get_or_create_entry
from acledit.config import config
from pathlib import Path
from getpass import getuser
import posix1e as acl
import os
import pwd


class AclStatusModal(html.Div):
    """
    Provides a high level report on who can access a file or directory
    """

    # Public
    current_file = declare_child("current_file")

    # Private
    _title = declare_child("title")
    _modal = declare_child("modal")
    _close = declare_child("close")
    _username = declare_child("username")
    _alerts = declare_child("alerts")
    _calculate_button = declare_child("calculate_button")

    def __init__(self, id: str, **kwargs):
        super().__init__(
            [
                dbc.Modal(
                    [
                        dbc.ModalHeader(
                            dbc.ModalTitle(
                                ["Status of ", html.Code(id=AclStatusModal._title(id))]
                            )
                        ),
                        dbc.ModalBody(
                            dbc.Container([
                                dbc.Row("Input a username. The application will calculate whether the user can access the chosen directory."),
                                dbc.Row(
                                    dbc.InputGroup([
                                        dbc.InputGroupText("Username"),
                                        dbc.Input(id=AclStatusModal._username(id))
                                    ]),
                                ),
                                dbc.Row(id=AclStatusModal._alerts(id))
                            ])
                        ),
                        dbc.ModalFooter(
                            [
                                dbc.Button(
                                    "Calculate",
                                    id=AclStatusModal._calculate_button(id),
                                    n_clicks=0,
                                ),
                                dbc.Button(
                                    "Close",
                                    id=AclStatusModal._close(id),
                                    n_clicks=0,
                                )
                            ]
                        ),
                    ],
                    is_open=False,
                    id=AclStatusModal._modal(id),
                ),
                dcc.Store(id=AclStatusModal.current_file(id)),
            ]
        )

@callback(
    Output(AclStatusModal._alerts(MATCH), "children"),
    Input(AclStatusModal._calculate_button(MATCH), "n_clicks"),
    State(AclStatusModal._username(MATCH), "value"),
    State(AclStatusModal.current_file(MATCH), "data")
)
def on_calculate(_n_clicks:int, user: str, path: str) -> list[dbc.Alert]:
    if not Path(path).exists():
        return [dbc.Alert(
            f'The path "{path}" does not exist!',
            dismissable=False,
            color="danger",
        )]
    try:
        pwd.getpwnam(user)
    except KeyError:
        return [dbc.Alert(
            f'The user "{user}" does not exist!',
            dismissable=False,
            color="danger",
        )]
    if AclSet.from_file(path).can_access(user):
        return [dbc.Alert(
            f"{user} CAN access {path}",
            dismissable=False,
            color="success",
        )
    ]

    return [dbc.Alert(
        f"{user} CANNOT access {path}",
        dismissable=False,
        color="danger",
    )]

@callback(
    Output(AclStatusModal._modal(MATCH), "is_open"),
    Output(AclStatusModal._title(MATCH), "children"),
    Output(AclStatusModal._alerts(MATCH), "children", allow_duplicate=True),
    Input(AclStatusModal.current_file(MATCH), "data"),
    prevent_initial_call=True,
)
def open_modal(filename: str | None) -> tuple[Literal[True], str, list]:
    if filename is None:
        raise PreventUpdate()

    # Open the modal, set its title, and clear alerts
    return True, filename, []

@callback(
    Output(AclStatusModal._modal(MATCH), "is_open", allow_duplicate=True),
    Input(AclStatusModal._close(MATCH), "n_clicks"),
    prevent_initial_call=True
)
def close_modal(_n_clicks: int):
    return False
