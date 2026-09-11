#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "amiget.h"
#include "aminet_index.h"

static void trim(char *s)
{
    char *start;
    char *end;

    if (s == NULL || *s == '\0')
        return;
    start = s;
    while (*start != '\0' && isspace((unsigned char)*start))
        start++;
    if (start != s)
        memmove(s, start, strlen(start) + 1);
    end = s + strlen(s);
    while (end > s && isspace((unsigned char)end[-1]))
        end--;
    *end = '\0';
}

static int copy_field(char *dst, size_t dst_size, const char *value)
{
    size_t len;
    if (dst == NULL || value == NULL || dst_size == 0)
        return 0;
    len = strlen(value);
    if (len >= dst_size)
        return 0;
    memcpy(dst, value, len + 1);
    return 1;
}

static int set_field(AmiGetPackage *pkg, const char *key, const char *value)
{
    if (strcmp(key, "format") == 0) return copy_field(pkg->format, sizeof(pkg->format), value);
    if (strcmp(key, "name") == 0) return copy_field(pkg->name, sizeof(pkg->name), value);
    if (strcmp(key, "version") == 0) return copy_field(pkg->version, sizeof(pkg->version), value);
    if (strcmp(key, "summary") == 0) return copy_field(pkg->summary, sizeof(pkg->summary), value);
    if (strcmp(key, "source") == 0) return copy_field(pkg->source, sizeof(pkg->source), value);
    if (strcmp(key, "aminet_path") == 0) return copy_field(pkg->aminet_path, sizeof(pkg->aminet_path), value);
    if (strcmp(key, "os_min") == 0) return copy_field(pkg->os_min, sizeof(pkg->os_min), value);
    if (strcmp(key, "cpu_min") == 0) return copy_field(pkg->cpu_min, sizeof(pkg->cpu_min), value);
    if (strcmp(key, "archive") == 0) return copy_field(pkg->archive, sizeof(pkg->archive), value);
    if (strcmp(key, "sha256") == 0) return copy_field(pkg->sha256, sizeof(pkg->sha256), value);
    if (strcmp(key, "install_recipe") == 0) return copy_field(pkg->install_recipe, sizeof(pkg->install_recipe), value);
    return 1;
}

static int package_valid(const AmiGetPackage *pkg)
{
    return pkg->format[0] != '\0' && pkg->name[0] != '\0' &&
           pkg->version[0] != '\0' && pkg->summary[0] != '\0' &&
           pkg->source[0] != '\0' && pkg->aminet_path[0] != '\0' &&
           pkg->os_min[0] != '\0' && pkg->cpu_min[0] != '\0' &&
           pkg->archive[0] != '\0' && pkg->sha256[0] != '\0' &&
           pkg->install_recipe[0] != '\0';
}

int amiget_load_package(const char *path, AmiGetPackage *pkg)
{
    FILE *fp;
    char line[AMIGET_MAX_LINE];

    if (path == NULL || pkg == NULL)
        return 0;
    memset(pkg, 0, sizeof(*pkg));
    fp = fopen(path, "r");
    if (fp == NULL)
        return 0;

    while (fgets(line, sizeof(line), fp) != NULL) {
        char *eq;
        char *key;
        char *value;
        trim(line);
        if (line[0] == '\0' || line[0] == '#')
            continue;
        eq = strchr(line, '=');
        if (eq == NULL) {
            fclose(fp);
            return 0;
        }
        *eq = '\0';
        key = line;
        value = eq + 1;
        trim(key);
        trim(value);
        if (key[0] == '\0' || value[0] == '\0' || !set_field(pkg, key, value)) {
            fclose(fp);
            return 0;
        }
    }
    fclose(fp);
    return package_valid(pkg);
}

static int text_contains_ci(const char *text, const char *needle)
{
    size_t i, j, text_len, needle_len;
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

static int catalogue_dir(const char *catalogue_path, char *out, size_t out_size)
{
    const char *slash1 = strrchr(catalogue_path, '/');
    const char *slash2 = strrchr(catalogue_path, ':');
    const char *slash = slash1;
    size_t len;

    if (slash2 != NULL && (slash == NULL || slash2 > slash))
        slash = slash2;
    if (slash == NULL) {
        if (out_size < 2) return 0;
        strcpy(out, ".");
        return 1;
    }
    len = (size_t)(slash - catalogue_path + 1);
    if (len >= out_size) return 0;
    memcpy(out, catalogue_path, len);
    out[len] = '\0';
    return 1;
}

static int join_package_path(const char *catalogue_path, const char *entry,
                             char *out, size_t out_size)
{
    char dir[AMIGET_MAX_PATH];
    size_t dir_len;
    int needs_sep;
    if (!catalogue_dir(catalogue_path, dir, sizeof(dir))) return 0;
    dir_len = strlen(dir);
    needs_sep = dir_len > 0 && dir[dir_len - 1] != '/' && dir[dir_len - 1] != ':';
    if (strlen(dir) + (needs_sep ? 1U : 0U) + strlen(entry) + 1U > out_size) return 0;
    strcpy(out, dir);
    if (needs_sep) strcat(out, "/");
    strcat(out, entry);
    return 1;
}

static int load_catalogue_entry(const char *catalogue_path, const char *entry,
                                AmiGetPackage *pkg)
{
    char package_path[AMIGET_MAX_PATH];
    if (!join_package_path(catalogue_path, entry, package_path, sizeof(package_path))) return 0;
    return amiget_load_package(package_path, pkg);
}

static int next_catalogue_entry(FILE *fp, char *entry, size_t entry_size)
{
    char line[AMIGET_MAX_LINE];
    while (fgets(line, sizeof(line), fp) != NULL) {
        trim(line);
        if (line[0] == '\0' || line[0] == '#') continue;
        if (strlen(line) >= entry_size) return -1;
        strcpy(entry, line);
        return 1;
    }
    return 0;
}

int amiget_list(const char *catalogue_path)
{
    FILE *fp = fopen(catalogue_path, "r");
    char entry[AMIGET_MAX_PATH];
    int rc;
    if (fp == NULL) {
        fprintf(stderr, "AmiGet: cannot open catalogue: %s\n", catalogue_path);
        return 1;
    }
    while ((rc = next_catalogue_entry(fp, entry, sizeof(entry))) > 0) {
        AmiGetPackage pkg;
        if (!load_catalogue_entry(catalogue_path, entry, &pkg)) {
            fprintf(stderr, "AmiGet: invalid package entry: %s\n", entry);
            fclose(fp);
            return 1;
        }
        printf("%-20s %-12s %s\n", pkg.name, pkg.version, pkg.summary);
    }
    fclose(fp);
    if (rc < 0) {
        fprintf(stderr, "AmiGet: catalogue entry too long\n");
        return 1;
    }
    return 0;
}

int amiget_search(const char *catalogue_path, const char *term)
{
    FILE *fp = fopen(catalogue_path, "r");
    char entry[AMIGET_MAX_PATH];
    int rc;
    int matches = 0;
    if (fp == NULL) {
        fprintf(stderr, "AmiGet: cannot open catalogue: %s\n", catalogue_path);
        return 1;
    }
    while ((rc = next_catalogue_entry(fp, entry, sizeof(entry))) > 0) {
        AmiGetPackage pkg;
        if (!load_catalogue_entry(catalogue_path, entry, &pkg)) {
            fprintf(stderr, "AmiGet: invalid package entry: %s\n", entry);
            fclose(fp);
            return 1;
        }
        if (text_contains_ci(pkg.name, term) || text_contains_ci(pkg.summary, term)) {
            printf("[curated] %-20s %-12s %s\n", pkg.name, pkg.version, pkg.summary);
            matches++;
        }
    }
    fclose(fp);
    if (rc < 0) {
        fprintf(stderr, "AmiGet: catalogue entry too long\n");
        return 1;
    }
    return matches > 0 ? 0 : 2;
}

static int file_exists(const char *path)
{
    FILE *fp = fopen(path, "r");
    if (fp == NULL) return 0;
    fclose(fp);
    return 1;
}

int amiget_search_combined(const char *catalogue_path, const char *cache_path,
                           const char *term, int cache_required)
{
    int curated_rc;
    int aminet_rc = 2;

    curated_rc = amiget_search(catalogue_path, term);
    if (curated_rc == 1)
        return 1;

    if (cache_path != NULL && file_exists(cache_path)) {
        printf("-- Aminet upstream --\n");
        aminet_rc = aminet_search_cache(cache_path, term);
        if (aminet_rc == 1)
            return 1;
    } else if (cache_required) {
        fprintf(stderr, "AmiGet: cannot open Aminet cache: %s\n", cache_path);
        return 1;
    }

    if (curated_rc == 0 || aminet_rc == 0)
        return 0;
    return 2;
}

int amiget_info(const char *catalogue_path, const char *name)
{
    FILE *fp = fopen(catalogue_path, "r");
    char entry[AMIGET_MAX_PATH];
    int rc;
    if (fp == NULL) {
        fprintf(stderr, "AmiGet: cannot open catalogue: %s\n", catalogue_path);
        return 1;
    }
    while ((rc = next_catalogue_entry(fp, entry, sizeof(entry))) > 0) {
        AmiGetPackage pkg;
        if (!load_catalogue_entry(catalogue_path, entry, &pkg)) {
            fprintf(stderr, "AmiGet: invalid package entry: %s\n", entry);
            fclose(fp);
            return 1;
        }
        if (strcmp(pkg.name, name) == 0) {
            printf("Name:           %s\n", pkg.name);
            printf("Version:        %s\n", pkg.version);
            printf("Summary:        %s\n", pkg.summary);
            printf("Source:         %s\n", pkg.source);
            printf("Aminet path:    %s\n", pkg.aminet_path);
            printf("Minimum OS:     %s\n", pkg.os_min);
            printf("Minimum CPU:    %s\n", pkg.cpu_min);
            printf("Archive:        %s\n", pkg.archive);
            printf("SHA-256:        %s\n", pkg.sha256);
            printf("Install recipe: %s\n", pkg.install_recipe);
            fclose(fp);
            return 0;
        }
    }
    fclose(fp);
    if (rc < 0) {
        fprintf(stderr, "AmiGet: catalogue entry too long\n");
        return 1;
    }
    fprintf(stderr, "AmiGet: package not found: %s\n", name);
    return 2;
}

static void usage(const char *prog)
{
    fprintf(stderr,
            "Usage:\n"
            "  %s version\n"
            "  %s list [catalogue]\n"
            "  %s search <term> [catalogue] [--aminet <cache>]\n"
            "  %s info <package> [catalogue]\n",
            prog, prog, prog, prog);
}

int main(int argc, char **argv)
{
    const char *catalogue;
    const char *cache;
    int cache_required;

    if (argc < 2) {
        usage(argv[0]);
        return 1;
    }
    if (strcmp(argv[1], "version") == 0) {
        printf("AmiGet %s\n", AMIGET_VERSION);
        return 0;
    }
    if (strcmp(argv[1], "list") == 0) {
        catalogue = argc >= 3 ? argv[2] : "packages/catalogue.lst";
        return amiget_list(catalogue);
    }
    if (strcmp(argv[1], "search") == 0) {
        if (argc < 3) {
            usage(argv[0]);
            return 1;
        }
        catalogue = "packages/catalogue.lst";
        cache = "cache/aminet.cache";
        cache_required = 0;
        if (argc >= 4 && strcmp(argv[3], "--aminet") != 0)
            catalogue = argv[3];
        if (argc >= 4 && strcmp(argv[3], "--aminet") == 0) {
            if (argc < 5) { usage(argv[0]); return 1; }
            cache = argv[4];
            cache_required = 1;
        } else if (argc >= 5 && strcmp(argv[4], "--aminet") == 0) {
            if (argc < 6) { usage(argv[0]); return 1; }
            cache = argv[5];
            cache_required = 1;
        }
        return amiget_search_combined(catalogue, cache, argv[2], cache_required);
    }
    if (strcmp(argv[1], "info") == 0) {
        if (argc < 3) {
            usage(argv[0]);
            return 1;
        }
        catalogue = argc >= 4 ? argv[3] : "packages/catalogue.lst";
        return amiget_info(catalogue, argv[2]);
    }
    usage(argv[0]);
    return 1;
}
