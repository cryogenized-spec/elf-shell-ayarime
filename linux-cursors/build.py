#!/usr/bin/env python3
"""Build seven self-contained native Xcursor themes from Ayarime's own PNGs.

Requires Linux's xcursorgen (Linux Mint / Ubuntu: sudo apt install x11-apps).
No sudo, live theme change, network access or desktop modifications are made.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tarfile
import tempfile

ROOT=Path(__file__).resolve().parent.parent
SOURCE=ROOT/"assets"/"cursors"
STATES=SOURCE/"states"
OUTROOT=ROOT/"dist"/"linux-cursors"
PACKAGE=OUTROOT/"Ayarime-Cursors"
ARCHIVE=OUTROOT/"Ayarime-Cursors-Linux-Mint.tar.gz"
ID="ayarime-cursors-v1"
# Each original design supplies its own default pointer. The six functional
# states are shared, and inherited Adwaita handles other cursor types.
POINTER_STYLES={
  "Ayarime-Core":None,
  "Ayarime-Classic-Spearhead":"classic-spearhead.png",
  "Ayarime-Crystal-Tech-Shard":"crystal-tech-shard.png",
  "Ayarime-Elven-Feather":"elven-feather.png",
  "Ayarime-Hollow-Frame":"hollow-frame.png",
  "Ayarime-Rune-Edged":"rune-edged.png",
  "Ayarime-Minimal-Precision":"minimal-precision.png",
}
HOTSPOTS={
  "pointer":((48,6,2),(64,8,3)),
  "ibeam":((48,21,24),(64,28,32)),
  "busy":((48,24,24),(64,32,32)),
  "crosshair":((48,24,24),(64,32,32)),
  "resize":((48,24,24),(64,32,32)),
  "link":((48,7,3),(64,9,4)),
}
# Cover common X11, GTK and CSS cursor spellings where the visuals match.
# Other shapes (vertical/horizontal resize, forbidden, move, etc.) inherit
# native Adwaita instead of falsely using an incompatible custom glyph.
ALIASES={
  "pointer":("left_ptr","default","arrow","top_left_arrow"),
  "ibeam":("xterm","text","ibeam"),
  "busy":("watch","wait","progress","left_ptr_watch"),
  "crosshair":("crosshair","cross","tcross","cell"),
  "resize":("size_fdiag","bd_double_arrow","nwse-resize"),
  "link":("hand2","hand","pointing_hand","pointer"),
}
def verify_png(path:Path,expected:int)->None:
    data=path.read_bytes()
    if data[:8]!=b"\x89PNG\r\n\x1a\n" or len(data)<24:
        raise ValueError("Missing or invalid PNG: "+str(path))
    width,height=struct.unpack(">II",data[16:24])
    if (width,height)!=(expected,expected):
        raise ValueError(f"{path}: expected {expected}x{expected} image, got {width}x{height}")

def build_cursor(path:Path,records:list[tuple[int,int,int,Path]])->None:
    config=[]
    for size,x,y,image in records:
        verify_png(image,size)
        if not (0<=x<size and 0<=y<size):
            raise ValueError(f"Invalid hotspot for {image}: {x},{y}")
        config.append(f"{size} {x} {y} {image.relative_to(ROOT).as_posix()}")
    proc=subprocess.run(
        ["xcursorgen","-",str(path)],cwd=ROOT,input="\n".join(config)+"\n",
        text=True,capture_output=True,check=False
    )
    if proc.returncode or not path.is_file():
        raise RuntimeError("xcursorgen failed for "+path.name+": "+proc.stderr.strip())
    if path.read_bytes()[:4]!=b"Xcur":
        raise RuntimeError("Not a valid Xcursor file: "+str(path))

def build() ->None:
    if not shutil.which("xcursorgen"):
        raise RuntimeError("xcursorgen missing. Linux Mint: sudo apt install x11-apps")
    if PACKAGE.exists():shutil.rmtree(PACKAGE)
    (PACKAGE/"themes").mkdir(parents=True)
    for name,alternate in POINTER_STYLES.items():
        theme=PACKAGE/"themes"/name
        cursors=theme/"cursors"
        cursors.mkdir(parents=True)
        (theme/"index.theme").write_text(
           f"[Icon Theme]\nName={name.replace('-', ' ')}\n"
           "Comment=Optional Ayarime cursor artwork; missing shapes inherit Adwaita.\n"
           "Inherits=Adwaita\n",encoding="utf-8")
        (theme/".ayarime-cursor-theme").write_text(ID+"\n",encoding="utf-8")
        for state,aliases in ALIASES.items():
            if state=="pointer" and alternate:
                records=[(64,2,2,SOURCE/alternate)]
            else:
                records=[(size,x,y,STATES/f"{state}-{size}.png")
                         for size,x,y in HOTSPOTS[state]]
            target=cursors/aliases[0]
            build_cursor(target,records)
            for alias in aliases[1:]:
                shutil.copyfile(target,cursors/alias)
    for src,dest in [
       (ROOT/"linux-cursors"/"install.sh",PACKAGE/"install.sh"),
       (ROOT/"linux-cursors"/"README.md",PACKAGE/"README.md"),
       (ROOT/"ARTWORK_LICENSE.md",PACKAGE/"ARTWORK_LICENSE.md")
    ]:
        shutil.copyfile(src,dest)
    (PACKAGE/"BUILD-MANIFEST.json").write_text(json.dumps({
       "format":"ayarime-linux-xcursor-v1",
       "variants":list(POINTER_STYLES),
       "functionalStates":list(HOTSPOTS),
       "inheritedFallback":"Adwaita",
       "busyAnimation":False,
       "noSudoOrSystemChanges":True,
       "source":"ELF//SHELL — Ayarime original cursor PNG assets"
    },indent=2)+"\n",encoding="utf-8")
    # Deterministic archive; tar entries are safe regular files only.
    OUTROOT.mkdir(parents=True,exist_ok=True)
    import gzip,io
    with ARCHIVE.open("wb") as target:
        with gzip.GzipFile(fileobj=target,mode="wb",filename="",mtime=0) as gz:
            with tarfile.open(fileobj=gz,mode="w",format=tarfile.PAX_FORMAT) as tar:
                for file in sorted(x for x in PACKAGE.rglob("*") if x.is_file()):
                    arcname=Path("Ayarime-Cursors")/file.relative_to(PACKAGE)
                    data=file.read_bytes()
                    info=tarfile.TarInfo(arcname.as_posix())
                    info.size=len(data);info.mtime=0;info.uid=0;info.gid=0
                    info.uname="";info.gname=""
                    info.mode=0o755 if file.name=="install.sh" else 0o644
                    tar.addfile(info,io.BytesIO(data))
    verify()
    print("Built native Linux cursor themes:",", ".join(POINTER_STYLES))
    print(f"Archive: {ARCHIVE} ({ARCHIVE.stat().st_size:,} bytes)")
    print("SHA256:",hashlib.sha256(ARCHIVE.read_bytes()).hexdigest())

def verify()->None:
    if not ARCHIVE.is_file():raise ValueError("Cursor archive has not been built")
    with tarfile.open(ARCHIVE,"r:gz") as archive:
        members=archive.getmembers()
        paths=[Path(m.name) for m in members]
        if len(paths)!=len(set(paths)):
            raise ValueError("Duplicate names in cursor archive")
        if not all(m.isfile() and not p.is_absolute() and
                   len(p.parts)>=2 and p.parts[0]=="Ayarime-Cursors" and
                   ".." not in p.parts and "\\" not in m.name
                   for m,p in zip(members,paths)):
            raise ValueError("Unsafe archive member")
        for name in POINTER_STYLES:
            names={m.name for m in members}
            prefix=f"Ayarime-Cursors/themes/{name}/"
            if prefix+"index.theme" not in names or prefix+".ayarime-cursor-theme" not in names:
                raise ValueError("Incomplete theme metadata: "+name)
            for names_for_state in ALIASES.values():
                for alias in names_for_state:
                    item=archive.extractfile(prefix+"cursors/"+alias)
                    if item is None or item.read(4)!=b"Xcur":
                        raise ValueError("Missing/broken Xcursor alias "+name+"/"+alias)
        if archive.extractfile("Ayarime-Cursors/install.sh") is None:
            raise ValueError("Installer missing")

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--verify-only",action="store_true")
    args=parser.parse_args()
    try:
        verify() if args.verify_only else build()
        if args.verify_only:print("PASS: native Xcursor archive structure and cursors verified")
    except Exception as e:
        print("FAILED:",e,file=sys.stderr)
        sys.exit(1)
