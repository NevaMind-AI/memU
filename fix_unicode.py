#!/usr/bin/env python3
# Script to fix unicode issues in proactive_loop.py

def fix_unicode_in_file(file_path):
    """
    Replaces problematic Unicode characters in proactive_loop.py with ASCII alternatives
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Dictionary of problematic Unicode strings and their ASCII replacements
    replacements = [
        # Emojis and symbols to replace
        ('"🔍 ', '"[SCAN] '),
        ('"📝 ', '"[NOTE] '),
        ('"📊 ', '"[LOG] '),
        ('"🧠 ', '"[MEM] '),
        ('"🎉 ', '"[SUCCESS] '),
        ('"🚀 ', '"[START] '),
        ('"📦 ', '"[CONSOL] '),
        ('"🎯 ', '"[TARGET] '),
        ('"🛑 ', '"[STOP] '),
        ('"💡 ', '"[IDEA] '),
        ('"💾 ', '"[DISK] '),
        ('"🔄 ', '"[LOOP] '),
        ('"🔄\\n', '"[LOOP]\\n'),
        ('f"🔍 ', 'f"[SCAN] '),
        ('f"📝 ', 'f"[NOTE] '),
        ('f"📊 ', 'f"[LOG] '),
        ('f"🧠 ', 'f"[MEM] '),
        ('f"🎉 ', 'f"[SUCCESS] '),
        ('f"🚀 ', 'f"[START] '),
        ('f"📦 ', 'f"[CONSOL] '),
        ('f"🎯 ', 'f"[TARGET] '),
        ('f"🛑 ', 'f"[STOP] '),
        ('f"💡 ', 'f"[IDEA] '),
        ('f"💾 ', 'f"[DISK] '),
        ('f"🔄 ', 'f"[LOOP] '),
        # Handle warning symbols (⚠️)
        ('"⚠️  ', '"[WARN] '),
        ('"⚠️ "', '"[WARN] "'),
        ('f"⚠️  ', 'f"[WARN] '),
        ('f"⚠️ "', 'f"[WARN] "'),
        # Handle information symbols (ℹ️)
        ('"ℹ️  ', '"[INFO] '),
        ('"ℹ️ "', '"[INFO] "'),
        ('f"ℹ️  ', 'f"[INFO] '),
        ('f"ℹ️ "', 'f"[INFO] "'),
    ]
    
    # Apply replacements
    for old, new in replacements:
        content = content.replace(old, new)
    
    # Write the fixed content back to file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Fixed Unicode issues in {file_path}")

if __name__ == "__main__":
    fix_unicode_in_file("C:/Users/16663/Desktop/openclaw/memU/proactive_loop.py")
    print("Done!")