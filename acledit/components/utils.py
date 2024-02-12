import contextlib
import functools
import uuid
from dash import MATCH
from dash.dependencies import _Wildcard

def make_id(child: str, id: str | _Wildcard = MATCH) -> dict:
    """
    Returns an ID object that can be used to register callbacks that update 
    or listen to a re-usable component's child component.
    Params:
        id: A unique identifier for the current instance of the component.
            Can pass MATCH in here to define class-wide callbacks
        child: An identifier for the child component of interest. This has
            to be unique within the re-usable component but not necessarily
            outside of it
    """
    return {
            "id": id,
            "child": child
        }


@contextlib.contextmanager
def use_id(id: str | None):
    if id is None:
        id = str(uuid.uuid4())
    yield functools.partial(make_id, id=id)
