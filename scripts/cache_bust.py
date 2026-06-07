import os
import glob

directory = r'd:\Documentos\Projeto AI\src\ui\nexus_modules'
html_files = glob.glob(os.path.join(directory, '*.html'))

for html_file in html_files:
    if "_compiled" in html_file:
        continue
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Simple cache buster
    content = content.replace('href="habits.css"', 'href="habits.css?v=2"')
    content = content.replace('href="tasks.css"', 'href="tasks.css?v=2"')
    content = content.replace('href="finance.css"', 'href="finance.css?v=2"')
    content = content.replace('href="nexus_theme.css"', 'href="nexus_theme.css?v=2"')
    content = content.replace('href="workflows.css"', 'href="workflows.css?v=2"')
    content = content.replace('href="overview.css"', 'href="overview.css?v=2"')
    
    # Remove switchTab
    content = content.replace("switchTab('novo');", "")
    content = content.replace("switchTab('hoje');", "")
    
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(content)

print("HTML cache busting applied.")
