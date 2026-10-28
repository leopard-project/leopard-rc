# PROJECT KNOWLEDGE BASE — leopard-rc

PID1 初始化系统（SysV init/RC 风格）。读 `/system/config/initrc`，fork/exec 拉起各用户态服务，
wait4 收尸并对标 respawn 的服务自动重启。基于 XAPI（`xtuiapi.h`），进程拉起用 `xapi_Fork()`+`xapi_Execve()`。

## 构建
    python3 gen_ninja.py && ninja build   # → out/leopard-rc.elf
    ninja pack                            # → out/leopard-rc-*.xbps

- 静态 ELF，依赖 `../leopard-sdk`（`include/` 头 + `obj-tui/` 运行时对象）。
- 安装位置 `/system/leopard/leopard-rc.elf`（内核 main.cpp 的 init 路径也指向这里）。

## 红线
- 不写回 OpenXSKernel/OpenXJ380；本仓库只产出用户态二进制。
- initrc 是启动期配置，必须在引导分区 `/system/config/`。
