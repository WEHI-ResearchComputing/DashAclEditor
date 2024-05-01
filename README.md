# Posix ACL GUI

A web app for editing Posix file access control lists (ACLs)

## Installation

```
git clone https://github.com/WEHI-ResearchComputing/DashAclEditor.git
pip install DashAclEditor
```

## Usage

### Development

```
python DashAclEditor/local.py
```

### Production (Passenger)

```
cd DashAclEditor
passenger start
```

### Production - gunicorn

```
pip install gunicorn
cd DashAclEditor
gunicorn -w 4 passenger_wsgi:application
```

## Configuration

Configuration can be defined by creating a file named `config.json` in the repository directory.
A full reference of the configuration options can be found in <https://github.com/WEHI-ResearchComputing/DashAclEditor/blob/main/acledit/config.py>
For example:

```json
{
    "python": "/path/to/venv/bin/python",
    "start_dir": "/projects",
    "shortcuts": {
        "Projects": "/projects",
        "My Scratch": "/scratch/users/{user}"
    },
    "hints": {
        "recursive": " Warning: this setting edits the ACL of multiple files meaning that mistakes can be difficult to fix.",
        "default": ""
    },
    "fs_mounts": ["/projects", "/scratch"],
    "editor": true,
    "url_prefix": "/pun/dev/AclEditorDash/"
}
```
