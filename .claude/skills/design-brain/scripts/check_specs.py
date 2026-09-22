#!/usr/bin/env python3
"""Lane S: check real file specs against a channel definition.

Reads actual dimensions, aspect ratio, file size and (for MP4) duration straight
from file headers — no Pillow, no ffprobe required. Uses ffprobe when it happens
to be installed, for formats the built-in readers do not cover.

Usage:
    check_specs.py asset.png --brain brain.json --channel meta-feed
    check_specs.py delivery/*.png --summarize
    check_specs.py asset.mp4 --ratio 9:16 --min-w 1080 --max-mb 4
    check_specs.py delivery/*.jpg --json

--summarize reports what is actually there, with no pass/fail. Run it first on any
new corpus or delivery folder; it surfaces the odd-one-out immediately.

Exit codes: 0 all pass (or summarize), 1 one or more fail, 2 nothing readable.
Stdlib only.
"""

import argparse
import fractions
import json
import os
import shutil
import struct
import subprocess
import sys

# --------------------------------------------------------------------------- readers


def _png(fh):
    fh.seek(0)
    head = fh.read(26)
    if head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        return None
    w, h = struct.unpack(">II", head[16:24])
    return {"format": "png", "width": w, "height": h}


def _jpeg(fh):
    fh.seek(0)
    if fh.read(2) != b"\xff\xd8":
        return None
    sof = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
           0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
    while True:
        byte = fh.read(1)
        if not byte:
            return None
        if byte != b"\xff":
            continue
        marker = fh.read(1)
        while marker == b"\xff":          # fill bytes
            marker = fh.read(1)
        if not marker:
            return None
        code = marker[0]
        if code in (0xD8, 0xD9) or 0xD0 <= code <= 0xD7:
            continue
        length_bytes = fh.read(2)
        if len(length_bytes) < 2:
            return None
        length = struct.unpack(">H", length_bytes)[0]
        if code in sof:
            data = fh.read(5)
            if len(data) < 5:
                return None
            h, w = struct.unpack(">HH", data[1:5])
            return {"format": "jpeg", "width": w, "height": h}
        fh.seek(length - 2, os.SEEK_CUR)


def _gif(fh):
    fh.seek(0)
    head = fh.read(10)
    if head[:6] not in (b"GIF87a", b"GIF89a"):
        return None
    w, h = struct.unpack("<HH", head[6:10])
    return {"format": "gif", "width": w, "height": h}


def _webp(fh):
    fh.seek(0)
    head = fh.read(30)
    if head[:4] != b"RIFF" or head[8:12] != b"WEBP":
        return None
    chunk = head[12:16]
    if chunk == b"VP8X":
        w = int.from_bytes(head[24:27], "little") + 1
        h = int.from_bytes(head[27:30], "little") + 1
        return {"format": "webp", "width": w, "height": h}
    if chunk == b"VP8 ":
        w, h = struct.unpack("<HH", head[26:30])
        return {"format": "webp", "width": w & 0x3FFF, "height": h & 0x3FFF}
    if chunk == b"VP8L":
        bits = int.from_bytes(head[21:25], "little")
        return {"format": "webp",
                "width": (bits & 0x3FFF) + 1,
                "height": ((bits >> 14) & 0x3FFF) + 1}
    return {"format": "webp", "width": None, "height": None}


def _bmp(fh):
    fh.seek(0)
    head = fh.read(26)
    if head[:2] != b"BM":
        return None
    w, h = struct.unpack("<ii", head[18:26])
    return {"format": "bmp", "width": abs(w), "height": abs(h)}


def _mp4(fh):
    """Walk the ISO-BMFF box tree for mvhd (duration) and tkhd (dimensions)."""
    fh.seek(0)
    head = fh.read(12)
    if len(head) < 12 or head[4:8] != b"ftyp":
        return None
    info = {"format": "mp4", "width": None, "height": None, "duration_s": None}

    def walk(start, end, depth=0):
        pos = start
        while pos < end and depth < 6:
            fh.seek(pos)
            header = fh.read(8)
            if len(header) < 8:
                return
            size = struct.unpack(">I", header[:4])[0]
            kind = header[4:8]
            body = pos + 8
            if size == 1:
                ext = fh.read(8)
                if len(ext) < 8:
                    return
                size = struct.unpack(">Q", ext)[0]
                body = pos + 16
            elif size == 0:
                size = end - pos
            if size < 8:
                return

            if kind in (b"moov", b"trak", b"mdia"):
                walk(body, pos + size, depth + 1)
            elif kind == b"mvhd":
                fh.seek(body)
                ver = fh.read(4)[0]
                if ver == 1:
                    # ctime(8) mtime(8) timescale(4) duration(8)
                    raw = fh.read(28)
                    if len(raw) < 28:
                        pos += size
                        continue
                    timescale = struct.unpack(">I", raw[16:20])[0]
                    duration = struct.unpack(">Q", raw[20:28])[0]
                else:
                    # ctime(4) mtime(4) timescale(4) duration(4)
                    raw = fh.read(16)
                    if len(raw) < 16:
                        pos += size
                        continue
                    timescale = struct.unpack(">I", raw[8:12])[0]
                    duration = struct.unpack(">I", raw[12:16])[0]
                if timescale:
                    info["duration_s"] = round(duration / timescale, 3)
            elif kind == b"tkhd":
                fh.seek(body)
                ver = fh.read(4)[0]
                fh.seek(body + (96 if ver == 1 else 84) - 8)
                raw = fh.read(8)
                if len(raw) == 8:
                    w = struct.unpack(">I", raw[0:4])[0] / 65536.0
                    h = struct.unpack(">I", raw[4:8])[0] / 65536.0
                    if w and h and not info["width"]:
                        info["width"], info["height"] = int(round(w)), int(round(h))
            pos += size

    fh.seek(0, os.SEEK_END)
    walk(0, fh.tell())
    return info


READERS = (_png, _jpeg, _gif, _webp, _bmp, _mp4)


def ffprobe_info(path):
    if not shutil.which("ffprobe"):
        return None
    try:
        raw = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", "-show_streams", path],
            capture_output=True, text=True, timeout=30, check=False).stdout
        data = json.loads(raw)
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError):
        return None
    video = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    if not video:
        return None
    duration = data.get("format", {}).get("duration") or video.get("duration")
    return {
        "format": data.get("format", {}).get("format_name", "?").split(",")[0],
        "width": video.get("width"),
        "height": video.get("height"),
        "duration_s": round(float(duration), 3) if duration else None,
        "via": "ffprobe",
    }


def read_asset(path):
    info = {"path": path, "name": os.path.basename(path), "format": None,
            "width": None, "height": None, "duration_s": None, "bytes": None,
            "via": "builtin"}
    try:
        info["bytes"] = os.path.getsize(path)
        with open(path, "rb") as fh:
            for reader in READERS:
                try:
                    found = reader(fh)
                except (struct.error, OSError, IndexError):
                    found = None
                if found:
                    info.update(found)
                    break
    except OSError as exc:
        info["error"] = str(exc)
        return info

    if info["width"] is None or (info["format"] == "mp4" and info["duration_s"] is None):
        probed = ffprobe_info(path)
        if probed:
            info.update({k: v for k, v in probed.items() if v is not None})

    if info["format"] is None:
        info["error"] = "unrecognised format (built-in readers cover png/jpeg/gif/webp/bmp/mp4)"
    if info["width"] and info["height"]:
        info["ratio"] = ratio_string(info["width"], info["height"])
        info["ratio_value"] = info["width"] / info["height"]
    return info


# Ratios people actually name, checked before falling back to a reduction.
COMMON_RATIOS = ("1:1", "4:5", "5:4", "9:16", "16:9", "2:3", "3:2",
                 "4:3", "3:4", "1.91:1", "2:1", "1:2", "21:9", "3:1")


def ratio_string(w, h, max_denom=40, tolerance=0.01):
    """Name the ratio the way a spec sheet would.

    Prefer a common named ratio, then an exact small-integer reduction, and only
    then a decimal. Avoids reporting 728x90 as an unreadable '275:34'.
    """
    value = w / h
    for name in COMMON_RATIOS:
        a, b = name.split(":")
        if abs(float(a) / float(b) - value) <= tolerance:
            return name
    frac = fractions.Fraction(w, h)          # exact, already reduced
    if frac.denominator <= max_denom:
        return "%d:%d" % (frac.numerator, frac.denominator)
    return "%.2f:1" % value if value >= 1 else "1:%.2f" % (1 / value)


def parse_ratio(text):
    if ":" in text:
        a, b = text.split(":", 1)
        return float(a) / float(b)
    return float(text)


# --------------------------------------------------------------------------- checks


def run_checks(info, checks):
    results = []
    for check in checks:
        kind = check.get("kind")
        params = check.get("params") or {}
        status, detail = "skip", "no data to check against"

        if info.get("error"):
            results.append({"kind": kind, "status": "skip", "detail": info["error"]})
            continue

        if kind == "aspect_ratio":
            allowed = params.get("allowed") or []
            tol = params.get("tolerance", 0.01)
            actual = info.get("ratio_value")
            if actual is None:
                status, detail = "skip", "no dimensions available"
            else:
                hit = next((a for a in allowed if abs(parse_ratio(a) - actual) <= tol), None)
                status = "pass" if hit else "fail"
                detail = ("%s (%dx%d)" % (info["ratio"], info["width"], info["height"])
                          if hit else "%s (%dx%d); allowed %s"
                          % (info["ratio"], info["width"], info["height"], ", ".join(allowed)))

        elif kind == "dimensions":
            w, h = info.get("width"), info.get("height")
            if w is None:
                status, detail = "skip", "no dimensions available"
            else:
                failures = []
                if params.get("min_w") and w < params["min_w"]:
                    failures.append("width %d < min %d" % (w, params["min_w"]))
                if params.get("min_h") and h < params["min_h"]:
                    failures.append("height %d < min %d" % (h, params["min_h"]))
                if params.get("max_w") and w > params["max_w"]:
                    failures.append("width %d > max %d" % (w, params["max_w"]))
                if params.get("max_h") and h > params["max_h"]:
                    failures.append("height %d > max %d" % (h, params["max_h"]))
                status = "fail" if failures else "pass"
                detail = "; ".join(failures) if failures else "%dx%d" % (w, h)

        elif kind == "file_size":
            size, cap = info.get("bytes"), params.get("max_bytes")
            if size is None or cap is None:
                status, detail = "skip", "no size limit defined"
            else:
                status = "fail" if size > cap else "pass"
                detail = "%.2f MB (limit %.2f MB)" % (size / 1048576, cap / 1048576)

        elif kind == "duration":
            dur = info.get("duration_s")
            if dur is None:
                status, detail = "skip", ("no duration readable"
                                          + ("" if shutil.which("ffprobe")
                                             else "; install ffmpeg for non-MP4 video"))
            else:
                failures = []
                if params.get("min_s") and dur < params["min_s"]:
                    failures.append("%.2fs < min %ss" % (dur, params["min_s"]))
                if params.get("max_s") and dur > params["max_s"]:
                    failures.append("%.2fs > max %ss" % (dur, params["max_s"]))
                status = "fail" if failures else "pass"
                detail = "; ".join(failures) if failures else "%.2fs" % dur

        else:
            status = "skip"
            detail = "'%s' is not mechanically checkable here — needs a visual pass" % kind

        results.append({"kind": kind, "status": status, "detail": detail})
    return results


def checks_from_args(args):
    checks = []
    if args.ratio:
        checks.append({"kind": "aspect_ratio",
                       "params": {"allowed": args.ratio, "tolerance": args.tolerance}})
    dims = {k: v for k, v in (("min_w", args.min_w), ("min_h", args.min_h),
                              ("max_w", args.max_w), ("max_h", args.max_h)) if v}
    if dims:
        checks.append({"kind": "dimensions", "params": dims})
    if args.max_mb:
        checks.append({"kind": "file_size",
                       "params": {"max_bytes": int(args.max_mb * 1048576)}})
    if args.min_s or args.max_s:
        dur = {k: v for k, v in (("min_s", args.min_s), ("max_s", args.max_s)) if v}
        checks.append({"kind": "duration", "params": dur})
    return checks


def summarize(infos):
    print("Spec survey — %d file(s)" % len(infos))
    print("=" * 74)
    print("%-30s %-7s %-12s %-9s %-9s %s"
          % ("file", "fmt", "dimensions", "ratio", "size", "duration"))
    print("-" * 74)
    for info in infos:
        if info.get("error"):
            print("%-30s %s" % (info["name"][:30], "! " + info["error"]))
            continue
        dims = ("%dx%d" % (info["width"], info["height"])) if info.get("width") else "—"
        size = "%.2fMB" % (info["bytes"] / 1048576) if info.get("bytes") else "—"
        dur = "%.2fs" % info["duration_s"] if info.get("duration_s") else "—"
        print("%-30s %-7s %-12s %-9s %-9s %s"
              % (info["name"][:30], info.get("format") or "?", dims,
                 info.get("ratio") or "—", size, dur))

    readable = [i for i in infos if not i.get("error") and i.get("ratio")]
    if len(readable) > 1:
        ratios, formats = {}, {}
        for info in readable:
            ratios[info["ratio"]] = ratios.get(info["ratio"], 0) + 1
            formats[info["format"]] = formats.get(info["format"], 0) + 1
        print("-" * 74)
        print("ratios:  " + ", ".join("%s x%d" % (r, n)
                                      for r, n in sorted(ratios.items(), key=lambda kv: -kv[1])))
        print("formats: " + ", ".join("%s x%d" % (f, n)
                                      for f, n in sorted(formats.items(), key=lambda kv: -kv[1])))
        # Only meaningful when there IS a house format to be odd against.
        dominant, dominant_n = max(ratios.items(), key=lambda kv: kv[1])
        if len(readable) >= 4 and dominant_n / len(readable) >= 0.6:
            odd = sorted(r for r, n in ratios.items() if r != dominant)
            if odd:
                print("")
                print("Dominant ratio is %s (%d of %d). Outliers: %s — check they are intentional."
                      % (dominant, dominant_n, len(readable), ", ".join(odd)))


def main():
    ap = argparse.ArgumentParser(description="Check delivered file specs (lane S).")
    ap.add_argument("assets", nargs="+")
    ap.add_argument("--brain", help="brain.json containing channel definitions")
    ap.add_argument("--channel", help="channel id within the brain")
    ap.add_argument("--summarize", action="store_true", help="report what is there, no pass/fail")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--ratio", action="append", help="allowed ratio, e.g. 9:16 (repeatable)")
    ap.add_argument("--tolerance", type=float, default=0.01)
    ap.add_argument("--min-w", type=int)
    ap.add_argument("--min-h", type=int)
    ap.add_argument("--max-w", type=int)
    ap.add_argument("--max-h", type=int)
    ap.add_argument("--max-mb", type=float)
    ap.add_argument("--min-s", type=float)
    ap.add_argument("--max-s", type=float)
    args = ap.parse_args()

    infos = [read_asset(p) for p in args.assets]
    if all(i.get("error") for i in infos):
        if args.summarize or args.json:
            pass
        else:
            print("nothing readable", file=sys.stderr)
            return 2

    checks, channel_label = checks_from_args(args), None
    if args.brain and args.channel:
        try:
            with open(args.brain, "r", encoding="utf-8") as fh:
                brain = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            print("cannot read brain: %s" % exc, file=sys.stderr)
            return 2
        channel = next((c for c in brain.get("channels") or []
                        if c.get("id") == args.channel), None)
        if not channel:
            available = ", ".join(c.get("id", "?") for c in brain.get("channels") or []) or "none"
            print("channel %r not in brain (available: %s)" % (args.channel, available),
                  file=sys.stderr)
            return 2
        checks = (channel.get("checks") or []) + checks
        channel_label = channel.get("label", args.channel)
        if not channel.get("verified"):
            print("! channel %r has never been verified against the platform's current spec.\n"
                  "  Treat failures as advisory until it is.\n" % args.channel, file=sys.stderr)

    if args.summarize or not checks:
        if args.json:
            print(json.dumps(infos, indent=2))
        else:
            summarize(infos)
            if not checks and not args.summarize:
                print("")
                print("No checks given — pass --brain/--channel or flags like --ratio 9:16.")
        return 0

    failed = False
    payload = []
    for info in infos:
        results = run_checks(info, checks)
        if any(r["status"] == "fail" for r in results):
            failed = True
        payload.append({"asset": info, "results": results})

    if args.json:
        print(json.dumps({"channel": args.channel, "assets": payload}, indent=2))
        return 1 if failed else 0

    print("Spec check%s — %d file(s)"
          % (" against %s" % channel_label if channel_label else "", len(infos)))
    print("=" * 66)
    for entry in payload:
        info = entry["asset"]
        print("")
        print(info["name"])
        for res in entry["results"]:
            mark = {"pass": "ok  ", "fail": "FAIL", "skip": "--  "}[res["status"]]
            print("  %s %-14s %s" % (mark, res["kind"], res["detail"]))
    print("")
    print("RESULT: %s" % ("FAIL" if failed else "PASS"))
    return 1 if failed else 0


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
