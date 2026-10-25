# LeopardRC

XJ380（OpenXSKernel）上的 SysV init / RC 风格基本初始化系统。读取一份
`initrc` 配置文件，拉起其它用户态服务，并对服务做收尸与 `respawn` 自动重启。

## 特性

- 基于 XAPI（`xtuiapi.h`）实现，进程拉起用 `xapi_Fork()` + `xapi_Execve()`。
- 读 `initrc` 配置，支持：
  - 拉起服务：`<路径> [参数...]`
  - 退出自动重启：`respawn <路径> [参数...]`
  - 内置指令：`echo`、`sleep`
  - `#` 注释、空行
- 配置缺失时回退拉起一个 shell（`/apps/system/shell.elf`），避免系统进入"无服务"状态。
- 监督循环用 POSIX `wait4` 收尸（`wait4` 不在 XAPI 里，经 `libsys.h` 的
  `enter_syscall(SYS_WAIT4, ...)` 调用）。
- 所有输出直接使用 `xapi_Printf(...)`。

## 目录结构

```
leopardrc/
├── include/          XACT SDK 头文件（xapi.h / xtuiapi.h / libsys.h / ...）
├── main.c        入口：root 校验、读配置、解析、启动服务、进入监督循环
├── service.h     服务管理接口声明
├── service.c     服务表、fallback、解析、spawn、收尸/重启
└── initrc            配置示例（安装到 /system/config/initrc）
```

## initrc 配置格式

```
# 注释
echo <文本>                # 输出一行日志
sleep <毫秒>              # 延时
<路径> [参数...]          # 拉起一个服务（退出不重启）
respawn <路径> [参数...]  # 拉起一个服务（退出自动重启）
```

示例：

```
echo LeopardRC bootstrap start
sleep 100

respawn /.../example-daemon.elf --daemon
/apps/system/shell.elf

echo LeopardRC bootstrap done
```

## 工作原理

1. `main()` 检查当前用户必须是 `XUT_Root`，否则 `xapi_Broken()` 停机。
2. 打开 `/system/config/initrc`（可用命令行参数覆盖路径），`xapi_ReadFile` 读入缓冲。
3. 逐行解析：`echo` / `sleep` 立即执行；其余按「路径 + 参数」登记进服务表。
4. `load_service()` 对每个服务 `xapi_Fork()`，子进程 `xapi_Execve()` 替换镜像。
5. `supervisor_loop()` 循环 `wait4(-1)` 收尸：
   - 匹配到服务 → 记录退出状态，`respawn` 服务自动重启；
   - 没有子进程（`-ECHILD`）→ `xapi_Sleep(200)` 避免空转。

## 设计说明 / 依赖

- **WSTR 即 `char*`**：SDK 头 `stdint.h` 中 `typedef char* WSTR`，所有 XAPI
  字符串参数实为窄字符串，故代码统一使用普通字符串字面量（不用 `L"..."`）。
- **`wait4` 不在 XAPI 内**：它属于内核的 POSIX/Linux ABI 层，通过
  `enter_syscall(SYS_WAIT4, ...)` 调用，是 init 收尸与重启能力的关键。
- **已知内核限制**（来自 `OpenXSKernel`）：
  - `mount(165)` / `umount2(166)` / `pivot_root(155)` 已声明编号，但
    `kernel/syscall/syscall.cpp` 的 dispatch 尚未接线，调用会 `-ENOSYS`。
  - `xapi_GetTaskList` / `xapi_KillProcess` 当前为空壳（`-ENOSYS`），
    需要杀进程请用 POSIX `kill(62)`。
