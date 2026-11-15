"""Build the standalone website from editable app/web/ sources."""
from pathlib import Path
import base64
import re

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / 'app/web'


def scoped_css(source):
    """Flatten weather selectors without relying on CSS nesting support."""
    output = []
    position = 0
    while position < len(source):
        opening = source.find('{', position)
        if opening < 0:
            break
        selector = source[position:opening].strip()
        depth, closing = 1, opening + 1
        while depth:
            depth += (source[closing] == '{') - (source[closing] == '}')
            closing += 1
        content = source[opening+1:closing-1]
        if selector.startswith('@media'):
            output.append(selector + '{' + scoped_css(content) + '}')
        else:
            selectors = [('#weather-page' if s.strip() == ':root' else '#weather-page ' + s.strip()) for s in selector.split(',')]
            output.append(','.join(selectors) + '{' + content + '}')
        position = closing
    return '\n'.join(output)


weather_css = scoped_css((WEB / 'forecast.css').read_text(encoding='utf-8'))
weather_css += '\n.challenge-note{padding:22px 26px;border-left:3px solid var(--green);background:white;margin-bottom:32px}.challenge-note p{margin:12px 0;color:var(--secondary)}.challenge-note a{color:var(--green);text-decoration:underline}.navigation{gap:20px}\n'
(WEB / 'weather-context.css').write_text(weather_css, encoding='utf-8')
html = (WEB / 'index.html').read_text(encoding='utf-8')
for name in ['fonts.css', 'styles.css', 'weather-context.css', 'dashboard.css', 'review.css']:
    css = (WEB / name).read_text(encoding='utf-8')
    css = re.sub(r"url\('\./fonts/([^']+)'\)", lambda m: "url('data:font/ttf;base64," + base64.b64encode((WEB/'fonts'/m.group(1)).read_bytes()).decode('ascii') + "')", css)
    html = html.replace(f'<link rel="stylesheet" href="./{name}">', '<style>\n' + css + '\n</style>')
for name in ['analysis-data.js', 'impact-data.js', 'reference-data.js', 'app.js', 'reference.js', 'review.js', 'forecast.js']:
    html = html.replace(f'<script src="./{name}" defer></script>', '')
html = html.replace('<link rel="icon" href="./favicon.svg" type="image/svg+xml">', '')
scripts = '\n'.join((WEB / name).read_text(encoding='utf-8') for name in ['analysis-data.js', 'impact-data.js', 'reference-data.js', 'app.js', 'reference.js', 'review.js', 'forecast.js'])
html = html.replace('</body>', '<script>\n' + scripts.replace('</script', '<\\/script') + '\n</script>\n</body>')
destination = ROOT / 'app/standalone' / 'index.html'
destination.parent.mkdir(parents=True,exist_ok=True)
destination.write_text(html, encoding='utf-8')
print('Built:', destination)
