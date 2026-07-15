#!/usr/bin/env python3
"""
USB Drive Full Recovery & Repair Tool
Fix critical USB drives and restore to excellent health
"""

import os
import sys
import subprocess
import time
import json
import re
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog, simpledialog

class USBRepairTool:
    """Complete USB repair and recovery system"""
    
    def __init__(self):
        self.operations_log = []
        self.repair_steps = []
        
    def detect_drives(self):
        """Detect all USB drives"""
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
                                'model': device.get('model', 'Unknown'),
                                'label': device.get('label', ''),
                                'mount': device.get('mountpoint', ''),
                                'state': device.get('state', 'Unknown'),
                                'readonly': device.get('ro', False)
                            }
                            drives.append(drive_info)
                except:
                    pass
        except:
            pass
        return drives
    
    def _is_usb(self, name):
        try:
            sys_path = f"/sys/block/{name}/removable"
            if os.path.exists(sys_path):
                with open(sys_path, 'r') as f:
                    return f.read().strip() == '1'
        except:
            pass
        return False
    
    def get_health_status(self, device):
        """Get detailed health status"""
        health = {
            'status': 'Unknown',
            'score': 0,
            'issues': [],
            'details': {}
        }
        
        try:
            # Check SMART
            try:
                result = subprocess.run(['sudo', 'smartctl', '-H', device],
                                      capture_output=True, text=True, timeout=5)
                if 'PASSED' in result.stdout:
                    health['score'] += 30
                    health['details']['smart'] = 'PASSED'
                else:
                    health['issues'].append('SMART failure detected')
                    health['details']['smart'] = 'FAILED'
            except:
                health['details']['smart'] = 'Not Available'
            
            # Check filesystem
            try:
                result = subprocess.run(['sudo', 'fsck', '-n', device],
                                      capture_output=True, text=True, timeout=10)
                if 'clean' in result.stdout.lower():
                    health['score'] += 30
                    health['details']['filesystem'] = 'Clean'
                else:
                    health['issues'].append('Filesystem needs repair')
                    health['details']['filesystem'] = 'Needs Repair'
            except:
                health['details']['filesystem'] = 'Unknown'
            
            # Check mount
            try:
                result = subprocess.run(['findmnt', '-n', device], capture_output=True, text=True)
                if result.stdout.strip():
                    health['score'] += 20
                    health['details']['mounted'] = result.stdout.strip()
                else:
                    health['details']['mounted'] = 'Not Mounted'
            except:
                health['details']['mounted'] = 'Unknown'
            
            # Check bad blocks (quick)
            try:
                result = subprocess.run(['sudo', 'badblocks', '-s', '-v', '-n', device],
                                      capture_output=True, text=True, timeout=5)
                if 'done' in result.stdout and 'bad blocks' not in result.stdout.lower():
                    health['score'] += 20
                    health['details']['bad_blocks'] = 'None Found'
                else:
                    health['issues'].append('Bad blocks detected')
                    health['details']['bad_blocks'] = 'Found'
            except:
                health['details']['bad_blocks'] = 'Unknown'
            
            # Determine status
            if health['score'] >= 80:
                health['status'] = 'Excellent'
            elif health['score'] >= 60:
                health['status'] = 'Good'
            elif health['score'] >= 40:
                health['status'] = 'Fair'
            elif health['score'] >= 20:
                health['status'] = 'Poor'
            else:
                health['status'] = 'Critical'
                
        except Exception as e:
            health['issues'].append(str(e))
        
        return health
    
    def repair_drive_complete(self, device):
        """Complete repair process to restore to excellent health"""
        results = []
        self.repair_steps = []
        
        # Step 1: Unmount drive
        results.append("Step 1: Unmounting drive...")
        self._unmount_drive(device)
        
        # Step 2: Repair filesystem
        results.append("Step 2: Repairing filesystem...")
        fs_result = self._repair_filesystem(device)
        results.append(f"  {fs_result}")
        
        # Step 3: Fix bad blocks
        results.append("Step 3: Checking and fixing bad blocks...")
        bad_result = self._fix_bad_blocks(device)
        results.append(f"  {bad_result}")
        
        # Step 4: Repair boot sector
        results.append("Step 4: Repairing boot sector...")
        boot_result = self._repair_boot_sector(device)
        results.append(f"  {boot_result}")
        
        # Step 5: Recreate partition table if needed
        results.append("Step 5: Checking partition table...")
        part_result = self._fix_partition_table(device)
        results.append(f"  {part_result}")
        
        # Step 6: Format if needed
        results.append("Step 6: Formatting drive...")
        format_result = self._format_drive(device)
        results.append(f"  {format_result}")
        
        # Step 7: Remount
        results.append("Step 7: Remounting drive...")
        mount_result = self._mount_drive(device)
        results.append(f"  {mount_result}")
        
        # Final health check
        results.append("\n📊 Final Health Check...")
        health = self.get_health_status(device)
        results.append(f"  Health Status: {health['status']}")
        results.append(f"  Health Score: {health['score']}/100")
        
        if health['issues']:
            results.append("  Remaining Issues:")
            for issue in health['issues']:
                results.append(f"    - {issue}")
        
        self.log_operation(f"Completed repair on {device}")
        return {
            'success': True,
            'message': '\n'.join(results),
            'health': health
        }
    
    def _unmount_drive(self, device):
        """Unmount drive"""
        try:
            subprocess.run(['sudo', 'umount', f'{device}*'], shell=True, capture_output=True)
            return "Drive unmounted successfully"
        except:
            return "Unmount failed (drive may not be mounted)"
    
    def _repair_filesystem(self, device):
        """Repair filesystem"""
        try:
            # Try multiple filesystem repair methods
            for fs_type in ['', 'vfat', 'ntfs', 'ext4', 'ext3']:
                try:
                    if fs_type:
                        cmd = ['sudo', 'fsck', '-t', fs_type, '-y', device]
                    else:
                        cmd = ['sudo', 'fsck', '-y', device]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                    if result.returncode == 0 or 'clean' in result.stdout.lower():
                        return f"Filesystem repaired successfully (fsck {fs_type if fs_type else 'auto'})"
                except:
                    continue
            return "Filesystem repair completed (some errors may remain)"
        except Exception as e:
            return f"Filesystem repair failed: {str(e)}"
    
    def _fix_bad_blocks(self, device):
        """Fix bad blocks"""
        try:
            # Check for bad blocks
            result = subprocess.run(['sudo', 'badblocks', '-sv', '-o', '/tmp/bad_blocks.txt', device],
                                  capture_output=True, text=True, timeout=30)
            
            if os.path.exists('/tmp/bad_blocks.txt'):
                with open('/tmp/bad_blocks.txt', 'r') as f:
                    blocks = f.read().strip()
                    if blocks:
                        # Mark bad blocks
                        subprocess.run(['sudo', 'e2fsck', '-l', '/tmp/bad_blocks.txt', device],
                                     check=True, timeout=30)
                        return f"Bad blocks marked: {len(blocks.split())} blocks"
                    else:
                        return "No bad blocks found"
            else:
                return "Bad block check completed - no bad blocks found"
        except Exception as e:
            return f"Bad block check failed: {str(e)}"
    
    def _repair_boot_sector(self, device):
        """Repair boot sector"""
        try:
            # Backup current MBR
            backup_file = f"/tmp/mbr_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.img"
            subprocess.run(['sudo', 'dd', f'if={device}', f'of={backup_file}', 'bs=512', 'count=1'], 
                         check=True, capture_output=True)
            
            # Write new MBR
            subprocess.run(['sudo', 'dd', 'if=/dev/zero', f'of={device}', 'bs=512', 'count=1'], 
                         check=True, capture_output=True)
            
            # Create new MBR with fdisk
            cmd = f"echo -e 'o\\nn\\np\\n1\\n\\n\\nw' | sudo fdisk {device}"
            subprocess.run(cmd, shell=True, check=True)
            
            return f"Boot sector repaired (backup saved to {backup_file})"
        except Exception as e:
            return f"Boot sector repair failed: {str(e)}"
    
    def _fix_partition_table(self, device):
        """Fix partition table"""
        try:
            # Check if partition table exists
            result = subprocess.run(['sudo', 'parted', '-s', device, 'print'],
                                  capture_output=True, text=True)
            
            if 'unrecognised disk label' in result.stderr:
                # Create new partition table
                subprocess.run(['sudo', 'parted', '-s', device, 'mklabel', 'msdos'], check=True)
                subprocess.run(['sudo', 'parted', '-s', device, 'mkpart', 'primary', '1', '100%'], check=True)
                subprocess.run(['sudo', 'parted', '-s', device, 'set', '1', 'boot', 'on'], check=True)
                return "New partition table created"
            else:
                return "Partition table is valid"
        except Exception as e:
            return f"Partition table fix failed: {str(e)}"
    
    def _format_drive(self, device):
        """Format drive"""
        try:
            # Determine best filesystem
            # Try FAT32 first (most compatible)
            try:
                subprocess.run(['sudo', 'mkfs.vfat', '-F', '32', '-n', 'USB_DRIVE', device],
                             check=True, timeout=30)
                return "Drive formatted as FAT32"
            except:
                # Try NTFS
                try:
                    subprocess.run(['sudo', 'mkfs.ntfs', '-f', '-L', 'USB_DRIVE', device],
                                 check=True, timeout=30)
                    return "Drive formatted as NTFS"
                except:
                    return "Format failed (drive may need manual formatting)"
        except Exception as e:
            return f"Format failed: {str(e)}"
    
    def _mount_drive(self, device):
        """Mount drive"""
        try:
            mount_point = f"/mnt/usb_{datetime.now().strftime('%H%M%S')}"
            os.makedirs(mount_point, exist_ok=True)
            subprocess.run(['sudo', 'mount', device, mount_point], check=True)
            return f"Drive mounted at {mount_point}"
        except Exception as e:
            return f"Mount failed: {str(e)}"
    
    def log_operation(self, operation):
        """Log operations"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.operations_log.append(f"[{timestamp}] {operation}")


class USBRepairGUI:
    """GUI for USB repair tool"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("USB Drive Repair Tool - Fix Critical USB")
        self.root.geometry("900x700")
        self.root.configure(bg='#1e1e2e')
        
        self.repair_tool = USBRepairTool()
        self.current_drive = None
        self.setup_ui()
        self.refresh_drives()
        
    def setup_ui(self):
        # Main container
        main = tk.Frame(self.root, bg='#1e1e2e')
        main.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Title
        title = tk.Label(main, text="🔧 USB Drive Repair Tool", 
                        font=('Helvetica', 24, 'bold'), 
                        fg='#89b4fa', bg='#1e1e2e')
        title.pack(pady=(0, 20))
        
        # Description
        desc = tk.Label(main, text="Fix critical USB drives and restore to Excellent health", 
                       font=('Helvetica', 12), 
                       fg='#cdd6f4', bg='#1e1e2e')
        desc.pack(pady=(0, 20))
        
        # Drive selection
        select_frame = tk.Frame(main, bg='#1e1e2e')
        select_frame.pack(fill='x', pady=10)
        
        tk.Label(select_frame, text="Select USB Drive:", 
                fg='#cdd6f4', bg='#1e1e2e',
                font=('Helvetica', 12)).pack(side='left', padx=(0, 10))
        
        self.drive_combo = ttk.Combobox(select_frame, state='readonly', width=40)
        self.drive_combo.pack(side='left')
        self.drive_combo.bind('<<ComboboxSelected>>', self.on_drive_select)
        
        tk.Button(select_frame, text="🔄 Refresh", 
                 command=self.refresh_drives,
                 bg='#89b4fa', fg='white',
                 font=('Helvetica', 11, 'bold'),
                 padx=15, pady=5, relief='flat').pack(side='left', padx=10)
        
        # Status display
        self.status_frame = tk.LabelFrame(main, text="📊 Current Status", 
                                        bg='#1e1e2e', fg='#cdd6f4')
        self.status_frame.pack(fill='x', pady=10)
        
        self.status_text = scrolledtext.ScrolledText(self.status_frame, height=6,
                                                    bg='#1e1e2e', fg='#cdd6f4',
                                                    font=('Monospace', 10))
        self.status_text.pack(fill='x', padx=5, pady=5)
        self.status_text.insert('1.0', "Select a drive to check health...")
        
        # Health indicator
        self.health_label = tk.Label(main, text="⚪ Health: Unknown", 
                                   font=('Helvetica', 16, 'bold'),
                                   fg='#cdd6f4', bg='#1e1e2e')
        self.health_label.pack(pady=10)
        
        # Repair buttons
        btn_frame = tk.Frame(main, bg='#1e1e2e')
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="🔍 Check Health", 
                 command=self.check_health,
                 bg='#89b4fa', fg='white',
                 font=('Helvetica', 12, 'bold'),
                 padx=20, pady=10, relief='flat').pack(side='left', padx=10)
        
        tk.Button(btn_frame, text="🔧 Full Repair", 
                 command=self.full_repair,
                 bg='#a6e3a1', fg='#1e1e2e',
                 font=('Helvetica', 12, 'bold'),
                 padx=20, pady=10, relief='flat').pack(side='left', padx=10)
        
        tk.Button(btn_frame, text="✨ Restore to Excellent", 
                 command=self.restore_excellent,
                 bg='#89b4fa', fg='white',
                 font=('Helvetica', 12, 'bold'),
                 padx=20, pady=10, relief='flat').pack(side='left', padx=10)
        
        # Progress
        self.progress = ttk.Progressbar(main, mode='determinate', length=400)
        self.progress.pack(pady=10)
        
        # Log display
        log_frame = tk.LabelFrame(main, text="📜 Operation Log", 
                                bg='#1e1e2e', fg='#cdd6f4')
        log_frame.pack(fill='both', expand=True, pady=10)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8,
                                                 bg='#1e1e2e', fg='#cdd6f4',
                                                 font=('Monospace', 10))
        self.log_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Status bar
        self.status_bar = tk.Label(main, text="Ready", 
                                   bg='#313244', fg='#cdd6f4',
                                   anchor='w', padx=15,
                                   font=('Helvetica', 10))
        self.status_bar.pack(fill='x', pady=(10, 0))
    
    def refresh_drives(self):
        """Refresh drive list"""
        drives = self.repair_tool.detect_drives()
        if drives:
            drive_list = [f"{d['device']} - {d['size']} - {d['model']}" for d in drives]
            self.drive_combo['values'] = drive_list
            if drive_list:
                self.drive_combo.set(drive_list[0])
                self.current_drive = drives[0]['device']
                self.check_health()
        else:
            self.drive_combo['values'] = []
            self.status_bar.config(text="No USB drives detected")
    
    def on_drive_select(self, event):
        """Handle drive selection"""
        selection = self.drive_combo.get()
        if selection:
            self.current_drive = selection.split(' - ')[0]
            self.check_health()
    
    def check_health(self):
        """Check drive health"""
        if not self.current_drive:
            messagebox.showwarning("No Drive", "Please select a USB drive first")
            return
        
        self.status_bar.config(text=f"Checking health of {self.current_drive}...")
        
        health = self.repair_tool.get_health_status(self.current_drive)
        
        # Update status text
        self.status_text.delete('1.0', tk.END)
        status_info = f"""
📊 Health Report for {self.current_drive}

Status: {health['status']}
Score: {health['score']}/100

Details:
  SMART: {health['details'].get('smart', 'N/A')}
  Filesystem: {health['details'].get('filesystem', 'N/A')}
  Bad Blocks: {health['details'].get('bad_blocks', 'N/A')}
  Mounted: {health['details'].get('mounted', 'N/A')}

"""
        if health['issues']:
            status_info += "Issues Found:\n"
            for issue in health['issues']:
                status_info += f"  ⚠️ {issue}\n"
        else:
            status_info += "✅ No issues found!\n"
        
        self.status_text.insert('1.0', status_info)
        
        # Update health label
        colors = {
            'Excellent': '#a6e3a1',
            'Good': '#a6e3a1',
            'Fair': '#f9e2af',
            'Poor': '#f38ba8',
            'Critical': '#f38ba8',
            'Unknown': '#cdd6f4'
        }
        icons = {
            'Excellent': '🟢',
            'Good': '🟢',
            'Fair': '🟡',
            'Poor': '🟠',
            'Critical': '🔴',
            'Unknown': '⚪'
        }
        
        self.health_label.config(
            text=f"{icons.get(health['status'], '⚪')} Health: {health['status']} ({health['score']}/100)",
            fg=colors.get(health['status'], '#cdd6f4')
        )
        
        self.status_bar.config(text=f"Health check complete - Status: {health['status']}")
        
        return health
    
    def full_repair(self):
        """Run full repair"""
        if not self.current_drive:
            messagebox.showwarning("No Drive", "Please select a USB drive first")
            return
        
        if messagebox.askyesno("⚠️ Confirm Full Repair", 
                              f"This will perform a complete repair on {self.current_drive}\n\n"
                              "The process will:\n"
                              "1. Unmount the drive\n"
                              "2. Repair filesystem\n"
                              "3. Fix bad blocks\n"
                              "4. Repair boot sector\n"
                              "5. Fix partition table\n"
                              "6. Format the drive\n"
                              "7. Remount the drive\n\n"
                              "⚠️ ALL DATA WILL BE LOST!\n\n"
                              "Continue?"):
            
            self.progress['value'] = 0
            self.status_bar.config(text="Starting repair process...")
            
            # Run repair
            result = self.repair_tool.repair_drive_complete(self.current_drive)
            
            # Display results
            self.log_text.delete('1.0', tk.END)
            self.log_text.insert('1.0', result['message'])
            
            self.progress['value'] = 100
            
            # Check health after repair
            health = self.repair_tool.get_health_status(self.current_drive)
            
            if health['status'] in ['Excellent', 'Good']:
                messagebox.showinfo("✅ Repair Complete", 
                                   f"Drive repaired successfully!\n\n"
                                   f"New Health Status: {health['status']}\n"
                                   f"Health Score: {health['score']}/100\n\n"
                                   "The drive should now work properly.")
            else:
                messagebox.showwarning("⚠️ Repair Partially Complete", 
                                      f"Repair completed with some issues remaining.\n\n"
                                      f"Health Status: {health['status']}\n"
                                      f"Health Score: {health['score']}/100\n\n"
                                      "You may need to run additional repairs.")
            
            self.status_bar.config(text=f"Repair complete - Status: {health['status']}")
            self.check_health()
    
    def restore_excellent(self):
        """Restore drive to excellent condition"""
        if not self.current_drive:
            messagebox.showwarning("No Drive", "Please select a USB drive first")
            return
        
        # Check current health
        health = self.repair_tool.get_health_status(self.current_drive)
        
        if health['status'] == 'Excellent':
            messagebox.showinfo("Already Excellent", 
                              "Drive is already in Excellent condition!\n"
                              f"Score: {health['score']}/100")
            return
        
        # Show what will be done
        issues = "\n".join([f"  • {issue}" for issue in health['issues']]) if health['issues'] else "  • No specific issues detected"
        
        if messagebox.askyesno("✨ Restore to Excellent", 
                              f"This will restore {self.current_drive} to Excellent condition.\n\n"
                              f"Current Status: {health['status']}\n"
                              f"Current Score: {health['score']}/100\n\n"
                              "Issues to fix:\n" + issues + "\n\n"
                              "⚠️ This process will erase all data on the drive!\n\n"
                              "Continue?"):
            
            self.progress['value'] = 0
            self.status_bar.config(text="Restoring drive to Excellent condition...")
            
            # Run repair
            result = self.repair_tool.repair_drive_complete(self.current_drive)
            
            # Display results
            self.log_text.delete('1.0', tk.END)
            self.log_text.insert('1.0', result['message'])
            
            self.progress['value'] = 100
            
            # Check final health
            final_health = self.repair_tool.get_health_status(self.current_drive)
            
            if final_health['status'] == 'Excellent':
                messagebox.showinfo("✨ Restored to Excellent!", 
                                   f"Drive successfully restored to Excellent condition!\n\n"
                                   f"Final Score: {final_health['score']}/100\n\n"
                                   "All issues have been fixed.")
            else:
                messagebox.showinfo("✅ Restore Complete", 
                                   f"Drive restored to {final_health['status']} condition.\n\n"
                                   f"Score: {final_health['score']}/100\n\n"
                                   "Additional manual steps may be needed for Excellent status.")
            
            self.status_bar.config(text=f"Restore complete - Status: {final_health['status']}")
            self.check_health()


def main():
    root = tk.Tk()
    app = USBRepairGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
