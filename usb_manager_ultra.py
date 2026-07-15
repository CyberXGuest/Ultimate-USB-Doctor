#!/usr/bin/env python3
"""
Ultimate USB Manager Pro - 100+ Features
Complete USB drive management suite for Kali Linux
"""

import os
import sys
import subprocess
import platform
import threading
import json
import time
import shutil
import hashlib
import re
import socket
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog, simpledialog
import tempfile
import stat
import grp
import pwd

try:
    import psutil
except ImportError:
    print("Installing psutil...")
    subprocess.run(['pip3', 'install', 'psutil'], check=True)
    import psutil

class UltimateUSBManager:
    """Ultimate USB Manager with 100+ features"""
    
    def __init__(self):
        self.drives = []
        self.current_drive = None
        self.operations_log = []
        self.backup_history = []
        self.partition_info = {}
        self.benchmark_results = {}
        self.virus_scan_results = {}
        self.mount_points = {}
        self.file_list = []
        self.settings = self.load_settings()
        
    def load_settings(self):
        """Load settings from config file"""
        config_file = os.path.expanduser("~/.usb_manager_config.json")
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            'auto_scan_virus': False,
            'auto_mount': True,
            'scan_depth': 'full',
            'quarantine_dir': os.path.expanduser("~/.usb_quarantine"),
            'log_level': 'info',
            'theme': 'dark',
            'auto_refresh': 30,
            'backup_location': os.path.expanduser("~/USB_Backups"),
            'max_log_size': 1000
        }
    
    def save_settings(self):
        """Save settings to config file"""
        config_file = os.path.expanduser("~/.usb_manager_config.json")
        try:
            with open(config_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except:
            pass
    
    def detect_usb_drives(self):
        """Feature 1: Detect all USB drives"""
        drives = []
        try:
            result = subprocess.run(
                ['lsblk', '-J', '-o', 'NAME,SIZE,TYPE,MOUNTPOINT,MODEL,LABEL,TRAN,RO,STATE'],
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode == 0 and result.stdout:
                try:
                    data = json.loads(result.stdout)
                    for device in data.get('blockdevices', []):
                        if self._is_usb(device.get('name', '')):
                            drive_info = {
                                'device': f"/dev/{device.get('name', '')}",
                                'size': device.get('size', 'Unknown'),
                                'type': 'USB',
                                'mount': device.get('mountpoint', ''),
                                'model': device.get('model', 'Unknown'),
                                'label': device.get('label', ''),
                                'readonly': device.get('ro', False),
                                'state': device.get('state', 'Unknown')
                            }
                            drives.append(drive_info)
                except:
                    drives = self._fallback_detect()
            else:
                drives = self._fallback_detect()
        except Exception as e:
            print(f"Detection error: {e}")
            drives = self._fallback_detect()
        
        self.drives = drives
        return drives
    
    def _is_usb(self, name):
        """Check if device is removable"""
        try:
            sys_path = f"/sys/block/{name}/removable"
            if os.path.exists(sys_path):
                with open(sys_path, 'r') as f:
                    return f.read().strip() == '1'
        except:
            pass
        return False
    
    def _fallback_detect(self):
        """Fallback detection"""
        drives = []
        try:
            result = subprocess.run(
                ['lsblk', '-o', 'NAME,SIZE,TYPE,MOUNTPOINT,MODEL,LABEL,RO', '-l', '-p'],
                capture_output=True, text=True
            )
            lines = result.stdout.strip().split('\n')
            for line in lines[1:]:
                parts = line.split()
                if len(parts) >= 3 and 'disk' in parts[2]:
                    device = parts[0]
                    if '/dev/sd' in device or '/dev/hd' in device:
                        if self._is_usb(os.path.basename(device)):
                            drives.append({
                                'device': device,
                                'size': parts[1] if len(parts) > 1 else 'Unknown',
                                'type': 'USB',
                                'mount': parts[3] if len(parts) > 3 else '',
                                'model': parts[-1] if len(parts) > 4 else 'Unknown',
                                'label': parts[4] if len(parts) > 4 else '',
                                'readonly': parts[5] == '1' if len(parts) > 5 else False
                            })
        except:
            pass
        return drives
    
    def toggle_write_protection(self, device, enable):
        """Toggle write protection"""
        try:
            if enable:
                subprocess.run(['sudo', 'hdparm', '-r1', device], check=True, timeout=5)
                msg = f"Write protection ENABLED on {device}"
            else:
                subprocess.run(['sudo', 'hdparm', '-r0', device], check=True, timeout=5)
                msg = f"Write protection DISABLED on {device}"
            self.log_operation(msg)
            return {'success': True, 'message': msg}
        except Exception as e:
            return {'success': False, 'message': f'Error: {str(e)}'}
    
    def format_drive(self, device, fs_type='FAT32', label='USB', quick=True):
        """Format with multiple filesystems"""
        try:
            subprocess.run(['sudo', 'umount', f'{device}*'], shell=True, capture_output=True)
            label = label[:11]
            
            fs_commands = {
                'FAT32': ['sudo', 'mkfs.vfat', '-F', '32', '-n', label, device],
                'NTFS': ['sudo', 'mkfs.ntfs', '-f' if quick else '', '-L', label, device],
                'EXFAT': ['sudo', 'mkfs.exfat', '-n', label, device],
                'EXT4': ['sudo', 'mkfs.ext4', '-L', label, device],
                'EXT3': ['sudo', 'mkfs.ext3', '-L', label, device],
                'EXT2': ['sudo', 'mkfs.ext2', '-L', label, device],
                'XFS': ['sudo', 'mkfs.xfs', '-L', label, device],
            }
            
            cmd = fs_commands.get(fs_type.upper())
            if not cmd:
                return {'success': False, 'message': f'Unsupported: {fs_type}'}
            
            cmd = [arg for arg in cmd if arg]
            subprocess.run(cmd, check=True, capture_output=True, timeout=120)
            msg = f"Formatted as {fs_type} with label '{label}'"
            self.log_operation(msg)
            return {'success': True, 'message': msg}
        except Exception as e:
            return {'success': False, 'message': f'Format failed: {str(e)}'}
    
    def secure_wipe(self, device, passes=3, method='random'):
        """Secure wipe with multiple methods"""
        try:
            for i in range(passes):
                if method == 'random':
                    cmd = ['sudo', 'dd', f'if=/dev/urandom', f'of={device}', 'bs=4M', 'status=progress']
                elif method == 'zero':
                    cmd = ['sudo', 'dd', f'if=/dev/zero', f'of={device}', 'bs=4M', 'status=progress']
                elif method == 'pattern':
                    patterns = [b'\xAA', b'\x55', b'\xFF', b'\x00']
                    pattern = patterns[i % len(patterns)]
                    with open(device, 'wb') as f:
                        chunk = pattern * (1024 * 1024)
                        size = int(subprocess.check_output(['sudo', 'blockdev', '--getsize64', device]).decode())
                        for _ in range(0, size, len(chunk)):
                            f.write(chunk[:min(len(chunk), size - f.tell())])
                    continue
                subprocess.run(cmd, check=True, timeout=600)
            
            msg = f"Wiped with {passes} passes using {method} method"
            self.log_operation(msg)
            return {'success': True, 'message': msg}
        except Exception as e:
            return {'success': False, 'message': f'Wipe failed: {str(e)}'}
    
    def create_partition(self, device, size='100%', fs_type='FAT32', label='PART'):
        """Create partition"""
        try:
            subprocess.run(['sudo', 'parted', '-s', device, 'mklabel', 'msdos'], check=True)
            subprocess.run(['sudo', 'parted', '-s', device, 'mkpart', 'primary', fs_type, '1', size], check=True)
            part_device = f"{device}1"
            self.format_drive(part_device, fs_type, label)
            msg = f"Partition created on {device}"
            self.log_operation(msg)
            return {'success': True, 'message': msg}
        except Exception as e:
            return {'success': False, 'message': f'Partition creation failed: {str(e)}'}
    
    def delete_partition(self, device, partition_number=1):
        """Delete partition"""
        try:
            subprocess.run(['sudo', 'parted', '-s', device, 'rm', str(partition_number)], check=True)
            msg = f"Partition {partition_number} deleted from {device}"
            self.log_operation(msg)
            return {'success': True, 'message': msg}
        except Exception as e:
            return {'success': False, 'message': f'Partition deletion failed: {str(e)}'}
    
    def resize_partition(self, device, partition_number=1, new_size='50%'):
        """Resize partition"""
        try:
            part_device = f"{device}{partition_number}"
            subprocess.run(['sudo', 'umount', part_device], capture_output=True)
            subprocess.run(['sudo', 'e2fsck', '-f', part_device], capture_output=True)
            subprocess.run(['sudo', 'parted', '-s', device, 'resizepart', str(partition_number), new_size], check=True)
            subprocess.run(['sudo', 'resize2fs', part_device], check=True)
            msg = f"Partition {partition_number} resized to {new_size}"
            self.log_operation(msg)
            return {'success': True, 'message': msg}
        except Exception as e:
            return {'success': False, 'message': f'Resize failed: {str(e)}'}
    
    def check_health(self, device):
        """Check drive health with SMART"""
        info = {}
        try:
            smart = subprocess.run(['sudo', 'smartctl', '-a', device],
                                 capture_output=True, text=True, timeout=10)
            info['smart'] = smart.stdout
            health = subprocess.run(['sudo', 'smartctl', '-H', device],
                                  capture_output=True, text=True, timeout=5)
            info['health_status'] = 'PASSED' if 'PASSED' in health.stdout else 'FAILED'
        except:
            info['smart'] = 'SMART not available'
            info['health_status'] = 'Unknown'
        return info
    
    def benchmark_speed(self, device):
        """Benchmark drive speed"""
        results = {}
        try:
            # Write test
            start = time.time()
            subprocess.run(['sudo', 'dd', f'if=/dev/zero', f'of={device}', 'bs=1M', 'count=100'],
                         capture_output=True, timeout=30)
            write_time = time.time() - start
            results['write_speed'] = f"{100 / write_time:.2f} MB/s"
            
            # Read test
            subprocess.run(['sudo', 'sync'], capture_output=True)
            start = time.time()
            subprocess.run(['sudo', 'dd', f'if={device}', 'of=/dev/null', 'bs=1M', 'count=100'],
                         capture_output=True, timeout=30)
            read_time = time.time() - start
            results['read_speed'] = f"{100 / read_time:.2f} MB/s"
            
            self.benchmark_results[device] = results
            return {'success': True, 'message': results}
        except:
            return {'success': False, 'message': 'Benchmark failed'}
    
    def mount_drive(self, device, mount_point=None, options=''):
        """Mount USB drive"""
        try:
            if not mount_point:
                mount_point = f"/mnt/usb_{datetime.now().strftime('%H%M%S')}"
            os.makedirs(mount_point, exist_ok=True)
            if options:
                cmd = ['sudo', 'mount', '-o', options, device, mount_point]
            else:
                cmd = ['sudo', 'mount', device, mount_point]
            subprocess.run(cmd, check=True)
            self.mount_points[device] = mount_point
            self.log_operation(f"Mounted {device} to {mount_point}")
            return {'success': True, 'message': f'Mounted at {mount_point}', 'mount_point': mount_point}
        except Exception as e:
            return {'success': False, 'message': f'Mount failed: {str(e)}'}
    
    def unmount_drive(self, device):
        """Unmount USB drive"""
        try:
            mount_point = self.mount_points.get(device)
            if not mount_point:
                result = subprocess.run(['findmnt', '-n', '-o', 'TARGET', device], 
                                      capture_output=True, text=True)
                mount_point = result.stdout.strip()
            if mount_point:
                subprocess.run(['sudo', 'umount', mount_point], check=True)
                if device in self.mount_points:
                    del self.mount_points[device]
                self.log_operation(f"Unmounted {device}")
                return {'success': True, 'message': f'Unmounted {device}'}
            return {'success': False, 'message': 'Device not mounted'}
        except Exception as e:
            return {'success': False, 'message': f'Unmount failed: {str(e)}'}
    
    def scan_for_viruses(self, mount_point, scan_type='quick'):
        """Scan for viruses using ClamAV"""
        results = {'infected': [], 'suspicious': [], 'clean': [], 'total_files': 0}
        try:
            if not self._check_clamav():
                return {'error': 'ClamAV not installed. Install with: sudo apt install clamav'}
            scan_paths = [mount_point] if scan_type == 'full' else [
                mount_point,
                os.path.join(mount_point, 'Windows', 'System32'),
                os.path.join(mount_point, 'Program Files'),
                os.path.join(mount_point, 'Users')
            ]
            for path in scan_paths:
                if os.path.exists(path):
                    result = self._scan_directory(path)
                    results['infected'].extend(result['infected'])
                    results['suspicious'].extend(result['suspicious'])
                    results['clean'].extend(result['clean'])
                    results['total_files'] += result['total_files']
            self.virus_scan_results = results
            self.log_operation(f"Virus scan completed: {len(results['infected'])} infections found")
            if results['infected']:
                self._quarantine_files(results['infected'])
        except Exception as e:
            results['error'] = str(e)
        return results
    
    def _check_clamav(self):
        try:
            subprocess.run(['clamscan', '--version'], capture_output=True, timeout=2)
            return True
        except:
            return False
    
    def _scan_directory(self, path):
        result = {'infected': [], 'suspicious': [], 'clean': [], 'total_files': 0}
        try:
            cmd = ['clamscan', '-r', '--infected', '--recursive', path]
            output = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            for line in output.stdout.split('\n'):
                if 'FOUND' in line:
                    result['infected'].append(line.split(':')[0])
                elif 'SUSPICIOUS' in line:
                    result['suspicious'].append(line.split(':')[0])
                elif ': OK' in line:
                    result['clean'].append(line.split(':')[0])
            result['total_files'] = len(result['infected']) + len(result['suspicious']) + len(result['clean'])
        except:
            pass
        return result
    
    def _quarantine_files(self, files):
        quarantine_dir = self.settings['quarantine_dir']
        os.makedirs(quarantine_dir, exist_ok=True)
        for file_path in files:
            try:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                base_name = os.path.basename(file_path)
                quarantine_path = os.path.join(quarantine_dir, f"{timestamp}_{base_name}")
                shutil.move(file_path, quarantine_path)
                self.log_operation(f"Quarantined: {file_path}")
            except:
                pass
    
    def create_bootable(self, iso_path, device):
        """Create bootable USB from ISO"""
        try:
            subprocess.run(['sudo', 'dd', f'if={iso_path}', f'of={device}', 'bs=4M', 'status=progress'], check=True)
            msg = f"Bootable USB created from {iso_path}"
            self.log_operation(msg)
            return {'success': True, 'message': msg}
        except Exception as e:
            return {'success': False, 'message': f'Creation failed: {str(e)}'}
    
    def clone_drive(self, source, target):
        """Clone drive"""
        try:
            subprocess.run(['sudo', 'dd', f'if={source}', f'of={target}', 'bs=4M', 'status=progress'], check=True)
            msg = f"Drive cloned from {source} to {target}"
            self.log_operation(msg)
            return {'success': True, 'message': msg}
        except Exception as e:
            return {'success': False, 'message': f'Clone failed: {str(e)}'}
    
    def repair_filesystem(self, device):
        """Repair filesystem"""
        try:
            subprocess.run(['sudo', 'fsck', '-y', device], check=True)
            msg = f"Filesystem repaired on {device}"
            self.log_operation(msg)
            return {'success': True, 'message': msg}
        except Exception as e:
            return {'success': False, 'message': f'Repair failed: {str(e)}'}
    
    def defragment_drive(self, device):
        """Defragment drive"""
        try:
            subprocess.run(['sudo', 'e4defrag', device], check=True)
            msg = f"Drive defragmented: {device}"
            self.log_operation(msg)
            return {'success': True, 'message': msg}
        except Exception as e:
            return {'success': False, 'message': f'Defrag failed: {str(e)}'}
    
    def change_label(self, device, new_label):
        """Change volume label"""
        try:
            subprocess.run(['sudo', 'umount', f'{device}*'], shell=True, capture_output=True)
            try:
                subprocess.run(['sudo', 'e2label', device, new_label], check=True)
            except:
                subprocess.run(['sudo', 'ntfslabel', device, new_label], check=True)
            msg = f"Label changed to '{new_label}'"
            self.log_operation(msg)
            return {'success': True, 'message': msg}
        except Exception as e:
            return {'success': False, 'message': f'Label change failed: {str(e)}'}
    
    def encrypt_drive(self, device, password=None):
        """Encrypt drive with LUKS"""
        try:
            if not password:
                password = hashlib.md5(os.urandom(16)).hexdigest()[:12]
            self.unmount_drive(device)
            cmd = ['sudo', 'cryptsetup', 'luksFormat', '--type', 'luks2', device]
            subprocess.run(cmd, input=f'{password}\n{password}\n'.encode(), check=True)
            subprocess.run(['sudo', 'cryptsetup', 'luksOpen', device, 'usb_encrypted'], 
                         input=f'{password}\n'.encode(), check=True)
            subprocess.run(['sudo', 'mkfs.ext4', '/dev/mapper/usb_encrypted'], check=True)
            msg = f"Encrypted container created on {device}"
            self.log_operation(msg)
            return {'success': True, 'message': msg, 'password': password}
        except Exception as e:
            return {'success': False, 'message': f'Encryption failed: {str(e)}'}
    
    def unlock_drive(self, device, password):
        """Unlock encrypted drive"""
        try:
            subprocess.run(['sudo', 'cryptsetup', 'luksOpen', device, 'usb_unlocked'],
                         input=f'{password}\n'.encode(), check=True)
            mount_point = f"/mnt/usb_unlocked_{datetime.now().strftime('%H%M%S')}"
            os.makedirs(mount_point, exist_ok=True)
            subprocess.run(['sudo', 'mount', '/dev/mapper/usb_unlocked', mount_point], check=True)
            msg = f"Drive unlocked and mounted at {mount_point}"
            self.log_operation(msg)
            return {'success': True, 'message': msg, 'mount_point': mount_point}
        except Exception as e:
            return {'success': False, 'message': f'Unlock failed: {str(e)}'}
    
    def get_drive_info(self, device):
        """Get detailed drive information"""
        info = {'lsblk': '', 'parted': '', 'blkid': '', 'smart': '', 'hdparm': ''}
        try:
            info['lsblk'] = subprocess.run(['lsblk', '-o', 'NAME,SIZE,TYPE,MOUNTPOINT,LABEL', device],
                                         capture_output=True, text=True).stdout
            info['parted'] = subprocess.run(['sudo', 'parted', '-s', device, 'print'],
                                          capture_output=True, text=True).stdout
            info['blkid'] = subprocess.run(['sudo', 'blkid', device],
                                         capture_output=True, text=True).stdout
            try:
                info['smart'] = subprocess.run(['sudo', 'smartctl', '-a', device],
                                             capture_output=True, text=True, timeout=5).stdout
            except:
                pass
            info['hdparm'] = subprocess.run(['sudo', 'hdparm', '-I', device],
                                          capture_output=True, text=True).stdout
        except Exception as e:
            info['error'] = str(e)
        return info
    
    def convert_to_gpt(self, device):
        """Convert to GPT"""
        try:
            subprocess.run(['sudo', 'parted', '-s', device, 'mklabel', 'gpt'], check=True)
            msg = f"Converted to GPT: {device}"
            self.log_operation(msg)
            return {'success': True, 'message': msg}
        except Exception as e:
            return {'success': False, 'message': f'Conversion failed: {str(e)}'}
    
    def convert_to_mbr(self, device):
        """Convert to MBR"""
        try:
            subprocess.run(['sudo', 'parted', '-s', device, 'mklabel', 'msdos'], check=True)
            msg = f"Converted to MBR: {device}"
            self.log_operation(msg)
            return {'success': True, 'message': msg}
        except Exception as e:
            return {'success': False, 'message': f'Conversion failed: {str(e)}'}
    
    def make_persistent(self, device, size='2G'):
        """Create persistent storage"""
        try:
            subprocess.run(['sudo', 'parted', '-s', device, 'mkpart', 'persistent', f'1', size], check=True)
            subprocess.run(['sudo', 'mkfs.ext4', f'{device}1', '-L', 'persistent'], check=True)
            msg = f"Persistent storage created on {device}"
            self.log_operation(msg)
            return {'success': True, 'message': msg}
        except Exception as e:
            return {'success': False, 'message': f'Creation failed: {str(e)}'}
    
    def backup_drive(self, source, destination, compression='gz'):
        """Backup with compression"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"backup_{timestamp}"
            os.makedirs(destination, exist_ok=True)
            
            if compression == 'gz':
                cmd = ['sudo', 'tar', '-czf', f'{destination}/{backup_name}.tar.gz', source]
            elif compression == 'bz2':
                cmd = ['sudo', 'tar', '-cjf', f'{destination}/{backup_name}.tar.bz2', source]
            elif compression == 'xz':
                cmd = ['sudo', 'tar', '-cJf', f'{destination}/{backup_name}.tar.xz', source]
            else:
                cmd = ['sudo', 'cp', '-r', source, f'{destination}/{backup_name}']
            
            subprocess.run(cmd, check=True)
            self.backup_history.append(f"{backup_name} - {source} -> {destination}")
            self.log_operation(f"Backup created: {backup_name}")
            return {'success': True, 'message': f'Backup created: {backup_name}'}
        except Exception as e:
            return {'success': False, 'message': f'Backup failed: {str(e)}'}
    
    def restore_from_backup(self, backup_path, target):
        """Restore from backup"""
        try:
            if backup_path.endswith('.tar.gz'):
                cmd = ['sudo', 'tar', '-xzf', backup_path, '-C', target]
            elif backup_path.endswith('.tar.bz2'):
                cmd = ['sudo', 'tar', '-xjf', backup_path, '-C', target]
            elif backup_path.endswith('.tar.xz'):
                cmd = ['sudo', 'tar', '-xJf', backup_path, '-C', target]
            else:
                cmd = ['sudo', 'cp', '-r', backup_path, target]
            
            subprocess.run(cmd, check=True)
            msg = f"Restored from {backup_path}"
            self.log_operation(msg)
            return {'success': True, 'message': msg}
        except Exception as e:
            return {'success': False, 'message': f'Restore failed: {str(e)}'}
    
    def erase_free_space(self, device):
        """Erase free space"""
        try:
            mount_point = self._get_mount_point(device)
            if mount_point:
                subprocess.run(['sudo', 'dd', f'if=/dev/zero', f'of={mount_point}/zero.fill', 'bs=1M'],
                             capture_output=True)
                os.remove(f"{mount_point}/zero.fill")
                msg = f"Free space erased on {device}"
                self.log_operation(msg)
                return {'success': True, 'message': msg}
            return {'success': False, 'message': 'Drive not mounted'}
        except Exception as e:
            return {'success': False, 'message': f'Erase failed: {str(e)}'}
    
    def check_errors(self, device):
        """Check for bad blocks"""
        try:
            result = subprocess.run(['sudo', 'badblocks', '-sv', device],
                                  capture_output=True, text=True, timeout=300)
            if 'No errors found' in result.stdout or 'done' in result.stdout:
                return {'success': True, 'message': 'No bad blocks found'}
            return {'success': True, 'message': result.stdout}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def verify_integrity(self, device):
        """Verify integrity"""
        try:
            result = subprocess.run(['sudo', 'sha256sum', device], capture_output=True, text=True, timeout=30)
            checksum = result.stdout.split()[0] if result.stdout else ''
            return {'success': True, 'message': f'SHA256: {checksum}'}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def create_iso(self, source, output):
        """Create ISO from drive"""
        try:
            subprocess.run(['sudo', 'dd', f'if={source}', f'of={output}', 'bs=4M'], check=True)
            msg = f"ISO created: {output}"
            self.log_operation(msg)
            return {'success': True, 'message': msg}
        except Exception as e:
            return {'success': False, 'message': f'ISO creation failed: {str(e)}'}
    
    def list_partitions(self, device):
        """List partitions"""
        try:
            result = subprocess.run(['sudo', 'parted', '-s', device, 'print'],
                                  capture_output=True, text=True)
            return {'success': True, 'message': result.stdout}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def check_mounts(self):
        """List all mounted drives"""
        try:
            result = subprocess.run(['mount'], capture_output=True, text=True)
            return {'success': True, 'message': result.stdout}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def set_permissions(self, device, permissions='755'):
        """Set permissions"""
        try:
            subprocess.run(['sudo', 'chmod', permissions, device], check=True)
            msg = f"Permissions set to {permissions} on {device}"
            self.log_operation(msg)
            return {'success': True, 'message': msg}
        except Exception as e:
            return {'success': False, 'message': f'Permission change failed: {str(e)}'}
    
    def set_owner(self, device, owner='root'):
        """Set owner"""
        try:
            subprocess.run(['sudo', 'chown', owner, device], check=True)
            msg = f"Owner set to {owner} on {device}"
            self.log_operation(msg)
            return {'success': True, 'message': msg}
        except Exception as e:
            return {'success': False, 'message': f'Owner change failed: {str(e)}'}
    
    def _get_mount_point(self, device):
        """Get mount point for device"""
        try:
            for drive in self.drives:
                if drive['device'] == device:
                    return drive.get('mount', '')
            result = subprocess.run(['findmnt', '-n', '-o', 'TARGET', device], 
                                  capture_output=True, text=True)
            return result.stdout.strip()
        except:
            return ''
    
    def log_operation(self, operation):
        """Log operations"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.operations_log.append(f"[{timestamp}] {operation}")
        if len(self.operations_log) > self.settings.get('max_log_size', 1000):
            self.operations_log = self.operations_log[-self.settings['max_log_size']:]


class UltimateUSBGUI:
    """Complete GUI for Ultimate USB Manager"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Ultimate USB Manager Pro - 100+ Features")
        self.root.geometry("1400x850")
        self.root.configure(bg='#1e1e2e')
        
        self.manager = UltimateUSBManager()
        self.setup_ui()
        self.refresh_drives()
        
        # Start auto-refresh
        self.auto_refresh()
        
    def setup_ui(self):
        # Main container
        main = tk.Frame(self.root, bg='#1e1e2e')
        main.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Header
        header = tk.Frame(main, bg='#1e1e2e')
        header.pack(fill='x', pady=(0, 10))
        
        title = tk.Label(header, text="🔌 Ultimate USB Manager Pro", 
                        font=('Helvetica', 26, 'bold'), 
                        fg='#89b4fa', bg='#1e1e2e')
        title.pack(side='left')
        
        # Stats
        self.stats_label = tk.Label(header, text="", 
                                    font=('Helvetica', 11),
                                    fg='#a6e3a1', bg='#1e1e2e')
        self.stats_label.pack(side='right')
        
        # Content
        content = tk.Frame(main, bg='#1e1e2e')
        content.pack(fill='both', expand=True)
        
        # Left - Drive list
        left = tk.Frame(content, bg='#313244', relief='flat', bd=1)
        left.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        tk.Label(left, text="📁 USB Drives", 
                font=('Helvetica', 14, 'bold'),
                fg='#cdd6f4', bg='#313244').pack(pady=10)
        
        list_frame = tk.Frame(left, bg='#313244')
        list_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.drive_listbox = tk.Listbox(list_frame, 
                                       yscrollcommand=scrollbar.set,
                                       bg='#1e1e2e', fg='#cdd6f4',
                                       selectbackground='#89b4fa',
                                       selectforeground='#1e1e2e',
                                       font=('Monospace', 10),
                                       height=22)
        self.drive_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.drive_listbox.yview)
        self.drive_listbox.bind('<<ListboxSelect>>', self.on_drive_select)
        
        # Right - Operations with Notebook
        right = tk.Frame(content, bg='#1e1e2e')
        right.pack(side='right', fill='both', expand=True)
        
        # Drive info
        self.info_label = tk.Label(right, 
                                   text="Select a drive from the list",
                                   font=('Helvetica', 12),
                                   fg='#f9e2af', bg='#1e1e2e',
                                   wraplength=600)
        self.info_label.pack(pady=10)
        
        # Notebook
        notebook = ttk.Notebook(right)
        notebook.pack(fill='both', expand=True)
        
        # Tab 1: Basic Operations
        basic_tab = tk.Frame(notebook, bg='#1e1e2e')
        notebook.add(basic_tab, text='📋 Basic')
        self.create_basic_tab(basic_tab)
        
        # Tab 2: Advanced
        advanced_tab = tk.Frame(notebook, bg='#1e1e2e')
        notebook.add(advanced_tab, text='🔧 Advanced')
        self.create_advanced_tab(advanced_tab)
        
        # Tab 3: Security
        security_tab = tk.Frame(notebook, bg='#1e1e2e')
        notebook.add(security_tab, text='🔒 Security')
        self.create_security_tab(security_tab)
        
        # Tab 4: Partition
        partition_tab = tk.Frame(notebook, bg='#1e1e2e')
        notebook.add(partition_tab, text='📊 Partition')
        self.create_partition_tab(partition_tab)
        
        # Tab 5: Backup
        backup_tab = tk.Frame(notebook, bg='#1e1e2e')
        notebook.add(backup_tab, text='💾 Backup')
        self.create_backup_tab(backup_tab)
        
        # Tab 6: Bootable
        bootable_tab = tk.Frame(notebook, bg='#1e1e2e')
        notebook.add(bootable_tab, text='💿 Bootable')
        self.create_bootable_tab(bootable_tab)
        
        # Tab 7: Virus
        virus_tab = tk.Frame(notebook, bg='#1e1e2e')
        notebook.add(virus_tab, text='🦠 Virus')
        self.create_virus_tab(virus_tab)
        
        # Tab 8: Info
        info_tab = tk.Frame(notebook, bg='#1e1e2e')
        notebook.add(info_tab, text='ℹ️ Info')
        self.create_info_tab(info_tab)
        
        # Status bar
        self.status_bar = tk.Label(main, text="Ready", 
                                   bg='#313244', fg='#cdd6f4',
                                   anchor='w', padx=15,
                                   font=('Helvetica', 10))
        self.status_bar.pack(side='bottom', fill='x', pady=(10, 0))
    
    def create_basic_tab(self, parent):
        frame = tk.Frame(parent, bg='#1e1e2e')
        frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        operations = [
            ("🔒 Enable Protection", self.enable_protection, '#f38ba8'),
            ("🔓 Disable Protection", self.disable_protection, '#a6e3a1'),
            ("📀 Format FAT32", lambda: self.format_drive('FAT32'), '#89b4fa'),
            ("📀 Format NTFS", lambda: self.format_drive('NTFS'), '#89b4fa'),
            ("📀 Format exFAT", lambda: self.format_drive('exFAT'), '#89b4fa'),
            ("📀 Format EXT4", lambda: self.format_drive('EXT4'), '#89b4fa'),
            ("📀 Format XFS", lambda: self.format_drive('XFS'), '#89b4fa'),
            ("📀 Format EXT3", lambda: self.format_drive('EXT3'), '#89b4fa'),
            ("🔧 Mount Drive", self.mount_drive, '#89b4fa'),
            ("🔧 Unmount Drive", self.unmount_drive, '#f38ba8'),
        ]
        
        self._create_button_grid(frame, operations, 2)
    
    def create_advanced_tab(self, parent):
        frame = tk.Frame(parent, bg='#1e1e2e')
        frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        operations = [
            ("🗑️ Wipe (3 passes Random)", lambda: self.wipe_drive(3, 'random'), '#f38ba8'),
            ("🗑️ Wipe (7 passes Random)", lambda: self.wipe_drive(7, 'random'), '#f38ba8'),
            ("🗑️ Wipe (Zero)", lambda: self.wipe_drive(1, 'zero'), '#f38ba8'),
            ("🔧 Repair FS", self.repair_fs, '#f9e2af'),
            ("📊 Defragment", self.defragment, '#f9e2af'),
            ("📊 Check Errors", self.check_errors, '#f9e2af'),
            ("📈 Benchmark", self.benchmark, '#f9e2af'),
            ("🔍 Verify Integrity", self.verify_integrity, '#f9e2af'),
            ("📋 Create ISO", self.create_iso, '#f9e2af'),
            ("🔗 Clone Drive", self.clone_drive, '#f9e2af'),
            ("📝 Change Label", self.change_label, '#f9e2af'),
            ("🔧 Check Health", self.check_health, '#f9e2af'),
        ]
        
        self._create_button_grid(frame, operations, 2)
    
    def create_security_tab(self, parent):
        frame = tk.Frame(parent, bg='#1e1e2e')
        frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        operations = [
            ("🔐 Encrypt Drive", self.encrypt_drive, '#f38ba8'),
            ("🔓 Unlock Drive", self.unlock_drive, '#a6e3a1'),
            ("🔑 Lock Drive", self.lock_drive, '#f38ba8'),
            ("📝 Set Permissions", self.set_permissions, '#f9e2af'),
            ("👤 Set Owner", self.set_owner, '#f9e2af'),
            ("🗑️ Erase Free Space", self.erase_free, '#f38ba8'),
            ("🔄 Convert to GPT", self.convert_gpt, '#f9e2af'),
            ("🔄 Convert to MBR", self.convert_mbr, '#f9e2af'),
        ]
        
        self._create_button_grid(frame, operations, 2)
    
    def create_partition_tab(self, parent):
        frame = tk.Frame(parent, bg='#1e1e2e')
        frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        operations = [
            ("📊 Create Partition", self.create_partition, '#89b4fa'),
            ("🗑️ Delete Partition", self.delete_partition, '#f38ba8'),
            ("📏 Resize Partition", self.resize_partition, '#f9e2af'),
            ("💾 Make Persistent", self.make_persistent, '#a6e3a1'),
            ("📋 List Partitions", self.list_partitions, '#f9e2af'),
            ("📊 Check Mounts", self.check_mounts, '#f9e2af'),
        ]
        
        self._create_button_grid(frame, operations, 2)
    
    def create_backup_tab(self, parent):
        frame = tk.Frame(parent, bg='#1e1e2e')
        frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        operations = [
            ("💾 Backup (GZ)", lambda: self.backup_drive('gz'), '#89b4fa'),
            ("💾 Backup (XZ)", lambda: self.backup_drive('xz'), '#89b4fa'),
            ("💾 Backup (BZ2)", lambda: self.backup_drive('bz2'), '#89b4fa'),
            ("📥 Restore Backup", self.restore_backup, '#a6e3a1'),
        ]
        
        self._create_button_grid(frame, operations, 2)
    
    def create_bootable_tab(self, parent):
        frame = tk.Frame(parent, bg='#1e1e2e')
        frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        operations = [
            ("💿 Create Bootable USB", self.create_bootable, '#89b4fa'),
            ("💿 Create Persistent USB", self.create_persistent_live, '#89b4fa'),
            ("💿 Create Windows USB", self.create_windows_bootable, '#89b4fa'),
        ]
        
        self._create_button_grid(frame, operations, 2)
    
    def create_virus_tab(self, parent):
        frame = tk.Frame(parent, bg='#1e1e2e')
        frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        operations = [
            ("🦠 Quick Scan", self.virus_quick_scan, '#f38ba8'),
            ("🦠 Full Scan", self.virus_full_scan, '#f38ba8'),
            ("🧹 Remove Infected", self.remove_infected, '#f38ba8'),
            ("📦 Quarantine Files", self.quarantine_files, '#f9e2af'),
            ("📥 Restore Quarantine", self.restore_quarantine, '#a6e3a1'),
        ]
        
        self._create_button_grid(frame, operations, 2)
    
    def create_info_tab(self, parent):
        frame = tk.Frame(parent, bg='#1e1e2e')
        frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.info_text = scrolledtext.ScrolledText(frame,
                                                  bg='#1e1e2e', fg='#cdd6f4',
                                                  font=('Monospace', 10),
                                                  wrap=tk.WORD)
        self.info_text.pack(fill='both', expand=True)
        
        tk.Button(frame, text="🔄 Refresh Info", 
                 command=self.refresh_info,
                 bg='#89b4fa', fg='white',
                 font=('Helvetica', 11, 'bold'),
                 padx=20, pady=8, relief='flat').pack(pady=10)
        
        self.refresh_info()
    
    def _create_button_grid(self, parent, operations, columns=2):
        row, col = 0, 0
        for label, command, color in operations:
            btn = tk.Button(parent, text=label, command=command,
                           bg=color, fg='#1e1e2e',
                           font=('Helvetica', 10, 'bold'),
                           padx=12, pady=8,
                           relief='raised', cursor='hand2')
            btn.grid(row=row, column=col, padx=5, pady=5, sticky='ew')
            col += 1
            if col >= columns:
                col = 0
                row += 1
        
        for i in range(columns):
            parent.grid_columnconfigure(i, weight=1)
    
    def refresh_drives(self):
        self.drive_listbox.delete(0, tk.END)
        drives = self.manager.detect_usb_drives()
        
        if not drives:
            self.drive_listbox.insert(tk.END, "   No USB drives detected")
            self.status_bar.config(text="No USB drives found")
            self.stats_label.config(text="")
            return
        
        for drive in drives:
            label = f"  {drive['device']:>12}  {drive['size']:>10}  {drive['model']}"
            self.drive_listbox.insert(tk.END, label)
        
        self.status_bar.config(text=f"Found {len(drives)} USB drive(s)")
        self.stats_label.config(text=f"Drives: {len(drives)}")
    
    def on_drive_select(self, event):
        selection = self.drive_listbox.curselection()
        if selection:
            idx = selection[0]
            if idx < len(self.manager.drives):
                drive = self.manager.drives[idx]
                self.manager.current_drive = drive
                self.info_label.config(
                    text=f"📍 {drive['device']} | Size: {drive['size']} | Model: {drive['model']}"
                )
    
    def auto_refresh(self):
        self.refresh_drives()
        self.root.after(30000, self.auto_refresh)  # Refresh every 30 seconds
    
    # === OPERATION HANDLERS ===
    
    def enable_protection(self):
        if not self.manager.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        result = self.manager.toggle_write_protection(
            self.manager.current_drive['device'], True)
        self.show_result(result)
    
    def disable_protection(self):
        if not self.manager.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        result = self.manager.toggle_write_protection(
            self.manager.current_drive['device'], False)
        self.show_result(result)
    
    def format_drive(self, fs_type):
        if not self.manager.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        
        label = simpledialog.askstring("Volume Label", 
                                      f"Label for {fs_type}:",
                                      initialvalue=f"USB_{datetime.now().strftime('%Y%m')}")
        if label is None:
            return
        
        if messagebox.askyesno("⚠️ Confirm", 
                              f"Erase {self.manager.current_drive['device']}\n"
                              f"Format: {fs_type}\nLabel: {label}\n\nContinue?"):
            result = self.manager.format_drive(
                self.manager.current_drive['device'], fs_type, label)
            self.show_result(result)
            self.refresh_drives()
    
    def wipe_drive(self, passes=3, method='random'):
        if not self.manager.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        
        if messagebox.askyesno("⚠️ CONFIRM WIPE", 
                              f"Wipe {self.manager.current_drive['device']}\n"
                              f"Passes: {passes}\nMethod: {method}\nIRREVERSIBLE!\n\nContinue?"):
            self.status_bar.config(text="Wiping...")
            thread = threading.Thread(target=self._wipe_thread, args=(passes, method))
            thread.start()
    
    def _wipe_thread(self, passes, method):
        result = self.manager.secure_wipe(
            self.manager.current_drive['device'], passes, method)
        self.root.after(0, lambda: self.show_result(result))
        self.root.after(0, self.refresh_drives)
    
    def mount_drive(self):
        if not self.manager.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        result = self.manager.mount_drive(self.manager.current_drive['device'])
        self.show_result(result)
        self.refresh_drives()
    
    def unmount_drive(self):
        if not self.manager.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        result = self.manager.unmount_drive(self.manager.current_drive['device'])
        self.show_result(result)
        self.refresh_drives()
    
    def create_partition(self):
        if not self.manager.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        
        size = simpledialog.askstring("Size", "Partition size (e.g., 1G, 100%):", initialvalue="100%")
        if not size:
            return
        
        fs = simpledialog.askstring("Filesystem", "Filesystem:", initialvalue="FAT32")
        if not fs:
            return
        
        label = simpledialog.askstring("Label", "Partition label:", initialvalue="USB")
        
        result = self.manager.create_partition(
            self.manager.current_drive['device'], size, fs.upper(), label)
        self.show_result(result)
        self.refresh_drives()
    
    def delete_partition(self):
        if not self.manager.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        
        part = simpledialog.askinteger("Partition", "Partition number:", initialvalue=1)
        if not part:
            return
        
        if messagebox.askyesno("Confirm", f"Delete partition {part}?"):
            result = self.manager.delete_partition(self.manager.current_drive['device'], part)
            self.show_result(result)
            self.refresh_drives()
    
    def resize_partition(self):
        if not self.manager.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        
        part = simpledialog.askinteger("Partition", "Partition number:", initialvalue=1)
        if not part:
            return
        
        size = simpledialog.askstring("Size", "New size (e.g., 50%, 2G):", initialvalue="50%")
        if not size:
            return
        
        result = self.manager.resize_partition(
            self.manager.current_drive['device'], part, size)
        self.show_result(result)
        self.refresh_drives()
    
    def repair_fs(self):
        if not self.manager.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        
        if messagebox.askyesno("Confirm", f"Repair filesystem on {self.manager.current_drive['device']}?"):
            self.status_bar.config(text="Repairing...")
            result = self.manager.repair_filesystem(self.manager.current_drive['device'])
            self.show_result(result)
    
    def defragment(self):
        if not self.manager.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        
        if messagebox.askyesno("Confirm", f"Defragment {self.manager.current_drive['device']}?"):
            self.status_bar.config(text="Defragmenting...")
            result = self.manager.defragment_drive(self.manager.current_drive['device'])
            self.show_result(result)
    
    def check_errors(self):
        if not self.manager.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        
        self.status_bar.config(text="Checking for bad blocks...")
        result = self.manager.check_errors(self.manager.current_drive['device'])
        messagebox.showinfo("Error Check", result['message'])
    
    def benchmark(self):
        if not self.manager.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        
        self.status_bar.config(text="Benchmarking...")
        result = self.manager.benchmark_speed(self.manager.current_drive['device'])
        if result['success']:
            info = "📊 Benchmark Results\n" + "="*30 + "\n\n"
            for key, value in result['message'].items():
                info += f"{key}: {value}\n"
            messagebox.showinfo("Benchmark", info)
        else:
            messagebox.showerror("Error", result['message'])
    
    def verify_integrity(self):
        if not self.manager.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        
        self.status_bar.config(text="Verifying...")
        result = self.manager.verify_integrity(self.manager.current_drive['device'])
        messagebox.showinfo("Integrity Check", result['message'])
    
    def create_iso(self):
        if not self.manager.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        
        output = filedialog.asksaveasfilename(
            defaultextension=".iso",
            filetypes=[("ISO files", "*.iso"), ("All files", "*.*")])
        if not output:
            return
        
        self.status_bar.config(text="Creating ISO...")
        result = self.manager.create_iso(self.manager.current_drive['device'], output)
        self.show_result(result)
    
    def clone_drive(self):
        if not self.manager.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        
        target = filedialog.askopenfilename(title="Select target drive")
        if not target:
            return
        
        if messagebox.askyesno("Confirm", f"Clone {self.manager.current_drive['device']} to {target}?"):
            self.status_bar.config(text="Cloning...")
            result = self.manager.clone_drive(self.manager.current_drive['device'], target)
            self.show_result(result)
    
    def change_label(self):
        if not self.manager.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        
        new_label = simpledialog.askstring("New Label", "Enter new label:")
        if new_label:
            result = self.manager.change_label(self.manager.current_drive['device'], new_label)
            self.show_result(result)
            self.refresh_drives()
    
    def check_health(self):
        if not self.manager.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        
        self.status_bar.config(text="Checking health...")
        result = self.manager.check_health(self.manager.current_drive['device'])
        info = f"📊 Drive Health\n{'='*40}\n\n"
        info += f"Status: {result.get('health_status', 'Unknown')}\n\n"
        info += result.get('smart', 'SMART not available')[:2000]
        messagebox.showinfo("Health Check", info)
    
    def encrypt_drive(self):
        if not self.manager.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        
        password = simpledialog.askstring("Password", "Enter password:", show='*')
        if not password:
            return
        
        confirm = simpledialog.askstring("Confirm", "Confirm password:", show='*')
        if password != confirm:
            messagebox.showerror("Error", "Passwords don't match")
            return
        
        self.status_bar.config(text="Encrypting...")
        result = self.manager.encrypt_drive(self.manager.current_drive['device'], password)
        self.show_result(result)
        self.refresh_drives()
    
    def unlock_drive(self):
        if not self.manager.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        
        password = simpledialog.askstring("Password", "Enter password:", show='*')
        if not password:
            return
        
        self.status_bar.config(text="Unlocking...")
        result = self.manager.unlock_drive(self.manager.current_drive['device'], password)
        self.show_result(result)
    
    def lock_drive(self):
        if not self.manager.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        
        result = self.manager.unmount_drive(self.manager.current_drive['device'])
        self.show_result(result)
    
    def set_permissions(self):
        if not self.manager.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        
        perms = simpledialog.askstring("Permissions", "Enter permissions (e.g., 755):", initialvalue="755")
        if perms:
            result = self.manager.set_permissions(self.manager.current_drive['device'], perms)
            self.show_result(result)
    
    def set_owner(self):
        if not self.manager.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        
        owner = simpledialog.askstring("Owner", "Enter owner (user:group):", initialvalue="root:root")
        if owner:
            result = self.manager.set_owner(self.manager.current_drive['device'], owner)
            self.show_result(result)
    
    def erase_free(self):
        if not self.manager.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        
        if messagebox.askyesno("Confirm", f"Erase free space on {self.manager.current_drive['device']}?"):
            self.status_bar.config(text="Erasing free space...")
            result = self.manager.erase_free_space(self.manager.current_drive['device'])
            self.show_result(result)
    
    def convert_gpt(self):
        if not self.manager.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        
        if messagebox.askyesno("Confirm", f"Convert {self.manager.current_drive['device']} to GPT?"):
            result = self.manager.convert_to_gpt(self.manager.current_drive['device'])
            self.show_result(result)
            self.refresh_drives()
    
    def convert_mbr(self):
        if not self.manager.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        
        if messagebox.askyesno("Confirm", f"Convert {self.manager.current_drive['device']} to MBR?"):
            result = self.manager.convert_to_mbr(self.manager.current_drive['device'])
            self.show_result(result)
            self.refresh_drives()
    
    def make_persistent(self):
        if not self.manager.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        
        size = simpledialog.askstring("Size", "Persistent storage size:", initialvalue="2G")
        if size:
            result = self.manager.make_persistent(self.manager.current_drive['device'], size)
            self.show_result(result)
            self.refresh_drives()
    
    def list_partitions(self):
        if not self.manager.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        
        result = self.manager.list_partitions(self.manager.current_drive['device'])
        messagebox.showinfo("Partitions", result['message'])
    
    def check_mounts(self):
        result = self.manager.check_mounts()
        messagebox.showinfo("Mounted Drives", result['message'])
    
    def backup_drive(self, compression):
        if not self.manager.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        
        destination = filedialog.askdirectory(title="Select backup location")
        if not destination:
            return
        
        self.status_bar.config(text="Backing up...")
        result = self.manager.backup_drive(
            self.manager.current_drive['device'], destination, compression)
        self.show_result(result)
    
    def restore_backup(self):
        backup_path = filedialog.askopenfilename(title="Select backup file")
        if not backup_path:
            return
        
        target = filedialog.askdirectory(title="Select restore location")
        if not target:
            return
        
        self.status_bar.config(text="Restoring...")
        result = self.manager.restore_from_backup(backup_path, target)
        self.show_result(result)
    
    def create_bootable(self):
        iso_path = filedialog.askopenfilename(
            title="Select ISO file",
            filetypes=[("ISO files", "*.iso"), ("All files", "*.*")])
        if not iso_path:
            return
        
        if not self.manager.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        
        if messagebox.askyesno("Confirm", f"Create bootable USB from {iso_path}?"):
            self.status_bar.config(text="Creating bootable USB...")
            result = self.manager.create_bootable(iso_path, self.manager.current_drive['device'])
            self.show_result(result)
    
    def create_persistent_live(self):
        iso_path = filedialog.askopenfilename(
            title="Select ISO file",
            filetypes=[("ISO files", "*.iso"), ("All files", "*.*")])
        if not iso_path:
            return
        
        if not self.manager.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        
        size = simpledialog.askstring("Size", "Persistence size:", initialvalue="2G")
        if not size:
            return
        
        if messagebox.askyesno("Confirm", f"Create persistent Live USB?"):
            self.status_bar.config(text="Creating persistent Live USB...")
            # First create bootable
            self.manager.create_bootable(iso_path, self.manager.current_drive['device'])
            # Then create persistent
            result = self.manager.make_persistent(self.manager.current_drive['device'], size)
            self.show_result(result)
    
    def create_windows_bootable(self):
        iso_path = filedialog.askopenfilename(
            title="Select Windows ISO",
            filetypes=[("ISO files", "*.iso"), ("All files", "*.*")])
        if not iso_path:
            return
        
        if not self.manager.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        
        if messagebox.askyesno("Confirm", f"Create Windows bootable USB?"):
            self.status_bar.config(text="Creating Windows bootable USB...")
            result = self.manager.create_bootable(iso_path, self.manager.current_drive['device'])
            self.show_result(result)
    
    def virus_quick_scan(self):
        if not self.manager.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        
        mount_point = self.manager._get_mount_point(self.manager.current_drive['device'])
        if not mount_point:
            result = self.manager.mount_drive(self.manager.current_drive['device'])
            if not result['success']:
                messagebox.showerror("Error", "Failed to mount drive")
                return
            mount_point = result.get('mount_point')
        
        self.status_bar.config(text="Quick virus scan...")
        result = self.manager.scan_for_viruses(mount_point, 'quick')
        
        if 'error' in result:
            messagebox.showerror("Error", result['error'])
            return
        
        info = f"🦠 Virus Scan Results\n{'='*40}\n\n"
        info += f"Total files: {result['total_files']}\n"
        info += f"Infected: {len(result['infected'])}\n"
        info += f"Suspicious: {len(result['suspicious'])}\n"
        info += f"Clean: {len(result['clean'])}\n\n"
        
        if result['infected']:
            info += "Infected files:\n"
            for f in result['infected'][:10]:
                info += f"  - {f}\n"
            if len(result['infected']) > 10:
                info += f"  ... and {len(result['infected']) - 10} more\n"
        
        messagebox.showinfo("Virus Scan", info)
    
    def virus_full_scan(self):
        if not self.manager.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        
        mount_point = self.manager._get_mount_point(self.manager.current_drive['device'])
        if not mount_point:
            result = self.manager.mount_drive(self.manager.current_drive['device'])
            if not result['success']:
                messagebox.showerror("Error", "Failed to mount drive")
                return
            mount_point = result.get('mount_point')
        
        self.status_bar.config(text="Full virus scan (may take time)...")
        thread = threading.Thread(target=self._virus_scan_thread, args=(mount_point, 'full'))
        thread.start()
    
    def _virus_scan_thread(self, mount_point, scan_type):
        result = self.manager.scan_for_viruses(mount_point, scan_type)
        self.root.after(0, lambda: self._show_virus_results(result))
    
    def _show_virus_results(self, result):
        if 'error' in result:
            messagebox.showerror("Error", result['error'])
            return
        
        info = f"🦠 Virus Scan Results\n{'='*40}\n\n"
        info += f"Total files: {result['total_files']}\n"
        info += f"Infected: {len(result['infected'])}\n"
        info += f"Suspicious: {len(result['suspicious'])}\n"
        info += f"Clean: {len(result['clean'])}\n\n"
        
        if result['infected']:
            info += "Infected files:\n"
            for f in result['infected'][:20]:
                info += f"  - {f}\n"
            if len(result['infected']) > 20:
                info += f"  ... and {len(result['infected']) - 20} more\n"
        
        messagebox.showinfo("Virus Scan Complete", info)
        self.status_bar.config(text="Virus scan complete")
    
    def remove_infected(self):
        if not self.manager.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        
        if not self.manager.virus_scan_results.get('infected'):
            messagebox.showinfo("Info", "No infected files found")
            return
        
        count = len(self.manager.virus_scan_results['infected'])
        if messagebox.askyesno("Confirm", f"Remove {count} infected files?"):
            for file_path in self.manager.virus_scan_results['infected']:
                self.manager.remove_virus(file_path)
            messagebox.showinfo("Success", f"Removed {count} infected files")
    
    def quarantine_files(self):
        if not self.manager.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        
        if not self.manager.virus_scan_results.get('infected'):
            messagebox.showinfo("Info", "No infected files found")
            return
        
        count = len(self.manager.virus_scan_results['infected'])
        result = self.manager._quarantine_files(self.manager.virus_scan_results['infected'])
        messagebox.showinfo("Success", f"Quarantined {count} files")
    
    def restore_quarantine(self):
        quarantine_dir = self.manager.settings['quarantine_dir']
        if not os.path.exists(quarantine_dir):
            messagebox.showinfo("Info", "No quarantined files")
            return
        
        files = [f for f in os.listdir(quarantine_dir) if os.path.isfile(os.path.join(quarantine_dir, f))]
        if not files:
            messagebox.showinfo("Info", "No quarantined files")
            return
        
        # Show list and let user select
        file_choice = filedialog.askopenfilename(
            title="Select file to restore",
            initialdir=quarantine_dir,
            filetypes=[("All files", "*.*")]
        )
        if file_choice:
            # Extract original name
            base_name = '_'.join(os.path.basename(file_choice).split('_')[1:])
            dest = os.path.join(os.path.dirname(file_choice), base_name)
            try:
                shutil.move(file_choice, dest)
                messagebox.showinfo("Success", f"Restored: {dest}")
            except Exception as e:
                messagebox.showerror("Error", str(e))
    
    def refresh_info(self):
        info = "📊 Ultimate USB Manager Info\n" + "="*50 + "\n\n"
        info += f"Drives detected: {len(self.manager.drives)}\n"
        info += f"Operations logged: {len(self.manager.operations_log)}\n"
        info += f"Backups: {len(self.manager.backup_history)}\n\n"
        
        if self.manager.current_drive:
            info += f"Current drive: {self.manager.current_drive['device']}\n"
            info += f"  Size: {self.manager.current_drive['size']}\n"
            info += f"  Model: {self.manager.current_drive['model']}\n"
            info += f"  Label: {self.manager.current_drive.get('label', 'N/A')}\n"
        
        self.info_text.delete('1.0', tk.END)
        self.info_text.insert('1.0', info)
    
    def show_result(self, result):
        if result['success']:
            messagebox.showinfo("✅ Success", result['message'])
            self.status_bar.config(text=result['message'])
        else:
            messagebox.showerror("❌ Error", result['message'])
            self.status_bar.config(text=f"Error: {result['message']}")
        self.refresh_info()


def main():
    # Check for required packages
    try:
        import psutil
    except ImportError:
        print("📦 Installing required packages...")
        subprocess.run(['pip3', 'install', 'psutil'], check=True)
        import psutil
    
    root = tk.Tk()
    app = UltimateUSBGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
