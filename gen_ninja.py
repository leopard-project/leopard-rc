#!/usr/bin/env python3
"""leopard-rc 构建 + xbps 打包。"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent          # leopard-rc/
SDK  = ROOT / ".." / "leopard-sdk"
INC  = SDK / "include"
OBJ  = SDK / "obj-tui"
OUT  = ROOT / "out"

SOURCES = ["main.c", "service.c"]
TARGET  = OUT / "leopard-rc.elf"

RUNTIME  = ["crt0.o", "libsys.cpp.o", "xgui_stubs.cpp.o",
            "constart.cpp.o", "xtuiapi.cpp.o", "krlibc.cpp.o"]
LIBALLOC = OBJ / "liballoc-x86_64.a"

PKG = {
    "pkgname": "leopard-rc",
    "pkgver":  "1.0_1",
    "arch":    "x86_64",
    "desc":    "Leopard PID1 init",
    "deps":    "leopard-base>=1.0_1",
    "install": "system/leopard/leopard-rc.elf",
    "conf":    [],
}


def rel(p):
    p = Path(p)
    if p.is_absolute():
        try: return str(p.relative_to(ROOT))
        except ValueError: return str(p)
    return str(p)


def esc(p):
    return rel(p).replace("$", "$$").replace(":", "$:").replace(" ", "$ ")


def emit_package(L, pkg, target):
    inst = pkg["install"]
    conf = " ".join(pkg["conf"])
    out  = OUT / f"{pkg['pkgname']}-{pkg['pkgver']}.{pkg['arch']}.xbps"
    L += [
        "rule stage_pkg",
        f"  command = rm -rf .pkg && mkdir -p .pkg/$$(dirname {inst}) && cp $in .pkg/{inst}",
        "",
        "rule package",
        f"  command = xbps-create -A {pkg['arch']} -n {pkg['pkgname']}-{pkg['pkgver']} "
        f"-s \"{pkg['desc']}\" -D \"{pkg['deps']}\" -c \"{conf}\" .pkg -o $out",
        "",
    ]
    L += [f"build .pkg/{inst}: stage_pkg {esc(target)}"]
    L += [f"build {esc(out)}: package .pkg/{inst}"]
    L += [f"build package: phony {esc(out)}", "default package"]


def main():
    cc   = os.environ.get("CC",  "clang")
    cxx  = os.environ.get("CXX", "clang++")
    ld   = os.environ.get("LD",  "ld")
    opt  = "-O" + os.environ.get("OPT_LEVEL", "2")
    col  = os.environ.get("DIAGNOSTICS_COLOR", "-fdiagnostics-color=always")

    common = (f"{col} {opt} -Wall -g -ffreestanding -fno-builtin -m64 -mstackrealign "
              "-fno-stack-protector -fno-exceptions -fno-strict-aliasing -fshort-wchar -nostdinc")
    c_flags   = f"{common} -std=c11   -I {rel(INC)} -I . -MMD -MP"
    cpp_flags = f"{common} -std=c++11 -I {rel(INC)} -I . -Wno-write-strings -MMD -MP"

    L = ["# leopard-rc 构建 + xbps 打包",
         "ninja_required_version = 1.10",
         f"cc = {cc}", f"cxx = {cxx}", f"ld = {ld}",
         f"c_flags = {c_flags}", f"cpp_flags = {cpp_flags}", ""]
    L += [
        "rule cc",
        "  command = mkdir -p $$(dirname $out) && $cc $c_flags -MF $out.d -c $in -o $out",
        "  depfile = $out.d", "  deps = gcc", "",
        "rule cxx",
        "  command = mkdir -p $$(dirname $out) && $cxx $cpp_flags -MF $out.d -c $in -o $out",
        "  depfile = $out.d", "  deps = gcc", "",
        "rule link",
        "  command = $ld -Ttext=0x200000 $in -o $out", "",
    ]

    app_objs = []
    for src in SOURCES:
        rule = "cc" if src.endswith(".c") else "cxx"
        obj = OUT / (src + ".o")
        L += [f"build {esc(obj)}: {rule} {esc(ROOT / src)}"]
        app_objs.append(obj)
    L += [""]

    ins = [OBJ / n for n in RUNTIME] + app_objs + [LIBALLOC]
    L += [f"build {esc(TARGET)}: link {' '.join(esc(o) for o in ins)}", ""]

    emit_package(L, PKG, TARGET)

    L += ["rule clean", "  command = rm -rf out .pkg", "build clean: clean"]
    (ROOT / "build.ninja").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("已生成 build.ninja（leopard-rc → .xbps）。构建：ninja")


if __name__ == "__main__":
    main()
