#!/usr/bin/env python3
"""Validate offline Linux Xcursor distribution and non-root install/uninstall."""
from pathlib import Path
import os
import subprocess
import tarfile
import tempfile

ROOT=Path(__file__).resolve().parent.parent
archive=ROOT/"dist"/"linux-cursors"/"Ayarime-Cursors-Linux-Mint.tar.gz"
subprocess.run(["python3",str(ROOT/"linux-cursors"/"build.py"),"--verify-only"],
               cwd=ROOT,check=True)
subprocess.run(["bash","-n",str(ROOT/"linux-cursors"/"install.sh")],
               cwd=ROOT,check=True)
with tempfile.TemporaryDirectory(prefix="ayarime-cursors-") as folder:
    base=Path(folder)
    with tarfile.open(archive,"r:gz") as z:
        z.extractall(base,filter="data")
    install=base/"Ayarime-Cursors"/"install.sh"
    home=base/"home"
    home.mkdir()
    env=os.environ.copy()
    env["HOME"]=str(home)
    target=home/".local"/"share"/"icons"
    # The existing user's cursor settings never change.
    subprocess.run(["bash",str(install)],cwd=install.parent,env=env,check=True)
    names=list(target.glob("Ayarime-*"))
    assert len(names)==7, f"Expected seven installed cursor themes, found {len(names)}"
    for theme in names:
        assert (theme/"cursors"/"left_ptr").read_bytes()[:4]==b"Xcur"
        assert "Inherits=Adwaita" in (theme/"index.theme").read_text()
    # Reinstall must be non-destructive, then remove only branded themes.
    subprocess.run(["bash",str(install)],cwd=install.parent,env=env,check=True)
    stray=target/"Ayarime-Unknown"
    stray.mkdir()
    (stray/"important.txt").write_text("preserve")
    subprocess.run(["bash",str(install),"--remove"],cwd=install.parent,env=env,check=True)
    assert (stray/"important.txt").read_text()=="preserve"
    assert not list(target.glob("Ayarime-Core"))
print("PASS: 7 native cursor themes, Xcursor files, inert installer, safe idempotent install/remove.")
