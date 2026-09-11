#ifndef AMIGET_H
#define AMIGET_H

#define AMIGET_VERSION "0.3.0-m3.2"
#define AMIGET_MAX_LINE 512
#define AMIGET_MAX_FIELD 256
#define AMIGET_MAX_PATH 512

typedef struct AmiGetPackage {
    char format[16];
    char name[64];
    char version[64];
    char summary[AMIGET_MAX_FIELD];
    char source[32];
    char aminet_path[AMIGET_MAX_FIELD];
    char os_min[32];
    char cpu_min[32];
    char archive[32];
    char sha256[80];
    char install_recipe[64];
} AmiGetPackage;

int amiget_load_package(const char *path, AmiGetPackage *pkg);
int amiget_list(const char *catalogue_path);
int amiget_search(const char *catalogue_path, const char *term);
int amiget_search_combined(const char *catalogue_path, const char *cache_path,
                           const char *term, int cache_required);
int amiget_info(const char *catalogue_path, const char *name);
int amiget_upstream_info(const char *cache_path, const char *name);

#endif
