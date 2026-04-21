"""
fix_datetime_format.py
──────────────────────
Fixes open_datetime float issue in one_day_proceeding.py.

Problem: date and hour columns are read as floats from CSV,
so timestamp becomes "20010110.0_61500.0" instead of "20010110_061500".

Run once from project root:
  python fix_datetime_format.py
"""

from pathlib import Path

TARGET = Path("one_day_proceeding/one_day_proceeding.py")

# what the generated code likely has (float concat)
PATTERNS = [
    # pattern → replacement
    (
        'timestamp = f"{last_row[\'date\']}_{last_row[\'hour\']}"',
        'timestamp = f"{int(last_row[\'date\'])}_{int(last_row[\'hour\']):06d}"',
    ),
    (
        "timestamp = f\"{last_row['date']}_{last_row['hour']}\"",
        "timestamp = f\"{int(last_row['date'])}_{int(last_row['hour']):06d}\"",
    ),
]

content = TARGET.read_text(encoding="utf-8")
fixed   = False

for old, new in PATTERNS:
    if old in content:
        content = content.replace(old, new, 1)
        print(f"[OK] Fixed: {old!r}")
        print(f"      → {new!r}")
        fixed = True
        break

if not fixed:
    # show surrounding lines so we can find it manually
    print("[WARN] Pattern not found automatically. Searching for 'timestamp' lines:")
    for i, line in enumerate(content.splitlines(), 1):
        if "timestamp" in line and ("date" in line or "hour" in line):
            print(f"  line {i}: {line.rstrip()}")
    print("\nManually replace the timestamp line to use int() conversion:")
    print('  timestamp = f"{int(last_row[\'date\'])}_{int(last_row[\'hour\']):06d}"')
else:
    # make backup then write
    backup = TARGET.with_suffix(".py.bak2")
    import shutil
    shutil.copy2(TARGET, backup)
    TARGET.write_text(content, encoding="utf-8")
    print(f"\n[OK] Written. Backup: {backup.name}")
    print("You can now re-run smoke_test.py")
