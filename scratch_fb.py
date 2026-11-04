import re
import sys

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

path = r'C:\Users\SNM\.gemini\antigravity\brain\4ac83bbf-4ada-4c62-b8af-0592a4f5a7a1\.system_generated\steps\610\content.md'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

title = re.findall(r'<title>([^<]+)</title>', text)
print('Page Title:', title)
og_title = re.findall(r'property="og:title" content="([^"]+)"', text)
print('OG Title:', og_title)
og_image = re.findall(r'property="og:image" content="([^"]+)"', text)
print('OG Image:', og_image)
og_desc = re.findall(r'property="og:description" content="([^"]+)"', text)
print('OG Desc:', og_desc)

# Find any post text or photo links
posts = re.findall(r'data-ad-preview="message"[^>]*>([^<]+)<', text)
print('Posts found:', posts)
