#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "aminet_index.h"

static int contains_ci(const char *text, const char *needle)
{
    size_t i;
    size_t j;
    size_t text_len;
    size_t needle_len;

    if (text == NULL || needle == NULL)
        return 0;

    text_len = strlen(text);
    needle_len = strlen(needle);
    if (needle_len == 0)
        return 1;
    if (needle_len > text_len)
        return 0;

    for (i = 0; i + needle_len <= text_len; i++) {
        for (j = 0; j < needle_len; j++) {
            if (tolower((unsigned char)text[i + j]) !=
                tolower((unsigned char)needle[j]))
                break;
        }
        if (j == needle_len)
            return 1;
    }

    return 0;
}

static int valid_size_field(const char *value)
{
    const unsigned char *p = (const unsigned char *)value;

    if (p == NULL || !isdigit(*p))
        return 0;
    while (isdigit(*p))
        p++;
    if (*p == '\0')
        return 1;
    return (p[0] == 'K' || p[0] == 'k' || p[0] == 'M' || p[0] == 'm' ||
            p[0] == 'G' || p[0] == 'g') && p[1] == '\0';
}

static int valid_age_field(const char *value)
{
    const unsigned char *p = (const unsigned char *)value;

    if (p == NULL || !isdigit(*p))
        return 0;
    while (isdigit(*p))
        p++;
    if (*p == '\0')
        return 1;
    return p[0] == '+' && p[1] == '\0';
}

int aminet_parse_index_line(const char *line, AminetIndexEntry *entry)
{
    int fields;

    if (line == NULL || entry == NULL)
        return 0;

    while (*line != '\0' && isspace((unsigned char)*line))
        line++;

    if (*line == '\0' || *line == '#' || *line == ';')
        return 0;

    memset(entry, 0, sizeof(*entry));

    fields = sscanf(line,
                    "%127s %127s %31s %31s %255[^\r\n]",
                    entry->name,
                    entry->directory,
                    entry->size,
                    entry->age,
                    entry->description);

    if (fields < 5)
        return 0;

    if (strchr(entry->name, '/') != NULL || strchr(entry->directory, ':') != NULL)
        return 0;
    if (strchr(entry->directory, '/') == NULL)
        return 0;
    if (!valid_size_field(entry->size))
        return 0;
    if (!valid_age_field(entry->age))
        return 0;

    return 1;
}

static int write_cache_entry(FILE *out, const AminetIndexEntry *entry)
{
    return fprintf(out, "%s\t%s\t%s\t%s\t%s\n",
                   entry->name,
                   entry->directory,
                   entry->size,
                   entry->age,
                   entry->description) >= 0;
}

int aminet_build_cache(const char *index_path, const char *cache_path)
{
    FILE *in;
    FILE *out;
    char line[1024];
    unsigned long accepted;

    if (index_path == NULL || cache_path == NULL)
        return 1;

    in = fopen(index_path, "r");
    if (in == NULL) {
        fprintf(stderr, "AmiGet: cannot open Aminet INDEX: %s\n", index_path);
        return 1;
    }

    out = fopen(cache_path, "w");
    if (out == NULL) {
        fclose(in);
        fprintf(stderr, "AmiGet: cannot create Aminet cache: %s\n", cache_path);
        return 1;
    }

    accepted = 0;
    while (fgets(line, sizeof(line), in) != NULL) {
        AminetIndexEntry entry;
        if (aminet_parse_index_line(line, &entry)) {
            if (!write_cache_entry(out, &entry)) {
                fclose(in);
                fclose(out);
                remove(cache_path);
                return 1;
            }
            accepted++;
        }
    }

    if (ferror(in) || fclose(in) != 0 || fclose(out) != 0) {
        remove(cache_path);
        return 1;
    }

    if (accepted == 0) {
        remove(cache_path);
        fprintf(stderr, "AmiGet: Aminet INDEX contained no usable entries\n");
        return 1;
    }

    printf("AmiGet: indexed %lu Aminet entries\n", accepted);
    return 0;
}

int aminet_update_cache_atomic(const char *index_path, const char *cache_path)
{
    char temp_path[1024];
    size_t cache_len;
    int rc;

    if (index_path == NULL || cache_path == NULL)
        return 1;

    cache_len = strlen(cache_path);
    if (cache_len + 5 >= sizeof(temp_path)) {
        fprintf(stderr, "AmiGet: cache path too long\n");
        return 1;
    }

    strcpy(temp_path, cache_path);
    strcat(temp_path, ".new");
    remove(temp_path);

    rc = aminet_build_cache(index_path, temp_path);
    if (rc != 0) {
        remove(temp_path);
        return rc;
    }

    if (rename(temp_path, cache_path) != 0) {
        fprintf(stderr,
                "AmiGet: cannot replace cache atomically: %s (temporary cache kept at %s)\n",
                cache_path, temp_path);
        return 1;
    }

    printf("AmiGet: cache updated: %s\n", cache_path);
    return 0;
}

static int split_cache_line(char *line, AminetIndexEntry *entry)
{
    char *fields[5];
    char *p;
    int i;

    fields[0] = line;
    for (i = 1; i < 5; i++) {
        p = strchr(fields[i - 1], '\t');
        if (p == NULL)
            return 0;
        *p = '\0';
        fields[i] = p + 1;
    }

    p = fields[4] + strlen(fields[4]);
    while (p > fields[4] && (p[-1] == '\n' || p[-1] == '\r'))
        *--p = '\0';

    if (strlen(fields[0]) >= sizeof(entry->name) ||
        strlen(fields[1]) >= sizeof(entry->directory) ||
        strlen(fields[2]) >= sizeof(entry->size) ||
        strlen(fields[3]) >= sizeof(entry->age) ||
        strlen(fields[4]) >= sizeof(entry->description))
        return 0;

    strcpy(entry->name, fields[0]);
    strcpy(entry->directory, fields[1]);
    strcpy(entry->size, fields[2]);
    strcpy(entry->age, fields[3]);
    strcpy(entry->description, fields[4]);
    return 1;
}

int aminet_search_cache(const char *cache_path, const char *term)
{
    FILE *fp;
    char line[1024];
    int matches;

    if (cache_path == NULL || term == NULL)
        return 1;

    fp = fopen(cache_path, "r");
    if (fp == NULL) {
        fprintf(stderr, "AmiGet: cannot open Aminet cache: %s\n", cache_path);
        return 1;
    }

    matches = 0;
    while (fgets(line, sizeof(line), fp) != NULL) {
        AminetIndexEntry entry;
        memset(&entry, 0, sizeof(entry));
        if (!split_cache_line(line, &entry)) {
            fclose(fp);
            fprintf(stderr, "AmiGet: malformed Aminet cache\n");
            return 1;
        }

        if (contains_ci(entry.name, term) ||
            contains_ci(entry.directory, term) ||
            contains_ci(entry.description, term)) {
            printf("%-24s %-16s %-8s %s\n",
                   entry.name, entry.directory, entry.size, entry.description);
            matches++;
        }
    }

    fclose(fp);
    return matches > 0 ? 0 : 2;
}
