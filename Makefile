CC ?= cc
CFLAGS ?= -O2 -Wall -Wextra -pedantic
CPPFLAGS ?= -Iinclude

TARGET = AmiGet
INDEX_TARGET = AmiGetIndex
SOURCES = src/amiget.c
INDEX_SOURCES = src/aminet_index.c tools/aminet_index_main.c

.PHONY: all clean check check-m0 check-m1 check-m2

all: $(TARGET) $(INDEX_TARGET)

$(TARGET): $(SOURCES) include/amiget.h
	$(CC) $(CPPFLAGS) $(CFLAGS) -o $@ $(SOURCES)

$(INDEX_TARGET): $(INDEX_SOURCES) include/aminet_index.h
	$(CC) $(CPPFLAGS) $(CFLAGS) -o $@ $(INDEX_SOURCES)

check: check-m0 check-m1 check-m2

check-m0:
	python3 tools/check_m0.py

check-m1: $(TARGET)
	python3 tools/check_m1.py

check-m2: $(INDEX_TARGET)
	python3 tools/check_m2.py

clean:
	rm -f $(TARGET) $(INDEX_TARGET)
