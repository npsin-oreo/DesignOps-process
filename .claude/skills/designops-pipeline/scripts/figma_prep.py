#!/usr/bin/env python3
"""
figma_prep.py — deterministic prep for Step 5 (Figma output).

Turns pipeline artifacts into the inputs the agent feeds to use_figma, so Step 5 is
repeatable (not hand-built). Zero-dependency (stdlib only), like the validators.

Outputs into --out:
  vars_<NN>_<collection>.json   compact [name, kind('c'|'f'|'s'), value] per library collection
                                (aliases resolved; colors = 'rrggbbaa'; opacity already 0..1)
  theme.json                    Theme semantic map: [name, lightRef, darkRef, scopeKind]
                                (refs = "collection/name" into the library, nearest-matched)
  manifest.json                 device frame size, theme modes, component list, screens, flows

Usage:
  figma_prep.py --tokens <DS>/tokens.json --aesthetic <out>/aesthetic.json \
    --screens <out>/screen-inventory.json --flows <out>/flows.json \
    [--brief <out>/brief.json] [--intel <out>/intelligence.json] \
    --out /tmp/figbuild [--skip-brand cerulean-blue,coral]
"""
import argparse, json, os, re, sys

# ── token parsing (DTCG / Tokens-Studio: $value/$type, {alias.path}) ───────────
def load_library(path):
    d = json.load(open(path))
    order = d.get("$metadata", {}).get("tokenSetOrder", [s for s in d if not s.startswith("$")])
    sets = [s for s in order if s in d]
    literal, shortidx, rank = {}, {}, {}
    def walk(r, o, p):
        if isinstance(o, dict):
            if "$value" in o:
                literal[p] = (o.get("$type"), o["$value"]); rank[p] = r
                sp = p.split("/", 2)[2] if p.count("/") >= 2 else p
                shortidx.setdefault(sp, []).append(p); return
            for k, v in o.items():
                if not k.startswith("$"): walk(r, v, p + "/" + k if p else k)
    for i, s in enumerate(sets): walk(i, d[s], s)
    def resolve(p, seen=None):
        seen = seen or set()
        if p in seen or p not in literal: return (None, None)
        seen.add(p); t, v = literal[p]
        if isinstance(v, str) and v.startswith("{") and v.endswith("}"):
            cands = shortidx.get(v.strip("{}").replace(".", "/"))
            if not cands: return (t, None)
            return resolve(sorted(cands, key=lambda x: rank[x])[0], seen)
        return (t, v)
    return sets, literal, resolve

def parse_color(v):
    m = re.fullmatch(r"#([0-9a-fA-F]{3,8})", (v or "").strip())
    if not m: return None
    h = m.group(1)
    if len(h) == 3: h = "".join(c * 2 for c in h)
    if len(h) == 6: h += "ff"
    return h.lower() if len(h) == 8 else None

def parse_dim(v):
    v = (v or "").strip()
    for suf, mul in (("px", 1), ("rem", 16), ("%", 0.01)):
        if v.endswith(suf):
            try: return round(float(v[:-len(suf)]) * mul, 4)
            except: return None
    try: return round(float(v), 4)
    except: return None

# ── emit compact per-collection var blobs ──────────────────────────────────────
def emit_vars(sets, literal, resolve, out, skip_groups):
    manifest_cols = []
    for s in sets:
        coll, mode = s.split("/", 1)
        items = []
        for p in [x for x in literal if x.startswith(s + "/")]:
            name = p[len(s) + 1:]
            if coll == "brand-color" and name.split("/")[0] in skip_groups:
                continue
            t, rv = resolve(p)
            if rv is None: continue
            if t == "color":
                c = parse_color(rv)
                if c: items.append([name, "c", c])
            elif t == "text":
                items.append([name, "s", str(rv)])
            else:
                n = parse_dim(rv)
                if n is None: continue
                items.append([name, "f", n / 100 if coll == "opacity" else n])
        fn = "vars_%02d_%s.json" % (len(manifest_cols), re.sub(r"[^a-z0-9]+", "-", coll.lower()))
        json.dump({"collection": coll, "mode": mode, "items": items},
                  open(os.path.join(out, fn), "w"), separators=(",", ":"))
        manifest_cols.append({"file": fn, "collection": coll, "count": len(items)})
    return manifest_cols

# ── Theme semantic layer (derive 19 tokens, nearest-match into the library) ─────
SEM_LIGHT = {
    "background": "ffffff", "foreground": "111827", "card": "ffffff", "card-foreground": "111827",
    "popover": "ffffff", "popover-foreground": "111827", "primary": None, "primary-foreground": "ffffff",
    "secondary": "fce7f3", "secondary-foreground": "111827", "muted": "f3f4f6", "muted-foreground": "6b7280",
    "accent": "fce7f3", "accent-foreground": "111827", "destructive": "dc2626", "destructive-foreground": "ffffff",
    "border": "e5e7eb", "input": "e5e7eb", "ring": None,
}
SEM_DARK = {
    "background": "111827", "foreground": "f9fafb", "card": "1f2937", "card-foreground": "f9fafb",
    "popover": "1f2937", "popover-foreground": "f9fafb", "primary": None, "primary-foreground": "ffffff",
    "secondary": "374151", "secondary-foreground": "f9fafb", "muted": "1f2937", "muted-foreground": "9ca3af",
    "accent": "374151", "accent-foreground": "f9fafb", "destructive": "dc2626", "destructive-foreground": "ffffff",
    "border": "374151", "input": "374151", "ring": None,
}
def scope_kind(name):
    if name.endswith("-foreground") or name == "foreground": return "text"
    if name in ("border", "input", "ring"): return "stroke"
    return "bg"

def color_index(sets, literal, resolve, prefer=("tw-colors", "rdx-colors", "brand-color", "shadcn-ui")):
    idx = []  # (hex, "collection/name", pref_rank)
    pref = {c: i for i, c in enumerate(prefer)}
    for p in literal:
        t, rv = resolve(p)
        if t != "color": continue
        c = parse_color(rv)
        if not c: continue
        coll = p.split("/", 1)[0]; name = p.split("/", 2)[2] if p.count("/") >= 2 else p
        idx.append((c, coll + "/" + name, pref.get(coll, 99)))
    return idx

def nearest(hex8, idx):
    r, g, b = int(hex8[0:2], 16), int(hex8[2:4], 16), int(hex8[4:6], 16)
    best, bestd = None, 1e18
    for c, ref, pr in idx:
        cr, cg, cb = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
        d = (cr - r) ** 2 + (cg - g) ** 2 + (cb - b) ** 2 + pr * 0.001
        if d < bestd: bestd, best = d, ref
    return best

def build_theme(aesthetic, idx):
    primary = sec = None
    if aesthetic:
        bc = aesthetic.get("brand_config", {}); tk = aesthetic.get("tokens", {})
        primary = parse_color(bc.get("primary") or tk.get("primary") or "")
        sec = parse_color(tk.get("secondary") or tk.get("accent") or "")
    primary = primary or "be185d"
    light = dict(SEM_LIGHT); dark = dict(SEM_DARK)
    for m in (light, dark):
        m["primary"] = primary; m["ring"] = primary
    if sec:
        light["secondary"] = light["accent"] = sec
    theme = []
    for name in SEM_LIGHT:
        theme.append([name, nearest(light[name], idx), nearest(dark[name], idx), scope_kind(name)])
    return theme

# ── device + manifest ──────────────────────────────────────────────────────────
def device_for(platform):
    p = (platform or "").lower()
    if "desktop" in p or ("web" in p and "mobile" not in p): return {"name": "Desktop", "w": 1440, "h": 1024}
    if "tablet" in p: return {"name": "Tablet", "w": 834, "h": 1194}
    return {"name": "Mobile", "w": 390, "h": 844}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tokens", required=True); ap.add_argument("--aesthetic")
    ap.add_argument("--screens", required=True); ap.add_argument("--flows")
    ap.add_argument("--brief"); ap.add_argument("--intel")
    ap.add_argument("--out", required=True)
    ap.add_argument("--skip-brand", default="cerulean-blue,coral")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    skip = set(x.strip() for x in a.skip_brand.split(",") if x.strip())

    sets, literal, resolve = load_library(a.tokens)
    cols = emit_vars(sets, literal, resolve, a.out, skip)

    aesthetic = json.load(open(a.aesthetic)) if a.aesthetic and os.path.exists(a.aesthetic) else None
    theme = build_theme(aesthetic, color_index(sets, literal, resolve))
    json.dump(theme, open(os.path.join(a.out, "theme.json"), "w"), separators=(",", ":"))

    screens = json.load(open(a.screens)); sc = screens.get("screens", [])
    platform = (screens.get("meta", {}) or {}).get("platform")
    if not platform and a.brief and os.path.exists(a.brief):
        platform = (json.load(open(a.brief)).get("constraints", {}) or {}).get("platform")
    comp_union = sorted({c for s in sc for c in s.get("components", [])})
    flows = json.load(open(a.flows)) if a.flows and os.path.exists(a.flows) else {"flows": []}
    manifest = {
        "device": device_for(platform), "theme_modes": ["Light", "Dark"],
        "font_default": "Noto Sans Thai",
        "font_brand": (aesthetic or {}).get("brand_config", {}).get("font_sans"),
        "collections": cols,
        "components": comp_union,
        "screens": [{"id": s.get("id"), "name": s.get("name"), "route": s.get("route"),
                     "components": s.get("components", []), "states": s.get("states", []),
                     "layout": s.get("layout_primitive")} for s in sc],
        "flows": [{"id": f.get("id"), "name": f.get("name"),
                   "steps": [st.get("action") for st in f.get("steps", [])]} for f in flows.get("flows", [])],
        "mandatory_flows": flows.get("mandatory_flows", []),
    }
    json.dump(manifest, open(os.path.join(a.out, "manifest.json"), "w"), indent=1)

    tot = sum(c["count"] for c in cols)
    print("[figma_prep] ✓ prep complete → %s" % a.out)
    print("  library vars : %d across %d collections (skipped brand: %s)" % (tot, len(cols), ",".join(sorted(skip))))
    print("  theme tokens : %d (Light/Dark, nearest-matched)" % len(theme))
    print("  device       : %s %dx%d" % (manifest["device"]["name"], manifest["device"]["w"], manifest["device"]["h"]))
    print("  components   : %d · screens: %d · flows: %d" % (len(comp_union), len(sc), len(manifest["flows"])))

if __name__ == "__main__":
    main()
