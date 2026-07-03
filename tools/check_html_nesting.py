import re
from pathlib import Path

html = Path(r"D:\Downloads\Projeto AI\mobile\index.html").read_text(encoding="utf-8")
start = html.find('<main class="app-content"')
end = html.find('</main>', start)
chunk = html[start:end]
lines = chunk.splitlines()

depth = 0
views = []
for i, line in enumerate(lines, 1):
    if 'id="view-' in line and 'class="view' in line:
        m = re.search(r'id="(view-[^"]+)"', line)
        if m:
            views.append((depth, m.group(1), i))
    opens = len(re.findall(r'<div[\s>]', line))
    closes = line.count('</div>')
    depth += opens - closes

print("Views at depth when opened:")
for d, vid, ln in views:
    print(f"  depth={d:2d} line={ln:4d} {vid}")
print(f"\nFinal depth in main: {depth}")
