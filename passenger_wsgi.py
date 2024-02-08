import json
import sys
import os.path

# Automatically enforce running this app with the configured interpreter
with open("config.json") as fp:
    target_interpreter = json.load(fp).get("python")
    if target_interpreter is None:
        raise Exception('You must have a config.json file in the app directory that specifies the Python interpreter to use, in the form {"python": "/path/to/python"}')
    else:
        target_interpreter = os.path.normpath(target_interpreter)

if os.path.normpath(sys.executable) != target_interpreter:
    os.execl(target_interpreter, target_interpreter, *sys.argv)
else:
    from acledit.app import app
    application = app.server
