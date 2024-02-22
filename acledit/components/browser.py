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
    clientside_callback,
)
import dash_bootstrap_components as dbc
from acledit.components.icon import FontAwesomeIcon
from acledit.components.utils import declare_child
from acledit.config import config
from pathlib import Path
from getpass import getuser


class FileBrowserFile(dbc.ListGroupItem):
    def __init__(self, parent_id: str, file: Path, name: str | None = None):
        """
        Params:
            name: Optional name for the path, otherwise the filename is used
        """
        not_dir = not file.is_dir()
        not_owned = file.owner() != getuser()
        if name is None:
            name = file.name
        super().__init__(
            dbc.Row(
                [
                    dbc.Col(
                        [
                            (
                                FontAwesomeIcon("folder")
                                if file.is_dir()
                                else FontAwesomeIcon("file")
                            ),
                            name,
                        ],
                        md=6,
                    ),
                    dbc.Col(
                        dbc.ButtonGroup(
                            [
                                dbc.Button(
                                    [FontAwesomeIcon("folder-open"), "Browse"],
                                    id=FileBrowser._dir_browse(
                                        aio_id=parent_id, filename=str(file)
                                    ),
                                    disabled=not_dir,
                                    title=(
                                        "You can only browse into directories"
                                        if not_dir
                                        else None
                                    ),
                                    className="btn btn-primary",
                                ),
                                dbc.Button(
                                    [FontAwesomeIcon("share"), "Share"],
                                    id=FileBrowser.share(
                                        aio_id=parent_id, filename=str(file)
                                    ),
                                    title=(
                                        "You can only share files that you own"
                                        if not_owned
                                        else None
                                    ),
                                    disabled=not_owned,
                                ),
                                dbc.Button(
                                    [FontAwesomeIcon("pen-to-square"), "Edit"],
                                    id=FileBrowser.edit(
                                        aio_id=parent_id, filename=str(file)
                                    ),
                                    title=(
                                        "You can only share files that you own"
                                        if not_owned
                                        else None
                                    ),
                                    disabled=not_owned,
                                ),
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
    share = declare_child("share", filename=ALL)
    edit = declare_child("edit", filename=ALL)

    # Private
    _file_list = declare_child("file_list")
    _dir_up = declare_child("dir_up")
    _dir_browse = declare_child("dir_browse", filename=ALL)
    _main_panel_title = declare_child("main_panel_title")
    # _shortcut = declare_child("my_scratch")

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
                                FileBrowserFile(id, Path(path), name=name)
                                for name, path in config.shortcuts.items()
                            ]
                        ),
                    ],
                    md=4,
                ),
                dbc.Col(
                    [
                        html.H3(id=FileBrowser._main_panel_title(id), children="Files"),
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
    parent_id = ctx.triggered_id["aio_id"]
    new_children = [
        dbc.ListGroupItem(
            children=[FontAwesomeIcon("arrow-left-long"), "Back"],
            id=FileBrowser._dir_up(aio_id=parent_id),
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


@callback(
    Output(FileBrowser.current_path(MATCH), "data", allow_duplicate=True),
    Input(FileBrowser._dir_up(MATCH), "n_clicks"),
    State(FileBrowser.current_path(MATCH), "data"),
    prevent_initial_call=True,
)
def up_dir(n_clicks: int | None, current_dir: str) -> str:
    if n_clicks is not None:
        return str(Path(current_dir).parent)
    else:
        return current_dir

@callback(
    Output(FileBrowser._main_panel_title(MATCH), "children"),
    Input(FileBrowser.current_path(MATCH), "data"),
    prevent_initial_call=True,
)
def update_title(current_dir: str) -> str:
    return current_dir
