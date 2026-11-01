#!/usr/bin/env python3
"""Pemeriksaan struktural ringan untuk folder aplikasi APEXlang.

Bukan pengganti `apex validate` (SQLcl). Memeriksa:
  - keseimbangan ( ) { } [ ] dan blok ``` per file
  - aturan "satu properti per baris" (tidak ada `{ a: 1 b: 2 }` inline)
  - referensi @<id> ke komponen shared (lov, authorization, list, breadcrumb, pageGroup, theme, authentication)
  - referensi @<id> ke region/button/pageItem di halaman yang sama
  - nomor halaman target link ada

    python3 tools/apexgen/check_apx.py apex/mbms
"""
import os
import re
import sys

root = sys.argv[1] if len(sys.argv) > 1 else "apex/mbms"
errors = []
decl_re = re.compile(r"^\s*([A-Za-z][A-Za-z0-9_]*)\s+(\S+?|\"[^\"]*\")\s*\($")
decl_noid_re = re.compile(r"^\s*([A-Za-z][A-Za-z0-9_]*)\s*\($")
ref_re = re.compile(r":\s*@([A-Za-z0-9_\-]+)\s*$")
page_re = re.compile(r"^\s*page:\s*(\d+)\s*$")

shared = {}          # kind -> set(ids)
page_comps = {}      # file -> {kind: set}
page_refs = {}       # file -> [(line, ref)]
page_targets = []    # (file, line, pageno)
pages = set()

for dp, _dn, fns in os.walk(root):
    for fn in fns:
        if not fn.endswith(".apx"):
            continue
        path = os.path.join(dp, fn)
        rel = os.path.relpath(path, root)
        lines = open(path, encoding="utf-8").read().split("\n")
        stack = []
        in_ml = False
        comps = {}
        refs = []
        for i, line in enumerate(lines, 1):
            s = line.strip()
            if s.startswith("```"):
                in_ml = not in_ml
                continue
            if in_ml:
                continue
            if not s or s.startswith("//"):
                continue
            m = decl_re.match(line) or decl_noid_re.match(line)
            if m and not s.endswith(": (") and ":" not in s.split("(")[0]:
                kind = m.group(1)
                ident = m.group(2).strip('"') if m.lastindex and m.lastindex >= 2 else None
                stack.append("(")
                comps.setdefault(kind, set()).add(ident)
                if kind == "page" and ident:
                    pages.add(int(ident))
                continue
            if s == ")":
                if not stack or stack.pop() != "(":
                    errors.append("%s:%d unbalanced )" % (rel, i))
                continue
            if s == "}":
                if not stack or stack.pop() != "{":
                    errors.append("%s:%d unbalanced }" % (rel, i))
                continue
            if s == "]":
                if not stack or stack.pop() != "[":
                    errors.append("%s:%d unbalanced ]" % (rel, i))
                continue
            if s.endswith("{"):
                body = s[:-1].strip()
                if "{" in body or "}" in body:
                    errors.append("%s:%d inline object/group: %s" % (rel, i, s))
                stack.append("{")
                continue
            if s.endswith("["):
                stack.append("[")
                continue
            if stack and stack[-1] == "[":
                continue
            if ":" not in s:
                errors.append("%s:%d not a property: %s" % (rel, i, s))
                continue
            if s.endswith(":"):
                # must be followed by multiline string
                nxt = lines[i].strip() if i < len(lines) else ""
                if not nxt.startswith("```"):
                    errors.append("%s:%d empty property without multiline: %s" % (rel, i, s))
                continue
            r = ref_re.search(s)
            if r and not r.group(1).startswith("/"):
                refs.append((i, s.split(":")[0].strip(), r.group(1)))
            pm = page_re.match(line)
            if pm:
                page_targets.append((rel, i, int(pm.group(1))))
        if stack:
            errors.append("%s: unclosed blocks %s" % (rel, stack))
        if in_ml:
            errors.append("%s: unclosed multiline string" % rel)
        if rel.startswith("pages" + os.sep):
            page_comps[rel] = comps
            page_refs[rel] = refs
        else:
            for k, v in comps.items():
                shared.setdefault(k, set()).update(v)
            page_refs[rel] = refs

# which property names point at which component kinds
prop_kind = {
    "lov": ["lov"], "authorizationScheme": ["authorization"], "scheme": ["authentication"],
    "list": ["list"], "breadcrumb": ["breadcrumb"], "pageGroup": ["pageGroup"], "currentTheme": ["theme"],
    "parentEntry": ["entry"], "region": ["region"], "formRegion": ["region"], "button": ["button"],
    "whenButtonPressed": ["button"], "associatedItem": ["pageItem"], "filteredRegion": ["region"],
}
for rel, refs in page_refs.items():
    local = page_comps.get(rel, {})
    for (line, prop, ref) in refs:
        kinds = prop_kind.get(prop)
        if not kinds:
            continue
        ok = False
        for k in kinds:
            if ref in local.get(k, set()) or ref in shared.get(k, set()):
                ok = True
        if not ok:
            errors.append("%s:%d unresolved @%s (%s)" % (rel, line, ref, prop))

for rel, line, p in page_targets:
    if p not in pages:
        errors.append("%s:%d link to missing page %d" % (rel, line, p))

if errors:
    print("\n".join(errors))
    print("FAILED: %d issue(s)" % len(errors))
    sys.exit(1)
print("OK: %d pages, shared components: %s" % (len(pages), ", ".join("%s=%d" % (k, len(v)) for k, v in sorted(shared.items()))))
