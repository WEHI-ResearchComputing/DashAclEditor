from dash import Input, Output, dcc, callback
import dash_bootstrap_components as dbc
from acledit.components.icon import FontAwesomeIcon
from acledit.components.utils import make_id, use_id
from pathlib import Path

class FileBrowser(dbc.ListGroup):
    # Public
    CURRENT_PATH = "current_path"

    # Private
    _FILE_LIST = "file_list"

    def __init__(self, id: str | None = None):
        with use_id(id) as make_id:
            super().__init__([
                dbc.ListGroup(id=make_id(self._FILE_LIST)),
                dcc.Store(id=make_id(child=self.CURRENT_PATH))
            ])

    @callback(
        Output(make_id(_FILE_LIST), "children"),
        Input(make_id(CURRENT_PATH), "data"),
    )
    def populate_filelist(dir: str | None) -> list[dbc.ListGroupItem]:
        new_children = [
            dbc.ListGroupItem(
                children=[FontAwesomeIcon("arrow-left-long"), "Back"],
                id={"type": "dir-up"},
                href="#",
            )
        ]
        if dir is None:
            dir = str(Path.home())
        for file in sorted(Path(dir).iterdir(), key=lambda path: path.name):
            if file.is_dir():
                icon = FontAwesomeIcon("folder")
                browse = dbc.Button(
                    [FontAwesomeIcon("folder-open"), "Browse"],
                    id={"filename": str(file), "type": "dir-browse"},
                )

            else:
                icon = FontAwesomeIcon("file")
                browse = ""

            new_children.append(
                dbc.ListGroupItem(
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    icon,
                                    file.name,
                                ]
                            ),
                            dbc.Col(browse),
                            dbc.Col(
                                dbc.Button(
                                    [FontAwesomeIcon("share"), "Share"],
                                    id={"type": "share-button", "filename": file.name},
                                )
                            ),
                        ],
                        className="justify-content-center",
                    ),
                    href="#",
                )
            )
        return new_children
