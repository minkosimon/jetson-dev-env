MODULE_NAME := helloworld_drv
obj-m := $(MODULE_NAME).o
$(MODULE_NAME)-objs := src/helloworld_drv.o

ccflags-y := -I$(src)/include

OUTPUT_DIR ?= ../output/default/driver
DTS_DIR    := dt

.PHONY: modules dtbo clean

modules:
	$(MAKE) -C $(KERNEL_SRC) ARCH=$(ARCH) CROSS_COMPILE=$(CROSS_COMPILE) \
		M=$(CURDIR) modules
	mkdir -p $(OUTPUT_DIR)
	cp $(MODULE_NAME).ko $(OUTPUT_DIR)/

# overlay indépendant de la carte : compatible injecté par sed depuis BOARD_COMPATIBLE
dtbo:
	mkdir -p $(OUTPUT_DIR)
	sed 's/@BOARD_COMPATIBLE@/$(BOARD_COMPATIBLE)/' $(DTS_DIR)/helloworld-overlay.dts \
		> $(OUTPUT_DIR)/helloworld-overlay.gen.dts
	$(DTC) -@ -I dts -O dtb -i $(DTS_DIR) \
		-o $(OUTPUT_DIR)/helloworld-overlay.dtbo \
		$(OUTPUT_DIR)/helloworld-overlay.gen.dts

clean:
	$(MAKE) -C $(KERNEL_SRC) ARCH=$(ARCH) CROSS_COMPILE=$(CROSS_COMPILE) \
		M=$(CURDIR) clean
	rm -rf $(OUTPUT_DIR)
