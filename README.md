# Ultimate USB Doctor Suite

A comprehensive, all-in-one graphical toolkit for advanced USB drive management, repair, and customization on Kali Linux and other Debian-based systems.

## Overview

This suite provides a complete solution for managing, diagnosing, repairing, and customizing USB drives. It combines the features of four powerful tools into one unified interface, offering over 100 functionalities for both casual users and professionals.

## Included Tools & Features

### 1. USB Doctor (`usb_doctor.py`)
The flagship all-in-one tool with complete USB management capabilities.

*   **Detection & Information**: Detects all connected USB drives, displays model, vendor, size, UUID, filesystem, and health status.
*   **Formatting & Repair**: Supports formatting with FAT32, NTFS, exFAT, EXT4, XFS, BTRFS, and more. Includes filesystem repair, boot sector repair, and bad block management.
*   **Security**: Secure wipe with multiple passes (random/zero/pattern), enable/disable write protection.
*   **Partition Management**: Create, delete, resize partitions; convert between MBR and GPT.
*   **Unlock & Fix**: Force unmount, kill processes using the drive, reset USB port.
*   **Customization**: Change volume label, model, vendor, and serial number.
*   **Health Monitoring**: Detailed SMART health checks and reports.
*   **Backup & Restore**: Full state backup and restore for drives.
*   sudo python3 usb_doctor.py

### 2. USB Manager Ultra (`usb_manager_ultra.py`)
The core management tool with a focus on usability and quick actions.

*   **Auto-Detection**: Automatically scans for `.exe` files in Wine prefixes and USB drives.
*   **Quick Actions**: Format, wipe, mount, unmount, and check health with a single click.
*   **Application Launcher**: Run Windows applications directly from the interface.
*   **Drive Information**: Display detailed drive information in an easy-to-read format.
*   **Auto-Refresh**: Continuously monitors for new drives.
sudo python3 usb_manager_ultra.py

### 3. USB Pro (`usb_pro.py`)
A professional-grade tool for advanced drive operations and customization.

*   **Advanced Formatting**: Control cluster size, quick/full format options.
*   **Comprehensive Partitioning**: Create, delete, and resize partitions with custom settings.
*   **Bootable USB Creation**: Create bootable drives from ISO files.
*   **Performance Benchmark**: Test read/write speeds.
*   **Enhanced Security**: Secure wipe with customizable passes, including DoD and Gutmann standards.
*   sudo python3 usb_pro.py

### 4. USB Customizer Pro (`usb_customizer_pro.py`)
Focuses on branding and personalizing your USB drives.

*   **Label & Model**: Change the volume label, model name, vendor, and serial number.
*   **Vendor Database**: Select from a pre-populated database of vendors or enter custom details.
*   **Apply Customizations**: Apply labels and customizations without reformatting.
*   **Format with Settings**: Format a drive while simultaneously applying all custom settings.
*   **Restore to Custom**: Restore a drive to a previously saved custom state.
*   
sudo python3 usb_customizer_pro.py
## Installation & Dependencies
git clone https://github.com/CyberXGuest/Ultimate-USB-Doctor.git
cd Ultimate-USB-Doctor
# Install system dependencies
sudo apt update
sudo apt install -y python3 python3-pip python3-tk python3-venv python3-dev dosfstools ntfs-3g exfatprogs e2fsprogs xfsprogs btrfs-progs f2fs-tools parted gdisk hdparm sdparm smartmontools util-linux udev usbutils lsof rsync p7zip-full unzip zip udisks2 udftools mtools

# Install Python package
pip3 install psutil
chmod +x usb_doctor.py
chmod +x usb_manager_ultra.py
chmod +x usb_pro.py
chmod +x usb_customizer_pro.py
sudo python3 usb_doctor.py
# Install system dependencies
sudo apt update
sudo apt install -y python3 python3-pip python3-tk python3-venv python3-dev dosfstools ntfs-3g exfatprogs e2fsprogs xfsprogs btrfs-progs f2fs-tools parted gdisk hdparm sdparm smartmontools util-linux udev usbutils lsof rsync p7zip-full unzip zip udisks2 udftools mtools

# Install Python package
pip3 install psutil

### System Dependencies

Before running any of the tools, ensure your system has the required packages:

```bash
sudo apt update
sudo apt install -y \
    python3 python3-pip python3-tk python3-venv python3-dev \
    dosfstools ntfs-3g exfatprogs e2fsprogs xfsprogs btrfs-progs f2fs-tools \
    parted gdisk hdparm sdparm smartmontools util-linux \
    udev usbutils lsof rsync p7zip-full unzip zip udisks2 udftools mtools

git clone https://github.com/CyberXGuest/Ultimate-USB-Doctor.git
cd Ultimate-USB-Doctor
sudo apt update
sudo apt install -y python3 python3-pip python3-tk
pip3 install psutil
sudo python3 usb_doctor.py
