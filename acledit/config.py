import json
from pydantic import BaseModel, Field
from pathlib import Path
from typing import Annotated

class Config(BaseModel):
    python: Annotated[Path, Field(
        description='The full file path to the Python interpreter that should be used by this application. For example: "/home/users/allstaff/milton.m/.conda/envs/miltonm-base/bin/python".'
    )]
    #: 
    prefix: Annotated[str, Field(
        description='The prefix at which the web app will be available, including a leading and trailing slash. For example, when installed in the dev sandbox for OnDemand, this might be "/pun/dev/AclEditorDash/"'
    )] = "/"
    start_dir: Annotated[Path, Field(
        description='The initial directory to start the file browsing. The variables `user` and `home` can be used as placeholders using the format() syntax, e.g. "{home}" or "/vast/scratch/users/{user}"'
    )]

with open("config.json", "rb") as f:
    config = Config.model_validate(json.load(f))
