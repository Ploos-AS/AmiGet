#include <stdio.h>
#include <string.h>

#include "aminet_index.h"

static void usage(const char *prog)
{
    fprintf(stderr,
            "Usage:\n"
            "  %s build <INDEX> <cache>\n"
            "  %s search <cache> <term>\n",
            prog, prog);
}

int main(int argc, char **argv)
{
    if (argc == 4 && strcmp(argv[1], "build") == 0)
        return aminet_build_cache(argv[2], argv[3]);

    if (argc == 4 && strcmp(argv[1], "search") == 0)
        return aminet_search_cache(argv[2], argv[3]);

    usage(argv[0]);
    return 1;
}
