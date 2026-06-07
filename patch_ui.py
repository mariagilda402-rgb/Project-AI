import re
from pathlib import Path

# Paths
base = Path(r'd:\Documentos\Projeto AI\src\ui\nexus_modules')
tasks_path = base / 'tasks.html'
habits_css_path = base / 'habits.css'
habits_html_path = base / 'habits.html'

def patch_css_display(content):
    # Change display:flex; to display:none; for modal-backdrop
    c = re.sub(r'\.modal-backdrop\s*\{[^}]*display:\s*flex;[^}]*\}', 
               lambda m: m.group(0).replace('display:flex;', 'display:none;'), content)
    # Add display:flex to .active
    if '.modal-backdrop.active { opacity:1;' in c:
        c = c.replace('.modal-backdrop.active { opacity:1;', '.modal-backdrop.active { display:flex; opacity:1;')
    else:
        c = c.replace('.modal-backdrop.active {', '.modal-backdrop.active { display:flex !important;')
    return c

# 1. Patch habits.css
if habits_css_path.exists():
    css = habits_css_path.read_text(encoding='utf-8')
    css = patch_css_display(css)
    habits_css_path.write_text(css, encoding='utf-8')
    print("habits.css patched.")

# 2. Patch tasks.html CSS
if tasks_path.exists():
    html = tasks_path.read_text(encoding='utf-8')
    html = patch_css_display(html)
    tasks_path.write_text(html, encoding='utf-8')
    print("tasks.html css patched.")

