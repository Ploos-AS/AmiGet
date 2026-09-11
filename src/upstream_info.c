#include <stdio.h>

#include "amiget.h"
#include "aminet_index.h"

int amiget_upstream_info(const char *cache_path, const char *name)
{
    AminetIndexEntry entry;
    char artifact[AMIGET_MAX_PATH];
    int rc;

    rc = aminet_lookup_cache(cache_path, name, &entry);
    if (rc == 1)
        return 1;
    if (rc == 2) {
        fprintf(stderr, "AmiGet: Aminet artifact not found: %s\n", name);
        return 2;
    }

    if (!aminet_format_artifact_path(&entry, artifact, sizeof(artifact))) {
        fprintf(stderr, "AmiGet: Aminet artifact path too long\n");
        return 1;
    }

    printf("Name:        %s\n", entry.name);
    printf("Source:      aminet\n");
    printf("Directory:   %s\n", entry.directory);
    printf("Artifact:    %s\n", artifact);
    printf("Size:        %s\n", entry.size);
    printf("Age:         %s\n", entry.age);
    printf("Description: %s\n", entry.description);
    printf("Checksum:    unavailable-in-index\n");
    printf("Install:     not-planned\n");
    return 0;
}
