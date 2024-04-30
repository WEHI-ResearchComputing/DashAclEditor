from acledit import app

app.app.run(
    host="0.0.0.0",
)
app.app.enable_dev_tools(
    debug=True,
    dev_tools_ui = True,
    dev_tools_props_check = True
)
