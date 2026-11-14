# PROJECT KNOWLEDGE BASE — leopard-rc

PID1 初始化系统（SysV init/RC 风格）。读 `/system/config/initrc`，fork/exec 拉起各用户态服务，
`waitpid()` 收尸并对标 respawn 的服务自动重启。基于 XAPI（`xtuiapi.h`），进程拉起用 `xapi_Fork()`+`xapi_Execve()`。

## 构建
    python3 gen_ninja.py && ninja build   # → out/leopard-rc.elf
    ninja pack                            # → out/leopard-rc-*.xbps

- 静态 ELF，依赖 `../XJ380-SDK/out/crt`（`include/` 头 + `lib/x86_64/` 启动对象与 `libxact.a`）。
- 安装位置 `/system/leopard/leopard-rc.elf`（内核 main.cpp 的 init 路径也指向这里）。
- 启动权限看 `xapi_QueryFileAccess(..., XFA_READ)`（permission policy），不再判断 `UserType == Root`。

## 红线
- 不写回 OpenXSKernel/OpenXJ380；本仓库只产出用户态二进制。
- initrc 是启动期配置，必须在引导分区 `/system/config/`。

## 加载语义（install-closure 后）
- `respawn <path>` → 后台拉起，收尸后自动重启。
- `<path>`（裸路径，无关键字）→ **一次性服务**：`load_service()` 会 `waitpid()` 等它跑完再继续下一个，
  这样 `leopard-mountd` 挂好 `/apps`、`/users` 之后才拉起 getty/oobe，避免服务抢跑。
- 子进程环境变量为空（`envp = { NULL }`）：服务二进制必须用绝对路径，PATH 无效。
- initrc 缺失时回退 `respawn /apps/system/xsh.elf`（该二进制当前无包，会无限重启）——装机流程
  必须保证 `leopard-base` 的 `system/config/initrc` 就位。
