#!/usr/bin/env python3
"""Merge ordered JPEG files into one multi-page PDF. Pure stdlib.

JPEGs are embedded verbatim (DCTDecode) -- no re-encoding, no quality loss.
Page size = pixel size at 300 DPI (scanner default), orientation via EXIF.
"""
import sys


def jpeg_size(data: bytes):
    """Return (width_px, height_px, orientation) from JPEG markers."""
    if not data.startswith(b"\xff\xd8"):
        raise ValueError("not a JPEG")
    w = h = 0
    orientation = 1
    pos = 2
    while pos < len(data) - 1:
        if data[pos] != 0xFF:
            pos += 1
            continue
        marker = data[pos + 1]
        if marker in (0xC0, 0xC1, 0xC2, 0xC3):  # SOF0..SOF3
            h = int.from_bytes(data[pos + 7 : pos + 9], "big")
            w = int.from_bytes(data[pos + 9 : pos + 11], "big")
            break
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            pos += 2
            continue
        if marker == 0xE1:  # APP1: EXIF orientation
            seg = data[pos + 4 : pos + 4 + int.from_bytes(data[pos + 2 : pos + 4], "big") - 2]
            if seg.startswith(b"Exif\x00\x00"):
                exif = seg[6:]
                little = exif[:2] == b"II"
                base = 8
                if len(exif) > base + 2 and exif[base : base + 2] in (b"MM", b"II"):
                    little = exif[base : base + 2] == b"II"
                    off = int.from_bytes(exif[base + 6 : base + 10], "little" if little else "big")
                    n = int.from_bytes(exif[base + 6 + off : base + 6 + off + 2], "little" if little else "big")
                    for i in range(n):
                        entry = base + 6 + off + 2 + i * 12
                        tag = int.from_bytes(exif[entry : entry + 2], "little" if little else "big")
                        if tag == 0x0112:
                            orientation = int.from_bytes(exif[entry + 8 : entry + 10], "little" if little else "big")
                            break
        if marker == 0xDD:  # DNR
            pos += 2 + int.from_bytes(data[pos + 2 : pos + 4], "big")
            continue
        if marker == 0xDA:  # SOS: scan data follows, stop looking
            break
        if pos + 2 < len(data):
            pos += 2 + int.from_bytes(data[pos + 2 : pos + 4], "big")
        else:
            break
    if w == 0 or h == 0:
        raise ValueError("no SOF marker found")
    # Declare ACTUAL pixel dimensions. Swapping for EXIF orientation makes the
    # declared W/H disagree with the embedded JPEG, which poppler rejects
    # (blank render, empty OCR). Scanner rasters are stored upright anyway.
    return w, h


def build_pdf(jpeg_paths):
    dpi = 300.0
    sizes = []
    blobs = []
    for p in jpeg_paths:
        data = open(p, "rb").read()
        w, h = jpeg_size(data)
        sizes.append((w, h))
        blobs.append(data)

    objects = []  # (num, body_bytes)
    page_objs, img_objs = [], []
    catalog_num, pages_num = 1, 2
    next_num = 3
    for blob, (w, h) in zip(blobs, sizes):
        img_num = next_num
        page_num = next_num + 1
        next_num += 2
        wpt = round(w * 72 / dpi, 2)
        hpt = round(h * 72 / dpi, 2)
        page_objs.append((page_num, img_num, wpt, hpt))
        img_objs.append(
            (img_num, b"<< /Type /XObject /Subtype /Image /Width %d /Height %d "
             b"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length %d >>\nstream\n%s\nendstream"
             % (w, h, len(blob), blob))
        )

    kids = b" ".join(b"%d 0 R" % n for n, _, _, _ in page_objs)
    objects.append((catalog_num, b"<< /Type /Catalog /Pages %d 0 R >>" % pages_num))
    objects.append((pages_num, b"<< /Type /Pages /Kids [%s] /Count %d >>" % (kids, len(page_objs))))
    for num, img_num, wpt, hpt in page_objs:
        objects.append((num, b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %.2f %.2f] /Resources << /XObject << /Im0 %d 0 R >> >> >>" % (pages_num, wpt, hpt, img_num)))
    objects.extend(img_objs)

    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num, body in sorted(objects):
        offsets[num] = len(out)
        out += b"%d 0 obj\n%s\nendobj\n" % (num, body)
    xref = len(out)
    n = max(offsets) + 1
    out += b"xref\n0 %d\n" % n
    out += b"0000000000 65535 f \n"
    for i in range(1, n):
        out += b"%010d 00000 n \n" % offsets.get(i, 0)
    out += b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (n, catalog_num, xref)
    return bytes(out)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: pdf_merge.py out.pdf page1.jpg page2.jpg ...", file=sys.stderr)
        raise SystemExit(2)
    pdf = build_pdf(sys.argv[2:])
    open(sys.argv[1], "wb").write(pdf)
    print("merged %d pages -> %s (%d bytes)" % (len(sys.argv) - 2, sys.argv[1], len(pdf)))
