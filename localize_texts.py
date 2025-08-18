#!/usr/bin/env python3
import argparse, os, re, shutil, sys
from pathlib import Path

TEXT_CALL_RE = re.compile(
    r'Text\(\s*"((?:[^"\\]|\\.)+)"\s*\)(?!\s*\.localized)'
)

LOC_LINE_RE = re.compile(
    r'^\s*"((?:[^"\\]|\\.)+)"\s*=\s*"((?:[^"\\]|\\.)+)"\s*;\s*$'
)

def unescape(s: str) -> str:
    return bytes(s, "utf-8").decode("unicode_escape")

def escape_for_strings(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')

def parse_localizable(path: Path):
    key_to_val, val_to_key = {}, {}
    if not path or not path.exists():
        return key_to_val, val_to_key
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            m = LOC_LINE_RE.match(line)
            if m:
                k, v = m.group(1), m.group(2)
                key_to_val[k] = v
                # prefer first seen mapping (avoid overwriting on duplicates)
                val_to_key.setdefault(v, k)
    return key_to_val, val_to_key

def slugify_key(s: str) -> str:
    # derive "example text" -> "example.text"
    import unicodedata
    s = s.strip().lower()
    s = unicodedata.normalize("NFKD", s)
    out = []
    prev_dot = False
    for ch in s:
        if ch.isalnum():
            out.append(ch)
            prev_dot = False
        else:
            if not prev_dot:
                out.append(".")
                prev_dot = True
    key = "".join(out).strip(".")
    if not key:
        key = "text"
    # limit length but keep meaningful suffix
    if len(key) > 60:
        key = key[:60].strip(".")
    return key

def generate_unique_key(base: str, existing_keys: set):
    key = base
    i = 2
    while key in existing_keys:
        key = f"{base}.{i}"
        i += 1
    return key

def should_skip_literal(lit: str) -> bool:
    # Skip interpolations or format placeholders – safer than guessing
    if r"\(" in lit:  # Swift string interpolation
        return True
    if "%@" in lit or "%d" in lit or "%f" in lit:  # printf style
        return True
    return False

def process_swift(content: str, val_to_key, existing_keys, additions):
    # additions: dict new_key -> value (unescaped)
    def repl(m: re.Match):
        raw = m.group(1)
        literal = raw.encode('utf-8').decode('unicode_escape')  # handle \" etc
        if should_skip_literal(literal):
            return m.group(0)  # leave as-is

        # If we already have this value, reuse its key
        key = val_to_key.get(literal)
        if not key:
            base = slugify_key(literal)
            key = generate_unique_key(base, existing_keys)
            existing_keys.add(key)
            additions.setdefault(key, literal)

        # Replace Text("value") -> Text("key".localized)
        return f'Text("{key}".localized)'

    new_content = TEXT_CALL_RE.sub(repl, content)
    return new_content

def write_strings(path: Path, key_to_val, additions):
    if not additions:
        return
    # Merge: keep existing, append new at end
    with path.open("a", encoding="utf-8") as f:
        if path.stat().st_size > 0:
            f.write("\n")
        for k in sorted(additions.keys()):
            v = additions[k]
            f.write(f"\"{escape_for_strings(k)}\" = \"{escape_for_strings(v)}\";\n")

def copy_tree(src: Path, dst: Path):
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)

def main():
    p = argparse.ArgumentParser(description="Convert hard-coded Text(\"…\") to Text(\"key\".localized)")
    p.add_argument("--src", required=True, help="Source folder (your project or a subfolder)")
    p.add_argument("--out", required=True, help="Output folder to write modified files")
    p.add_argument("--strings", required=False, help="Path to Localizable.strings to seed keys/values")
    p.add_argument("--write-strings", action="store_true",
                   help="Write/append an updated Localizable.strings into the output folder")
    p.add_argument("--strings-out", default="Localizable.strings",
                   help="Relative output path for strings file (default: Localizable.strings)")
    p.add_argument("--dry-run", action="store_true", help="Scan and report without writing changes")
    args = p.parse_args()

    src = Path(args.src).resolve()
    out = Path(args.out).resolve()
    strings_in = Path(args.strings).resolve() if args.strings else None

    key_to_val, val_to_key = parse_localizable(strings_in) if strings_in else ({}, {})
    existing_keys = set(key_to_val.keys())

    if not args.dry_run:
        copy_tree(src, out)

    additions = {}  # new key -> value
    changed_files = 0
    touched_literals = 0
    skipped_literals = 0

    for root, _, files in os.walk(src):
        for name in files:
            if not name.endswith(".swift"):
                continue
            in_path = Path(root) / name
            rel = in_path.relative_to(src)
            with in_path.open("r", encoding="utf-8") as f:
                content = f.read()

            # Count candidates first
            candidates = list(TEXT_CALL_RE.finditer(content))
            if not candidates:
                continue

            # Process
            new_content = process_swift(content, val_to_key, existing_keys, additions)

            if new_content != content:
                changed_files += 1
                # recompute touched/skip roughly
                for m in candidates:
                    lit = m.group(1).encode('utf-8').decode('unicode_escape')
                    if should_skip_literal(lit):
                        skipped_literals += 1
                    else:
                        touched_literals += 1

                if not args.dry_run:
                    out_path = out / rel
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    with out_path.open("w", encoding="utf-8") as f:
                        f.write(new_content)

    if args.write_strings and not args.dry_run:
        strings_out_path = out / args.strings_out
        strings_out_path.parent.mkdir(parents=True, exist_ok=True)
        # If you provided an input strings file, copy it first so we append
        if strings_in and strings_in.exists():
            shutil.copy2(strings_in, strings_out_path)
        else:
            strings_out_path.touch()
        write_strings(strings_out_path, key_to_val, additions)

    # Report
    print("=== Localization rewrite report ===")
    print(f"Source:  {src}")
    print(f"Output:  {'(dry-run)' if args.dry_run else out}")
    print(f"Strings input: {strings_in if strings_in else 'none'}")
    print(f"New keys to add: {len(additions)}")
    if args.write_strings and not args.dry_run:
        print(f"Strings written to: {out / args.strings_out}")
    print(f"Swift files changed: {changed_files}")
    print(f"Text() replaced: {touched_literals}")
    print(f"Text() skipped (interpolated/format): {skipped_literals}")
    if additions:
        print("\nNew keys preview:")
        for k in list(additions.keys())[:20]:
            print(f'  "{k}" = "{additions[k]}"')
        if len(additions) > 20:
            print(f"  ... and {len(additions)-20} more")

if __name__ == "__main__":
    sys.exit(main())
