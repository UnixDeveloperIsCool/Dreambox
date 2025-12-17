from fastapi.responses import HTMLResponse

# Paste your existing CSS/BASE_STYLE from your current dashboard here to keep the same look.
BASE_STYLE = """<!-- KEEP YOUR EXISTING BASE STYLE HERE -->"""

def render(title: str, body: str):
    return HTMLResponse(f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{title}</title>
{BASE_STYLE}
</head>
<body>
{body}
</body>
</html>""")
