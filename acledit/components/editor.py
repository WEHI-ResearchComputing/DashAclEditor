from typing import Any, Literal
from dash import Dash, html, Input, Output, ALL, dcc, ctx, State, MATCH, callback
from dash.development.base_component import Component
import dash_bootstrap_components as dbc
from acledit.components.utils import declare_child, real_event
from dash.exceptions import PreventUpdate
from acledit.acl import AclSet
from acledit.components.icon import FontAwesomeIcon


class AclEditorModal(html.Div):
    # Public
    current_file = declare_child("current_file")

    # Private
    _acl = declare_child("acl")
    _title = declare_child("title")
    _acls_body = declare_child("acls_body")
    _default_acls_body = declare_child("default_acls_body")
    _modal = declare_child("modal")
    _save = declare_child("save")
    _delete_entry = declare_child("save")
    _add_entry = declare_child("save")

    def __init__(self, id: str, **kwargs):
        super().__init__(
            [
                dbc.Modal(
                    [
                        dbc.ModalHeader(
                            dbc.ModalTitle("Header", id=AclEditorModal._title(id))
                        ),
                        dbc.ModalBody(
                            dbc.Form(
                                [
                                    html.H3("Access Control"),
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
                                            html.Tbody(id=AclEditorModal._acls_body(id)),
                                        ]
                                    ),
                                    # dbc.Button("New ACL", class_name="btn-block", id=AclEditorModal._add_entry(id, default = False)),
                                    html.H3("Default Access Control"),
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
                                                        html.Th("Delete"),
                                                    ]
                                                )
                                            ),
                                            html.Tbody(id=AclEditorModal._default_acls_body(id)),
                                        ]
                                    ),
                                    # dbc.Button("New ACL", class_name="btn-block", id=AclEditorModal._add_entry(id, default=True)),
                                ]
                            )
                        ),
                        dbc.ModalFooter([
                            dbc.Button(
                                "Save",
                                n_clicks=0,
                                id=AclEditorModal._save(id)
                            ),
                            dbc.Button(
                                "Close",
                                color="secondary",
                                n_clicks=0,
                            )
                        ]),
                    ],
                    is_open=False,
                    id=AclEditorModal._modal(id)
                ),
                dcc.Store(id=AclEditorModal.current_file(id)),
                dcc.Store(id=AclEditorModal._acl(id)),
            ]
        )


@callback(
    Output(AclEditorModal._acl(MATCH), "data"),
    Input(AclEditorModal.current_file(MATCH), "data"),
    prevent_initial_call=True,
)
def update_acl_from_path(path: str | None):
    if path is None:
        raise PreventUpdate()
    return AclSet.from_file(path).model_dump()

@callback(
    Output(AclEditorModal._modal(MATCH), "is_open"),
    Output(AclEditorModal._title(MATCH), "children"),
    Output(AclEditorModal._acls_body(MATCH), "children"),
    Output(AclEditorModal._default_acls_body(MATCH), "children"),
    Input(AclEditorModal._acl(MATCH), "data"),
    prevent_initial_call=True,
)
def open_modal(acl_data: dict) -> tuple[Literal[True], str, list[html.Tr], list[html.Tr]]:
    id = ctx.triggered_id["aio_id"]
    acls = AclSet.model_validate(acl_data)

    return True, acls.file_path, [html.Tr([
        html.Td(entry.tag_type),
        html.Td(entry.qualifier),
        html.Td(dbc.Checkbox(value=entry.read, disabled=True)),
        html.Td(dbc.Checkbox(value=entry.write, disabled=True)),
        html.Td(dbc.Checkbox(value=entry.execute, disabled=True)),
        html.Td(dbc.Button(FontAwesomeIcon("trash"), color="danger", id=AclEditorModal._delete_entry(id, index=i, default=False))),
    ]) for i, entry in enumerate(acls.acls)], [html.Tr([
        html.Td(entry.tag_type),
        html.Td(entry.qualifier),
        html.Td(dbc.Checkbox(value=entry.read, disabled=True)),
        html.Td(dbc.Checkbox(value=entry.write, disabled=True)),
        html.Td(dbc.Checkbox(value=entry.execute, disabled=True)),
        html.Td(dbc.Button(FontAwesomeIcon("trash"), color="danger", id=AclEditorModal._delete_entry(id, index=i, default=True))),
    ]) for i, entry in enumerate(acls.default_acls)]


@callback(
    Output(AclEditorModal._acl(MATCH), "data", allow_duplicate=True),
    Input(AclEditorModal._delete_entry(MATCH, index=ALL, default=ALL), "n_clicks"),
    State(AclEditorModal._acl(MATCH), "data"),
    prevent_initial_call=True
)
def delete_entry(_n_clicks: int, acl_data: dict):
    if not real_event(0):
        raise PreventUpdate()
    index: int = ctx.triggered_id["index"]
    default: bool = ctx.triggered_id["default"]
    acls = AclSet.model_validate(acl_data)
    if default:
        del acls.default_acls[index]
    else:
        del acls.acls[index]
    return acls.model_dump()

@callback(
    Output(AclEditorModal._modal(MATCH), "is_open", allow_duplicate=True),
    Input(AclEditorModal._save(MATCH), "n_clicks"),
    State(AclEditorModal._acl(MATCH), "data"),
    prevent_initial_call=True
)
def save_acl(_n_clicks: int, acl_data: dict):
    AclSet.model_validate(acl_data).apply()
    return False
