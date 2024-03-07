from pydantic import BaseModel
from typing import Iterable, TypeAlias, Literal
import posix1e as acl 
import pwd
import grp
import sys
from pathlib import Path

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

STR_TO_ERROR = dict(
    multi_error = acl.ACL_MULTI_ERROR,
    duplicate_error = acl.ACL_DUPLICATE_ERROR,
    miss_error = acl.ACL_MISS_ERROR,
    entry_error = acl.ACL_ENTRY_ERROR
)
ERROR_TO_STR = {
    acl.ACL_MULTI_ERROR: "Multiple entries",
    acl.ACL_DUPLICATE_ERROR: "Duplicate entries",
    acl.ACL_MISS_ERROR: "Missing or wrong entry",
    acl.ACL_ENTRY_ERROR: "Invalid entry type"
}

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

    def add_to_acl(self, parent: acl.ACL):
        """
        Convert back to a true ACL
        """
        entry = acl.Entry(parent)
        entry.tag_type = STR_TO_ACL_TYPE[self.tag_type]
        if self.qualifier is not None:
            if self.tag_type == "user":
                entry.qualifier = pwd.getpwnam(self.qualifier).pw_uid
            elif self.tag_type == "group":
                entry.qualifier = grp.getgrnam(self.qualifier).gr_gid
        entry.permset.read = self.read
        entry.permset.write = self.write
        entry.permset.execute = self.execute


class AclSet(BaseModel):
    file_path: str
    acls: list[AclEntry]
    # Files don't have default ACLs
    default_acls: list[AclEntry] | None

    @staticmethod
    def from_file(path: str) -> "AclSet":
        if Path(path).is_dir():
            default_acls = list(AclEntry.from_acl(acl.ACL(filedef=path)))
        else:
            default_acls = None

        return AclSet(
            file_path=path,
            acls=list(AclEntry.from_acl(acl.ACL(file=path))),
            default_acls=default_acls
        )

    def can_access(self, user: str) -> bool:
        """Returns True if the given user can read from this file or directory"""
        for entry in self.acls:
            if entry.tag_type == "other" and entry.read:
                return True
            elif entry.tag_type == "user" and entry.qualifier == user and entry.read:
                return True
            elif entry.tag_type == "group" and entry.read and entry.qualifier is not None:
                grp_members = grp.getgrnam(entry.qualifier).gr_mem
                if user in grp_members:
                    return True
            elif entry.tag_type == "owner" and Path(self.file_path).owner() == user:
                return True
        return False

    def apply(self):
        """
        Applies this ACL set to the file
        """
        facl = acl.ACL()
        for entry in self.acls:
            entry.add_to_acl(facl)
        facl.applyto(self.file_path, acl.ACL_TYPE_ACCESS)

        if Path(self.file_path).is_dir() and self.default_acls is not None:
            dfacl = acl.ACL()
            for entry in self.default_acls:
                entry.add_to_acl(dfacl)
            dfacl.applyto(self.file_path, acl.ACL_TYPE_DEFAULT)


def validate_acl(acl: acl.ACL) -> None:
    """
    If the ACL is invalid, returns a string explaining the issue
    """
    if acl.valid():
        return
    if sys.platform == "linux":
        error_type, index = acl.check()
        error_str = ERROR_TO_STR[error_type]
        entries = list(AclEntry.from_acl(acl))
        if index < len(entries):
            raise Exception(f"{error_str}: {entries[index]}")
        else:
            raise Exception(error_str)
    else:
        raise Exception("Unknown ACL error")

def grant_user(file_path: str, user_id: int, permissions: list[ACL_PERMISSION] = [], default: bool = False, recursive: bool = False):
    """
    Creates a new ACL entry on the file specified that grants permissions to the user specified.
    Params:
        permissions: A list of permissions such as `posix1e.ACL_WRITE`
    """
    path = Path(file_path)
    is_dir = path.is_dir()

    # Set access ACL
    facl = acl.ACL(file=file_path)
    grant_user_entry(facl, user_id, permissions)
    apply_acl_safely(facl, file_path, type=acl.ACL_TYPE_ACCESS)

    # Set default ACL
    if default and is_dir:
        dfacl = acl.ACL(filedef=file_path)
        
        # All ACLs seem to require a user owner, group owner and other entry, 
        # so we copy it from the standard ACL
        if len(list(dfacl)) == 0:
            for entry in facl:
                if entry.tag_type in {acl.ACL_USER_OBJ, acl.ACL_GROUP_OBJ, acl.ACL_OTHER}:
                    dfacl.append(entry)

        grant_user_entry(dfacl, user_id, permissions)
        apply_acl_safely(dfacl, file_path, type=acl.ACL_TYPE_DEFAULT)

    # Recurse
    if recursive and is_dir:
        for child in path.iterdir():
            grant_user(str(child), user_id, permissions=permissions, default=default, recursive=recursive)

def grant_user_entry(facl: acl.ACL, user_id: int, permissions: list[ACL_PERMISSION] = []):
    """
    Grant a user some permissions onto an existing ACL
    """
    entry = acl.Entry(facl)
    entry.tag_type = acl.ACL_USER
    entry.qualifier = user_id
    for perm in permissions:
        entry.permset.add(perm)

def get_or_create_entry(facl: acl.ACL, tag_type: int, qualifier: int):
    """
    Gets an entry if it already exists, otherwise creates a new one with the specified characteristics
    """
    for entry in facl:
        if entry.tag_type == tag_type and entry.qualifier == qualifier:
            return entry
    entry = acl.Entry(facl)
    entry.tag_type = tag_type
    entry.qualifier = qualifier
    return entry

def apply_acl_safely(facl: acl.ACL, file: str, type: int = acl.ACL_TYPE_ACCESS,):
    """
    Try to apply an ACL.
    If it fails, run validation to work out why it might have failed.
    """
    try:
        facl.applyto(file, type)
    except OSError as e:
        validate_acl(facl)
        raise e
