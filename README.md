# Localize Texts Script

This repository contains a Python script that automatically converts hard‑coded SwiftUI `Text("...")` strings into localized strings using the `.localized` pattern.

---

## ✨ Features
- Recursively scans your Swift project.
- Converts `Text("Example")` → `Text("example.text".localized)`.
- Skips strings already localized.
- Skips interpolated/format strings (like `"Hi \(name)"` or `"%@"`).
- Mirrors folder structure into an **output folder**.
- Optionally updates/creates `Localizable.strings` with new keys.

---

## 📂 Folder Structure
```
string loc/               # Folder containing the script
 └── localize_texts.py    # The main script
```

---

## 🖥️ Requirements
- Python 3.8+ (preinstalled on macOS).
- (Optional) Docker if you prefer containerized execution.

---

## 🚀 Usage

### 1. Run directly with Python
```bash
python3 "/path/to/localize_texts.py" \
  --src "/path/to/YourProject" \
  --out "/path/to/output" \
  --strings "/path/to/YourProject/Localization/Localizable.strings" \
  --write-strings \
  --dry-run
```

- `--src` → source project folder  
- `--out` → destination folder for processed files  
- `--strings` → path to existing `Localizable.strings` (optional but recommended)  
- `--write-strings` → append new keys/values to a strings file in the output folder  
- `--dry-run` → preview changes without writing  

After reviewing the dry-run, re-run without `--dry-run`.

### 2. Run inside Docker
Create a `Dockerfile`:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY localize_texts.py /app/localize_texts.py
ENTRYPOINT ["python", "/app/localize_texts.py"]
```

Build:
```bash
docker build -t localize-texts .
```

Run:
```bash
docker run --rm \
  -v "/absolute/path/to/YourProject":/src \
  -v "/absolute/path/to/output":/out \
  -v "/absolute/path/to/YourProject/Localization":/strings \
  localize-texts \
  --src /src \
  --out /out \
  --strings /strings/Localizable.strings \
  --write-strings \
  --dry-run
```

---

## ✅ Example
```bash
python3 "/Users/you/Desktop/string loc/localize_texts.py" \
  --src "/Users/you/Desktop/Lascade/D2Flight/D2Flight" \
  --out "/Users/you/Desktop/output" \
  --strings "/Users/you/Desktop/Lascade/D2Flight/D2Flight/Localization/Localizable.strings" \
  --write-strings
```

---

## ⚠️ Notes
- The script only modifies `.swift` files and only `Text("...")` literals.
- Output folder will be a **full copy** of the input project. Always use a separate folder for `--out`.
- Skips `Text(verbatim: ...)`, already localized strings, and dynamic interpolations.
- Generates keys from text (e.g., `"Example Text"` → `example.text`). Ensures uniqueness with `.2`, `.3`, etc.

---

## 📝 License
MIT License
