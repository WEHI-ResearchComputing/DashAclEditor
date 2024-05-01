"""
Classes for representing ACLs in Python, decoupled from GUI code
"""
from pathlib import Path
from pydantic import BaseModel
from typing import Iterable, TypeAlias, Literal
import posix1e as acl 
import pwd
import grp

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
    """
    Represents a single ACL entry via Python data structures
    """
    #: Type of ACL
    tag_type: ACL_TYPE_STR
    #: User or group name
    qualifier: str | None
    read: bool
    write: bool
    execute: bool

    @staticmethod
    def from_acl(acl_obj: acl.ACL) -> Iterable["AclEntry"]:
        """
        Creates several instances of this class based on a true ACL pointer
        """
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
        Add this as an entry to a true ACL pointer
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
    """
    Represents all the ACLs on a single file, using Python data structures
    """
    file_path: str
    acls: list[AclEntry]
    # Files don't have default ACLs
    default_acls: list[AclEntry] | None

    @property
    def iter_default(self) -> Iterable[AclEntry]:
        """
        Iterate the default ACLs. If the current ACL is for a file, this never yields.
        """
        if self.default_acls is not None:
            yield from self.default_acls

    def find_entry(self, default: bool, type: str, qualifier: str | None) -> AclEntry | None:
        """
        Returns an existing entry with the given attributes
        """
        try:
            collection = self.iter_default if default else self.acls
            return next(entry for entry in collection if entry.tag_type == type and (qualifier is None or qualifier == entry.qualifier))
        except StopIteration:
            # If nothing is found, return None
            return None

    def qualified_acls(self, default: bool = False) -> Iterable[AclEntry]:
        """
        Returns the ACLs that have a qualifier, namely the user and group ACLs 
        """
        for acl in (self.iter_default if default else self.acls):
            if acl.tag_type in {"user", "group"}:
                yield acl

    @staticmethod
    def from_file(path: str) -> "AclSet":
        """
        Create an instance of this class from a file path
        """
        if Path(path).is_dir():
            default_acls = list(AclEntry.from_acl(acl.ACL(filedef=path)))
        else:
            default_acls = None

        return AclSet(
            file_path=path,
            acls=list(AclEntry.from_acl(acl.ACL(file=path))),
            default_acls=default_acls
        )

    def can_access(self, user: str, permission: str = "read") -> bool:
        """
        Returns True if the given user has `permission` on this file or directory
        Note that this doesn't consider parent directories
        
        Params:
            permission: either "read", "write" or "execute"
            user: a username
        """
        for entry in self.acls:
            if entry.tag_type == "other" and getattr(entry, permission):
                return True
            elif entry.tag_type == "user" and entry.qualifier == user and getattr(entry, permission):
                return True
            elif entry.tag_type == "group" and getattr(entry, permission) and entry.qualifier is not None:
                grp_members = grp.getgrnam(entry.qualifier).gr_mem
                if user in grp_members:
                    return True
            elif entry.tag_type == "owner" and Path(self.file_path).owner() == user and getattr(entry, permission):
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
