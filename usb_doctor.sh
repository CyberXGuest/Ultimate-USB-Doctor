#!/bin/bash
# USB Doctor Dependencies Installer

echo "🔧 Installing USB Doctor Dependencies..."
echo "========================================="

# Update package list
echo "📡 Updating package list..."
sudo apt update

# Install system packages
echo "📦 Installing system packages..."
sudo apt install -y \
    python3 \
    python3-pip \
    python3-tk \
    python3-venv \
    python3-dev \
    dosfstools \
    ntfs-3g \
    exfatprogs \
    e2fsprogs \
    xfsprogs \
    btrfs-progs \
    f2fs-tools \
    parted \
    gdisk \
    hdparm \
    sdparm \
    smartmontools \
    util-linux \
    udev \
    usbutils \
    lsof \
    rsync \
    p7zip-full \
    unzip \
    zip \
    udisks2 \
    udftools \
    mtools

# Install Python packages
echo "🐍 Installing Python packages..."
pip3 install psutil

echo ""
echo "✅ All dependencies installed successfully!"
echo ""
echo "📋 To run USB Doctor:"
echo "   sudo python3 usb_doctor.py"
