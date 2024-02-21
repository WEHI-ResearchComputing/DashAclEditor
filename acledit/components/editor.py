from typing import Literal
from dash import Dash, html, Input, Output, ALL, dcc, ctx, State, MATCH, callback
from dash.development.base_component import Component
import dash_bootstrap_components as dbc
from acledit.components.utils import declare_child
from dash.exceptions import PreventUpdate
from acledit.acl import AclSet


class AclEditorModal(html.Div):
    # Public
    current_file = declare_child("current_file")

    # Private
    _acl = declare_child("acl")
    _title = declare_child("title")
    _acls_body = declare_child("acls_body")
    _default_acls_body = declare_child("default_acls_body")
    _modal = declare_child("modal")

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
                                                    ]
                                                )
                                            ),
                                            html.Tbody(id=AclEditorModal._default_acls_body(id)),
                                        ]
                                    )
                                ]
                            )
                        ),
                        dbc.ModalFooter(
                            dbc.Button(
                                "Close",
                                className="ms-auto",
                                n_clicks=0,
                            )
                        ),
                    ],
                    is_open=False,
                    id=AclEditorModal._modal(id)
                ),
                dcc.Store(id=AclEditorModal.current_file(id)),
                dcc.Store(id=AclEditorModal._acl(id)),
            ]
        )

@callback(
    Output(AclEditorModal._modal(MATCH), "is_open"),
    Output(AclEditorModal._title(MATCH), "children"),
    Output(AclEditorModal._acls_body(MATCH), "children"),
    Output(AclEditorModal._default_acls_body(MATCH), "children"),
    Input(AclEditorModal.current_file(MATCH), "data"),
    prevent_initial_call=True,
)
def open_modal(filename: str | None) -> tuple[Literal[True], str, list[html.Tr], list[html.Tr]]:
    if filename is None:
        raise PreventUpdate()
    acls = AclSet.from_file(filename)
    return True, filename, [html.Tr([
        html.Td(entry.tag_type),
        html.Td(entry.qualifier),
        html.Td(dbc.Checkbox(value=entry.read)),
        html.Td(dbc.Checkbox(value=entry.write)),
        html.Td(dbc.Checkbox(value=entry.execute)),
    ]) for entry in acls.acls], [html.Tr([
        html.Td(entry.tag_type),
        html.Td(entry.qualifier),
        html.Td(dbc.Checkbox(value=entry.read)),
        html.Td(dbc.Checkbox(value=entry.write)),
        html.Td(dbc.Checkbox(value=entry.execute)),
    ]) for entry in acls.default_acls]
