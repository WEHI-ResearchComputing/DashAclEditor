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
