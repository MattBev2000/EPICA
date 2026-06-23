#!/bin/bash

# Prompt for overlay name (without .dtbo extension)
read -p "Enter the overlay name (without .dtbo extension, e.g., pl): " OVERLAY_NAME

# Add .dtbo extension to overlay name
DTBO_FILE="${OVERLAY_NAME}.dtbo"

# Prompt for .bin file name
read -p "Enter the .bin file name (e.g., design_1_wrapper.bin): " BIN_FILE

# Copy files to /lib/firmware
sudo cp "$DTBO_FILE" "$BIN_FILE" /lib/firmware/

# Load the FPGA bitstream
sudo sh -c "echo '$BIN_FILE' > /sys/class/fpga_manager/fpga0/firmware"

# Check if device tree overlay directory exists, if not create it
OVERLAY_DIR="/sys/kernel/config/device-tree/overlays/$OVERLAY_NAME"
if [ ! -d "$OVERLAY_DIR" ]; then
    sudo mkdir -p "$OVERLAY_DIR"
    echo "Created overlay directory: $OVERLAY_DIR"
else
    echo "Overlay directory already exists: $OVERLAY_DIR, skipping creation."
fi

# Apply the device tree overlay
sudo sh -c "echo '$DTBO_FILE' > $OVERLAY_DIR/path"

echo "FPGA bitstream and