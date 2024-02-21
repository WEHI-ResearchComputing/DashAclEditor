import contextlib
import functools
import uuid
from dash import MATCH
from dash.dependencies import _Wildcard
from typing import Callable, TypeAlias, NewType

ParentId: TypeAlias = str | _Wildcard
IdDict = NewType("IdDict", dict)

def make_id(child: str, parent: ParentId = MATCH) -> IdDict:
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
    return IdDict({
        "id": parent,
        "child": child
    })

def declare_child(child: str, **kwargs: ParentId) -> Callable[..., IdDict]:
    """
    Declare a child component with a given ID
    Params:
        child: This is the name of the component within the current class
        kwargs: Additional keys should be attributes that this child has, with their values set to ALL.
            For example, if a component has a filename attribute, you should use `declare_child("child", filename=ALL)`
    """
    # We can't use functools.partial here because it would expect the 
    # first positional argument to be child, but we want it to be id
    @classmethod
    def _make_id(cls, aio_id: ParentId, **inner_kwargs: ParentId):
        merged_kwargs = {
            **kwargs,
            **inner_kwargs
        }
        return IdDict({
            # aio_id is the top level ID that the user passes in when defining the app. This is not set by the component author.
            "aio_id": aio_id,
            # Child is used to distinguish child components within the current component, as determined by the component author
            "child": child,
            # Automatically set to the component's class name. This is needed in cases where `aio_id`` is set to MATCH and `child` clashes
            # with another component in the app
            "cls": cls.__name__,
            **merged_kwargs
        }) #make_id(child=child, parent=parent)

    return _make_id
