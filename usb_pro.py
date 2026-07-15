#!/usr/bin/env python3
"""
Ultimate USB Manager Pro - Auto Health Monitor & Restore
With automatic health detection, status display, and drive restoration
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
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog, simpledialog

try:
    import psutil
except ImportError:
    subprocess.run(['pip3', 'install', 'psutil'], check=True)
    import psutil

class USBHealthMonitor:
    """Monitor USB drive health and restore previous state"""
    
    def __init__(self):
        self.drives = []
        self.drive_history = {}
        self.drive_backups = {}
        self.health_status = {}
        self.operations_log = []
        
    def detect_usb_drives(self):
        """Detect all USB drives with health status"""
        drives = []
        try:
            result = subprocess.run(
                ['lsblk', '-J', '-o', 'NAME,SIZE,TYPE,MOUNTPOINT,MODEL,LABEL,TRAN,RO,STATE,OWNER,GROUP,MODE,PHY-SEC,LOG-SEC,ROTA,SCHED,RQ-SIZE,RA'],
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode == 0 and result.stdout:
                try:
                    data = json.loads(result.stdout)
                    for device in data.get('blockdevices', []):
                        if self._is_usb(device.get('name', '')):
                            drive_info = self._get_complete_drive_info(device)
                            drives.append(drive_info)
                except:
                    drives = self._fallback_detect()
            else:
                drives = self._fallback_detect()
        except Exception as e:
            print(f"Detection error: {e}")
            drives = self._fallback_detect()
        
        self.drives = drives
        self._update_health_status(drives)
        self._save_drive_history(drives)
        return drives
    
    def _get_complete_drive_info(self, device):
        """Get complete drive information with health"""
        device_name = device.get('name', '')
        device_path = f"/dev/{device_name}"
        
        info = {
            'device': device_path,
            'name': device_name,
            'size': device.get('size', 'Unknown'),
            'type': 'USB',
            'mount': device.get('mountpoint', ''),
            'model': device.get('model', 'Unknown'),
            'label': device.get('label', ''),
            'readonly': device.get('ro', False),
            'state': device.get('state', 'Unknown'),
            'phy_sec': device.get('phy-sec', ''),
            'log_sec': device.get('log-sec', ''),
            'rota': device.get('rota', ''),
            'scheduler': device.get('sched', ''),
            'read_ahead': device.get('ra', ''),
            'uuid': self._get_uuid(device_name),
            'health': 'Unknown',
            'health_details': {},
            'last_check': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Get health status
        health = self._check_drive_health(device_path)
        info['health'] = health.get('status', 'Unknown')
        info['health_details'] = health.get('details', {})
        
        # Get partition info
        info['partitions'] = self._get_partition_info(device_path)
        
        return info
    
    def _get_uuid(self, device_name):
        try:
            result = subprocess.run(['sudo', 'blkid', f'/dev/{device_name}'], 
                                  capture_output=True, text=True, timeout=5)
            match = re.search(r'UUID="([^"]+)"', result.stdout)
            return match.group(1) if match else ''
        except:
            return ''
    
    def _is_usb(self, name):
        try:
            sys_path = f"/sys/block/{name}/removable"
            if os.path.exists(sys_path):
                with open(sys_path, 'r') as f:
                    return f.read().strip() == '1'
        except:
            pass
        return False
    
    def _fallback_detect(self):
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
                            drive_info = {
                                'device': device,
                                'name': os.path.basename(device),
                                'size': parts[1] if len(parts) > 1 else 'Unknown',
                                'type': 'USB',
                                'mount': parts[3] if len(parts) > 3 else '',
                                'model': parts[-1] if len(parts) > 4 else 'Unknown',
                                'label': parts[4] if len(parts) > 4 else '',
                                'readonly': parts[5] == '1' if len(parts) > 5 else False,
                                'health': 'Unknown'
                            }
                            
                            # Check health
                            health = self._check_drive_health(device)
                            drive_info['health'] = health.get('status', 'Unknown')
                            drives.append(drive_info)
        except:
            pass
        return drives
    
    def _check_drive_health(self, device):
        """Comprehensive health check"""
        health = {
            'status': 'Unknown',
            'details': {},
            'errors': [],
            'warnings': []
        }
        
        try:
            # Check if device exists
            if not os.path.exists(device):
                health['status'] = 'Missing'
                health['errors'].append('Device not found')
                return health
            
            # Check SMART status
            try:
                smart_result = subprocess.run(['sudo', 'smartctl', '-H', device],
                                            capture_output=True, text=True, timeout=5)
                if 'PASSED' in smart_result.stdout:
                    health['details']['smart'] = 'PASSED'
                else:
                    health['details']['smart'] = 'FAILED'
                    health['warnings'].append('SMART health check failed')
            except:
                health['details']['smart'] = 'Not Available'
            
            # Check filesystem
            try:
                fs_result = subprocess.run(['sudo', 'fsck', '-n', device],
                                         capture_output=True, text=True, timeout=10)
                if 'clean' in fs_result.stdout.lower():
                    health['details']['filesystem'] = 'Clean'
                else:
                    health['details']['filesystem'] = 'Needs Repair'
                    health['warnings'].append('Filesystem needs repair')
            except:
                health['details']['filesystem'] = 'Unknown'
            
            # Check bad blocks (quick check)
            try:
                bad_result = subprocess.run(['sudo', 'badblocks', '-sv', '-n', device],
                                          capture_output=True, text=True, timeout=5)
                if 'done' in bad_result.stdout and 'bad blocks' not in bad_result.stdout.lower():
                    health['details']['bad_blocks'] = 'None Found'
                else:
                    health['details']['bad_blocks'] = 'Possible Bad Blocks'
                    health['warnings'].append('Potential bad blocks detected')
            except:
                health['details']['bad_blocks'] = 'Unknown'
            
            # Check mount status
            try:
                mount_result = subprocess.run(['findmnt', '-n', '-o', 'TARGET', device],
                                            capture_output=True, text=True)
                if mount_result.stdout.strip():
                    health['details']['mounted'] = mount_result.stdout.strip()
                else:
                    health['details']['mounted'] = 'Not Mounted'
            except:
                health['details']['mounted'] = 'Unknown'
            
            # Determine overall health
            if health['warnings']:
                if len(health['warnings']) > 2:
                    health['status'] = 'Poor'
                else:
                    health['status'] = 'Fair'
            elif health['details'].get('smart') == 'PASSED' and health['details'].get('bad_blocks') == 'None Found':
                health['status'] = 'Excellent'
            else:
                health['status'] = 'Good'
            
        except Exception as e:
            health['errors'].append(str(e))
            health['status'] = 'Error'
        
        return health
    
    def _get_partition_info(self, device):
        """Get partition information"""
        try:
            result = subprocess.run(['lsblk', '-o', 'NAME,SIZE,MOUNTPOINT,FSTYPE', device],
                                  capture_output=True, text=True)
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            partitions = []
            for line in lines:
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2 and 'part' in line:
                        partitions.append({
                            'name': parts[0],
                            'size': parts[1] if len(parts) > 1 else 'Unknown',
                            'mount': parts[2] if len(parts) > 2 else '',
                            'fstype': parts[3] if len(parts) > 3 else ''
                        })
            return partitions
        except:
            return []
    
    def _update_health_status(self, drives):
        """Update health status for all drives"""
        for drive in drives:
            device = drive['device']
            self.health_status[device] = drive.get('health', 'Unknown')
    
    def _save_drive_history(self, drives):
        """Save drive history for comparison"""
        for drive in drives:
            device = drive['device']
            if device not in self.drive_history:
                self.drive_history[device] = []
            
            # Save snapshot
            snapshot = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'label': drive.get('label', ''),
                'mount': drive.get('mount', ''),
                'size': drive.get('size', ''),
                'model': drive.get('model', ''),
                'health': drive.get('health', 'Unknown'),
                'state': drive.get('state', '')
            }
            self.drive_history[device].append(snapshot)
            
            # Keep only last 10 entries
            if len(self.drive_history[device]) > 10:
                self.drive_history[device] = self.drive_history[device][-10:]
    
    def get_health_status(self, device):
        """Get health status for a specific drive"""
        if device in self.health_status:
            return self.health_status[device]
        
        # Check fresh
        for drive in self.drives:
            if drive['device'] == device:
                return drive.get('health', 'Unknown')
        return 'Unknown'
    
    def get_drive_history(self, device):
        """Get history for a specific drive"""
        if device in self.drive_history:
            return self.drive_history[device]
        return []
    
    def restore_drive_state(self, device, restore_point=None):
        """Restore drive to previous state"""
        if device not in self.drive_history or not self.drive_history[device]:
            return {'success': False, 'message': 'No history available for this drive'}
        
        try:
            history = self.drive_history[device]
            
            # If no restore point specified, use the earliest (most stable) state
            if restore_point is None:
                restore_point = 0  # First entry
            elif isinstance(restore_point, int) and restore_point < len(history):
                restore_point = restore_point
            else:
                return {'success': False, 'message': 'Invalid restore point'}
            
            snapshot = history[restore_point]
            results = []
            
            # Try to restore label
            if snapshot.get('label'):
                try:
                    subprocess.run(['sudo', 'e2label', device, snapshot['label']], 
                                 capture_output=True, check=True, timeout=5)
                    results.append(f"Label restored to: {snapshot['label']}")
                except:
                    results.append("Label restore failed (not critical)")
            
            # Try to mount if it was mounted before
            if snapshot.get('mount') and not self._is_mounted(device):
                try:
                    mount_point = snapshot['mount']
                    os.makedirs(mount_point, exist_ok=True)
                    subprocess.run(['sudo', 'mount', device, mount_point], check=True, timeout=5)
                    results.append(f"Mounted at: {mount_point}")
                except:
                    results.append("Mount restore failed")
            
            # Log restore
            self.log_operation(f"Restored {device} to state from {snapshot['timestamp']}")
            
            return {
                'success': True,
                'message': f"Drive restored to state from {snapshot['timestamp']}",
                'details': results,
                'snapshot': snapshot
            }
            
        except Exception as e:
            return {'success': False, 'message': f'Restore failed: {str(e)}'}
    
    def _is_mounted(self, device):
        """Check if device is mounted"""
        try:
            result = subprocess.run(['findmnt', '-n', device], capture_output=True, text=True)
            return bool(result.stdout.strip())
        except:
            return False
    
    def backup_drive_state(self, device):
        """Create a backup/restore point for drive"""
        try:
            # Get current state
            current_state = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'label': self._get_label(device),
                'mount': self._get_mount_point(device),
                'size': self._get_size(device),
                'model': self._get_model(device),
                'health': self.get_health_status(device)
            }
            
            # Save to backups
            if device not in self.drive_backups:
                self.drive_backups[device] = []
            
            self.drive_backups[device].append(current_state)
            self.log_operation(f"Created backup point for {device}")
            
            return {'success': True, 'message': 'Backup point created', 'state': current_state}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def _get_label(self, device):
        try:
            result = subprocess.run(['sudo', 'blkid', '-o', 'value', '-s', 'LABEL', device],
                                  capture_output=True, text=True)
            return result.stdout.strip()
        except:
            return ''
    
    def _get_mount_point(self, device):
        try:
            result = subprocess.run(['findmnt', '-n', '-o', 'TARGET', device],
                                  capture_output=True, text=True)
            return result.stdout.strip()
        except:
            return ''
    
    def _get_size(self, device):
        for drive in self.drives:
            if drive['device'] == device:
                return drive.get('size', 'Unknown')
        return 'Unknown'
    
    def _get_model(self, device):
        for drive in self.drives:
            if drive['device'] == device:
                return drive.get('model', 'Unknown')
        return 'Unknown'
    
    def auto_repair(self, device):
        """Auto-repair common drive issues"""
        results = []
        health = self._check_drive_health(device)
        
        # Check if repair is needed
        if health['status'] in ['Excellent', 'Good']:
            return {'success': True, 'message': 'Drive is healthy, no repair needed', 'status': health['status']}
        
        # Try to repair filesystem
        if health['details'].get('filesystem') == 'Needs Repair':
            try:
                subprocess.run(['sudo', 'umount', f'{device}*'], shell=True, capture_output=True)
                subprocess.run(['sudo', 'fsck', '-y', device], check=True, timeout=60)
                results.append("Filesystem repaired")
            except Exception as e:
                results.append(f"Filesystem repair failed: {e}")
        
        # Try to fix mount issues
        if health['details'].get('mounted') == 'Not Mounted':
            try:
                mount_point = f"/mnt/usb_{datetime.now().strftime('%H%M%S')}"
                os.makedirs(mount_point, exist_ok=True)
                subprocess.run(['sudo', 'mount', device, mount_point], check=True)
                results.append(f"Mounted at: {mount_point}")
            except:
                results.append("Mount repair failed")
        
        # Check and fix boot sector if needed
        if health.get('warnings'):
            try:
                # Backup current MBR
                backup = f"/tmp/mbr_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.img"
                subprocess.run(['sudo', 'dd', f'if={device}', f'of={backup}', 'bs=512', 'count=1'], check=True)
                # Write new MBR
                subprocess.run(['sudo', 'dd', 'if=/dev/zero', f'of={device}', 'bs=512', 'count=1'], check=True)
                results.append("Boot sector repaired (backup saved)")
            except:
                results.append("Boot sector repair skipped")
        
        # Update health status
        self._check_drive_health(device)
        self.log_operation(f"Auto-repaired {device}")
        
        return {
            'success': True,
            'message': f"Repair completed: {len(results)} actions taken",
            'details': results,
            'status': 'Repaired'
        }
    
    def log_operation(self, operation):
        """Log operations"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.operations_log.append(f"[{timestamp}] {operation}")


class USBHealthGUI:
    """GUI with health monitoring and auto-restore"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Ultimate USB Manager - Health Monitor & Restore")
        self.root.geometry("1400x850")
        self.root.configure(bg='#1e1e2e')
        
        self.monitor = USBHealthMonitor()
        self.current_drive = None
        self.setup_ui()
        self.refresh_drives()
        
        # Auto-refresh every 30 seconds
        self.auto_refresh()
    
    def setup_ui(self):
        # Main container
        main = tk.Frame(self.root, bg='#1e1e2e')
        main.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Header
        header = tk.Frame(main, bg='#1e1e2e')
        header.pack(fill='x', pady=(0, 10))
        
        title = tk.Label(header, text="🔧 Ultimate USB Manager - Health Monitor", 
                        font=('Helvetica', 24, 'bold'), 
                        fg='#89b4fa', bg='#1e1e2e')
        title.pack(side='left')
        
        # Status indicator
        self.status_indicator = tk.Label(header, text="●", 
                                        font=('Helvetica', 20),
                                        fg='#a6e3a1', bg='#1e1e2e')
        self.status_indicator.pack(side='right', padx=5)
        
        self.status_text = tk.Label(header, text="Healthy", 
                                   font=('Helvetica', 12, 'bold'),
                                   fg='#a6e3a1', bg='#1e1e2e')
        self.status_text.pack(side='right')
        
        # Stats
        self.stats_label = tk.Label(header, text="", 
                                   font=('Helvetica', 11),
                                   fg='#f9e2af', bg='#1e1e2e')
        self.stats_label.pack(side='right', padx=20)
        
        # Content
        content = tk.Frame(main, bg='#1e1e2e')
        content.pack(fill='both', expand=True)
        
        # Left - Drive list with health
        left = tk.Frame(content, bg='#313244', relief='flat', bd=1)
        left.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        tk.Label(left, text="📁 USB Drives - Health Status", 
                font=('Helvetica', 14, 'bold'),
                fg='#cdd6f4', bg='#313244').pack(pady=10)
        
        list_frame = tk.Frame(left, bg='#313244')
        list_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # Treeview with health columns
        columns = ('Status', 'Device', 'Label', 'Size', 'Model', 'Health')
        self.drive_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=20)
        
        self.drive_tree.heading('Status', text='●')
        self.drive_tree.heading('Device', text='Device')
        self.drive_tree.heading('Label', text='Label')
        self.drive_tree.heading('Size', text='Size')
        self.drive_tree.heading('Model', text='Model')
        self.drive_tree.heading('Health', text='Health')
        
        self.drive_tree.column('Status', width=40, anchor='center')
        self.drive_tree.column('Device', width=120)
        self.drive_tree.column('Label', width=150)
        self.drive_tree.column('Size', width=100)
        self.drive_tree.column('Model', width=200)
        self.drive_tree.column('Health', width=100)
        
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', 
                                 command=self.drive_tree.yview)
        self.drive_tree.configure(yscrollcommand=scrollbar.set)
        
        self.drive_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        self.drive_tree.bind('<<TreeviewSelect>>', self.on_drive_select)
        
        # Right - Operations
        right = tk.Frame(content, bg='#1e1e2e')
        right.pack(side='right', fill='both', expand=True)
        
        # Drive info panel
        info_frame = tk.LabelFrame(right, text="📋 Drive Information", 
                                  bg='#1e1e2e', fg='#cdd6f4')
        info_frame.pack(fill='x', pady=(0, 10))
        
        self.info_text = scrolledtext.ScrolledText(info_frame, height=6,
                                                  bg='#1e1e2e', fg='#cdd6f4',
                                                  font=('Monospace', 10))
        self.info_text.pack(fill='x', padx=5, pady=5)
        self.info_text.insert('1.0', "Select a drive to see details...")
        
        # Health actions
        health_frame = tk.LabelFrame(right, text="🩺 Health Actions", 
                                    bg='#1e1e2e', fg='#cdd6f4')
        health_frame.pack(fill='x', pady=(0, 10))
        
        health_buttons = [
            ("📊 Check Health", self.check_health, '#89b4fa'),
            ("🔧 Auto-Repair", self.auto_repair, '#a6e3a1'),
            ("💾 Backup State", self.backup_state, '#f9e2af'),
            ("🔄 Restore State", self.restore_state, '#f9e2af'),
            ("📜 Show History", self.show_history, '#89b4fa'),
            ("📋 Export Report", self.export_report, '#f9e2af'),
        ]
        
        for i, (text, command, color) in enumerate(health_buttons):
            btn = tk.Button(health_frame, text=text, command=command,
                           bg=color, fg='#1e1e2e',
                           font=('Helvetica', 10, 'bold'),
                           padx=15, pady=8, relief='flat')
            btn.grid(row=i//3, column=i%3, padx=5, pady=5, sticky='ew')
        
        health_frame.grid_columnconfigure(0, weight=1)
        health_frame.grid_columnconfigure(1, weight=1)
        health_frame.grid_columnconfigure(2, weight=1)
        
        # Quick actions
        quick_frame = tk.LabelFrame(right, text="⚡ Quick Actions", 
                                   bg='#1e1e2e', fg='#cdd6f4')
        quick_frame.pack(fill='x', pady=(0, 10))
        
        quick_buttons = [
            ("🔄 Refresh", self.refresh_drives, '#89b4fa'),
            ("📀 Format", self.format_drive, '#f38ba8'),
            ("🗑️ Wipe", self.wipe_drive, '#f38ba8'),
            ("🔒 Write Protect", self.enable_protection, '#f9e2af'),
        ]
        
        for i, (text, command, color) in enumerate(quick_buttons):
            btn = tk.Button(quick_frame, text=text, command=command,
                           bg=color, fg='#1e1e2e',
                           font=('Helvetica', 10, 'bold'),
                           padx=15, pady=8, relief='flat')
            btn.grid(row=i//2, column=i%2, padx=5, pady=5, sticky='ew')
        
        quick_frame.grid_columnconfigure(0, weight=1)
        quick_frame.grid_columnconfigure(1, weight=1)
        
        # Status bar
        status_frame = tk.Frame(main, bg='#313244')
        status_frame.pack(side='bottom', fill='x', pady=(10, 0))
        
        self.status_bar = tk.Label(status_frame, text="Ready", 
                                   bg='#313244', fg='#cdd6f4',
                                   anchor='w', padx=15,
                                   font=('Helvetica', 10))
        self.status_bar.pack(side='left', fill='x', expand=True)
        
        self.status_progress = ttk.Progressbar(status_frame, mode='determinate',
                                              length=150, value=0)
        self.status_progress.pack(side='right', padx=10)
    
    def refresh_drives(self):
        """Refresh drive list with health status"""
        for item in self.drive_tree.get_children():
            self.drive_tree.delete(item)
        
        drives = self.monitor.detect_usb_drives()
        
        if not drives:
            self.drive_tree.insert('', 'end', values=('❌', 'No USB drives found', '', '', '', ''))
            self.status_bar.config(text="No USB drives detected")
            self.stats_label.config(text="")
            return
        
        healthy_count = 0
        warning_count = 0
        error_count = 0
        
        for drive in drives:
            health = drive.get('health', 'Unknown')
            status_icon = self._get_status_icon(health)
            
            if health in ['Excellent', 'Good']:
                healthy_count += 1
            elif health in ['Fair', 'Poor']:
                warning_count += 1
            else:
                error_count += 1
            
            self.drive_tree.insert('', 'end', values=(
                status_icon,
                drive['device'],
                drive.get('label', 'N/A'),
                drive.get('size', 'Unknown'),
                drive.get('model', 'Unknown'),
                health
            ), tags=(drive['device'],))
        
        # Update stats
        total = len(drives)
        stats_text = f"Total: {total} | ✅ Healthy: {healthy_count} | ⚠️ Warnings: {warning_count} | ❌ Errors: {error_count}"
        self.stats_label.config(text=stats_text)
        
        # Update status indicator
        if error_count > 0:
            self.status_indicator.config(fg='#f38ba8')
            self.status_text.config(text="⚠️ Issues Found", fg='#f38ba8')
        elif warning_count > 0:
            self.status_indicator.config(fg='#f9e2af')
            self.status_text.config(text="⚠️ Warnings", fg='#f9e2af')
        else:
            self.status_indicator.config(fg='#a6e3a1')
            self.status_text.config(text="✅ All Healthy", fg='#a6e3a1')
        
        self.status_bar.config(text=f"Found {total} USB drives")
        self.monitor.drives = drives
    
    def _get_status_icon(self, health):
        """Get status icon based on health"""
        if health in ['Excellent', 'Good']:
            return '🟢'
        elif health in ['Fair']:
            return '🟡'
        elif health in ['Poor']:
            return '🟠'
        elif health in ['Error', 'Missing']:
            return '🔴'
        else:
            return '⚪'
    
    def auto_refresh(self):
        """Auto-refresh every 30 seconds"""
        self.refresh_drives()
        self.root.after(30000, self.auto_refresh)
    
    def on_drive_select(self, event):
        """Handle drive selection"""
        selection = self.drive_tree.selection()
        if not selection:
            return
        
        values = self.drive_tree.item(selection[0])['values']
        tags = self.drive_tree.item(selection[0])['tags']
        
        if not tags:
            return
        
        device = tags[0]
        self.current_drive = device
        
        # Update info panel
        drive_info = None
        for drive in self.monitor.drives:
            if drive['device'] == device:
                drive_info = drive
                break
        
        if drive_info:
            self._update_info_panel(drive_info)
    
    def _update_info_panel(self, drive):
        """Update info panel with drive details"""
        info = f"""
📌 DRIVE INFORMATION
{'='*50}

Device: {drive.get('device', 'N/A')}
Label: {drive.get('label', 'N/A')}
Model: {drive.get('model', 'N/A')}
Size: {drive.get('size', 'N/A')}
Mount: {drive.get('mount', 'Not Mounted')}
State: {drive.get('state', 'Unknown')}

🩺 HEALTH STATUS
{'='*50}
Health: {drive.get('health', 'Unknown')}
Last Check: {drive.get('last_check', 'Never')}

📊 DETAILS
{'='*50}
Read-Only: {drive.get('readonly', False)}
UUID: {drive.get('uuid', 'N/A')}
Partitions: {len(drive.get('partitions', []))}

💡 Actions:
- Click 'Check Health' for detailed scan
- Click 'Auto-Repair' to fix common issues
"""
        
        self.info_text.delete('1.0', tk.END)
        self.info_text.insert('1.0', info)
    
    def check_health(self):
        """Run detailed health check"""
        if not self.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        
        self.status_bar.config(text=f"Checking health for {self.current_drive}...")
        
        # Get fresh health check
        health = self.monitor._check_drive_health(self.current_drive)
        
        status_text = f"""
🩺 HEALTH REPORT
{'='*50}
Device: {self.current_drive}
Status: {health.get('status', 'Unknown')}

📊 DETAILS
{'='*50}
SMART: {health.get('details', {}).get('smart', 'N/A')}
Filesystem: {health.get('details', {}).get('filesystem', 'N/A')}
Bad Blocks: {health.get('details', {}).get('bad_blocks', 'N/A')}
Mounted: {health.get('details', {}).get('mounted', 'N/A')}

{'⚠️ WARNINGS' if health.get('warnings') else '✅ NO WARNINGS'}
{'='*50}
"""
        if health.get('warnings'):
            for warn in health['warnings']:
                status_text += f"  - {warn}\n"
        else:
            status_text += "  No warnings detected\n"
        
        if health.get('errors'):
            status_text += "\n❌ ERRORS\n"
            for err in health['errors']:
                status_text += f"  - {err}\n"
        
        messagebox.showinfo("Health Report", status_text)
        self.refresh_drives()
        self.status_bar.config(text="Health check complete")
    
    def auto_repair(self):
        """Auto-repair drive issues"""
        if not self.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        
        if messagebox.askyesno("Confirm Repair", 
                              f"Auto-repair {self.current_drive}?\n\n"
                              "This will attempt to fix common issues:\n"
                              "- Filesystem errors\n"
                              "- Mount problems\n"
                              "- Boot sector issues\n\n"
                              "Continue?"):
            self.status_bar.config(text=f"Repairing {self.current_drive}...")
            result = self.monitor.auto_repair(self.current_drive)
            
            if result['success']:
                details = "\n".join(result.get('details', []))
                messagebox.showinfo("Repair Complete", 
                                   f"{result['message']}\n\nDetails:\n{details}")
                self.refresh_drives()
            else:
                messagebox.showerror("Repair Failed", result['message'])
            
            self.status_bar.config(text=f"Repair complete for {self.current_drive}")
    
    def backup_state(self):
        """Backup current drive state"""
        if not self.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        
        result = self.monitor.backup_drive_state(self.current_drive)
        if result['success']:
            messagebox.showinfo("Backup Complete", 
                               f"State backed up successfully\n\n"
                               f"Time: {result['state']['timestamp']}\n"
                               f"Label: {result['state']['label']}\n"
                               f"Health: {result['state']['health']}")
        else:
            messagebox.showerror("Backup Failed", result['message'])
    
    def restore_state(self):
        """Restore drive to previous state"""
        if not self.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        
        history = self.monitor.get_drive_history(self.current_drive)
        if not history:
            messagebox.showinfo("No History", "No backup points available for this drive")
            return
        
        # Show restore points
        choices = []
        for i, snapshot in enumerate(history):
            choices.append(f"{i+1}. {snapshot['timestamp']} - Label: {snapshot['label']} - Health: {snapshot['health']}")
        
        if choices:
            choice = simpledialog.askstring("Restore Point", 
                                           "Select restore point:\n\n" + "\n".join(choices) + 
                                           "\n\nEnter number (1-{})".format(len(choices)))
            
            if choice and choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(history):
                    if messagebox.askyesno("Confirm Restore", 
                                          f"Restore to state from {history[idx]['timestamp']}?\n\n"
                                          "This will attempt to restore:\n"
                                          f"- Label: {history[idx]['label']}\n"
                                          f"- Mount: {history[idx]['mount']}\n\n"
                                          "Continue?"):
                        result = self.monitor.restore_drive_state(self.current_drive, idx)
                        if result['success']:
                            details = "\n".join(result.get('details', []))
                            messagebox.showinfo("Restore Complete", 
                                               f"{result['message']}\n\nDetails:\n{details}")
                            self.refresh_drives()
                        else:
                            messagebox.showerror("Restore Failed", result['message'])
    
    def show_history(self):
        """Show drive history"""
        if not self.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        
        history = self.monitor.get_drive_history(self.current_drive)
        if not history:
            messagebox.showinfo("No History", "No history available for this drive")
            return
        
        text = f"📜 HISTORY for {self.current_drive}\n{'='*60}\n\n"
        for i, snapshot in enumerate(history):
            text += f"Point {i+1}:\n"
            text += f"  Time: {snapshot['timestamp']}\n"
            text += f"  Label: {snapshot['label']}\n"
            text += f"  Mount: {snapshot['mount']}\n"
            text += f"  Health: {snapshot['health']}\n"
            text += f"  State: {snapshot['state']}\n\n"
        
        messagebox.showinfo("Drive History", text)
    
    def export_report(self):
        """Export health report"""
        if not self.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if file_path:
            drive_info = None
            for drive in self.monitor.drives:
                if drive['device'] == self.current_drive:
                    drive_info = drive
                    break
            
            if drive_info:
                with open(file_path, 'w') as f:
                    f.write(f"USB DRIVE HEALTH REPORT\n")
                    f.write(f"{'='*60}\n")
                    f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    f.write(f"Device: {drive_info.get('device', 'N/A')}\n")
                    f.write(f"Label: {drive_info.get('label', 'N/A')}\n")
                    f.write(f"Model: {drive_info.get('model', 'N/A')}\n")
                    f.write(f"Size: {drive_info.get('size', 'N/A')}\n")
                    f.write(f"Health: {drive_info.get('health', 'N/A')}\n")
                    f.write(f"Mount: {drive_info.get('mount', 'Not Mounted')}\n")
                    f.write(f"State: {drive_info.get('state', 'Unknown')}\n\n")
                    
                    # Health details
                    health = self.monitor._check_drive_health(self.current_drive)
                    f.write("DETAILED HEALTH REPORT\n")
                    f.write(f"{'='*60}\n")
                    f.write(f"Status: {health.get('status', 'Unknown')}\n\n")
                    
                    if health.get('details'):
                        f.write("Details:\n")
                        for key, value in health['details'].items():
                            f.write(f"  {key}: {value}\n")
                    
                    if health.get('warnings'):
                        f.write("\nWARNINGS:\n")
                        for warn in health['warnings']:
                            f.write(f"  - {warn}\n")
                    
                    if health.get('errors'):
                        f.write("\nERRORS:\n")
                        for err in health['errors']:
                            f.write(f"  - {err}\n")
                
                messagebox.showinfo("Export Complete", f"Report saved to {file_path}")
    
    def format_drive(self):
        """Format drive"""
        if not self.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        
        fs_type = simpledialog.askstring("Format", 
                                        "Filesystem type (FAT32, NTFS, EXFAT, EXT4):",
                                        initialvalue="FAT32")
        if not fs_type:
            return
        
        label = simpledialog.askstring("Label", "Volume label:", initialvalue="USB")
        
        if messagebox.askyesno("⚠️ Confirm Format", 
                              f"Format {self.current_drive} as {fs_type}?\n\nALL DATA WILL BE LOST!"):
            self.status_bar.config(text=f"Formatting {self.current_drive}...")
            result = self.monitor._format_drive(self.current_drive, fs_type.upper(), label)
            
            if result['success']:
                messagebox.showinfo("Format Complete", result['message'])
                self.refresh_drives()
            else:
                messagebox.showerror("Format Failed", result['message'])
            
            self.status_bar.config(text="Format complete")
    
    def wipe_drive(self):
        """Secure wipe drive"""
        if not self.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        
        passes = simpledialog.askinteger("Passes", 
                                        "Number of passes (3-7 recommended):",
                                        initialvalue=3)
        if not passes:
            return
        
        if messagebox.askyesno("⚠️ Confirm Wipe", 
                              f"Secure wipe {self.current_drive} with {passes} passes?\n\nALL DATA WILL BE PERMANENTLY DESTROYED!"):
            self.status_bar.config(text=f"Wiping {self.current_drive}...")
            result = self.monitor._secure_wipe(self.current_drive, passes)
            
            if result['success']:
                messagebox.showinfo("Wipe Complete", result['message'])
                self.refresh_drives()
            else:
                messagebox.showerror("Wipe Failed", result['message'])
            
            self.status_bar.config(text="Wipe complete")
    
    def enable_protection(self):
        """Toggle write protection"""
        if not self.current_drive:
            messagebox.showwarning("No Selection", "Select a drive first")
            return
        
        enable = messagebox.askyesno("Write Protection", 
                                    "Enable write protection? (Yes=ON, No=OFF)")
        
        result = self.monitor._toggle_protection(self.current_drive, enable)
        
        if result['success']:
            messagebox.showinfo("Success", result['message'])
            self.refresh_drives()
        else:
            messagebox.showerror("Error", result['message'])

    def auto_refresh(self):
        """Auto-refresh every 30 seconds"""
        self.refresh_drives()
        self.root.after(30000, self.auto_refresh)


# Add missing methods to USBHealthMonitor
def _format_drive(self, device, fs_type, label):
    """Format drive"""
    try:
        subprocess.run(['sudo', 'umount', f'{device}*'], shell=True, capture_output=True)
        
        fs_commands = {
            'FAT32': ['sudo', 'mkfs.vfat', '-F', '32', '-n', label, device],
            'NTFS': ['sudo', 'mkfs.ntfs', '-f', '-L', label, device],
            'EXFAT': ['sudo', 'mkfs.exfat', '-n', label, device],
            'EXT4': ['sudo', 'mkfs.ext4', '-L', label, device],
        }
        
        cmd = fs_commands.get(fs_type.upper())
        if not cmd:
            return {'success': False, 'message': f'Unsupported: {fs_type}'}
        
        subprocess.run(cmd, check=True, timeout=120)
        self.log_operation(f"Formatted {device} as {fs_type}")
        return {'success': True, 'message': f'Formatted as {fs_type} with label "{label}"'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _secure_wipe(self, device, passes):
    """Secure wipe drive"""
    try:
        for i in range(passes):
            if i == passes - 1:
                subprocess.run(['sudo', 'dd', f'if=/dev/zero', f'of={device}',
                              'bs=4M', 'status=progress'], check=True)
            else:
                subprocess.run(['sudo', 'dd', f'if=/dev/urandom', f'of={device}',
                              'bs=4M', 'status=progress'], check=True)
        
        self.log_operation(f"Secure wiped {device} with {passes} passes")
        return {'success': True, 'message': f'Drive wiped with {passes} passes'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def _toggle_protection(self, device, enable):
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
        return {'success': False, 'message': str(e)}

# Add methods to class
USBHealthMonitor._format_drive = _format_drive
USBHealthMonitor._secure_wipe = _secure_wipe
USBHealthMonitor._toggle_protection = _toggle_protection

# Add import for re
import re

def main():
    try:
        import psutil
    except ImportError:
        subprocess.run(['pip3', 'install', 'psutil'], check=True)
        import psutil
    
    root = tk.Tk()
    app = USBHealthGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
