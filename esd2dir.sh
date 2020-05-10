#/bin/bash

set -eux

# ESD extraction for Windows 10 Enterprise x64
# Based on instructions from https://deploymentresearch.com/Research/Post/399/How-to-REALLY-create-a-Windows-10-ISO-no-3rd-party-tools-needed
# Assumes wimlib utilities are accessible in $PATH

ESD_PATH=$1
OUTPUT_PATH=$2

mkdir "$OUTPUT_PATH" || true

# Extract "Windows Setup Media" image into target dir
wimapply "$ESD_PATH" 1 "$OUTPUT_PATH"

# Create boot.wim from "Microsoft Windows PE (x64)" image
# TODO: Try using "recovery" or --solid compression
wimexport "$ESD_PATH" 2 "$OUTPUT_PATH"/sources/boot.wim --compress=maximum --boot

# Append "Microsoft Windows Setup (x64)" image to boot.wim
# TODO: Try using "recovery" or --solid compression
wimexport "$ESD_PATH" 3 "$OUTPUT_PATH"/sources/boot.wim --compress=maximum --boot

# Display info from created boot.wim
wiminfo "$OUTPUT_PATH"/sources/boot.wim

# Create install.wim based upon "Windows 10 Enterprise" image
wimexport "$ESD_PATH" 6 "$OUTPUT_PATH"/sources/install.wim --compress=LZMS

# Display info from created boot.wim
wiminfo "$OUTPUT_PATH"/sources/install.wim
