"""
Functions for working with ACLs, decoupled from GUI code
"""
from getpass import getuser
import pwd
import posix1e as acl 
import sys
from pathlib import Path
from acledit.acl_set import AclSet, ERROR_TO_STR, AclEntry, ACL_PERMISSION


def can_read_recursive(user: str, path: Path) -> bool:
    """
    Walks through a file and its ancestors, and checks if the user has read access to all of them
    """
    # The user needs read on the file in question
    if not AclSet.from_file(str(path)).can_access(user, permission="read"):
        return False
    # The user needs execute on the parent directories
    for parent in path.parents:
        if not AclSet.from_file(str(parent)).can_access(user, permission="execute"):
            return False
    return True

def validate_acl(acl: acl.ACL) -> None:
    """
    If the ACL is invalid, raises an exception explaining the issue
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

def ensure_mask(facl: acl.ACL):
    """
    Adds a rwx mask to the ACL if it doesn't already exist
    """
    for entry in facl:
        if entry.tag_type == acl.ACL_MASK:
            return
    mask = acl.Entry(facl)
    mask.tag_type = acl.ACL_MASK
    mask.permset.add(acl.ACL_READ)
    mask.permset.add(acl.ACL_WRITE)
    mask.permset.add(acl.ACL_EXECUTE)

def grant_user_entry(facl: acl.ACL, user_id: int, permissions: list[ACL_PERMISSION] = []):
    """
    Grant a user some permissions onto an existing ACL
    """
    ensure_mask(facl)
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

def apply_acl_safely(facl: acl.ACL, file: str, type: int = acl.ACL_TYPE_ACCESS):
    """
    Try to apply an ACL.
    If it fails, run validation to work out why it might have failed.
    """
    try:
        facl.applyto(file, type)
    except OSError as e:
        validate_acl(facl)
        raise e

def execute_share(
    path: str,
    share_user: str,
    editable: bool,
    recursive: bool,
    default: bool,
) -> None:
    """
    High level operation that shares `path` with `share_user`, automatically adjusting parent directory ACLs where necessary
    """
    current_path = Path(path)
    current_user = getuser()

    try:
        recipient_id = pwd.getpwnam(share_user).pw_uid
    except KeyError:
        raise Exception(f"Username {share_user} is not a valid Milton user!")

    if current_path.owner() != getuser():
        raise Exception(f"You do not own this file or directory. The current owner is {current_path.owner()}. Only the owner can share it.")

    acls = AclSet.from_file(path)
    for permission in acls.acls:
        if permission.tag_type == "user" and permission.qualifier == share_user:
            raise Exception(f"There is already some access control configured for {share_user}. Consider opening the Editor.")

    # Grant X access to each parent so that the directory can be listed
    # We iterate in reverse so that we can fail early
    for parent in reversed(current_path.parents):
        if parent.owner() == current_user:
            entry = get_or_create_entry(
                facl=acl.ACL(file=str(parent)),
                tag_type=acl.ACL_USER,
                qualifier=recipient_id,
            )
            entry.permset.execute = True
        else:
            parent_acl = AclSet.from_file(str(parent))
            if not parent_acl.can_access(share_user):
                raise Exception(f"Share failed because the parent directory {parent} is not owned by you, and cannot be accessed by {share_user}. Please contact {parent.owner()} and request that they share this directory with {share_user}.")

    perms = [acl.ACL_EXECUTE, acl.ACL_READ]
    if editable:
        perms.append(acl.ACL_WRITE)
    grant_user(
        path,
        recipient_id,
        permissions=perms,
        default=default,
        recursive=recursive,
    )
