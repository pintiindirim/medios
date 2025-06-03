# -*- coding: utf-8 -*-
#!/usr/bin/env python

import os

def find_non_utf8_in_file(path):
    with open(path, "rb") as f:
        data = f.read()
    try:
        data.decode("utf-8")
        return None
    except UnicodeDecodeError as e:
        return e

def scan_py_files(root_dir):
    results = []
    for dirpath, _, filenames in os.walk(root_dir):
        for fn in filenames:
            if fn.endswith(".py"):
                full = os.path.join(dirpath, fn)
                err = find_non_utf8_in_file(full)
                if err:
                    results.append((full, err.start, err.reason))
    return results

if __name__ == "__main__":
    root = os.getcwd()  # veya proje klasörünüzün yolunu tam yazın
    bad = scan_py_files(root)
    if not bad:
        print("Tüm .py dosyaları geçerli UTF-8.")
    else:
        print("UTF-8 hatası bulunan dosyalar:")
        for path, pos, reason in bad:
            print(f"  • {path} — byte konumu: {pos}, nedeni: {reason}")
