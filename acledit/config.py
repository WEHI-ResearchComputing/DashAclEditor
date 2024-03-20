import json
from pydantic import BaseModel, Field, AfterValidator
from pathlib import Path
from typing import Annotated
from pwd import getpwuid
from os import getuid


def interpolate_start_dir(v: str) -> Path:
    pwd_struct = getpwuid(getuid())
    return Path(v.format(user=pwd_struct.pw_name, home=pwd_struct.pw_dir))

class Hints(BaseModel):
    
    recursive: Annotated[
        str,
        Field(
            description='An optional string that will be added onto the text used to describe the "recursive" share option.'
        ),
    ] = ""

    edit: Annotated[
        str,
        Field(
            description='An optional string that will be added onto the text used to describe the "grant edit" share option.'
        ),
    ] = ""

    default: Annotated[
        str,
        Field(
            description='An optional string that will be added onto the text used to describe the "default" share option.'
        ),
    ] = ""

class Config(BaseModel):

    python: Annotated[
        Path,
        Field(
            description='The full file path to the Python interpreter that should be used by this application. For example: "/home/users/allstaff/milton.m/.conda/envs/miltonm-base/bin/python".'
        ),
    ]

    url_prefix: Annotated[
        str,
        Field(
            description='The prefix at which the web app will be available, including a leading and trailing slash. For example, when installed in the dev sandbox for OnDemand, this might be "/pun/dev/AclEditorDash/"'
        ),
    ] = "/"

    start_dir: Annotated[
        str,
        Field(
            description='The initial directory to start the file browsing. The variables `user` and `home` can be used as placeholders using the format() syntax, e.g. "{home}" or "/vast/scratch/users/{user}"'
        ),
        AfterValidator(interpolate_start_dir),
    ]

    shortcuts: Annotated[
        dict[str, Annotated[str, AfterValidator(interpolate_start_dir)]],
        Field(
            description='A dictionary of "shortcuts" in the file browser. Each key is a shortcut name, and each value is a path. The variables `{user}` and `{home}` can be used.'
        ),
    ] = {}

    hints: Annotated[Hints, Field(description="Hints used to add site-specific text to sharing options")] = Hints()

    fs_mounts: Annotated[list[Path], Field(description="A list of paths for which ACLs will be considered to be enabled and supported")] = [Path("/")]

    def has_acls(self, path: Path) -> bool:
        "Returns True if the given path supports ACLs"
        return any(path.is_relative_to(mount) for mount in self.fs_mounts)


with open("config.json", "rb") as f:
    config = Config.model_validate(json.load(f))
