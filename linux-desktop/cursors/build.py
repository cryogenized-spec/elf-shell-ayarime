#!/usr/bin/env python3
"""Build native, scalable Xcursor themes in an ELF//SHELL-inspired palette.

The public project does not include the original Firefox cursor bitmaps;
these are new Linux-specific illustrations, not an exact asset export.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import struct
import math

from PIL import Image, ImageDraw

PALETTES = {
    'rose': {'bright': '#F39ABE', 'shade': '#742C67', 'name': 'ELF-SHELL-Rose'},
    'teal': {'bright': '#7AE7DB', 'shade': '#185F73', 'name': 'ELF-SHELL-Teal'},
    'gold': {'bright': '#F2CB7C', 'shade': '#765338', 'name': 'ELF-SHELL-Gold'},
}
SIZES = (24, 32, 48)
# Standard cursor aliases for Xcursor, GTK and Chromium/Firefox fallback.
ALIASES = {
    'default': ['left_ptr', 'arrow', 'top_left_arrow', 'X_cursor'],
    'pointer': ['hand1', 'hand2', 'pointing_hand', 'link', 'pointer'],
    'text': ['xterm', 'ibeam', 'text', 'vertical-text'],
    'cross': ['crosshair', 'cross', 'tcross', 'cross_reverse'],
    'wait': ['watch', 'wait', 'left_ptr_watch', 'progress', 'half-busy'],
    'move': ['fleur', 'move', 'all-scroll'],
    'forbidden': ['not-allowed', 'no-drop', 'crossed_circle'],
    'resize_h': ['sb_h_double_arrow', 'h_double_arrow', 'ew-resize', 'col-resize', 'size_hor'],
    'resize_v': ['sb_v_double_arrow', 'v_double_arrow', 'ns-resize', 'row-resize', 'size_ver'],
    'help': ['question_arrow', 'help', 'whats_this'],
}


def draw_icon(kind: str, size: int, bright: str, shade: str, frame: int = 0) -> tuple[Image.Image, int, int]:
    scale = 4
    S = size * scale
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    def p(points):
        return [(round(x * S), round(y * S)) for x, y in points]
    def line(points, color, width=.07, joint='curve'):
        d.line(p(points), fill=color, width=max(1, round(S * width)), joint=joint)
    def ell(box, fill=None, outline=None, width=.06):
        d.ellipse(tuple(round(v*S) for v in box), fill=fill, outline=outline, width=max(1,round(S*width)))
    hotspot = (.12, .10)
    if kind in ('default', 'help'):
        poly = p([(.10,.07),(.12,.81),(.31,.62),(.43,.91),(.57,.85),(.45,.57),(.72,.54)])
        d.polygon(poly, fill=shade)
        d.line(poly + [poly[0]], fill=bright, width=max(2,round(.055*S)), joint='curve')
        if kind == 'help':
            ell((.60,.06,.94,.41), fill=shade, outline=bright, width=.055)
            d.text((round(.704*S),round(.078*S)), '?', fill=bright)
    elif kind == 'pointer':
        hotspot=(.35,.09)
        # Hand silhouette, index raised; four knuckles and broad cuff.
        poly=p([(.26,.11),(.33,.05),(.40,.10),(.40,.40),(.49,.34),(.56,.37),(.62,.34),(.70,.39),(.76,.41),(.80,.48),(.74,.75),(.65,.88),(.35,.88),(.20,.67),(.16,.51),(.23,.47),(.32,.54)])
        d.polygon(poly, fill=shade)
        d.line(poly+[poly[0]], fill=bright, width=round(.052*S), joint='curve')
        line([(.40,.43),(.40,.67)],bright,.035)
    elif kind == 'text':
        hotspot=(.48,.48)
        line([(.48,.10),(.48,.90)],shade,.17)
        line([(.48,.10),(.48,.90)],bright,.085)
        for y in (.12,.88):
            line([(.26,y),(.70,y)],bright,.065)
    elif kind == 'cross':
        hotspot=(.50,.50)
        ell((.36,.36,.64,.64),fill=shade,outline=bright)
        for seg in [[(.50,.08),(.50,.32)],[(.50,.68),(.50,.92)],[(.08,.50),(.32,.50)],[(.68,.50),(.92,.50)]]:
            line(seg,bright,.065)
    elif kind == 'wait':
        hotspot=(.50,.50)
        ell((.15,.15,.85,.85), fill=shade, outline=bright, width=.09)
        angle=frame*2*math.pi/8 - math.pi/2
        tip=(.50+.28*math.cos(angle), .50+.28*math.sin(angle))
        line([(.50,.50),tip],bright,.095)
        ell((.44,.44,.56,.56),fill=bright)
    elif kind == 'move':
        hotspot=(.50,.50)
        line([(.5,.16),(.5,.84)],shade,.15)
        line([(.16,.5),(.84,.5)],shade,.15)
        line([(.5,.16),(.5,.84)],bright,.065)
        line([(.16,.5),(.84,.5)],bright,.065)
        for poly in [[(.50,.06),(.38,.27),(.62,.27)],[(.50,.94),(.38,.73),(.62,.73)],[(.06,.50),(.27,.38),(.27,.62)],[(.94,.50),(.73,.38),(.73,.62)]]:
            d.polygon(p(poly),fill=bright)
    elif kind == 'forbidden':
        hotspot=(.50,.50)
        ell((.12,.12,.88,.88),fill=shade,outline=bright,width=.09)
        line([(.25,.75),(.75,.25)],bright,.085)
    elif kind in ('resize_h','resize_v'):
        hotspot=(.50,.50)
        if kind == 'resize_h':
            line([(.14,.5),(.86,.5)],shade,.16)
            line([(.14,.5),(.86,.5)],bright,.065)
            for poly in [[(.06,.5),(.29,.29),(.29,.71)],[(.94,.5),(.71,.29),(.71,.71)]]:
                d.polygon(p(poly),fill=bright)
        else:
            line([(.5,.14),(.5,.86)],shade,.16)
            line([(.5,.14),(.5,.86)],bright,.065)
            for poly in [[(.5,.06),(.29,.29),(.71,.29)],[(.5,.94),(.29,.71),(.71,.71)]]:
                d.polygon(p(poly),fill=bright)
    else:
        raise ValueError(kind)
    # True Xcursor hotspots are pixels of the 24/32/48 image, not the 4x raster.
    return img.resize((size,size),Image.Resampling.LANCZOS), round(hotspot[0]*size),round(hotspot[1]*size)


def write_xcursor(path: Path, variants: list[tuple[int, Image.Image, int, int, int]]) -> None:
    """Write the Xcursor v1 file format directly, without external xcursorgen.

    Each variant is (nominal_size, image, hotspot_x, hotspot_y, delay_ms).
    Repeated entries with the same nominal size are animation frames.
    """
    IMAGE_TYPE=0xFFFD0002
    VERSION=0x00010000
    toc_size=16+12*len(variants)
    offsets=[]
    current=toc_size
    for _size,img,_x,_y,_delay in variants:
        offsets.append(current)
        current+=36+4*img.width*img.height
    with path.open('wb') as fh:
        fh.write(struct.pack('<4sIII',b'Xcur',16,VERSION,len(variants)))
        for (size,*_),offset in zip(variants,offsets):
            fh.write(struct.pack('<III',IMAGE_TYPE,size,offset))
        for size,img,x,y,delay in variants:
            # Xcursor pixels are 32-bit premultiplied ARGB values in machine
            # little-endian byte order; generate transparent-edge premultiplication.
            rgba=img.convert('RGBA')
            buffer=bytearray()
            for r,g,b,a in rgba.getdata():
                buffer.extend((b*a//255,g*a//255,r*a//255,a))
            fh.write(struct.pack('<IIIIIIIII',36,IMAGE_TYPE,size,VERSION,
                                 img.width,img.height,x,y,delay))
            fh.write(buffer)


def build_theme(key: str, output: Path) -> Path:
    config = PALETTES[key]
    destination = output / config['name']
    destination.mkdir(parents=True,exist_ok=True)
    cursors = destination / 'cursors'
    cursors.mkdir(exist_ok=True)
    (destination/'index.theme').write_text(
        '[Icon Theme]\nName='+config['name']+'\nComment=ELF//SHELL-inspired Linux native cursor theme\nInherits=Adwaita\n',
        encoding='utf-8')
    for kind, aliases in ALIASES.items():
        variants=[]
        for size in SIZES:
            frame_count=8 if kind=='wait' else 1
            for frame in range(frame_count):
                img,hx,hy=draw_icon(kind,size,config['bright'],config['shade'],frame)
                variants.append((size,img,hx,hy,95 if frame_count>1 else 0))
        primary=cursors/aliases[0]
        if primary.is_symlink():
            primary.unlink()
        write_xcursor(primary,variants)
        for alias in aliases[1:]:
            path=cursors/alias
            if path.is_symlink() or path.is_file():
                path.unlink()
            path.symlink_to(primary.name)
    return destination


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path.home()/'.local/share/icons')
    parser.add_argument('--palette',choices=(*PALETTES.keys(),'all'),default='all')
    args=parser.parse_args()
    for key in (PALETTES if args.palette=='all' else [args.palette]):
        location=build_theme(key,args.output)
        print(f'Installed {location.name} at {location}')
    print('Select a theme in Linux Mint: System Settings → Themes → Mouse Pointer.')

if __name__=='__main__':
    main()
