#ifndef AMINET_INDEX_H
#define AMINET_INDEX_H

#include <stddef.h>

#define AMINET_NAME_MAX 128
#define AMINET_DIR_MAX 128
#define AMINET_SIZE_MAX 32
#define AMINET_AGE_MAX 32
#define AMINET_DESC_MAX 256

typedef struct AminetIndexEntry {
    char name[AMINET_NAME_MAX];
    char directory[AMINET_DIR_MAX];
    char size[AMINET_SIZE_MAX];
    char age[AMINET_AGE_MAX];
    char description[AMINET_DESC_MAX];
} AminetIndexEntry;

int aminet_parse_index_line(const char *line, AminetIndexEntry *entry);
int aminet_build_cache(const char *index_path, const char *cache_path);
int aminet_update_cache_atomic(const char *index_path, const char *cache_path);
int aminet_search_cache(const char *cache_path, const char *term);
int aminet_lookup_cache(const char *cache_path, const char *name,
                        AminetIndexEntry *entry);
int aminet_format_artifact_path(const AminetIndexEntry *entry,
                                char *out, size_t out_size);

#endif
