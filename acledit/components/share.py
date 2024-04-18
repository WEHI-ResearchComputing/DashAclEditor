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
    _default = declare_child("default")
    _recursive = declare_child("recursive")
    _editable = declare_child("editable")

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
                            dbc.Row(
                                dbc.Col(
                                    dbc.Checkbox(
                                        id=self._editable(id),
                                        label=html.Div([
                                            html.Strong("Grant Edit."),
                                            " Allow the user to edit this file or directory.",
                                            config.hints.edit
                                        ]),
                                        value=False,
                                    ),
                                    md="12"
                                ),
                            ),
                            dbc.Row(
                                dbc.Col(
                                    dbc.Checkbox(
                                        id=self._recursive(id),
                                        label=html.Div([
                                            html.Strong("Recursive."),
                                            " Also share all subdirectories.",
                                            config.hints.recursive
                                        ]),
                                        value=False,
                                    ),
                                ),
                            ),
                            dbc.Row(
                                dbc.Col(
                                    dbc.Checkbox(
                                        id=self._default(id),
                                        label=html.Div([
                                            html.Strong("Inherit."),
                                            " Future files will inherit these sharing settings.",
                                            config.hints.default
                                        ]),
                                        value=False,
                                    ),
                                    md="12"
                                ),
                            ),
                            dbc.Row(dbc.Col(id=AclShareModal._alerts(id)), class_name="gy-5"),
                        ], class_name="gy-5"),
                        ),
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
    State(AclShareModal._editable(MATCH), "value"),
    State(AclShareModal._recursive(MATCH), "value"),
    State(AclShareModal._default(MATCH), "value"),
    prevent_initial_call=True
)
def execute_share(_n_clicks: int, current_file: str, share_user: str, editable: bool, recursive: bool, default: bool) -> list:
    try:
        current_path = Path(current_file)
        current_user = getuser()
        current_uid = os.getuid()

        try:
            recipient_id = pwd.getpwnam(share_user).pw_uid
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
        # We iterate in reverse so that we can fail early
        for parent in reversed(current_path.parents):
            if parent.owner() == current_user:
                entry = get_or_create_entry(facl=acl.ACL(file=str(parent)), tag_type=acl.ACL_USER, qualifier=recipient_id)
                entry.permset.execute = True
            else:
                parent_acl = AclSet.from_file(str(parent))
                if not parent_acl.can_access(share_user):
                    return [dbc.Alert(
                    f"Share failed because the parent directory {parent} is not owned by you, and cannot be accessed by {share_user}. Please contact {parent.owner()} and request that they share this directory with {share_user}.",
                    dismissable=True,
                    color="danger"
                )]

        perms = [acl.ACL_EXECUTE, acl.ACL_READ]
        if editable:
            perms.append(acl.ACL_WRITE)
        grant_user(current_file, recipient_id, permissions=perms, default=default, recursive=recursive)

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
