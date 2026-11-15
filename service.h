#pragma once

void rc_log(const char *format, ...);

void fallback(const char *cfg_path);
void str2srv(char *);
void load_service();
void supervisor_loop();
