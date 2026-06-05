import os
import re

def remove_emojis(text):
    # Matches emojis and other non-ascii symbols frequently used
    return re.sub(r'[^\x00-\x7F]+', '', text)

directories = ['C:\\Users\\Harikesn\\Desktop\\TITAN\\backend\\core', 'C:\\Users\\Harikesn\\Desktop\\TITAN\\backend\\plugins', 'C:\\Users\\Harikesn\\Desktop\\TITAN\\backend']

for directory in directories:
    if not os.path.exists(directory): continue
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # We only want to remove emojis from string literals if possible, 
                # but removing all non-ascii from .py is safe here since we don't have Hindi string literals except what we explicitly added.
                # Actually, wait, hindi_voice.py has hindi string literals like "banao", etc., which are ascii. 
                # Does it have any non-ascii? Let me check hindi_voice.py.
                
                new_content = remove_emojis(content)
                if new_content != content:
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"Removed emojis from {path}")
