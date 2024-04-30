from dash import html

class FontAwesomeIcon(html.I):
    def __init__(self, icon: str, **kwargs):
        """
        Font Awesome Icon

        Args:
            icon: The name of the FontAwesome icon *without* the fa- prefix
        """
        super().__init__(
            className=f"fa-solid fa-{icon}",
            style={"marginLeft": "10px", "marginRight": "10px"},
            **kwargs
        )
