from typing import Literal
from dash import Dash, html, Input, Output, ALL, dcc, ctx, State, MATCH, callback
from dash.development.base_component import Component
import dash_bootstrap_components as dbc
from acledit.components.utils import declare_child
from dash.exceptions import PreventUpdate
from acledit.acl import AclSet, grant_user
from pathlib import Path
from getpass import getuser
import posix1e as acl 
import os
import pwd

class AclShareModal(html.Div):
    # Public
    current_file = declare_child("current_file")

    # Private
    _acl = declare_child("acl")
    _title = declare_child("title")
    _modal = declare_child("modal")
    _close = declare_child("close")
    _share = declare_child("share")
    _username = declare_child("username")
    _alerts = declare_child("alerts")
    # _default = declare_child("default")

    def __init__(self, id: str, **kwargs):
        super().__init__(
            [
                dbc.Modal(
                    [
                        dbc.ModalHeader(
                            dbc.ModalTitle([
                                "Share ",
                                html.Code(id=AclShareModal._title(id))
                            ])
                        ),
                        dbc.ModalBody(dbc.Container([
                            dbc.Row(dbc.Col(dbc.Form(
                                [
                                    dbc.InputGroup([
                                        dbc.InputGroupText("Username"),
                                        dbc.Input(id=AclShareModal._username(id))
                                    ]),
                                ]
                            )), class_name="gy-5"),
                            dbc.Row(dbc.Col(id=AclShareModal._alerts(id)), class_name="gy-5"),
                        ])),
                        dbc.ModalFooter([
                            dbc.Button(
                                "Share",
                                id=AclShareModal._share(id),
                            ),
                            dbc.Button(
                                "Close",
                                id=AclShareModal._close(id),
                                n_clicks=0,
                            )
                        ]),
                    ],
                    is_open=False,
                    id=AclShareModal._modal(id)
                ),
                dcc.Store(id=AclShareModal.current_file(id)),
                dcc.Store(id=AclShareModal._acl(id)),
            ]
        )

@callback(
    Output(AclShareModal._modal(MATCH), "is_open"),
    Output(AclShareModal._title(MATCH), "children"),
    Output(AclShareModal._alerts(MATCH), "children", allow_duplicate=True),
    Input(AclShareModal.current_file(MATCH), "data"),
    prevent_initial_call=True,
)
def open_modal(filename: str | None) -> tuple[Literal[True], str, list]:
    if filename is None:
        raise PreventUpdate()

    # Open the modal, set its title, and clear alerts
    return True, filename, []

@callback(
    Output(AclShareModal._modal(MATCH), "is_open", allow_duplicate=True),
    Input(AclShareModal._close(MATCH), "n_clicks"),
    prevent_initial_call=True
)
def close_modal(_n_clicks: int):
    return False

@callback(
    Output(AclShareModal._alerts(MATCH), "children", allow_duplicate=True),
    Input(AclShareModal._share(MATCH), "n_clicks"),
    State(AclShareModal.current_file(MATCH), "data"),
    State(AclShareModal._username(MATCH), "value"),
    prevent_initial_call=True
)
def execute_share(_n_clicks: int, current_file: str, share_user: str) -> list:
    try:
        current_path = Path(current_file)
        current_uid = os.getuid()

        try:
            pwd.getpwnam(share_user)
        except KeyError as e:
            return [dbc.Alert(
                f"Username {share_user} is not a valid Milton user!",
                dismissable=True,
                color="danger"
            )]

        if current_path.owner() != getuser():
            return [dbc.Alert(
                f"You do not own this file or directory. The current owner is {current_path.owner()}. Only the owner can share it.",
                dismissable=True,
                color="danger"
            )]

        acls = AclSet.from_file(current_file)
        for permission in acls.acls:
            if permission.tag_type == "user" and permission.qualifier == share_user:
                return [dbc.Alert(
                    f"There is already some access control configured for {share_user}. Consider opening the Editor.",
                    dismissable=True,
                    color="danger"
                )]

        # Grant X access to each parent so that the directory can be listed
        for parent in current_path.parents:
            if parent.owner() == share_user:
                grant_user(str(parent), current_uid, [acl.ACL_EXECUTE])

        grant_user(current_file, current_uid, [acl.ACL_EXECUTE, acl.ACL_READ])

        return [dbc.Alert(
            f"File successfully shared!",
            dismissable=True,
            color="success"
        )]
    except Exception as e:
        return [dbc.Alert(
            str(e),
            dismissable=True,
            color="danger"
        )]
