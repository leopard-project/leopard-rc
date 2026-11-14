#include "xtuiapi.h"
#include "service.h"

#define CFG_CAP (128 * 1024)

/* 非 const：str2srv()/解析会原地改写这块缓冲 */
static char s_cfg[CFG_CAP];

static void init_main(const char *);

int main(int argc, char *argv[], char *envp[])
{
        (void)envp;

        /* start booting */
        const char *cfg_path = "/system/config/initrc";
        if (argc > 1)
                cfg_path = argv[1];

        /* Capability gate: the init process needs ordinary read, system
         * directory traversal and system-file read.  The policy data decides
         * which grade gets those bits; do not special-case a user type. */
        UserPermisson perms;
        if (xapi_GetCurrentPermissions(&perms) != 0 ||
            !perms.ReadFile || !perms.VisitSysDir || !perms.ReadSysFile) {
                xapi_Broken("LeopardRC: insufficient permissions for init");
        }

        init_main(cfg_path);
        return 0;
}

static void init_main(const char *cfg_path)
{
        xapi_Printf("LeopardRC: init started, config=%s\n", cfg_path);
        XFILE *fp = xapi_OpenFile((WSTR)cfg_path);
        if (fp == NULL) {
                fallback(cfg_path);
                goto skip_load;
        }
        uint64_t len = fp->length;
        if (len >= CFG_CAP)
                len = CFG_CAP - 1;
        uint64_t got = xapi_ReadFile((WSTR)cfg_path, s_cfg, len, 0);
        xapi_CloseFile(fp);
        s_cfg[got] = '\0';
        xapi_Printf("LeopardRC: read %llu bytes\n", (unsigned long long)got);

        char *line = s_cfg;
        while (*line) {
                char *nl = strchr(line, '\n');
                if (nl)
                        *nl = '\0';
                while (*line == ' ' || *line == '\t' || *line == '\r')
                        line++;
                if (*line != '\0' && *line != '#')
                        str2srv(line);
                if (!nl)
                        break;
                line = nl + 1;
        }
        load_service();
skip_load:
        for (;;)
                supervisor_loop();
}
