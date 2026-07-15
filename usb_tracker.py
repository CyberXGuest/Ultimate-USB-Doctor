#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
USB History Tracker - Personal USB Connection Logger
Tracks all USB devices connected to your system
For personal system administration ONLY
"""

import os
import sys
import subprocess
import json
import time
import re
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog

class USBHistoryTracker:
    """Track and log all USB devices connected to the system"""
    
    def __init__(self):
        self.db_path = os.path.expanduser("~/.usb_history.db")
        self.log_file = os.path.expanduser("~/usb_connection_log.txt")
        self.setup_database()
        
    def setup_database(self):
        """Create SQLite database for USB history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create USB history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usb_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_path TEXT,
                device_name TEXT,
                vendor TEXT,
                product TEXT,
                serial TEXT,
                uuid TEXT,
                size TEXT,
                filesystem TEXT,
                mount_point TEXT,
                first_seen TIMESTAMP,
                last_seen TIMESTAMP,
                connection_count INTEGER DEFAULT 1,
                is_removed BOOLEAN DEFAULT 0,
                details TEXT
            )
        ''')
        
        # Create connection log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS connection_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id INTEGER,
                action TEXT,
                timestamp TIMESTAMP,
                details TEXT,
                FOREIGN KEY (device_id) REFERENCES usb_history(id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def detect_current_usb(self):
        """Detect all currently connected USB devices with full details"""
        devices = []
        try:
            # Get detailed USB info using lsblk with JSON
            result = subprocess.run(
                ['lsblk', '-J', '-o', 'NAME,SIZE,TYPE,MOUNTPOINT,MODEL,LABEL,TRAN,RO,STATE,VENDOR,REV,SERIAL'],
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode == 0 and result.stdout:
                try:
                    data = json.loads(result.stdout)
                    for device in data.get('blockdevices', []):
                        if self._is_usb(device.get('name', '')):
                            dev_info = self._get_usb_details(device)
                            if dev_info:
                                devices.append(dev_info)
                except:
                    pass
        except:
            pass
        
        # Also get USB devices from lsusb
        try:
            result = subprocess.run(['lsusb', '-v'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                usb_devices = self._parse_lsusb(result.stdout)
                for dev in usb_devices:
                    # Check if this USB device has a block device associated
                    for d in devices:
                        if dev.get('vendor') in d.get('vendor', '') or dev.get('product') in d.get('product', ''):
                            d.update(dev)
                            break
                    else:
                        devices.append(dev)
        except:
            pass
        
        return devices
    
    def _is_usb(self, name):
        """Check if device is USB"""
        try:
            sys_path = f"/sys/block/{name}/removable"
            if os.path.exists(sys_path):
                with open(sys_path, 'r') as f:
                    return f.read().strip() == '1'
        except:
            pass
        return False
    
    def _get_usb_details(self, device):
        """Get USB device details"""
        name = device.get('name', '')
        device_path = f"/dev/{name}"
        
        # Get UUID
        uuid = self._get_uuid(name)
        
        # Get filesystem
        filesystem = self._get_filesystem(device_path)
        
        # Get vendor details from udev
        vendor_info = self._get_udev_info(name)
        
        return {
            'device_path': device_path,
            'device_name': name,
            'vendor': vendor_info.get('vendor', device.get('vendor', 'Unknown')),
            'product': vendor_info.get('product', device.get('model', 'Unknown')),
            'serial': vendor_info.get('serial', device.get('serial', '')),
            'uuid': uuid,
            'size': device.get('size', 'Unknown'),
            'filesystem': filesystem,
            'mount_point': device.get('mountpoint', ''),
            'model': device.get('model', ''),
            'label': device.get('label', ''),
            'state': device.get('state', 'Unknown'),
            'readonly': device.get('ro', False),
            'tran': device.get('tran', 'usb')
        }
    
    def _get_uuid(self, name):
        """Get UUID of device"""
        try:
            result = subprocess.run(['sudo', 'blkid', f'/dev/{name}'], 
                                  capture_output=True, text=True, timeout=5)
            match = re.search(r'UUID="([^"]+)"', result.stdout)
            return match.group(1) if match else ''
        except:
            return ''
    
    def _get_filesystem(self, device_path):
        """Get filesystem type"""
        try:
            result = subprocess.run(['sudo', 'blkid', '-o', 'value', '-s', 'TYPE', device_path],
                                  capture_output=True, text=True, timeout=5)
            fs = result.stdout.strip()
            return fs.upper() if fs else 'Unknown'
        except:
            return 'Unknown'
    
    def _get_udev_info(self, name):
        """Get USB info from udev"""
        info = {}
        try:
            result = subprocess.run(['udevadm', 'info', '--query=property', f'--name={name}'],
                                  capture_output=True, text=True, timeout=3)
            for line in result.stdout.split('\n'):
                if 'ID_VENDOR=' in line:
                    info['vendor'] = line.split('=')[1].strip()
                elif 'ID_MODEL=' in line:
                    info['product'] = line.split('=')[1].strip()
                elif 'ID_SERIAL=' in line:
                    info['serial'] = line.split('=')[1].strip()
        except:
            pass
        return info
    
    def _parse_lsusb(self, output):
        """Parse lsusb output for USB device details"""
        devices = []
        current = {}
        
        for line in output.split('\n'):
            if 'Bus' in line and 'Device' in line:
                if current:
                    devices.append(current)
                current = {
                    'vendor': 'Unknown',
                    'product': 'Unknown',
                    'serial': ''
                }
                # Extract bus and device info
                parts = line.split()
                for i, part in enumerate(parts):
                    if 'idVendor' in part:
                        if i+1 < len(parts):
                            current['vendor'] = parts[i+1]
                    elif 'idProduct' in part:
                        if i+1 < len(parts):
                            current['product'] = parts[i+1]
            elif 'Serial Number' in line:
                parts = line.split('Serial Number')
                if len(parts) > 1:
                    current['serial'] = parts[1].strip()
        
        if current:
            devices.append(current)
        
        return devices
    
    def log_usb_connection(self, device_info):
        """Log USB connection to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if device already exists
        cursor.execute('''
            SELECT id, connection_count FROM usb_history 
            WHERE device_path = ? OR (vendor = ? AND product = ? AND serial != '')
        ''', (device_info.get('device_path', ''), 
              device_info.get('vendor', ''), 
              device_info.get('product', '')))
        
        result = cursor.fetchone()
        
        if result:
            # Update existing device
            device_id, count = result
            cursor.execute('''
                UPDATE usb_history 
                SET last_seen = ?, connection_count = ?, is_removed = 0,
                    mount_point = ?, details = ?
                WHERE id = ?
            ''', (
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                count + 1,
                device_info.get('mount_point', ''),
                json.dumps(device_info),
                device_id
            ))
            
            # Log connection event
            cursor.execute('''
                INSERT INTO connection_log (device_id, action, timestamp, details)
                VALUES (?, 'reconnected', ?, ?)
            ''', (device_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), json.dumps(device_info)))
            
        else:
            # New device
            cursor.execute('''
                INSERT INTO usb_history (
                    device_path, device_name, vendor, product, serial, uuid,
                    size, filesystem, mount_point, first_seen, last_seen,
                    connection_count, details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                device_info.get('device_path', ''),
                device_info.get('device_name', ''),
                device_info.get('vendor', 'Unknown'),
                device_info.get('product', 'Unknown'),
                device_info.get('serial', ''),
                device_info.get('uuid', ''),
                device_info.get('size', 'Unknown'),
                device_info.get('filesystem', 'Unknown'),
                device_info.get('mount_point', ''),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                1,
                json.dumps(device_info)
            ))
            
            device_id = cursor.lastrowid
            
            # Log connection event
            cursor.execute('''
                INSERT INTO connection_log (device_id, action, timestamp, details)
                VALUES (?, 'connected', ?, ?)
            ''', (device_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), json.dumps(device_info)))
        
        conn.commit()
        conn.close()
        
        # Also write to log file
        self._write_to_log(device_info)
        
        return True
    
    def _write_to_log(self, device_info):
        """Write USB connection to log file"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(self.log_file, 'a') as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"USB CONNECTION LOG - {timestamp}\n")
            f.write(f"{'='*60}\n")
            f.write(f"Device: {device_info.get('device_path', 'Unknown')}\n")
            f.write(f"Name: {device_info.get('device_name', 'Unknown')}\n")
            f.write(f"Vendor: {device_info.get('vendor', 'Unknown')}\n")
            f.write(f"Product: {device_info.get('product', 'Unknown')}\n")
            f.write(f"Serial: {device_info.get('serial', 'Unknown')}\n")
            f.write(f"UUID: {device_info.get('uuid', 'Unknown')}\n")
            f.write(f"Size: {device_info.get('size', 'Unknown')}\n")
            f.write(f"Filesystem: {device_info.get('filesystem', 'Unknown')}\n")
            f.write(f"Mount Point: {device_info.get('mount_point', 'Not Mounted')}\n")
            f.write(f"Model: {device_info.get('model', 'Unknown')}\n")
            f.write(f"Label: {device_info.get('label', 'Unknown')}\n")
            f.write(f"{'='*60}\n")
    
    def mark_removed(self, device_path):
        """Mark a USB device as removed"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE usb_history SET is_removed = 1
            WHERE device_path = ?
        ''', (device_path,))
        
        cursor.execute('''
            SELECT id FROM usb_history WHERE device_path = ?
        ''', (device_path,))
        result = cursor.fetchone()
        
        if result:
            cursor.execute('''
                INSERT INTO connection_log (device_id, action, timestamp, details)
                VALUES (?, 'removed', ?, ?)
            ''', (result[0], datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'Device removed'))
        
        conn.commit()
        conn.close()
    
    def get_history(self, limit=100):
        """Get USB connection history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                h.id, h.device_path, h.device_name, h.vendor, h.product,
                h.serial, h.uuid, h.size, h.filesystem, h.mount_point,
                h.first_seen, h.last_seen, h.connection_count,
                GROUP_CONCAT(DISTINCT l.action) as actions
            FROM usb_history h
            LEFT JOIN connection_log l ON h.id = l.device_id
            GROUP BY h.id
            ORDER BY h.last_seen DESC
            LIMIT ?
        ''', (limit,))
        
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    def get_full_log(self):
        """Get all connection logs"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT l.id, h.device_name, h.vendor, h.product, h.serial,
                   l.action, l.timestamp, l.details
            FROM connection_log l
            JOIN usb_history h ON l.device_id = h.id
            ORDER BY l.timestamp DESC
            LIMIT 1000
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    def export_to_csv(self, filename):
        """Export history to CSV"""
        import csv
        history = self.get_history(limit=1000)
        
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['ID', 'Device', 'Name', 'Vendor', 'Product', 'Serial', 
                           'UUID', 'Size', 'Filesystem', 'First Seen', 'Last Seen', 'Count'])
            for row in history:
                writer.writerow(row)
        
        return True
    
    def clear_history(self):
        """Clear all history (with confirmation)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM connection_log')
        cursor.execute('DELETE FROM usb_history')
        conn.commit()
        conn.close()
        
        # Clear log file
        with open(self.log_file, 'w') as f:
            f.write('USB History Cleared\n')
        
        return True


class USBHistoryGUI:
    """GUI for USB History Tracker"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("USB History Tracker - Personal USB Logger")
        self.root.geometry("1300x800")
        self.root.configure(bg='#1e1e2e')
        
        self.tracker = USBHistoryTracker()
        self.monitoring = True
        self.setup_ui()
        self.refresh_history()
        
        # Start monitoring thread
        self.start_monitor()
    
    def setup_ui(self):
        # Main container
        main = tk.Frame(self.root, bg='#1e1e2e')
        main.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Header
        header = tk.Frame(main, bg='#1e1e2e')
        header.pack(fill='x', pady=(0, 10))
        
        title = tk.Label(header, text="USB History Tracker", 
                        font=('Helvetica', 24, 'bold'), 
                        fg='#89b4fa', bg='#1e1e2e')
        title.pack(side='left')
        
        # Stats
        self.stats_label = tk.Label(header, text="", 
                                   font=('Helvetica', 11),
                                   fg='#a6e3a1', bg='#1e1e2e')
        self.stats_label.pack(side='right')
        
        # Toolbar
        toolbar = tk.Frame(main, bg='#1e1e2e')
        toolbar.pack(fill='x', pady=(0, 10))
        
        tk.Button(toolbar, text="Refresh", command=self.refresh_history,
                 bg='#89b4fa', fg='white',
                 font=('Helvetica', 11, 'bold'),
                 padx=15, pady=8, relief='flat').pack(side='left', padx=2)
        
        tk.Button(toolbar, text="Scan Now", command=self.scan_now,
                 bg='#a6e3a1', fg='#1e1e2e',
                 font=('Helvetica', 11, 'bold'),
                 padx=15, pady=8, relief='flat').pack(side='left', padx=2)
        
        tk.Button(toolbar, text="Export CSV", command=self.export_csv,
                 bg='#f9e2af', fg='#1e1e2e',
                 font=('Helvetica', 11, 'bold'),
                 padx=15, pady=8, relief='flat').pack(side='left', padx=2)
        
        tk.Button(toolbar, text="View Log", command=self.view_log,
                 bg='#89b4fa', fg='white',
                 font=('Helvetica', 11, 'bold'),
                 padx=15, pady=8, relief='flat').pack(side='left', padx=2)
        
        tk.Button(toolbar, text="Clear History", command=self.clear_history,
                 bg='#f38ba8', fg='white',
                 font=('Helvetica', 11, 'bold'),
                 padx=15, pady=8, relief='flat').pack(side='left', padx=2)
        
        # Status
        self.status_bar = tk.Label(main, text="Monitoring USB connections...", 
                                   bg='#313244', fg='#cdd6f4',
                                   anchor='w', padx=15,
                                   font=('Helvetica', 10))
        self.status_bar.pack(side='bottom', fill='x', pady=(10, 0))
        
        # Main content
        content = tk.Frame(main, bg='#1e1e2e')
        content.pack(fill='both', expand=True)
        
        # Notebook
        notebook = ttk.Notebook(content)
        notebook.pack(fill='both', expand=True)
        
        # Tab 1: History
        history_tab = tk.Frame(notebook, bg='#1e1e2e')
        notebook.add(history_tab, text='History')
        self.create_history_tab(history_tab)
        
        # Tab 2: Log
        log_tab = tk.Frame(notebook, bg='#1e1e2e')
        notebook.add(log_tab, text='Connection Log')
        self.create_log_tab(log_tab)
        
        # Tab 3: Current
        current_tab = tk.Frame(notebook, bg='#1e1e2e')
        notebook.add(current_tab, text='Current USB')
        self.create_current_tab(current_tab)
    
    def create_history_tab(self, parent):
        frame = tk.Frame(parent, bg='#1e1e2e')
        frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Search
        search_frame = tk.Frame(frame, bg='#1e1e2e')
        search_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(search_frame, text="Search:", fg='#cdd6f4', bg='#1e1e2e',
                font=('Helvetica', 11)).pack(side='left', padx=(0, 10))
        
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self.filter_history())
        
        search_entry = tk.Entry(search_frame, textvariable=self.search_var,
                               bg='#313244', fg='#cdd6f4', width=30,
                               font=('Helvetica', 11))
        search_entry.pack(side='left')
        
        # History list
        list_frame = tk.Frame(frame, bg='#313244')
        list_frame.pack(fill='both', expand=True)
        
        columns = ('ID', 'Device', 'Vendor', 'Product', 'Serial', 'Size', 'First Seen', 'Last Seen', 'Count')
        self.history_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=25)
        
        self.history_tree.heading('ID', text='ID')
        self.history_tree.heading('Device', text='Device')
        self.history_tree.heading('Vendor', text='Vendor')
        self.history_tree.heading('Product', text='Product')
        self.history_tree.heading('Serial', text='Serial')
        self.history_tree.heading('Size', text='Size')
        self.history_tree.heading('First Seen', text='First Seen')
        self.history_tree.heading('Last Seen', text='Last Seen')
        self.history_tree.heading('Count', text='Count')
        
        self.history_tree.column('ID', width=50)
        self.history_tree.column('Device', width=120)
        self.history_tree.column('Vendor', width=150)
        self.history_tree.column('Product', width=150)
        self.history_tree.column('Serial', width=150)
        self.history_tree.column('Size', width=80)
        self.history_tree.column('First Seen', width=150)
        self.history_tree.column('Last Seen', width=150)
        self.history_tree.column('Count', width=60)
        
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', 
                                 command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        
        self.history_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Double click to show details
        self.history_tree.bind('<Double-Button-1>', self.show_details)
    
    def create_log_tab(self, parent):
        frame = tk.Frame(parent, bg='#1e1e2e')
        frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.log_text = scrolledtext.ScrolledText(frame,
                                                 bg='#1e1e2e', fg='#cdd6f4',
                                                 font=('Monospace', 10))
        self.log_text.pack(fill='both', expand=True)
        
        # Load log
        self.load_log()
    
    def create_current_tab(self, parent):
        frame = tk.Frame(parent, bg='#1e1e2e')
        frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.current_text = scrolledtext.ScrolledText(frame,
                                                     bg='#1e1e2e', fg='#cdd6f4',
                                                     font=('Monospace', 10))
        self.current_text.pack(fill='both', expand=True)
        
        # Show current USB devices
        self.show_current_usb()
    
    def refresh_history(self):
        """Refresh history display"""
        # Clear tree
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        history = self.tracker.get_history(limit=200)
        
        for row in history:
            self.history_tree.insert('', 'end', values=(
                row[0],  # ID
                row[1],  # Device
                row[3],  # Vendor
                row[4],  # Product
                row[5],  # Serial
                row[7],  # Size
                row[10], # First Seen
                row[11], # Last Seen
                row[12]  # Count
            ))
        
        # Update stats
        total = len(history)
        self.stats_label.config(text=f"Total Devices: {total}")
        self.status_bar.config(text=f"Loaded {total} USB devices from history")
    
    def filter_history(self):
        """Filter history by search term"""
        search = self.search_var.get().lower()
        
        for item in self.history_tree.get_children():
            values = self.history_tree.item(item)['values']
            # Search in device, vendor, product
            match = False
            for val in values[1:5]:  # Device, Vendor, Product, Serial
                if search in str(val).lower():
                    match = True
                    break
            
            if match:
                self.history_tree.reattach(item, '', 'end')
            else:
                self.history_tree.detach(item)
    
    def scan_now(self):
        """Scan for current USB devices and log them"""
        self.status_bar.config(text="Scanning for USB devices...")
        
        devices = self.tracker.detect_current_usb()
        
        if devices:
            for device in devices:
                self.tracker.log_usb_connection(device)
            
            messagebox.showinfo("Scan Complete", f"Found and logged {len(devices)} USB devices")
            self.refresh_history()
            self.show_current_usb()
            self.load_log()
            self.status_bar.config(text=f"Scan complete - Found {len(devices)} USB devices")
        else:
            messagebox.showinfo("Scan Complete", "No USB devices found")
            self.status_bar.config(text="No USB devices found")
    
    def show_current_usb(self):
        """Show current USB devices"""
        self.current_text.delete('1.0', tk.END)
        
        devices = self.tracker.detect_current_usb()
        
        if not devices:
            self.current_text.insert('1.0', "No USB devices currently connected")
            return
        
        info = "CURRENTLY CONNECTED USB DEVICES\n"
        info += "="*60 + "\n\n"
        
        for i, device in enumerate(devices, 1):
            info += f"[{i}] Device: {device.get('device_path', 'Unknown')}\n"
            info += f"    Name: {device.get('device_name', 'Unknown')}\n"
            info += f"    Vendor: {device.get('vendor', 'Unknown')}\n"
            info += f"    Product: {device.get('product', 'Unknown')}\n"
            info += f"    Serial: {device.get('serial', 'Unknown')}\n"
            info += f"    UUID: {device.get('uuid', 'Unknown')}\n"
            info += f"    Size: {device.get('size', 'Unknown')}\n"
            info += f"    Filesystem: {device.get('filesystem', 'Unknown')}\n"
            info += f"    Mount Point: {device.get('mount_point', 'Not Mounted')}\n"
            info += f"    Model: {device.get('model', 'Unknown')}\n"
            info += f"    Label: {device.get('label', 'Unknown')}\n"
            info += "-"*50 + "\n"
        
        self.current_text.insert('1.0', info)
    
    def load_log(self):
        """Load connection log"""
        self.log_text.delete('1.0', tk.END)
        
        log_entries = self.tracker.get_full_log()
        
        if not log_entries:
            self.log_text.insert('1.0', "No log entries yet")
            return
        
        for entry in log_entries:
            self.log_text.insert(tk.END, f"[{entry[6]}] {entry[2]} {entry[3]} - {entry[5]}\n")
        
        self.log_text.see(tk.END)
    
    def view_log(self):
        """View log file"""
        try:
            os.system(f'xdg-open "{self.tracker.log_file}"')
        except:
            messagebox.showinfo("Log File", f"Log file location: {self.tracker.log_file}")
    
    def show_details(self, event):
        """Show detailed information about selected USB device"""
        selection = self.history_tree.selection()
        if not selection:
            return
        
        values = self.history_tree.item(selection[0])['values']
        if not values:
            return
        
        device_id = values[0]
        
        # Get full details from database
        conn = sqlite3.connect(self.tracker.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM usb_history WHERE id = ?
        ''', (device_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            details = f"""
USB Device Details
{'='*50}

ID: {result[0]}
Device: {result[1]}
Name: {result[2]}
Vendor: {result[3]}
Product: {result[4]}
Serial: {result[5]}
UUID: {result[6]}
Size: {result[7]}
Filesystem: {result[8]}
Mount Point: {result[9]}
First Seen: {result[10]}
Last Seen: {result[11]}
Connection Count: {result[12]}
Status: {'Removed' if result[13] else 'Active'}
"""
            messagebox.showinfo("USB Device Details", details)
    
    def export_csv(self):
        """Export history to CSV"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if file_path:
            success = self.tracker.export_to_csv(file_path)
            if success:
                messagebox.showinfo("Export Complete", f"History exported to {file_path}")
    
    def clear_history(self):
        """Clear all history"""
        if messagebox.askyesno("Confirm Clear", "Clear all USB history?"):
            self.tracker.clear_history()
            self.refresh_history()
            self.load_log()
            self.status_bar.config(text="History cleared")
    
    def start_monitor(self):
        """Start monitoring USB connections"""
        def monitor():
            last_devices = set()
            
            while self.monitoring:
                try:
                    # Get current USB devices
                    current = self.tracker.detect_current_usb()
                    current_paths = {d.get('device_path', '') for d in current if d.get('device_path')}
                    
                    # Check for new devices
                    new_devices = current_paths - last_devices
                    for device_path in new_devices:
                        for device in current:
                            if device.get('device_path') == device_path:
                                self.tracker.log_usb_connection(device)
                                self.root.after(0, self.refresh_history)
                                self.root.after(0, self.show_current_usb)
                                break
                    
                    # Check for removed devices
                    removed_devices = last_devices - current_paths
                    for device_path in removed_devices:
                        self.tracker.mark_removed(device_path)
                        self.root.after(0, self.refresh_history)
                    
                    last_devices = current_paths
                    
                except:
                    pass
                
                time.sleep(5)  # Check every 5 seconds
        
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()


def main():
    root = tk.Tk()
    app = USBHistoryGUI(root)
    
    # Handle window close
    def on_closing():
        app.monitoring = False
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
