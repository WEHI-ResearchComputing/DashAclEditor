"""
Tests for AclSet.can_access, following the access check algorithm at
https://man7.org/linux/man-pages/man5/acl.5.html#ACCESS_CHECK_ALGORITHM
"""
import contextlib
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Generator
from unittest.mock import patch, DEFAULT

import pytest

from acledit.acl_set import AclEntry, AclSet, is_group_member

# The user whose access is checked in every can_access scenario
TEST_USER = "test_user"


@contextlib.contextmanager
def mock_user(user: SimpleNamespace):
    """
    Returns the provided user if it is looked up by name, other users are unaffected.
    """
    def lookup_user(name: str) -> SimpleNamespace:
        if name == user.pw_name:
            return user
        return DEFAULT

    with patch("acledit.acl_set.pwd.getpwnam", side_effect=lookup_user):
        yield

@contextlib.contextmanager
def mock_groups(groups: list[SimpleNamespace]):
    """
    Returns the corresponding group if it is looked up by name, other groups are unaffected.
    """
    def lookup_group(name: str) -> SimpleNamespace:
        return next((g for g in groups if g.name == name), DEFAULT)
    with patch("acledit.acl_set.grp.getgrnam", side_effect=lookup_group):
        yield

@contextlib.contextmanager
def patch_file_ownership(owner: str, group: str):
    """
    Patches the owner and group of a file.
    """
    with patch("acledit.acl_set.Path.owner", return_value=owner), patch("acledit.acl_set.Path.group", return_value=group):
        yield

class TestIsGroupMember:
    def test_primary_gid_match(self):
        # If the user has a primary group ID that matches the group ID, they are a member of that group
        with (
            mock_user(SimpleNamespace(pw_name=TEST_USER, pw_gid=200)),
            mock_groups([SimpleNamespace(name="staff", gr_gid=200, gr_mem=[])]),
        ):
            assert is_group_member(TEST_USER, "staff") is True

    def test_supplementary_member_match(self):
        # If the user is listed in the group's members, they are a member of that group
        with (
            mock_user(SimpleNamespace(pw_name=TEST_USER, pw_gid=999)),
            mock_groups([SimpleNamespace(name="devs", gr_gid=400, gr_mem=[TEST_USER])])
        ):
            assert is_group_member(TEST_USER, "devs") is True

    def test_no_match(self):
        # If the user is not listed in the group's members, and their primary group ID does not match, they are not a member of that group
        with (
            mock_user(SimpleNamespace(pw_name=TEST_USER, pw_gid=999)),
            mock_groups([SimpleNamespace(name="staff", gr_gid=200, gr_mem=[])]),
        ):
            assert is_group_member(TEST_USER, "staff") is False


@dataclass
class CanAccessCase:
    """A single scenario for AclSet.can_access"""
    #: Fake groups
    groups: list[SimpleNamespace]
    user: SimpleNamespace
    file_owner: str
    file_group: str
    acl_set: AclSet
    #: Permission being checked, one of "read", "write", or "execute"
    permission: str
    expected: bool



CASES = [
    pytest.param(
        # Even if the mask denies access, if the owner entry grants access, the owner can access the file
        CanAccessCase(
            groups=[SimpleNamespace(name="staff", gr_gid=200, gr_mem=[])],
            user=SimpleNamespace(pw_name=TEST_USER, pw_gid=999),
            file_owner=TEST_USER,
            file_group="staff",
            acl_set=AclSet(
                file_path="/some/fake/path",
                default_acls=None,
                acls=[
                    AclEntry(tag_type="owner", qualifier=None, read=True, write=False, execute=False),
                    AclEntry(tag_type="group_owner", qualifier=None, read=False, write=False, execute=False),
                    AclEntry(tag_type="mask", qualifier=None, read=False, write=False, execute=False),
                    AclEntry(tag_type="other", qualifier=None, read=False, write=False, execute=False),
                ],
            ),
            permission="read",
            expected=True,
        ),
        id="owner_granted_ignores_mask",
    ),
    pytest.param(
        # Even if the user is the owner, if the owner entry denies access, the user cannot access the file
        CanAccessCase(
            groups=[SimpleNamespace(name="staff", gr_gid=200, gr_mem=[])],
            user=SimpleNamespace(pw_name=TEST_USER, pw_gid=999),
            file_owner=TEST_USER,
            file_group="staff",
            acl_set=AclSet(
                file_path="/some/fake/path",
                default_acls=None,
                acls=[
                    AclEntry(tag_type="owner", qualifier=None, read=False, write=False, execute=False),
                    AclEntry(tag_type="group_owner", qualifier=None, read=False, write=False, execute=False),
                    AclEntry(tag_type="other", qualifier=None, read=False, write=False, execute=False),
                ],
            ),
            permission="write",
            expected=False,
        ),
        id="owner_denied_missing_permission",
    ),
    pytest.param(
        # If the user is granted access via a named user entry, and the mask allows it, the user can access the file
        CanAccessCase(
            groups=[],
            user=SimpleNamespace(pw_name=TEST_USER, pw_gid=999),
            file_owner="someone_else",
            file_group="staff",
            acl_set=AclSet(
                file_path="/some/fake/path",
                default_acls=None,
                acls=[
                    AclEntry(tag_type="owner", qualifier=None, read=False, write=False, execute=False),
                    AclEntry(tag_type="user", qualifier=TEST_USER, read=True, write=False, execute=False),
                    AclEntry(tag_type="mask", qualifier=None, read=True, write=False, execute=False),
                    AclEntry(tag_type="group_owner", qualifier=None, read=False, write=False, execute=False),
                    AclEntry(tag_type="other", qualifier=None, read=False, write=False, execute=False),
                ],
            ),
            permission="read",
            expected=True,
        ),
        id="named_user_granted_with_mask",
    ),
    pytest.param(
        # If the user is granted access via a named user entry, but the mask denies it, the user cannot access the file
        CanAccessCase(
            groups=[],
            user=SimpleNamespace(pw_name=TEST_USER, pw_gid=999),
            file_owner="someone_else",
            file_group="staff",
            acl_set=AclSet(
                file_path="/some/fake/path",
                default_acls=None,
                acls=[
                    AclEntry(tag_type="owner", qualifier=None, read=False, write=False, execute=False),
                    AclEntry(tag_type="user", qualifier=TEST_USER, read=True, write=False, execute=False),
                    AclEntry(tag_type="mask", qualifier=None, read=False, write=False, execute=False),
                    AclEntry(tag_type="group_owner", qualifier=None, read=False, write=False, execute=False),
                    AclEntry(tag_type="other", qualifier=None, read=False, write=False, execute=False),
                ],
            ),
            permission="read",
            expected=False,
        ),
        id="named_user_denied_by_mask",
    ),
    pytest.param(
        # If the user is granted access via a named group entry, and the user's primary group is that group,
        # and the mask allows it, the user can access the file
        CanAccessCase(
            groups=[SimpleNamespace(name="staff", gr_gid=200, gr_mem=[])],
            user=SimpleNamespace(pw_name=TEST_USER, pw_gid=200),
            file_owner="someone_else",
            file_group="wheel",
            acl_set=AclSet(
                file_path="/some/fake/path",
                default_acls=None,
                acls=[
                    AclEntry(tag_type="owner", qualifier=None, read=False, write=False, execute=False),
                    AclEntry(tag_type="group", qualifier="staff", read=True, write=False, execute=False),
                    AclEntry(tag_type="mask", qualifier=None, read=True, write=False, execute=False),
                    AclEntry(tag_type="group_owner", qualifier=None, read=False, write=False, execute=False),
                    AclEntry(tag_type="other", qualifier=None, read=False, write=False, execute=False),
                ],
            ),
            permission="read",
            expected=True,
        ),
        id="named_group_granted_via_primary_gid",
    ),
    pytest.param(
        # If the user is granted access via a named group entry, and the user is a supplementary member of that group,
        # and the mask allows it, the user can access the file
        CanAccessCase(
            groups=[SimpleNamespace(name="devs", gr_gid=400, gr_mem=[TEST_USER])],
            user=SimpleNamespace(pw_name=TEST_USER, pw_gid=999),
            file_owner="someone_else",
            file_group="wheel",
            acl_set=AclSet(
                file_path="/some/fake/path",
                default_acls=None,
                acls=[
                    AclEntry(tag_type="owner", qualifier=None, read=False, write=False, execute=False),
                    AclEntry(tag_type="group", qualifier="devs", read=True, write=False, execute=False),
                    AclEntry(tag_type="mask", qualifier=None, read=True, write=False, execute=False),
                    AclEntry(tag_type="group_owner", qualifier=None, read=False, write=False, execute=False),
                    AclEntry(tag_type="other", qualifier=None, read=False, write=False, execute=False),
                ],
            ),
            permission="read",
            expected=True,
        ),
        id="named_group_granted_via_supplementary_membership",
    ),
    pytest.param(
        # If the user is granted access via one group, but denied access via another group, the user can still access the file
        CanAccessCase(
            groups=[
                SimpleNamespace(name="devs", gr_gid=400, gr_mem=[TEST_USER]),
                SimpleNamespace(name="staff", gr_gid=200, gr_mem=[]),
            ],
            user=SimpleNamespace(pw_name=TEST_USER, pw_gid=200),
            file_owner="someone_else",
            file_group="wheel",
            acl_set=AclSet(
                file_path="/some/fake/path",
                default_acls=None,
                acls=[
                    AclEntry(tag_type="owner", qualifier=None, read=False, write=False, execute=False),
                    AclEntry(tag_type="group", qualifier="devs", read=False, write=False, execute=False),
                    AclEntry(tag_type="group", qualifier="staff", read=True, write=False, execute=False),
                    AclEntry(tag_type="mask", qualifier=None, read=True, write=False, execute=False),
                    AclEntry(tag_type="group_owner", qualifier=None, read=False, write=False, execute=False),
                    AclEntry(tag_type="other", qualifier=None, read=False, write=False, execute=False),
                ],
            ),
            permission="read",
            expected=True,
        ),
        id="named_group_continues_after_failed_match",
    ),
    pytest.param(
        # If the user is denied access via one group, but allowed by other entries, the user cannot access the file
        CanAccessCase(
            groups=[
                SimpleNamespace(name="devs", gr_gid=400, gr_mem=[TEST_USER]),
            ],
            user=SimpleNamespace(pw_name=TEST_USER, pw_gid=999),
            file_owner="someone_else",
            file_group="not_important",
            acl_set=AclSet(
                file_path="/some/fake/path",
                default_acls=None,
                acls=[
                    AclEntry(tag_type="owner", qualifier=None, read=False, write=False, execute=False),
                    AclEntry(tag_type="group", qualifier="devs", read=False, write=False, execute=False),
                    AclEntry(tag_type="mask", qualifier=None, read=True, write=False, execute=False),
                    AclEntry(tag_type="group_owner", qualifier=None, read=True, write=False, execute=False),
                    AclEntry(tag_type="other", qualifier=None, read=True, write=False, execute=False),
                ],
            ),
            permission="read",
            expected=False,
        ),
        id="group_checked_before_other",
    ),
    pytest.param(
        # If the user is granted access via the group owner entry, but the mask denies it, the user cannot access the file
        CanAccessCase(
            groups=[SimpleNamespace(name="wheel", gr_gid=300, gr_mem=[])],
            user=SimpleNamespace(pw_name=TEST_USER, pw_gid=300),
            file_owner="someone_else",
            file_group="wheel",
            acl_set=AclSet(
                file_path="/some/fake/path",
                default_acls=None,
                acls=[
                    AclEntry(tag_type="owner", qualifier=None, read=False, write=False, execute=False),
                    AclEntry(tag_type="group_owner", qualifier=None, read=True, write=False, execute=False),
                    AclEntry(tag_type="mask", qualifier=None, read=False, write=False, execute=False),
                    # forces a mask entry to exist
                    AclEntry(tag_type="user", qualifier="dave", read=True, write=False, execute=False),
                    AclEntry(tag_type="other", qualifier=None, read=True, write=False, execute=False),
                ],
            ),
            permission="read",
            expected=False,
        ),
        id="group_owner_denied_by_mask",
    ),
    pytest.param(
        # If the user is granted access via the group owner entry, and the mask allows it, the user can access the file
        CanAccessCase(
            groups=[SimpleNamespace(name="wheel", gr_gid=300, gr_mem=[])],
            user=SimpleNamespace(pw_name=TEST_USER, pw_gid=300),
            file_owner="someone_else",
            file_group="wheel",
            acl_set=AclSet(
                file_path="/some/fake/path",
                default_acls=None,
                acls=[
                    AclEntry(tag_type="owner", qualifier=None, read=False, write=False, execute=False),
                    AclEntry(tag_type="group_owner", qualifier=None, read=True, write=False, execute=False),
                    AclEntry(tag_type="mask", qualifier=None, read=True, write=False, execute=False),
                    AclEntry(tag_type="user", qualifier="dave", read=True, write=False, execute=False),
                    AclEntry(tag_type="other", qualifier=None, read=False, write=False, execute=False),
                ],
            ),
            permission="read",
            expected=True,
        ),
        id="group_owner_granted_with_mask",
    ),
    pytest.param(
        # If the user is granted access via the group owner entry, and there is no mask entry, the user can access the file
        CanAccessCase(
            groups=[SimpleNamespace(name="wheel", gr_gid=300, gr_mem=[])],
            user=SimpleNamespace(pw_name=TEST_USER, pw_gid=300),
            file_owner="someone_else",
            file_group="wheel",
            acl_set=AclSet(
                file_path="/some/fake/path",
                default_acls=None,
                acls=[
                    AclEntry(tag_type="owner", qualifier=None, read=False, write=False, execute=False),
                    AclEntry(tag_type="group_owner", qualifier=None, read=True, write=False, execute=False),
                    AclEntry(tag_type="other", qualifier=None, read=False, write=False, execute=False),
                ],
            ),
            permission="read",
            expected=True,
        ),
        id="group_owner_without_mask_uses_entry_directly",
    ),
    pytest.param(
        # If the user is neither the owner nor a member of the group owner, and is not granted access via a named user or group entry,
        # access is determined by the other entry
        CanAccessCase(
            groups=[SimpleNamespace(name="wheel", gr_gid=300, gr_mem=[])],
            user=SimpleNamespace(pw_name=TEST_USER, pw_gid=999),
            file_owner="someone_else",
            file_group="wheel",
            acl_set=AclSet(
                file_path="/some/fake/path",
                default_acls=None,
                acls=[
                    AclEntry(tag_type="owner", qualifier=None, read=False, write=False, execute=False),
                    AclEntry(tag_type="group_owner", qualifier=None, read=False, write=False, execute=False),
                    AclEntry(tag_type="other", qualifier=None, read=True, write=False, execute=False),
                ],
            ),
            permission="read",
            expected=True,
        ),
        id="falls_back_to_other",
    ),
]


@pytest.mark.parametrize("case", CASES)
def test_can_access(case: CanAccessCase):
    with (
        mock_user(case.user),
        mock_groups(case.groups),
        patch_file_ownership(case.file_owner, case.file_group),
    ):
        assert case.acl_set.can_access(TEST_USER, case.permission) is case.expected


class TestMissingMask:
    """An ACL with a named user or group entry, but no mask entry, is invalid and should raise"""

    def test_named_user_entry_raises(self):
        with (
            patch_file_ownership(owner="someone_else", group="staff"),
            mock_user(SimpleNamespace(pw_name=TEST_USER, pw_gid=999))
        ):
            acls = AclSet(
                file_path="/some/fake/path",
                default_acls=None,
                acls=[
                    AclEntry(tag_type="owner", qualifier=None, read=False, write=False, execute=False),
                    AclEntry(tag_type="user", qualifier=TEST_USER, read=True, write=False, execute=False),
                    AclEntry(tag_type="group_owner", qualifier=None, read=False, write=False, execute=False),
                    AclEntry(tag_type="other", qualifier=None, read=False, write=False, execute=False),
                ],
            )
            with pytest.raises(Exception):
                acls.can_access(TEST_USER, "read")

    def test_named_group_entry_raises(self):
        with (
            patch_file_ownership(owner="someone_else", group="wheel"),
            mock_user(SimpleNamespace(pw_name=TEST_USER, pw_gid=999)),
            mock_groups([SimpleNamespace(name="devs", gr_gid=400, gr_mem=[TEST_USER])])
        ):
            acls = AclSet(
                file_path="/some/fake/path",
                default_acls=None,
                acls=[
                    AclEntry(tag_type="owner", qualifier=None, read=False, write=False, execute=False),
                    AclEntry(tag_type="group", qualifier="devs", read=True, write=False, execute=False),
                    AclEntry(tag_type="group_owner", qualifier=None, read=False, write=False, execute=False),
                    AclEntry(tag_type="other", qualifier=None, read=False, write=False, execute=False),
                ],
            )
            with pytest.raises(Exception):
                acls.can_access(TEST_USER, "read")
