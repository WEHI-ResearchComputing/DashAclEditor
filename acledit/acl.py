from pydantic import BaseModel
from typing import Iterable, TypeAlias, Literal
import posix1e as acl 
import pwd
import grp
import os

ACL_PERMISSION: TypeAlias = Literal[
    acl.ACL_WRITE,
    acl.ACL_READ,
    acl.ACL_EXECUTE
]

ACL_TYPE_STR: TypeAlias = Literal[
    "user",
    "group",
    "other",
    "owner",
    "group_owner",
    "mask",
    "undefined"
]

STR_TO_ACL_TYPE: dict[ACL_TYPE_STR, int] = dict(
    user = acl.ACL_USER,
    group = acl.ACL_GROUP,
    other = acl.ACL_OTHER,
    owner = acl.ACL_USER_OBJ,
    group_owner = acl.ACL_GROUP_OBJ,
    mask = acl.ACL_MASK,
    undefined = acl.ACL_UNDEFINED_TAG
)
ACL_TYPE_TO_STR: dict[int, ACL_TYPE_STR] = {value: key for key, value in STR_TO_ACL_TYPE.items()}

class AclEntry(BaseModel):
    #: Type of ACL
    tag_type: ACL_TYPE_STR
    #: User or group name
    qualifier: str | None
    read: bool
    write: bool
    execute: bool

    @staticmethod
    def from_acl(acl_obj: acl.ACL) -> Iterable["AclEntry"]:
        for entry in acl_obj:
            if entry.tag_type == acl.ACL_USER:
                qualifier = pwd.getpwuid(entry.qualifier).pw_name
            elif entry.tag_type == acl.ACL_GROUP:
                qualifier = grp.getgrgid(entry.qualifier).gr_name
            else:
                qualifier = None
            yield AclEntry(
                tag_type=ACL_TYPE_TO_STR[entry.tag_type],
                # Only group and user ACLs have qualifiers
                qualifier=qualifier,
                read=entry.permset.read,
                write=entry.permset.write,
                execute=entry.permset.execute,
            )


class AclSet(BaseModel):
    file_path: str
    acls: list[AclEntry]
    default_acls: list[AclEntry]

    @staticmethod
    def from_file(path: str) -> "AclSet":
        return AclSet(
            file_path=path,
            acls=list(AclEntry.from_acl(acl.ACL(file=path))),
            default_acls=list(AclEntry.from_acl(acl.ACL(filedef=path)))
        )

def grant_user(file_path: str, user_id: int, permissions: list[ACL_PERMISSION] = []):
    """
    Creates a new ACL on the file specified that grants permissions to the user specified.
    Params:
        permissions: A list of permissions such as `posix1e.ACL_WRITE`
    """
    acls = acl.ACL(file=file_path)
    entry = acl.Entry(acls)
    entry.tag_type = acl.ACL_USER
    entry.qualifier = user_id
    for perm in permissions:
        entry.permset.add(perm)
    acls.applyto(file_path)
