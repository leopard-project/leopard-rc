#include "service.h"
#include "xtuiapi.h"   /* xapi_* / WSTR */
#include <sys/wait.h>   /* waitpid（v5 SDK 的 syscall 封装） */

#define MAX_SERVICES 64
#define MAX_LINE     512
#define MAX_ARGS     32

typedef struct {
        char     *path;
        char     *argv[MAX_ARGS];
        int       argc;
        int       respawn;
        uint64_t  pid;
        int       active;
} Service;

static Service s_services[MAX_SERVICES];
static int     s_service_count = 0;
static const char *s_fallback_path = "/apps/system/xsh.elf";
static char       *s_empty_envp[]  = { NULL };

static int  add_service(char *, char **, int, int);
static void spawn_service(Service *);

void fallback(const char *cfg_path)
{
        xapi_Printf("LeopardRC: cannot open config %s\n", cfg_path);
        xapi_Printf("LeopardRC: falling back to %s\n", s_fallback_path);
        char *fallback_argv[2];
        fallback_argv[0] = (char *)s_fallback_path;
        fallback_argv[1] = NULL;
        if (add_service((char *)s_fallback_path, fallback_argv, 1, 1) != 0)
                xapi_Broken("LeopardRC: no config and no fallback");
}

void str2srv(char *line)
{
        char *argv[MAX_ARGS];
        int   argc = 0;
        char *tok;
        for (tok = strtok(line, " \t\r");
             tok != NULL && argc < MAX_ARGS - 1;
             tok = strtok(NULL, " \t\r"))
                argv[argc++] = tok;
        argv[argc] = NULL;
        if (argc == 0)
                return;
        if (strcmp(argv[0], "echo") == 0) {
                char   buf[MAX_LINE];
                size_t off = 0;
                for (int i = 1; i < argc && off < sizeof(buf) - 1; i++) {
                        int w = snprintf(buf + off, sizeof(buf) - off, "%s%s",
                                         argv[i], (i + 1 < argc) ? " " : "");
                        if (w < 0)
                                break;
                        off += (size_t)w;
                        if (off >= sizeof(buf) - 1)
                                break;
                }
                xapi_Printf("%s\n", buf);
        } else if (strcmp(argv[0], "sleep") == 0) {
                uint64_t ms = argc > 1 ? (uint64_t)atoi(argv[1]) : 0;
                xapi_Sleep(ms);
        } else if (strcmp(argv[0], "respawn") == 0 && argc >= 2) {
                add_service(argv[1], &argv[1], argc - 1, 1);
        } else {
                add_service(argv[0], &argv[0], argc, 0);
        }
}

void load_service(void)
{
        for (int i = 0; i < s_service_count; i++)
        {
                Service *sv = &s_services[i];
                spawn_service(sv);
                if (sv->respawn) continue;

                /* 一次性服务（如 leopard-mountd）必须跑完再继续：
                   /apps、/users 是后续服务（getty/oobe/shell）的落地位置，不能跟它们抢跑。 */
                int status = 0;
                int waited = waitpid((int)sv->pid, &status, 0);
                if (waited == (int)sv->pid)
                {
                        xapi_Printf("[leopard-rc] oneshot done %s status=%d\n", sv->path, status);
                        sv->active = 0;
                }
                else
                {
                        xapi_Printf("[leopard-rc] oneshot wait failed %s\n", sv->path);
                }
        }
}

void supervisor_loop(void)
{
        int status = 0;
        int exited = waitpid(-1, &status, 0);
        /* 没有子进程可收（ECHILD -> -1）-> 短睡，避免空转 */
        if (exited <= 0) {
                xapi_Sleep(200);
                return; //返回到下一个循环
        }
        int handled = 0;
        for (int i = 0; i < s_service_count; i++) {
                Service *sv = &s_services[i];
                if(!sv->active || sv->pid != (uint64_t)exited) continue;

                xapi_Printf("[leopard-rc] exited %s status=%d\n", sv->path, status);
                sv->active = 0;
                if (sv->respawn) {
                        xapi_Printf("[leopard-rc] respawn %s\n", sv->path);
                        spawn_service(sv);
                }
                handled = 1;
                break;
        }
        if (!handled)
                xapi_Printf("[leopard-rc] reaped unknown pid=%d\n", exited);
}

static int add_service(char *path, char **argv, int argc, int respawn)
{
        if (s_service_count >= MAX_SERVICES)
                return -1;
        Service *sv = &s_services[s_service_count++];
        sv->path    = path;
        sv->respawn = respawn;
        sv->pid     = 0;
        sv->active  = 0;
        int i;
        for (i = 0; i < argc && i < MAX_ARGS - 1; i++)
                sv->argv[i] = argv[i];
        sv->argv[i] = NULL;
        sv->argc    = i;
        return 0;
}

static void spawn_service(Service *sv)
{
        uint64_t pid = xapi_Fork();
        if (pid == 0) {
                xapi_Execve((WSTR)sv->path, (WSTR *)sv->argv, (WSTR *)s_empty_envp);
                xapi_Printf("LeopardRC: execve failed: %s\n", sv->path);
                xapi_Exit(127);
        }
        sv->pid    = pid;
        sv->active = 1;
        xapi_Printf("[leopard-rc] start %s pid=%llu\n", sv->path, (unsigned long long)pid);
}
