CC ?= cc
CFLAGS ?= -O2 -Wall -Wextra -pedantic
CPPFLAGS ?= -Iinclude

TARGET = AmiGet
SOURCES = src/amiget.c

.PHONY: all clean check check-m0 check-m1

all: $(TARGET)

$(TARGET): $(SOURCES) include/amiget.h
	$(CC) $(CPPFLAGS) $(CFLAGS) -o $@ $(SOURCES)

check: check-m0 check-m1

check-m0:
	python3 tools/check_m0.py

check-m1: $(TARGET)
	python3 tools/check_m1.py

clean:
	rm -f $(TARGET)
