CC         := $(CROSS_COMPILE)gcc
OUTPUT_DIR ?= ../output/default/app
BIN        := $(OUTPUT_DIR)/helloworld_app
SRC        := src/helloworld_app.c
CFLAGS     := -Wall -O2 -Iinclude -I../driver/include

.PHONY: all host clean

all: $(BIN)

$(BIN): $(SRC) | $(OUTPUT_DIR)
	$(CC) $(CFLAGS) -o $@ $<

$(OUTPUT_DIR):
	mkdir -p $@

# build natif hôte (hors toolchain Jetson) pour tests unitaires rapides
host:
	mkdir -p $(OUTPUT_DIR)
	gcc $(CFLAGS) -o $(OUTPUT_DIR)/helloworld_app_host $(SRC)

clean:
	rm -rf $(OUTPUT_DIR)
