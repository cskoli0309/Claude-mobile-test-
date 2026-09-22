#!/usr/bin/env python3
"""Lane V: extract an image's palette, map it to the brain, and check contrast.

Works with no third-party packages: PNGs are decoded in pure Python (zlib is
stdlib). Pillow is used automatically when installed, which adds JPEG/WEBP/GIF.

Usage:
    extract_palette.py hero.png
    extract_palette.py hero.png --brain brains/acme/brain.json
    extract_palette.py evidence/approved/*.png --aggregate     # induce a palette from a corpus
    extract_palette.py hero.png --json --colors 12

With --brain it checks colour rules (color_presence, palette_share, color_contrast)
and reports off-palette colours as candidate findings.

With --aggregate it reports colours common across a corpus — this is how you induce
core-palette rules during 'build'. Colours in >=80% of assets are palette
candidates; colours in one asset are noise, not accents.

Exit codes: 0 ok / no violations, 1 violations found, 2 nothing readable.
"""

import argparse
import colorsys
import glob as globmod
import json
import os
import struct
import sys
import zlib

# --------------------------------------------------------------------------- colour maths


def hex_to_rgb(value):
    value = value.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    if len(value) != 6:
        raise ValueError("bad hex colour %r" % value)
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#%02X%02X%02X" % tuple(int(round(c)) for c in rgb)


def _linear(channel):
    c = channel / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def rgb_to_lab(rgb):
    """sRGB -> CIE Lab (D65). Used for perceptual distance, not display."""
    r, g, b = (_linear(c) for c in rgb)
    x = (r * 0.4124 + g * 0.3576 + b * 0.1805) / 0.95047
    y = (r * 0.2126 + g * 0.7152 + b * 0.0722) / 1.00000
    z = (r * 0.0193 + g * 0.1192 + b * 0.9505) / 1.08883

    def f(t):
        return t ** (1.0 / 3.0) if t > 0.008856 else (7.787 * t) + (16.0 / 116.0)

    fx, fy, fz = f(x), f(y), f(z)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def delta_e(rgb_a, rgb_b):
    """CIE76. Rule of thumb: <1 imperceptible, <3 a close match, >10 clearly different."""
    la, aa, ba = rgb_to_lab(rgb_a)
    lb, ab, bb = rgb_to_lab(rgb_b)
    return ((la - lb) ** 2 + (aa - ab) ** 2 + (ba - bb) ** 2) ** 0.5


def relative_luminance(rgb):
    r, g, b = (_linear(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(rgb_a, rgb_b):
    la, lb = relative_luminance(rgb_a), relative_luminance(rgb_b)
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


def wcag_verdict(ratio, context="text"):
    floors = {"text": (4.5, 7.0), "large_text": (3.0, 4.5), "ui": (3.0, 3.0)}
    aa, aaa = floors.get(context, floors["text"])
    if ratio >= aaa:
        return "AAA"
    if ratio >= aa:
        return "AA"
    return "FAIL"


def describe(rgb):
    """A short human label, so a report does not read as a wall of hex.

    Uses chroma (max-min) rather than HLS saturation: at very high or very low
    lightness, HLS saturation overstates colourfulness and would label an
    off-white as 'pale orange'. Chroma tracks what the eye actually reads, and
    the tinted-neutral labels ('warm off-white') are how designers name these.
    """
    r, g, b = rgb
    chroma = max(r, g, b) - min(r, g, b)
    light = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)[1]
    hue = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)[0] * 360

    def by_lightness():
        if light < 0.10:
            return "near-black"
        if light < 0.30:
            return "dark grey"
        if light < 0.62:
            return "mid grey"
        if light < 0.88:
            return "light grey"
        return "near-white"

    if chroma < 10:
        return by_lightness()

    warm = hue < 90 or hue >= 300
    if chroma < 32:
        tint = "warm" if warm else "cool"
        if light >= 0.88:
            return tint + " off-white"
        if light < 0.16:
            return tint + " near-black"
        return "%s %s" % (tint, by_lightness())

    names = [(15, "red"), (45, "orange"), (68, "yellow"), (160, "green"),
             (200, "cyan"), (255, "blue"), (290, "violet"), (330, "magenta"), (360, "red")]
    name = next(n for bound, n in names if hue < bound)
    if light < 0.22:
        return "deep " + name
    if light > 0.80:
        return "pale " + name
    if chroma < 80:
        return "muted " + name
    return name


# --------------------------------------------------------------------------- decoding


def decode_png(path, max_side=200):
    """Minimal PNG decoder -> list of (r,g,b). Handles colour types 0/2/3/4/6, depth 8/16."""
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return None

    pos, idat, palette, trns = 8, [], None, None
    width = height = depth = ctype = None
    interlace = 0
    while pos < len(data):
        if pos + 8 > len(data):
            break
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        kind = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        if kind == b"IHDR":
            width, height, depth, ctype, _, _, interlace = struct.unpack(">IIBBBBB", body)
        elif kind == b"PLTE":
            palette = [tuple(body[i:i + 3]) for i in range(0, len(body), 3)]
        elif kind == b"tRNS":
            trns = body
        elif kind == b"IDAT":
            idat.append(body)
        elif kind == b"IEND":
            break
        pos += 12 + length

    if width is None or not idat or interlace:
        return None                      # interlaced PNGs are rare; fall through to Pillow
    if depth not in (8, 16):
        return None

    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(ctype)
    if channels is None:
        return None

    try:
        raw = zlib.decompress(b"".join(idat))
    except zlib.error:
        return None

    sample_bytes = depth // 8
    bpp = channels * sample_bytes
    stride = width * bpp
    if len(raw) < (stride + 1) * height:
        return None

    step = max(1, max(width, height) // max_side)
    pixels, prev = [], bytearray(stride)
    offset = 0
    for y in range(height):
        filt = raw[offset]
        offset += 1
        line = bytearray(raw[offset:offset + stride])
        offset += stride

        if filt == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 0xFF
        elif filt == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif filt == 3:
            for i in range(stride):
                left = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 0xFF
        elif filt == 4:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                b = prev[i]
                c = prev[i - bpp] if i >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pred = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pred) & 0xFF
        prev = line

        if y % step:
            continue
        for x in range(0, width, step):
            base = x * bpp
            if ctype == 3:
                idx = line[base]
                if palette and idx < len(palette):
                    if trns and idx < len(trns) and trns[idx] < 128:
                        continue
                    pixels.append(palette[idx])
            elif ctype in (0, 4):
                if ctype == 4 and line[base + sample_bytes] < 128:
                    continue
                v = line[base]
                pixels.append((v, v, v))
            else:
                if ctype == 6 and line[base + 3 * sample_bytes] < 128:
                    continue
                pixels.append((line[base],
                               line[base + sample_bytes],
                               line[base + 2 * sample_bytes]))
    return pixels


def load_pixels(path, max_side=200):
    """Try Pillow (broad format support), then the built-in PNG decoder."""
    try:
        from PIL import Image
        with Image.open(path) as img:
            img = img.convert("RGB")
            img.thumbnail((max_side, max_side))
            return list(img.getdata()), "pillow"
    except ImportError:
        pass
    except Exception:
        pass
    pixels = decode_png(path, max_side)
    if pixels:
        return pixels, "builtin-png"
    return None, None


# --------------------------------------------------------------------------- quantisation


def quantize(pixels, n_colors=8, merge_threshold=12.0):
    """Coarse bucket, then merge perceptually-close buckets. Deterministic."""
    if not pixels:
        return []
    buckets = {}
    for r, g, b in pixels:
        key = (r >> 4, g >> 4, b >> 4)
        acc = buckets.get(key)
        if acc is None:
            buckets[key] = [r, g, b, 1]
        else:
            acc[0] += r
            acc[1] += g
            acc[2] += b
            acc[3] += 1

    entries = []
    for r, g, b, n in buckets.values():
        entries.append({"rgb": (r / n, g / n, b / n), "count": n})
    entries.sort(key=lambda e: -e["count"])

    merged = []
    for entry in entries:
        for target in merged:
            if delta_e(entry["rgb"], target["rgb"]) < merge_threshold:
                total = target["count"] + entry["count"]
                target["rgb"] = tuple(
                    (target["rgb"][i] * target["count"] + entry["rgb"][i] * entry["count"]) / total
                    for i in range(3))
                target["count"] = total
                break
        else:
            merged.append(dict(entry))

    merged.sort(key=lambda e: -e["count"])
    total = sum(e["count"] for e in merged) or 1
    out = []
    for entry in merged[:n_colors]:
        rgb = tuple(int(round(c)) for c in entry["rgb"])
        out.append({
            "hex": rgb_to_hex(rgb),
            "rgb": rgb,
            "share_pct": round(entry["count"] / total * 100, 2),
            "label": describe(rgb),
        })
    return out


# --------------------------------------------------------------------------- brain

def brain_palette(brain):
    """Collect allowed/forbidden colours from the brain's colour rules."""
    allowed, forbidden, rules = {}, {}, []
    for rule in brain.get("rules") or []:
        check = rule.get("check") or {}
        if check.get("kind") not in ("color_presence", "palette_share", "color_contrast"):
            continue
        rules.append(rule)
        params = check.get("params") or {}
        for value in params.get("allowed") or []:
            try:
                allowed[value.upper()] = hex_to_rgb(value)
            except ValueError:
                pass
        for value in params.get("forbidden") or []:
            try:
                forbidden[value.upper()] = hex_to_rgb(value)
            except ValueError:
                pass
    return allowed, forbidden, rules


def check_against_brain(palette, brain):
    allowed, forbidden, rules = brain_palette(brain)
    findings = []

    for entry in palette:
        rgb = entry["rgb"]
        if forbidden:
            for name, target in forbidden.items():
                d = delta_e(rgb, target)
                if d <= 3:
                    findings.append({
                        "kind": "forbidden_color",
                        "observed": "%s (%s, %.1f%% of canvas) matches forbidden %s (dE %.1f)"
                                    % (entry["hex"], entry["label"], entry["share_pct"], name, d),
                    })
        if allowed:
            best_name, best_d = None, 1e9
            for name, target in allowed.items():
                d = delta_e(rgb, target)
                if d < best_d:
                    best_name, best_d = name, d
            entry["nearest"] = best_name
            entry["delta_e"] = round(best_d, 1)
            if best_d > 10 and entry["share_pct"] >= 2:
                findings.append({
                    "kind": "off_palette",
                    "observed": "%s (%s, %.1f%%) is off-palette; nearest brand colour %s is dE %.1f away"
                                % (entry["hex"], entry["label"], entry["share_pct"],
                                   best_name, best_d),
                })

    for rule in rules:
        check = rule.get("check") or {}
        params = check.get("params") or {}
        if check.get("kind") != "palette_share":
            continue
        target_hex = (params.get("color") or "").upper()
        if not target_hex:
            continue
        try:
            target = hex_to_rgb(target_hex)
        except ValueError:
            continue
        share = sum(e["share_pct"] for e in palette if delta_e(e["rgb"], target) <= 10)
        if params.get("max_pct") is not None and share > params["max_pct"]:
            findings.append({
                "kind": "palette_share",
                "rule_id": rule.get("id"),
                "observed": "%s covers ~%.0f%% of the canvas; %s caps it at %s%%"
                            % (target_hex, share, rule.get("id"), params["max_pct"]),
            })
        if params.get("min_pct") is not None and share < params["min_pct"]:
            findings.append({
                "kind": "palette_share",
                "rule_id": rule.get("id"),
                "observed": "%s covers ~%.0f%%; %s requires at least %s%%"
                            % (target_hex, share, rule.get("id"), params["min_pct"]),
            })
    return findings


def contrast_pairs(palette, limit=3):
    """Contrast between the dominant colour and the next few — a proxy for text on ground."""
    if len(palette) < 2:
        return []
    ground = palette[0]
    pairs = []
    for entry in palette[1:limit + 1]:
        ratio = contrast_ratio(ground["rgb"], entry["rgb"])
        pairs.append({
            "fg": entry["hex"], "bg": ground["hex"],
            "ratio": round(ratio, 2),
            "text": wcag_verdict(ratio, "text"),
            "large_text": wcag_verdict(ratio, "large_text"),
        })
    return pairs


# --------------------------------------------------------------------------- aggregate

def aggregate(results, threshold_pct=80.0, match_de=10.0):
    """Colours recurring across a corpus are palette candidates; one-offs are noise."""
    clusters = []
    n_assets = len(results)
    for res in results:
        seen = []
        for entry in res["palette"]:
            for cluster in clusters:
                if delta_e(entry["rgb"], cluster["rgb"]) <= match_de:
                    if id(cluster) not in seen:
                        cluster["assets"] += 1
                        seen.append(id(cluster))
                    cluster["shares"].append(entry["share_pct"])
                    total = cluster["n"] + 1
                    cluster["rgb"] = tuple(
                        (cluster["rgb"][i] * cluster["n"] + entry["rgb"][i]) / total
                        for i in range(3))
                    cluster["n"] = total
                    break
            else:
                cluster = {"rgb": entry["rgb"], "n": 1, "assets": 1,
                           "shares": [entry["share_pct"]]}
                clusters.append(cluster)
                seen.append(id(cluster))

    out = []
    for cluster in sorted(clusters, key=lambda c: -c["assets"]):
        rgb = tuple(int(round(c)) for c in cluster["rgb"])
        presence = cluster["assets"] / n_assets * 100
        out.append({
            "hex": rgb_to_hex(rgb),
            "label": describe(rgb),
            "in_assets": cluster["assets"],
            "of_assets": n_assets,
            "presence_pct": round(presence, 1),
            "mean_share_pct": round(sum(cluster["shares"]) / len(cluster["shares"]), 1),
            "verdict": ("core" if presence >= threshold_pct
                        else "secondary" if presence >= 40
                        else "noise"),
        })
    return out


# --------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="Extract a palette and check it against a brain.")
    ap.add_argument("images", nargs="+")
    ap.add_argument("--brain")
    ap.add_argument("--colors", type=int, default=8)
    ap.add_argument("--max-side", type=int, default=200, help="downsample before quantising")
    ap.add_argument("--aggregate", action="store_true",
                    help="induce a corpus palette instead of per-asset reports")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    paths = []
    for pattern in args.images:
        hits = globmod.glob(pattern)
        paths.extend(hits if hits else [pattern])

    brain = None
    if args.brain:
        try:
            with open(args.brain, "r", encoding="utf-8") as fh:
                brain = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            print("cannot read brain: %s" % exc, file=sys.stderr)
            return 2

    results, unreadable = [], []
    for path in paths:
        pixels, via = load_pixels(path, args.max_side)
        if not pixels:
            unreadable.append(path)
            continue
        palette = quantize(pixels, args.colors)
        entry = {"asset": os.path.basename(path), "path": path,
                 "via": via, "palette": palette}
        if brain:
            entry["findings"] = check_against_brain(palette, brain)
        entry["contrast"] = contrast_pairs(palette)
        results.append(entry)

    if not results:
        msg = "nothing readable"
        try:
            import PIL  # noqa: F401
        except ImportError:
            msg += " (only PNG is supported without Pillow; `pip install Pillow` adds JPEG/WEBP/GIF)"
        print(msg, file=sys.stderr)
        return 2

    if args.aggregate:
        agg = aggregate(results)
        if args.json:
            print(json.dumps({"assets": len(results), "clusters": agg,
                              "unreadable": unreadable}, indent=2))
            return 0
        print("Corpus palette — %d asset(s)" % len(results))
        print("=" * 68)
        print("%-9s %-14s %-10s %-9s %s" % ("hex", "label", "presence", "mean", "verdict"))
        print("-" * 68)
        for c in agg:
            print("%-9s %-14s %3d/%-3d %2.0f%%  %5.1f%%   %s"
                  % (c["hex"], c["label"][:14], c["in_assets"], c["of_assets"],
                     c["presence_pct"], c["mean_share_pct"], c["verdict"]))
        core = [c for c in agg if c["verdict"] == "core"]
        print("")
        print("%d core colour(s) — present in >=80%% of the corpus." % len(core))
        if core:
            print("Candidate rule: color_presence, allowed = [%s]"
                  % ", ".join('"%s"' % c["hex"] for c in core))
            print("Support: count/of per colour above. Tag 'inferred' (max severity: major).")
        if unreadable:
            print("")
            print("Unreadable (%d): %s" % (len(unreadable), ", ".join(unreadable[:5])))
        return 0

    if args.json:
        print(json.dumps({"results": results, "unreadable": unreadable}, indent=2))
        return 1 if any(r.get("findings") for r in results) else 0

    violations = False
    for res in results:
        print("")
        print("%s   [%s]" % (res["asset"], res["via"]))
        print("-" * 62)
        for entry in res["palette"]:
            line = "  %-9s %-14s %5.1f%%" % (entry["hex"], entry["label"], entry["share_pct"])
            if "nearest" in entry:
                line += "   nearest %s (dE %.1f)" % (entry["nearest"], entry["delta_e"])
            print(line)
        if res["contrast"]:
            print("")
            print("  contrast vs dominant %s:" % res["palette"][0]["hex"])
            for pair in res["contrast"]:
                print("    %s  %5.2f:1   text %-4s  large %s"
                      % (pair["fg"], pair["ratio"], pair["text"], pair["large_text"]))
        if res.get("findings"):
            violations = True
            print("")
            print("  findings:")
            for f in res["findings"]:
                prefix = ("%s " % f["rule_id"]) if f.get("rule_id") else ""
                print("    ! %s%s" % (prefix, f["observed"]))
    if unreadable:
        print("")
        print("Unreadable (%d): %s" % (len(unreadable), ", ".join(unreadable[:5])))
    print("")
    return 1 if violations else 0


if __name__ == "__main__":
    # Piping into head/less closes stdout early; exit quietly instead of tracebacking.
    try:
        import signal
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    except (AttributeError, ValueError, OSError):
        pass
    try:
        sys.exit(main())
    except BrokenPipeError:
        try:
            sys.stdout.close()
        except Exception:
            pass
        sys.exit(0)
    except KeyboardInterrupt:
        sys.exit(130)
