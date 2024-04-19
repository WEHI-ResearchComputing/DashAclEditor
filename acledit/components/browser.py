from dash import (
    Input,
    Output,
    dcc,
    callback,
    callback_context as ctx,
    ALL,
    MATCH,
    State,
    html,
)
import dash_bootstrap_components as dbc
from acledit.components.icon import FontAwesomeIcon
from acledit.components.utils import declare_child, real_event
from acledit.config import config
from pathlib import Path
from getpass import getuser
import os
from dash.exceptions import PreventUpdate
import pwd

class FileBrowserFile(dbc.ListGroupItem):
    share = declare_child("share", filename=ALL)
    edit = declare_child("edit", filename=ALL)
    status = declare_child("status", filename=ALL)

    def __init__(self, parent_id: str, file: Path, name: str | None = None, **kwargs):
        """
        Params:
            name: Optional name for the path, otherwise the filename is used
            kwargs: Other distinguishing arguments
        """
        # We specifically don't care about the target of the symlink in this case
        stat = file.stat(follow_symlinks=False)
        not_owned = pwd.getpwuid(stat.st_uid).pw_name != getuser()
        acl_mount = config.has_acls(file)
        disabled = not_owned or not acl_mount

        error_message: str | None = None
        if not_owned:
            error_message = "You can only share files that you own"
        elif not acl_mount:
            error_message = "This file is not part of a filesystem that supports ACLs"

        if name is None:
            name = file.name
        super().__init__(
            dbc.Row(
                [
                    dbc.Col(
                        html.A(
                            [
                                (
                                    FontAwesomeIcon("folder")
                                    if file.is_dir()
                                    else FontAwesomeIcon("file")
                                ),
                                name,
                            ],
                            href="#",
                            id=FileBrowser._dir_browse(
                                aio_id=parent_id, filename=str(file), **kwargs
                            ),
                        )
                    ),
                    dbc.Col(
                        dbc.ButtonGroup(
                            [
                                dbc.Button(
                                    [FontAwesomeIcon("share"), "Share"],
                                    id=FileBrowserFile.share(
                                        aio_id=parent_id, filename=str(file), **kwargs
                                    ),
                                    title=error_message,
                                    disabled=disabled,
                                ),
                                dbc.Button(
                                    [FontAwesomeIcon("pen-to-square"), "Edit"],
                                    id=FileBrowserFile.edit(
                                        aio_id=parent_id, filename=str(file), **kwargs 
                                    ),
                                    title=error_message,
                                    disabled=disabled,
                                )
                            ]
                        ),
                        className="justify-content-end d-flex",
                        md=6,
                    ),
                ],
                className="justify-content-center",
            )
        )


class FileBrowser(dbc.Row):
    # Public
    current_path = declare_child("current_path")

    # Private
    _file_list = declare_child("file_list")
    _dir_up = declare_child("dir_up")
    _dir_browse = declare_child("dir_browse", filename=ALL)
    _main_panel_title = declare_child("main_panel_title")
    _dir_go_input = declare_child("dir_go_input")
    _dir_go_button = declare_child("dir_go_button")

    def __init__(self, id: str):
        self._id = id
        super().__init__(
            [
                dcc.Store(id=self.current_path(id), data=str(config.start_dir)),
                dbc.Col(
                    [
                        html.H3("Shortcuts"),
                        dbc.ListGroup(
                            [
                                # We need shortcut to ensure this doesn't have a duplicate ID with 
                                # a file in the right panel
                                FileBrowserFile(id, Path(path), name=name, shortcut=True)
                                for name, path in config.shortcuts.items()
                            ]
                        ),
                    ],
                    md=4,
                ),
                dbc.Col(
                    [
                        html.H3(id=FileBrowser._main_panel_title(id), children="Files"),
                        dbc.InputGroup(
                            [
                                dbc.InputGroupText(FontAwesomeIcon("pen")),
                                dbc.Input(id=self._dir_go_input(id)),
                                dbc.InputGroupText(
                                    dbc.Button("Go", id=self._dir_go_button(id))
                                ),
                            ]
                        ),
                        dbc.ListGroup(id=self._file_list(id)),
                    ],
                    md=8,
                ),
            ]
        )


@callback(
    Output(FileBrowser._file_list(MATCH), "children"),
    Input(FileBrowser.current_path(MATCH), "data"),
)
def populate_filelist(dir: str | None) -> list[dbc.ListGroupItem]:
    if not real_event():
        return []
    parent_id = ctx.triggered_id["aio_id"]
    new_children = [
        dbc.ListGroupItem(
            children=[FontAwesomeIcon("arrow-left-long"), "Back"],
            id=FileBrowser._dir_up(parent_id),
            href="#",
        )
    ]
    if dir is None:
        dir = str(Path.home())
    for file in sorted(Path(dir).iterdir(), key=lambda path: path.name):
        new_children.append(FileBrowserFile(parent_id, file=file))
    return new_children


@callback(
    Output(FileBrowser.current_path(MATCH), "data"),
    Input(FileBrowser._dir_browse(MATCH, filename=ALL), "n_clicks"),
    State(FileBrowser.current_path(MATCH), "data"),
)
def browse_dir(_n_clicks: int, current_path: str) -> str:
    if real_event(0):
        new_path: str = ctx.triggered_id["filename"]
        if not Path(new_path).is_dir():
            raise Exception("Not a directory")
        elif not os.access(new_path, os.R_OK | os.X_OK):
            raise Exception("Don't have permission to browse here.")
        else:
            return new_path
    else:
        # If a button wasn't really pressed, don't do anything
        return current_path


@callback(
    Output(FileBrowser.current_path(MATCH), "data", allow_duplicate=True),
    Input(FileBrowser._dir_go_button(MATCH), "n_clicks"),
    State(FileBrowser._dir_go_input(MATCH), "value"),
    prevent_initial_call=True,
)
def dir_go(_n_clicks: int, path: str) -> str:
    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise PreventUpdate()
    else:
        return str(p)

@callback(
    Output(FileBrowser.current_path(MATCH), "data", allow_duplicate=True),
    Input(FileBrowser._dir_up(MATCH), "n_clicks"),
    State(FileBrowser.current_path(MATCH), "data"),
    prevent_initial_call=True,
)
def up_dir(n_clicks: int | None, current_dir: str) -> str:
    if n_clicks is not None and real_event():
        return str(Path(current_dir).parent)
    else:
        return current_dir


@callback(
    Output(FileBrowser._main_panel_title(MATCH), "children"),
    Output(FileBrowser._dir_go_input(MATCH), "value"),
    Input(FileBrowser.current_path(MATCH), "data"),
    prevent_initial_call=True,
)
def update_title(current_dir: str) -> tuple[str, str]:
    return current_dir, current_dir
