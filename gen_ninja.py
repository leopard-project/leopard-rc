#!/usr/bin/env python3
"""leopard-rc 构建 + xbps 打包（build / pack 两个 target）。"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent          # leopard-rc/
SDK  = ROOT / ".." / "leopard-sdk"              # SDK 根（目录名若不同，改这里）
INC  = SDK / "include"
OBJ  = SDK / "obj-tui"
OUT  = ROOT / "out"

SOURCES = ["main.c", "service.c"]
TARGET  = OUT / "leopard-rc.elf"

# SDK 运行时，链接顺序：crt0 入口 → 运行时 → 应用 → liballoc
RUNTIME  = ["crt0.o", "libsys.cpp.o", "xgui_stubs.cpp.o",
            "constart.cpp.o", "xtuiapi.cpp.o", "krlibc.cpp.o"]
LIBALLOC = OBJ / "liballoc-x86_64.a"

# ---- xbps 包配置 ----
PKG = {
    "pkgname": "leopard-rc",
    "pkgver":  "1.0_1",                          # version_revision
    "arch":    "x86_64",
    "desc":    "Leopard PID1 init",
    "deps":    "leopard-base>=1.0_1",            # 运行时依赖（仅元数据，装时才校验）
    "install": "system/leopard/leopard-rc.elf",  # 安装位置（相对 /，无前导斜杠）
    "conf":    [],                               # conf 文件，可留空
}


def rel(p):
    p = Path(p)
    if p.is_absolute():
        try:
            return str(p.relative_to(ROOT))
        except ValueError:
            return str(p)
    return str(p)


def esc(p):
    return rel(p).replace("$", "$$").replace(":", "$:").replace(" ", "$ ")


def emit_package(L, pkg, target):
    inst = pkg["install"]
    conf = " ".join(pkg["conf"])
    out  = OUT / f"{pkg['pkgname']}-{pkg['pkgver']}.{pkg['arch']}.xbps"

    extra = ""
    if pkg["deps"]:
        extra += f' -D "{pkg["deps"]}"'
    if conf:
        extra += f' -c "{conf}"'

    L += [
        "rule stage_pkg",
        f"  command = rm -rf .pkg && mkdir -p .pkg/$$(dirname {inst}) && cp $in .pkg/{inst}",
        "",
        "rule package",
        f"  command = xbps-create -A {pkg['arch']} -n {pkg['pkgname']}-{pkg['pkgver']} "
        f"-s \"{pkg['desc']}\"{extra} .pkg -o $out",
        "",
    ]
    L += [f"build .pkg/{inst}: stage_pkg {esc(target)}"]
    L += [f"build {esc(out)}: package .pkg/{inst}"]
    L += [f"build build: phony {esc(target)}"]
    L += [f"build pack: phony {esc(out)}"]
    L += ["default build"]


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

    L = ["# leopard-rc 构建 + xbps 打包", "ninja_required_version = 1.10",
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
    print("已生成 build.ninja（leopard-rc）。用法：ninja build / ninja pack")


if __name__ == "__main__":
    main()
