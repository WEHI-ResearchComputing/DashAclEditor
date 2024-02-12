from pydantic import BaseModel
from typing import Iterable, Literal, Self
import posix1e as acl 

STR_TO_ACL_TYPE: dict[str, int] = dict(
    user = acl.ACL_USER,
    group = acl.ACL_GROUP,
    other = acl.ACL_OTHER,
    owner = acl.ACL_USER_OBJ,
    group_owner = acl.ACL_GROUP_OBJ,
    mask = acl.ACL_MASK,
    undefined = acl.ACL_UNDEFINED_TAG
)
ACL_TYPE_TO_STR = {value: key for key, value in STR_TO_ACL_TYPE.items()}

class AclEntry(BaseModel):
    #: Type of ACL
    tag_type: str
    #: User or group ID
    qualifier: str | None
    read: bool
    write: bool
    execute: bool

    @staticmethod
    def from_acl(acl_obj: acl.ACL) -> Iterable["AclEntry"]:
        for entry in acl_obj:
            yield AclEntry(
                tag_type=ACL_TYPE_TO_STR[entry.tag_type],
                # Only group and user ACLs have qualifiers
                qualifier=entry.qualifier if entry.tag_type in {acl.ACL_USER, acl.ACL_GROUP} else None,
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
