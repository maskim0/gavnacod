# ======================= UNICONTROL ============================
# Это бесплатная программа, которой я уже не занимаюсь.
# Итак, в этой программе я хотел реализовать одну из самых
# важных фишек macOS для винды, централизованность всех параметров.
# Это то чего нет в винде и точно не будет в ближайшее время.
# Почему я не хочу допиливать программу?  Мне просто лень

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import os
import ctypes
import winreg
import platform
import psutil
import sys
import json
import shutil
from PIL import Image, ImageTk
import subprocess
import datetime
import threading
import time

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()

def get_installed_layouts():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Keyboard Layout\Preload") as key:
            layouts = []
            i = 1
            while True:
                try:
                    layout_id = winreg.QueryValueEx(key, str(i))[0]
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                      f"SYSTEM\\CurrentControlSet\\Control\\Keyboard Layouts\\{layout_id}") as layout_key:
                        layout_name = winreg.QueryValueEx(layout_key, "Layout Text")[0]
                    layouts.append((layout_id, layout_name))
                    i += 1
                except OSError:
                    break
        return layouts
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось получить раскладки: {e}")
        return []

def add_keyboard_layout(layout_id):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Keyboard Layout\Preload", 0, winreg.KEY_ALL_ACCESS) as key:
            i = 1
            while True:
                try:
                    winreg.QueryValueEx(key, str(i))
                    i += 1
                except OSError:
                    break
            winreg.SetValueEx(key, str(i), 0, winreg.REG_SZ, layout_id)
        ctypes.windll.user32.LoadKeyboardLayoutW(layout_id, 1)
        return True
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось добавить раскладку: {e}")
        return False

def remove_keyboard_layout(index):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Keyboard Layout\Preload", 0, winreg.KEY_ALL_ACCESS) as key:
            winreg.DeleteValue(key, str(index))
            i = index + 1
            while True:
                try:
                    value = winreg.QueryValueEx(key, str(i))[0]
                    winreg.DeleteValue(key, str(i))
                    winreg.SetValueEx(key, str(i-1), 0, winreg.REG_SZ, value)
                    i += 1
                except OSError:
                    break
        return True
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось удалить раскладку: {e}")
        return False

# --- Управление обоями ---
def find_windows_wallpapers():
    wallpapers = {"(Нет)": None}
    search_paths = [
        os.path.join(os.environ["SystemRoot"], "Web", "Wallpaper"),
        os.path.join(os.environ["SystemRoot"], "Web", "Wallpaper", "Windows"),
        os.path.join(os.environ["SystemRoot"], "Web", "Wallpaper", "Theme1"),
        os.path.join(os.environ["SystemRoot"], "Web", "Wallpaper", "Theme2"),
        os.path.join(os.environ["SystemRoot"], "Web", "4K", "Wallpaper", "Windows"),
    ]
    
    for path in search_paths:
        if os.path.exists(path):
            for root, _, files in os.walk(path):
                for file in files:
                    if file.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                        full_path = os.path.join(root, file)
                        display_name = f"{os.path.splitext(file)[0]} ({os.path.basename(root)})" if root != path else os.path.splitext(file)[0]
                        wallpapers[display_name] = full_path
    return wallpapers

def set_wallpaper(image_path, position="center"):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                         r"Control Panel\Desktop", 0, winreg.KEY_WRITE) as key:
            winreg.SetValueEx(key, "Wallpaper", 0, winreg.REG_SZ, image_path if image_path else "")
            
            if position == "tile":
                winreg.SetValueEx(key, "TileWallpaper", 0, winreg.REG_SZ, "1")
                winreg.SetValueEx(key, "WallpaperStyle", 0, winreg.REG_SZ, "0")
            elif position == "stretch":
                winreg.SetValueEx(key, "TileWallpaper", 0, winreg.REG_SZ, "0")
                winreg.SetValueEx(key, "WallpaperStyle", 0, winreg.REG_SZ, "2")
            else:
                winreg.SetValueEx(key, "TileWallpaper", 0, winreg.REG_SZ, "0")
                winreg.SetValueEx(key, "WallpaperStyle", 0, winreg.REG_SZ, "0")
        
        SPI_SETDESKWALLPAPER = 20
        SPIF_UPDATEINIFILE = 0x01
        SPIF_SENDCHANGE = 0x02
        ctypes.windll.user32.SystemParametersInfoW(
            SPI_SETDESKWALLPAPER, 0, image_path,
            SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
        )
        return True
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось установить обои: {e}")
        return False

def get_current_wallpaper():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop") as key:
            return winreg.QueryValueEx(key, "Wallpaper")[0]
    except:
        return None

# --- Управление файлами ---
def toggle_hidden_files(show=True):
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                           r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                           0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "Hidden", 0, winreg.REG_DWORD, 1 if show else 0)
        winreg.CloseKey(key)
        ctypes.windll.user32.PostMessageW(0xFFFF, 0x1A, 0, None)
        return True
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось изменить настройки: {e}")
        return False

def toggle_file_extensions(show=True):
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                           r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                           0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "HideFileExt", 0, winreg.REG_DWORD, 0 if show else 1)
        winreg.CloseKey(key)
        ctypes.windll.user32.PostMessageW(0xFFFF, 0x1A, 0, None)
        return True
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось изменить настройки: {e}")
        return False

# --- Оптимизация системы ---
def clean_temp_files():
    try:
        temp_dirs = [
            os.environ.get('TEMP', ''),
            os.environ.get('TMP', ''),
            os.path.join(os.environ.get('USERPROFILE', ''), 'AppData', 'Local', 'Temp')
        ]
        
        deleted = 0
        total_size = 0
        
        for temp_dir in temp_dirs:
            if os.path.exists(temp_dir):
                for root, _, files in os.walk(temp_dir):
                    for file in files:
                        try:
                            file_path = os.path.join(root, file)
                            file_size = os.path.getsize(file_path)
                            os.remove(file_path)
                            deleted += 1
                            total_size += file_size
                        except:
                            continue
        
        messagebox.showinfo("Очистка завершена", 
                          f"Удалено файлов: {deleted}\n"
                          f"Освобождено места: {total_size/1024/1024:.2f} MB")
        return True
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось очистить временные файлы: {e}")
        return False

# --- Управление электропитанием ---
def set_power_scheme(scheme_guid):
    try:
        subprocess.run(f"powercfg /S {scheme_guid}", shell=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Ошибка", f"Не удалось изменить схему питания: {e}")
        return False

def get_power_schemes():
    try:
        result = subprocess.run("powercfg /L", shell=True, capture_output=True, text=True)
        schemes = []
        for line in result.stdout.split('\n'):
            if '*' in line:
                current = True
                line = line.replace('*', '').strip()
            else:
                current = False
            if 'GUID' in line:
                parts = line.split()
                guid = parts[3]
                name = ' '.join(parts[4:])
                schemes.append({'guid': guid, 'name': name, 'current': current})
        return schemes
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось получить схемы питания: {e}")
        return []

# --- Управление службами ---
def get_services():
    try:
        services = []
        output = subprocess.check_output("sc query", shell=True).decode('cp866')
        for line in output.split('\n'):
            if 'SERVICE_NAME:' in line:
                name = line.split(':')[1].strip()
                services.append(name)
        return services
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось получить список служб: {e}")
        return []

def change_service_state(service_name, start=True):
    try:
        action = "start" if start else "stop"
        subprocess.run(f"net {action} {service_name}", shell=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Ошибка", f"Не удалось изменить состояние службы: {e}")
        return False

# --- Управление автозагрузкой ---
def get_startup_programs():
    locations = [
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run")
    ]
    
    programs = []
    for root, path in locations:
        try:
            with winreg.OpenKey(root, path) as key:
                i = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, i)
                        programs.append({'name': name, 'path': value, 'location': "Пользователь" if root == winreg.HKEY_CURRENT_USER else "Система"})
                        i += 1
                    except OSError:
                        break
        except Exception as e:
            print(f"Ошибка при чтении автозагрузки: {e}")
    return programs

def toggle_startup_program(name, path, enable=True, location="user"):
    root = winreg.HKEY_CURRENT_USER if location == "user" else winreg.HKEY_LOCAL_MACHINE
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    
    try:
        with winreg.OpenKey(root, key_path, 0, winreg.KEY_SET_VALUE) as key:
            if enable:
                winreg.SetValueEx(key, name, 0, winreg.REG_SZ, path)
            else:
                winreg.DeleteValue(key, name)
        return True
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось изменить автозагрузку: {e}")
        return False

# --- Управление сетевыми адаптерами ---
def get_network_adapters():
    try:
        adapters = []
        output = subprocess.check_output("wmic nic get Name,NetConnectionStatus /format:list", shell=True).decode('cp866')
        for line in output.split('\n'):
            if 'Name=' in line:
                name = line.split('=')[1].strip()
            elif 'NetConnectionStatus=' in line:
                status_code = line.split('=')[1].strip()
                status = {
                    '0': 'Отключен',
                    '1': 'Подключен',
                    '2': 'Соединение разорвано',
                    '3': 'Соединение устанавливается',
                    '4': 'Неизвестно'
                }.get(status_code, 'Неизвестно')
                adapters.append({'name': name, 'status': status})
        return adapters
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось получить сетевые адаптеры: {e}")
        return []

def toggle_network_adapter(name, enable=True):
    try:
        action = "enable" if enable else "disable"
        subprocess.run(f"netsh interface set interface \"{name}\" {action}", shell=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Ошибка", f"Не удалось изменить состояние адаптера: {e}")
        return False

# --- Управление учетными записями ---
def get_user_accounts():
    try:
        users = []
        output = subprocess.check_output("net user", shell=True).decode('cp866').split('\n')
        for line in output[4:-2]:
            if line.strip():
                for username in line.split():
                    users.append(username.strip())
        return users
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось получить список пользователей: {e}")
        return []

def create_user_account(username, password):
    try:
        subprocess.run(f"net user {username} {password} /add", shell=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Ошибка", f"Не удалось создать пользователя: {e}")
        return False

def change_user_password(username, new_password):
    try:
        subprocess.run(f"net user {username} {new_password}", shell=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Ошибка", f"Не удалось изменить пароль: {e}")
        return False

def add_user_to_group(username, group):
    try:
        subprocess.run(f"net localgroup {group} {username} /add", shell=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Ошибка", f"Не удалось добавить в группу: {e}")
        return False

# --- Управление программами ---
def get_installed_programs():
    try:
        programs = []
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall") as key:
            i = 0
            while True:
                try:
                    subkey_name = winreg.EnumKey(key, i)
                    with winreg.OpenKey(key, subkey_name) as subkey:
                        try:
                            name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                            version = winreg.QueryValueEx(subkey, "DisplayVersion")[0] if winreg.QueryValueEx(subkey, "DisplayVersion") else ""
                            programs.append({'name': name, 'version': version})
                        except OSError:
                            pass
                    i += 1
                except OSError:
                    break
        return programs
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось получить список программ: {e}")
        return []

def uninstall_program(program_name):
    try:
        subprocess.run(f"wmic product where name='{program_name}' call uninstall", shell=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Ошибка", f"Не удалось удалить программу: {e}")
        return False

# --- Системное время ---
def set_system_time(new_time):
    try:
        subprocess.run(f"time {new_time}", shell=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Ошибка", f"Не удалось изменить время: {e}")
        return False

def set_system_date(new_date):
    try:
        subprocess.run(f"date {new_date}", shell=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Ошибка", f"Не удалось изменить дату: {e}")
        return False

# --- Удаленный рабочий стол ---
def toggle_remote_desktop(enable=True):
    try:
        value = "1" if enable else "0"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                          r"SYSTEM\CurrentControlSet\Control\Terminal Server",
                          0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "fDenyTSConnections", 0, winreg.REG_DWORD, int(value))
        return True
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось изменить настройки удаленного рабочего стола: {e}")
        return False

# --- Резервное копирование ---
def export_settings(file_path):
    try:
        settings = {
            "wallpaper": get_current_wallpaper(),
            "keyboard_layouts": get_installed_layouts(),
            "power_scheme": next((s["guid"] for s in get_power_schemes() if s["current"]), None),
            "startup_programs": get_startup_programs(),
            "hidden_files": bool(winreg.QueryValueEx(winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"), "Hidden")[0]),
            "file_extensions": not bool(winreg.QueryValueEx(winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"), "HideFileExt")[0])
        }
        with open(file_path, "w") as f:
            json.dump(settings, f, indent=4)
        return True
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось экспортировать настройки: {e}")
        return False

def import_settings(file_path):
    try:
        with open(file_path, "r") as f:
            settings = json.load(f)
        
        if settings.get("wallpaper"):
            set_wallpaper(settings["wallpaper"], "center")
        if settings.get("keyboard_layouts"):
            for layout in settings["keyboard_layouts"]:
                add_keyboard_layout(layout[0])
        if settings.get("power_scheme"):
            set_power_scheme(settings["power_scheme"])
        if settings.get("hidden_files") is not None:
            toggle_hidden_files(settings["hidden_files"])
        if settings.get("file_extensions") is not None:
            toggle_file_extensions(settings["file_extensions"])
        return True
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось импортировать настройки: {e}")
        return False

# --- Мониторинг системы ---
def get_system_stats():
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage("/").percent
    network = psutil.net_io_counters()
    return {
        "cpu": cpu,
        "ram": ram,
        "disk": disk,
        "network_sent": network.bytes_sent,
        "network_recv": network.bytes_recv
    }

# --- Управление процессами ---
def get_running_processes():
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent']):
        processes.append({
            "pid": proc.info['pid'],
            "name": proc.info['name'],
            "user": proc.info['username'],
            "cpu": proc.info['cpu_percent'],
            "memory": proc.info['memory_percent']
        })
    return processes

def kill_process(pid):
    try:
        psutil.Process(pid).terminate()
        return True
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось завершить процесс: {e}")
        return False

# --- Управление дисками ---
def get_disk_info():
    disks = []
    for partition in psutil.disk_partitions():
        usage = psutil.disk_usage(partition.mountpoint)
        disks.append({
            "device": partition.device,
            "mountpoint": partition.mountpoint,
            "fstype": partition.fstype,
            "total": usage.total,
            "used": usage.used,
            "free": usage.free,
            "percent": usage.percent
        })
    return disks

def format_disk(disk, fs_type="NTFS"):
    try:
        subprocess.run(f"format {disk} /FS:{fs_type} /Q", shell=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Ошибка", f"Не удалось отформатировать диск: {e}")
        return False

class WallpaperTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.available_wallpapers = find_windows_wallpapers()
        self.create_widgets()
    
    def create_widgets(self):
        left_frame = ttk.Frame(self)
        left_frame.pack(side="left", fill="y", padx=5, pady=5)
        
        ttk.Label(left_frame, text="Фоновый рисунок:").pack(anchor="w")
        
        self.wallpaper_list = tk.Listbox(left_frame, width=30, height=15)
        self.wallpaper_list.pack(fill="y", pady=5)
        self.wallpaper_list.bind('<<ListboxSelect>>', self.on_wallpaper_select)
        
        for name in sorted(self.available_wallpapers.keys()):
            self.wallpaper_list.insert(tk.END, name)
        
        ttk.Button(left_frame, text="Обзор...", command=self.browse_wallpaper).pack(pady=5)
        
        right_frame = ttk.Frame(self)
        right_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)
        
        self.preview_label = ttk.Label(right_frame, background="white")
        self.preview_label.pack(fill="both", expand=True)
        
        position_frame = ttk.LabelFrame(right_frame, text="Расположение изображения")
        position_frame.pack(fill="x", pady=5)
        
        self.position_var = tk.StringVar(value="center")
        
        ttk.Radiobutton(position_frame, text="По центру", variable=self.position_var, value="center").pack(anchor="w")
        ttk.Radiobutton(position_frame, text="Замостить", variable=self.position_var, value="tile").pack(anchor="w")
        ttk.Radiobutton(position_frame, text="Растянуть", variable=self.position_var, value="stretch").pack(anchor="w")
        
        btn_frame = ttk.Frame(right_frame)
        btn_frame.pack(fill="x", pady=10)
        
        ttk.Button(btn_frame, text="Применить", command=self.apply_wallpaper).pack(side="right", padx=5)
    
    def on_wallpaper_select(self, event):
        selection = self.wallpaper_list.curselection()
        if not selection:
            return
            
        selected_name = self.wallpaper_list.get(selection[0])
        selected_path = self.available_wallpapers.get(selected_name)
        
        self.show_preview(selected_path)
    
    def show_preview(self, image_path):
        if not image_path:
            self.preview_label.config(background="#0180C5")
            return
        
        try:
            img = Image.open(image_path)
            img.thumbnail((300, 200))
            photo = ImageTk.PhotoImage(img)
            
            self.preview_label.config(image=photo)
            self.preview_label.image = photo
        except Exception as e:
            print(f"Ошибка загрузки изображения: {e}")
            self.preview_label.config(image='')
            self.preview_label.image = None
            self.preview_label.config(background="#0180C5")
    
    def browse_wallpaper(self):
        filetypes = (
            ("Изображения", "*.bmp;*.jpg;*.jpeg;*.png"),
            ("Все файлы", "*.*")
        )
        
        filename = filedialog.askopenfilename(
            title="Выбор фонового рисунка",
            initialdir=os.path.join(os.environ["USERPROFILE"], "Pictures"),
            filetypes=filetypes
        )
        
        if filename:
            display_name = os.path.basename(filename)
            
            if display_name not in self.available_wallpapers:
                self.available_wallpapers[display_name] = filename
                self.wallpaper_list.insert(tk.END, display_name)
            
            self.wallpaper_list.selection_clear(0, tk.END)
            self.wallpaper_list.selection_set(tk.END)
            self.wallpaper_list.see(tk.END)
            self.show_preview(filename)
    
    def apply_wallpaper(self):
        selection = self.wallpaper_list.curselection()
        if not selection:
            return
            
        selected_name = self.wallpaper_list.get(selection[0])
        wallpaper_path = self.available_wallpapers.get(selected_name, "")
        position = self.position_var.get()
        
        if set_wallpaper(wallpaper_path, position):
            messagebox.showinfo("Успех", "Обои успешно изменены!")

class KeyboardTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.create_widgets()
        self.update_layouts_list()
    
    def create_widgets(self):
        ttk.Label(self, text="Установленные раскладки:").pack(anchor="w")
        
        self.layouts_list = ttk.Treeview(self, columns=("id", "name"), show="headings", height=5)
        self.layouts_list.heading("id", text="ID")
        self.layouts_list.heading("name", text="Название")
        self.layouts_list.column("id", width=100)
        self.layouts_list.column("name", width=200)
        self.layouts_list.pack(fill="x", pady=5)
        
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", pady=5)
        
        ttk.Button(btn_frame, text="Добавить раскладку", command=self.add_layout).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Удалить выбранную", command=self.remove_layout).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Обновить список", command=self.update_layouts_list).pack(side="right", padx=5)
    
    def update_layouts_list(self):
        self.layouts_list.delete(*self.layouts_list.get_children())
        for layout_id, layout_name in get_installed_layouts():
            self.layouts_list.insert("", "end", values=(layout_id, layout_name))
    
    def add_layout(self):
        dialog = tk.Toplevel(self)
        dialog.title("Добавить раскладку")
        dialog.geometry("400x300")
        
        ttk.Label(dialog, text="Выберите раскладку:").pack(anchor="w", padx=10, pady=5)
        
        # Получаем все доступные раскладки из реестра
        available_layouts = self.get_available_layouts()
        
        self.layout_var = tk.StringVar()
        layout_combobox = ttk.Combobox(dialog, textvariable=self.layout_var, values=[name for _, name in available_layouts])
        layout_combobox.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(dialog, text="Добавить", command=lambda: self.do_add_layout(dialog)).pack(pady=10)
    
    def get_available_layouts(self):
        layouts = []
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Keyboard Layouts") as key:
                i = 0
                while True:
                    try:
                        layout_id = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, layout_id) as subkey:
                            try:
                                layout_name = winreg.QueryValueEx(subkey, "Layout Text")[0]
                                layouts.append((layout_id, layout_name))
                            except WindowsError:
                                pass
                        i += 1
                    except WindowsError:
                        break
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось получить список раскладок: {e}")
        return layouts
    
    def do_add_layout(self, dialog):
        selected_name = self.layout_var.get()
        if not selected_name:
            messagebox.showwarning("Ошибка", "Выберите раскладку!")
            return
        
        # Находим ID выбранной раскладки
        available_layouts = self.get_available_layouts()
        layout_id = None
        for lid, name in available_layouts:
            if name == selected_name:
                layout_id = lid
                break
        
        if layout_id and add_keyboard_layout(layout_id):
            messagebox.showinfo("Успех", "Раскладка добавлена!")
            dialog.destroy()
            self.update_layouts_list()
        else:
            messagebox.showerror("Ошибка", "Не удалось добавить раскладку")
    
    def remove_layout(self):
        selected = self.layouts_list.focus()
        if selected:
            index = int(self.layouts_list.index(selected)) + 1
            if remove_keyboard_layout(index):
                self.update_layouts_list()
class SystemTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        
        # Секция файлов
        files_frame = ttk.LabelFrame(self, text="Отображение файлов")
        files_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(files_frame, text="Показать скрытые файлы", 
                  command=lambda: toggle_hidden_files(True)).pack(fill="x", pady=2)
        ttk.Button(files_frame, text="Скрыть скрытые файлы", 
                  command=lambda: toggle_hidden_files(False)).pack(fill="x", pady=2)
        ttk.Button(files_frame, text="Показать расширения", 
                  command=lambda: toggle_file_extensions(True)).pack(fill="x", pady=2)
        ttk.Button(files_frame, text="Скрыть расширения", 
                  command=lambda: toggle_file_extensions(False)).pack(fill="x", pady=2)
        
        # Секция оптимизации
        optimize_frame = ttk.LabelFrame(self, text="Оптимизация системы")
        optimize_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(optimize_frame, text="Очистить временные файлы", 
                  command=clean_temp_files).pack(fill="x", pady=5)

class PowerTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.create_widgets()
        self.update_schemes()
    
    def create_widgets(self):
        ttk.Label(self, text="Схемы управления питанием:").pack(anchor="w")
        
        self.schemes_list = ttk.Treeview(self, columns=("guid", "name", "current"), show="headings", height=5)
        self.schemes_list.heading("guid", text="GUID")
        self.schemes_list.heading("name", text="Название")
        self.schemes_list.heading("current", text="Текущая")
        self.schemes_list.column("guid", width=250)
        self.schemes_list.column("name", width=200)
        self.schemes_list.column("current", width=80)
        self.schemes_list.pack(fill="x", pady=5)
        
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", pady=5)
        
        ttk.Button(btn_frame, text="Применить схему", command=self.apply_scheme).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Обновить список", command=self.update_schemes).pack(side="right", padx=5)
    
    def update_schemes(self):
        self.schemes_list.delete(*self.schemes_list.get_children())
        for scheme in get_power_schemes():
            self.schemes_list.insert("", "end", values=(scheme['guid'], scheme['name'], "Да" if scheme['current'] else "Нет"))
    
    def apply_scheme(self):
        selected = self.schemes_list.focus()
        if selected:
            guid = self.schemes_list.item(selected)['values'][0]
            if set_power_scheme(guid):
                self.update_schemes()

class ServicesTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.create_widgets()
        self.update_services()
    
    def create_widgets(self):
        ttk.Label(self, text="Системные службы:").pack(anchor="w")
        
        self.services_list = ttk.Treeview(self, columns=("name", "status"), show="headings", height=10)
        self.services_list.heading("name", text="Имя службы")
        self.services_list.heading("status", text="Статус")
        self.services_list.column("name", width=300)
        self.services_list.column("status", width=150)
        self.services_list.pack(fill="both", expand=True, pady=5)
        
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", pady=5)
        
        ttk.Button(btn_frame, text="Запустить", command=lambda: self.change_service(True)).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Остановить", command=lambda: self.change_service(False)).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Обновить", command=self.update_services).pack(side="right", padx=5)
    
    def update_services(self):
        self.services_list.delete(*self.services_list.get_children())
        for service in get_services():
            self.services_list.insert("", "end", values=(service, "Неизвестно"))
    
    def change_service(self, start):
        selected = self.services_list.focus()
        if selected:
            service_name = self.services_list.item(selected)['values'][0]
            if change_service_state(service_name, start):
                self.update_services()

class StartupTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.create_widgets()
        self.update_programs()
    
    def create_widgets(self):
        ttk.Label(self, text="Программы в автозагрузке:").pack(anchor="w")
        
        self.programs_list = ttk.Treeview(self, columns=("name", "path", "location"), show="headings", height=8)
        self.programs_list.heading("name", text="Имя программы")
        self.programs_list.heading("path", text="Путь")
        self.programs_list.heading("location", text="Расположение")
        self.programs_list.column("name", width=200)
        self.programs_list.column("path", width=250)
        self.programs_list.column("location", width=100)
        self.programs_list.pack(fill="both", expand=True, pady=5)
        
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", pady=5)
        
        ttk.Button(btn_frame, text="Добавить", command=self.add_program).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Удалить", command=self.remove_program).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Обновить", command=self.update_programs).pack(side="right", padx=5)
    
    def update_programs(self):
        self.programs_list.delete(*self.programs_list.get_children())
        for program in get_startup_programs():
            self.programs_list.insert("", "end", values=(program['name'], program['path'], program['location']))
    
    def add_program(self):
        dialog = tk.Toplevel(self)
        dialog.title("Добавить программу в автозагрузку")
        dialog.geometry("500x300")
        
        ttk.Label(dialog, text="Имя программы:").pack(anchor="w", padx=10, pady=5)
        name_entry = ttk.Entry(dialog)
        name_entry.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(dialog, text="Путь к программе:").pack(anchor="w", padx=10, pady=5)
        path_entry = ttk.Entry(dialog)
        path_entry.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(dialog, text="Обзор...", command=lambda: self.browse_program(path_entry)).pack(pady=5)
        
        ttk.Label(dialog, text="Расположение:").pack(anchor="w", padx=10, pady=5)
        location_var = tk.StringVar(value="user")
        ttk.Radiobutton(dialog, text="Только для текущего пользователя", variable=location_var, value="user").pack(anchor="w")
        ttk.Radiobutton(dialog, text="Для всех пользователей", variable=location_var, value="system").pack(anchor="w")
        
        ttk.Button(dialog, text="Добавить", command=lambda: self.do_add_program(
            name_entry.get(),
            path_entry.get(),
            location_var.get(),
            dialog
        )).pack(pady=10)
    
    def browse_program(self, entry):
        filename = filedialog.askopenfilename(
            title="Выбор программы",
            filetypes=(("Исполняемые файлы", "*.exe"), ("Все файлы", "*.*"))
        )
        if filename:
            entry.delete(0, tk.END)
            entry.insert(0, filename)
    
    def do_add_program(self, name, path, location, dialog):
        if name and path:
            if toggle_startup_program(name, path, True, location):
                dialog.destroy()
                self.update_programs()
    
    def remove_program(self):
        selected = self.programs_list.focus()
        if selected:
            program = self.programs_list.item(selected)['values']
            if toggle_startup_program(program[0], program[1], False, "user" if program[2] == "Пользователь" else "system"):
                self.update_programs()

class NetworkTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.create_widgets()
        self.update_adapters()
    
    def create_widgets(self):
        ttk.Label(self, text="Сетевые адаптеры:").pack(anchor="w")
        
        self.adapters_list = ttk.Treeview(self, columns=("name", "status"), show="headings", height=8)
        self.adapters_list.heading("name", text="Имя адаптера")
        self.adapters_list.heading("status", text="Статус")
        self.adapters_list.column("name", width=300)
        self.adapters_list.column("status", width=150)
        self.adapters_list.pack(fill="both", expand=True, pady=5)
        
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", pady=5)
        
        ttk.Button(btn_frame, text="Включить", command=lambda: self.toggle_adapter(True)).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Выключить", command=lambda: self.toggle_adapter(False)).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Обновить", command=self.update_adapters).pack(side="right", padx=5)
    
    def update_adapters(self):
        self.adapters_list.delete(*self.adapters_list.get_children())
        for adapter in get_network_adapters():
            self.adapters_list.insert("", "end", values=(adapter['name'], adapter['status']))
    
    def toggle_adapter(self, enable):
        selected = self.adapters_list.focus()
        if selected:
            adapter_name = self.adapters_list.item(selected)['values'][0]
            if toggle_network_adapter(adapter_name, enable):
                self.update_adapters()

class UsersTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.create_widgets()
        self.update_users()
    
    def create_widgets(self):
        ttk.Label(self, text="Учетные записи пользователей:").pack(anchor="w")
        
        self.users_list = ttk.Treeview(self, columns=("name",), show="headings", height=8)
        self.users_list.heading("name", text="Имя пользователя")
        self.users_list.column("name", width=300)
        self.users_list.pack(fill="both", expand=True, pady=5)
        
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", pady=5)
        
        ttk.Button(btn_frame, text="Создать пользователя", command=self.create_user).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Изменить пароль", command=self.change_password).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Добавить в группу", command=self.add_to_group).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Обновить", command=self.update_users).pack(side="right", padx=5)
    
    def update_users(self):
        self.users_list.delete(*self.users_list.get_children())
        for user in get_user_accounts():
            self.users_list.insert("", "end", values=(user,))
    
    def create_user(self):
        dialog = tk.Toplevel(self)
        dialog.title("Создание нового пользователя")
        dialog.geometry("300x200")
        
        ttk.Label(dialog, text="Имя пользователя:").pack(anchor="w", padx=10, pady=5)
        name_entry = ttk.Entry(dialog)
        name_entry.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(dialog, text="Пароль:").pack(anchor="w", padx=10, pady=5)
        pass_entry = ttk.Entry(dialog, show="*")
        pass_entry.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(dialog, text="Создать", command=lambda: self.do_create_user(
            name_entry.get(),
            pass_entry.get(),
            dialog
        )).pack(pady=10)
    
    def do_create_user(self, username, password, dialog):
        if username and password:
            if create_user_account(username, password):
                dialog.destroy()
                self.update_users()
    
    def change_password(self):
        selected = self.users_list.focus()
        if selected:
            username = self.users_list.item(selected)['values'][0]
            new_password = simpledialog.askstring("Изменение пароля", f"Введите новый пароль для {username}:", show="*")
            if new_password:
                if change_user_password(username, new_password):
                    messagebox.showinfo("Успех", "Пароль изменен!")
    
    def add_to_group(self):
        selected = self.users_list.focus()
        if selected:
            username = self.users_list.item(selected)['values'][0]
            group = simpledialog.askstring("Добавление в группу", f"Введите название группы для {username}:")
            if group:
                if add_user_to_group(username, group):
                    messagebox.showinfo("Успех", f"Пользователь {username} добавлен в группу {group}!")

class ProgramsTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.create_widgets()
        self.update_programs()
    
    def create_widgets(self):
        ttk.Label(self, text="Установленные программы:").pack(anchor="w")
        
        self.programs_list = ttk.Treeview(self, columns=("name", "version"), show="headings", height=15)
        self.programs_list.heading("name", text="Имя программы")
        self.programs_list.heading("version", text="Версия")
        self.programs_list.column("name", width=300)
        self.programs_list.column("version", width=150)
        self.programs_list.pack(fill="both", expand=True, pady=5)
        
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", pady=5)
        
        ttk.Button(btn_frame, text="Удалить", command=self.uninstall_program).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Обновить", command=self.update_programs).pack(side="right", padx=5)
    
    def update_programs(self):
        self.programs_list.delete(*self.programs_list.get_children())
        for program in get_installed_programs():
            self.programs_list.insert("", "end", values=(program['name'], program['version']))
    
    def uninstall_program(self):
        selected = self.programs_list.focus()
        if selected:
            program_name = self.programs_list.item(selected)['values'][0]
            if messagebox.askyesno("Подтверждение", f"Вы действительно хотите удалить {program_name}?"):
                if uninstall_program(program_name):
                    self.update_programs()

class SystemSettingsTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.create_widgets()
    
    def create_widgets(self):
        # Дата и время
        time_frame = ttk.LabelFrame(self, text="Дата и время")
        time_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(time_frame, text="Изменить дату", command=self.change_date).pack(fill="x", pady=2)
        ttk.Button(time_frame, text="Изменить время", command=self.change_time).pack(fill="x", pady=2)
        
        # Удаленный рабочий стол
        remote_frame = ttk.LabelFrame(self, text="Удаленный рабочий стол")
        remote_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(remote_frame, text="Включить удаленный доступ", 
                  command=lambda: toggle_remote_desktop(True)).pack(fill="x", pady=2)
        ttk.Button(remote_frame, text="Отключить удаленный доступ", 
                  command=lambda: toggle_remote_desktop(False)).pack(fill="x", pady=2)
    
    def change_date(self):
        new_date = simpledialog.askstring("Изменение даты", "Введите новую дату (ДД-ММ-ГГГГ):")
        if new_date:
            set_system_date(new_date)
    
    def change_time(self):
        new_time = simpledialog.askstring("Изменение времени", "Введите новое время (ЧЧ:ММ:СС):")
        if new_time:
            set_system_time(new_time)

class BackupTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.create_widgets()

    def create_widgets(self):
        ttk.Label(self, text="Резервное копирование настроек:").pack(anchor="w", pady=5)
        
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", pady=5)
        
        ttk.Button(btn_frame, text="Экспорт настроек", command=self.export_settings).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Импорт настроек", command=self.import_settings).pack(side="left", padx=5)

    def export_settings(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if file_path:
            if export_settings(file_path):
                messagebox.showinfo("Успех", "Настройки успешно экспортированы!")

    def import_settings(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if file_path:
            if import_settings(file_path):
                messagebox.showinfo("Успех", "Настройки успешно импортированы!")

class SystemMonitorTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.create_widgets()
        self.update_stats()

    def create_widgets(self):
        ttk.Label(self, text="Мониторинг системы:").pack(anchor="w", pady=5)
        
        # CPU
        self.cpu_label = ttk.Label(self, text="CPU: 0%")
        self.cpu_label.pack(anchor="w")
        self.cpu_bar = ttk.Progressbar(self, length=200, mode="determinate")
        self.cpu_bar.pack(fill="x", pady=2)
        
        # RAM
        self.ram_label = ttk.Label(self, text="RAM: 0%")
        self.ram_label.pack(anchor="w")
        self.ram_bar = ttk.Progressbar(self, length=200, mode="determinate")
        self.ram_bar.pack(fill="x", pady=2)
        
        # Disk
        self.disk_label = ttk.Label(self, text="Disk (C:): 0%")
        self.disk_label.pack(anchor="w")
        self.disk_bar = ttk.Progressbar(self, length=200, mode="determinate")
        self.disk_bar.pack(fill="x", pady=2)

    def update_stats(self):
        stats = get_system_stats()
        self.cpu_label.config(text=f"CPU: {stats['cpu']}%")
        self.cpu_bar["value"] = stats["cpu"]
        self.ram_label.config(text=f"RAM: {stats['ram']}%")
        self.ram_bar["value"] = stats["ram"]
        self.disk_label.config(text=f"Disk (C:): {stats['disk']}%")
        self.disk_bar["value"] = stats["disk"]
        self.after(1000, self.update_stats)

class ProcessManagerTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.create_widgets()
        self.update_processes()

    def create_widgets(self):
        ttk.Label(self, text="Управление процессами:").pack(anchor="w", pady=5)
        
        self.processes_list = ttk.Treeview(self, columns=("pid", "name", "user", "cpu", "memory"), show="headings", height=15)
        self.processes_list.heading("pid", text="PID")
        self.processes_list.heading("name", text="Имя")
        self.processes_list.heading("user", text="Пользователь")
        self.processes_list.heading("cpu", text="CPU (%)")
        self.processes_list.heading("memory", text="RAM (%)")
        self.processes_list.column("pid", width=80)
        self.processes_list.column("name", width=200)
        self.processes_list.column("user", width=150)
        self.processes_list.column("cpu", width=80)
        self.processes_list.column("memory", width=80)
        self.processes_list.pack(fill="both", expand=True, pady=5)
        
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", pady=5)
        
        ttk.Button(btn_frame, text="Обновить", command=self.update_processes).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Завершить процесс", command=self.kill_selected_process).pack(side="left", padx=5)

    def update_processes(self):
        self.processes_list.delete(*self.processes_list.get_children())
        for proc in get_running_processes():
            self.processes_list.insert("", "end", values=(proc["pid"], proc["name"], proc["user"], f"{proc['cpu']:.1f}", f"{proc['memory']:.1f}"))

    def kill_selected_process(self):
        selected = self.processes_list.focus()
        if selected:
            pid = int(self.processes_list.item(selected)["values"][0])
            if kill_process(pid):
                self.update_processes()

class DiskManagerTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.create_widgets()
        self.update_disks()

    def create_widgets(self):
        ttk.Label(self, text="Управление дисками:").pack(anchor="w", pady=5)
        
        self.disks_list = ttk.Treeview(self, columns=("device", "mountpoint", "fstype", "total", "used", "free", "percent"), show="headings", height=8)
        self.disks_list.heading("device", text="Диск")
        self.disks_list.heading("mountpoint", text="Точка монтирования")
        self.disks_list.heading("fstype", text="Файловая система")
        self.disks_list.heading("total", text="Всего (GB)")
        self.disks_list.heading("used", text="Использовано (GB)")
        self.disks_list.heading("free", text="Свободно (GB)")
        self.disks_list.heading("percent", text="Заполнено (%)")
        self.disks_list.column("device", width=100)
        self.disks_list.column("mountpoint", width=150)
        self.disks_list.column("fstype", width=100)
        self.disks_list.column("total", width=100)
        self.disks_list.column("used", width=100)
        self.disks_list.column("free", width=100)
        self.disks_list.column("percent", width=100)
        self.disks_list.pack(fill="both", expand=True, pady=5)
        
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", pady=5)
        
        ttk.Button(btn_frame, text="Обновить", command=self.update_disks).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Форматировать", command=self.format_selected_disk).pack(side="left", padx=5)

    def update_disks(self):
        self.disks_list.delete(*self.disks_list.get_children())
        for disk in get_disk_info():
            total_gb = disk["total"] / (1024 ** 3)
            used_gb = disk["used"] / (1024 ** 3)
            free_gb = disk["free"] / (1024 ** 3)
            self.disks_list.insert("", "end", values=(
                disk["device"],
                disk["mountpoint"],
                disk["fstype"],
                f"{total_gb:.2f}",
                f"{used_gb:.2f}",
                f"{free_gb:.2f}",
                f"{disk['percent']:.1f}"
            ))

    def format_selected_disk(self):
        selected = self.disks_list.focus()
        if selected:
            disk = self.disks_list.item(selected)["values"][0]
            if messagebox.askyesno("Подтверждение", f"Форматировать диск {disk}? Все данные будут удалены!"):
                if format_disk(disk):
                    self.update_disks()

# ======================== ОСНОВНОЕ ОКНО ========================
class ControlPanelApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("UniControl - Полная панель управления")
        self.root.geometry("1200x800")
        
        if not is_admin():
            messagebox.showwarning("Внимание", "Некоторые функции требуют прав администратора!")
            run_as_admin()
        
        self.create_ui()
    
    def create_ui(self):
        # Настройка стилей (темы)
        self.style = ttk.Style()
        self.style.theme_use("clam")  # Базовая тема
        
        # Переключатель темы
        self.dark_mode = tk.BooleanVar(value=False)
        theme_switch = ttk.Checkbutton(self.root, text="Темная тема", variable=self.dark_mode, command=self.toggle_theme)
        theme_switch.pack(anchor="ne", padx=10, pady=5)
        
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Добавляем вкладки
        notebook.add(WallpaperTab(notebook), text="Обои")
        notebook.add(KeyboardTab(notebook), text="Раскладки")
        notebook.add(SystemTab(notebook), text="Система")
        notebook.add(PowerTab(notebook), text="Питание")
        notebook.add(ServicesTab(notebook), text="Службы")
        notebook.add(StartupTab(notebook), text="Автозагрузка")
        notebook.add(NetworkTab(notebook), text="Сеть")
        notebook.add(UsersTab(notebook), text="Пользователи")
        notebook.add(ProgramsTab(notebook), text="Программы")
        notebook.add(SystemSettingsTab(notebook), text="Настройки")
        notebook.add(BackupTab(notebook), text="Резервное копирование")
        notebook.add(SystemMonitorTab(notebook), text="Мониторинг")
        notebook.add(ProcessManagerTab(notebook), text="Процессы")
        notebook.add(DiskManagerTab(notebook), text="Диски")
        
        notebook.select(0)
    
    def toggle_theme(self):
        if self.dark_mode.get():
            self.root.configure(bg="#2d2d2d")
            self.style.theme_use("alt")
        else:
            self.root.configure(bg="SystemButtonFace")
            self.style.theme_use("clam")
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = ControlPanelApp()
    app.run()
