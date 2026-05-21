import tkinter as tk
from tkinter import ttk, messagebox
import threading
import webbrowser
import time
from pathlib import Path
import requests

from config import config
from database import database
from utils.logger import logger
from openclaw_trigger import openclaw_trigger
from utils.subtitle_extractor import subtitle_extractor
import asyncio


class MainWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Bilibili AI Client")
        self.root.geometry("900x600")
        self.root.minsize(800, 500)

        self._setup_ui()
        self._load_data()
        self._start_auto_refresh()

        if config.get("window_geometry"):
            try:
                self.root.geometry(config.get("window_geometry"))
            except Exception:
                pass

        self.refresh_job = None
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _start_auto_refresh(self):
        self._auto_refresh()

    def _auto_refresh(self):
        self._refresh_messages()
        self._refresh_history()
        self.refresh_job = self.root.after(5000, self._auto_refresh)

    def _setup_ui(self):
        menu_bar = tk.Menu(self.root)
        self.root.config(menu=menu_bar)

        file_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="刷新", command=self._refresh)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self._on_close)

        help_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="关于", command=self._show_about)

        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        left_frame = ttk.Frame(main_paned, width=250)
        main_paned.add(left_frame, weight=0)

        self._setup_left_panel(left_frame)

        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=1)

        self._setup_right_panel(right_frame)

        self.status_bar = ttk.Label(self.root, text="就绪", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _setup_left_panel(self, parent):
        title_label = ttk.Label(parent, text="白名单管理", font=("", 12, "bold"))
        title_label.pack(pady=(0, 10))

        input_frame = ttk.Frame(parent)
        input_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(input_frame, text="UID:").grid(row=0, column=0, sticky=tk.W)
        self.uid_entry = ttk.Entry(input_frame, width=15)
        self.uid_entry.grid(row=0, column=1, padx=5)

        ttk.Label(input_frame, text="用户名:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        self.username_entry = ttk.Entry(input_frame, width=15)
        self.username_entry.grid(row=1, column=1, padx=5, pady=(5, 0))

        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(btn_frame, text="添加", command=self._add_whitelist).pack(side=tk.LEFT, expand=True, padx=2)
        ttk.Button(btn_frame, text="删除", command=self._remove_whitelist).pack(side=tk.LEFT, expand=True, padx=2)

        list_frame = ttk.Frame(parent)
        list_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(list_frame, text="白名单列表:").pack(anchor=tk.W)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.whitelist_box = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, height=15)
        self.whitelist_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.whitelist_box.yview)

    def _setup_right_panel(self, parent):
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True)

        tab1 = ttk.Frame(notebook)
        tab2 = ttk.Frame(notebook)
        tab3 = ttk.Frame(notebook)
        tab4 = ttk.Frame(notebook)

        notebook.add(tab1, text="消息记录")
        notebook.add(tab2, text="摘要历史")
        notebook.add(tab3, text="统计")
        notebook.add(tab4, text="设置")

        self._setup_messages_tab(tab1)
        self._setup_history_tab(tab2)
        self._setup_stats_tab(tab3)
        self._setup_settings_tab(tab4)

    def _setup_messages_tab(self, parent):
        scrollbar = ttk.Scrollbar(parent)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.message_list = tk.Listbox(parent, yscrollcommand=scrollbar.set,
                                        font=("Consolas", 9), height=10)
        self.message_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.config(command=self.message_list.yview)

        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(btn_frame, text="刷新", command=self._refresh_messages).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="处理选中", command=self._process_message).pack(side=tk.LEFT, padx=2)

        self.message_list.bind("<Double-Button-1>", lambda e: self._process_message())

    def _setup_history_tab(self, parent):
        scrollbar = ttk.Scrollbar(parent)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.history_list = tk.Listbox(parent, yscrollcommand=scrollbar.set,
                                       font=("Consolas", 9))
        self.history_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.config(command=self.history_list.yview)

        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(btn_frame, text="刷新", command=self._refresh_history).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="查看详情", command=self._view_summary).pack(side=tk.LEFT, padx=2)

    def _setup_stats_tab(self, parent):
        stats_frame = ttk.Frame(parent, padding=20)
        stats_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(stats_frame, text="统计数据", font=("", 14, "bold")).pack(pady=(0, 20))

        self.today_label = ttk.Label(stats_frame, text="今日处理: 0", font=("", 12))
        self.today_label.pack(pady=10)

        self.total_label = ttk.Label(stats_frame, text="总处理量: 0", font=("", 12))
        self.total_label.pack(pady=10)

        ttk.Button(stats_frame, text="刷新", command=self._refresh_stats).pack(pady=10)

    def _load_data(self):
        self._refresh_whitelist()
        self._refresh_messages()
        self._refresh_history()
        self._refresh_stats()

    def _refresh_whitelist(self):
        self.whitelist_box.delete(0, tk.END)
        for item in database.get_whitelist():
            self.whitelist_box.insert(tk.END, f"{item['uid']} ({item.get('username', '')})")

    def _refresh_messages(self):
        self.message_list.delete(0, tk.END)
        for msg in database.get_messages(50):
            status_icon = "✓" if msg["status"] == "processed" else "○"
            self.message_list.insert(tk.END,
                f"{status_icon} [{msg['bv_id']}] {msg.get('sender_name', msg['sender_uid'])}: {msg.get('content', '')[:50]}")

    def _refresh_history(self):
        self.history_list.delete(0, tk.END)
        for s in database.get_summaries(100):
            self.history_list.insert(tk.END,
                f"[{s['bv_id']}] {s.get('sender_name', s.get('sender_uid', ''))} - {s.get('summary_text', '')[:50]}")

    def _refresh_stats(self):
        today = database.get_today_count()
        total = database.get_total_count()
        self.today_label.config(text=f"今日处理: {today}")
        self.total_label.config(text=f"总处理量: {total}")

    def _setup_settings_tab(self, parent):
        settings_frame = ttk.Frame(parent, padding=20)
        settings_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(settings_frame, text="B站认证Cookie:", font=("", 10, "bold")).pack(anchor=tk.W, pady=(0, 5))
        auth_frame = ttk.Frame(settings_frame)
        auth_frame.pack(fill=tk.X, pady=(0, 20))

        self.auth_entry = tk.Text(auth_frame, height=4, width=50, font=("Consolas", 9), state="disabled")
        self.auth_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.auth_entry.insert("1.0", config.get("bili_auth", "") or "未登录")

        auth_btn_frame = ttk.Frame(settings_frame)
        auth_btn_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Button(auth_btn_frame, text="网页登录", command=self._open_bili_login).pack(side=tk.LEFT, padx=2)
        ttk.Button(auth_btn_frame, text="手动输入Cookie", command=self._show_cookie_input).pack(side=tk.LEFT, padx=2)
        ttk.Button(auth_btn_frame, text="清除登录", command=self._clear_cookie).pack(side=tk.LEFT, padx=2)

        ttk.Label(settings_frame, text="轮询间隔(秒):").pack(anchor=tk.W, pady=(0, 5))
        interval_frame = ttk.Frame(settings_frame)
        interval_frame.pack(fill=tk.X, pady=(0, 20))

        self.interval_entry = ttk.Entry(interval_frame, width=10)
        self.interval_entry.pack(side=tk.LEFT)
        self.interval_entry.insert(0, str(config.get("polling_interval", 30)))

        ttk.Label(settings_frame, text="OpenClaw 路径:").pack(anchor=tk.W, pady=(0, 5))
        openclaw_frame = ttk.Frame(settings_frame)
        openclaw_frame.pack(fill=tk.X, pady=(0, 20))

        self.openclaw_path_entry = ttk.Entry(openclaw_frame, width=50)
        self.openclaw_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.openclaw_path_entry.insert(0, config.get("openclaw_path", "openclaw"))

        ttk.Label(settings_frame, text="Webhook接收端口:").pack(anchor=tk.W, pady=(0, 5))
        port_frame = ttk.Frame(settings_frame)
        port_frame.pack(fill=tk.X, pady=(0, 20))

        self.port_entry = ttk.Entry(port_frame, width=10)
        self.port_entry.pack(side=tk.LEFT)
        self.port_entry.insert(0, str(config.get("webhook_port", 18792)))

        self.auto_start_var = tk.BooleanVar(value=config.get("auto_start", True))
        ttk.Checkbutton(settings_frame, text="启动时自动开始轮询", variable=self.auto_start_var).pack(anchor=tk.W, pady=(0, 20))

        ttk.Button(settings_frame, text="保存设置", command=self._save_settings).pack(pady=10)

    def _save_settings(self):
        interval = self.interval_entry.get().strip()
        openclaw_path = self.openclaw_path_entry.get().strip()
        port = self.port_entry.get().strip()
        auto_start = self.auto_start_var.get()

        try:
            config.set("polling_interval", int(interval))
        except ValueError:
            pass
        config.set("openclaw_path", openclaw_path)
        try:
            config.set("webhook_port", int(port))
        except ValueError:
            pass
        config.set("auto_start", auto_start)

        self._set_status("设置已保存")

    def _refresh(self):
        self._load_data()
        self._set_status("已刷新")

    def _add_whitelist(self):
        uid = self.uid_entry.get().strip()
        username = self.username_entry.get().strip()

        if not uid:
            messagebox.showwarning("警告", "请输入UID")
            return

        if database.add_whitelist(uid, username or None):
            self._refresh_whitelist()
            self.uid_entry.delete(0, tk.END)
            self.username_entry.delete(0, tk.END)
            self._set_status(f"已添加白名单: {uid}")
            threading.Thread(target=self._reprocess_blocked, args=(uid,), daemon=True).start()
        else:
            messagebox.showerror("错误", "添加失败")

    def _remove_whitelist(self):
        selection = self.whitelist_box.curselection()
        if not selection:
            return

        content = self.whitelist_box.get(selection[0])
        uid = content.split()[0]

        if database.remove_whitelist(uid):
            self._refresh_whitelist()
            self._set_status(f"已删除白名单: {uid}")
        else:
            messagebox.showerror("错误", "删除失败")

    def _reprocess_blocked(self, uid=None):
        try:
            import main
            blocked = database.get_not_whitelisted_messages()
            if blocked:
                logger.info(f"重新处理 {len(blocked)} 条被拦截的消息")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(main.reprocess_blocked_messages(uid=uid))
                loop.close()
                self._refresh_messages()
        except Exception as e:
            logger.error(f"重新处理消息失败: {e}")

    def _process_message(self):
        selection = self.message_list.curselection()
        if not selection:
            return

        content = self.message_list.get(selection[0])
        try:
            bv_id = content.split("[")[1].split("]")[0]
        except Exception:
            self._set_status("无法解析BV号")
            return

        self._set_status(f"处理中: {bv_id}")

        def do_process():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                subtitle_text = subtitle_extractor.extract_text(f"https://www.bilibili.com/video/{bv_id}")

                if subtitle_text:
                    success = openclaw_trigger.trigger(
                        bv_id=bv_id,
                        subtitle_text=subtitle_text,
                        sender_uid="",
                        sender_name=""
                    )
                    if success:
                        self._set_status(f"已触发: {bv_id}")
                    else:
                        self._set_status(f"触发失败: {bv_id}")
                else:
                    self._set_status(f"无字幕: {bv_id}")

                loop.close()
            except Exception as e:
                self._set_status(f"错误: {e}")

        threading.Thread(target=do_process, daemon=True).start()

    def _view_summary(self):
        selection = self.history_list.curselection()
        if not selection:
            return

        content = self.history_list.get(selection[0])
        try:
            bv_id = content.split("[")[1].split("]")[0]
        except Exception:
            return

        summaries = database.get_summaries(100)
        target = None
        for s in summaries:
            if s["bv_id"] == bv_id:
                target = s
                break

        if not target:
            return

        detail_win = tk.Toplevel(self.root)
        detail_win.title(f"摘要详情 - {bv_id}")
        detail_win.geometry("600x400")

        info_frame = ttk.Frame(detail_win, padding=10)
        info_frame.pack(fill=tk.X)

        ttk.Label(info_frame, text=f"BV号: {bv_id}").pack(anchor=tk.W)
        ttk.Label(info_frame, text=f"发送者: {target.get('sender_name', target.get('sender_uid', 'N/A'))}").pack(anchor=tk.W)
        ttk.Label(info_frame, text=f"时间: {target.get('created_at', 'N/A')}").pack(anchor=tk.W)

        ttk.Label(detail_win, text="字幕内容:", padding=(10, 10, 0, 0)).pack(anchor=tk.W)

        sub_text = tk.Text(detail_win, height=8, font=("Consolas", 9))
        sub_text.pack(fill=tk.X, padx=10)
        sub_text.insert("1.0", target.get("subtitle_text", "无")[:2000])
        sub_text.config(state="disabled")

        ttk.Label(detail_win, text="摘要:", padding=(10, 10, 0, 0)).pack(anchor=tk.W)

        sum_text = tk.Text(detail_win, height=8, font=("Consolas", 9))
        sum_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        sum_text.insert("1.0", target.get("summary_text", "无"))
        sum_text.config(state="disabled")

    def _open_bili_login(self):
        existing_cookie = config.get("bili_auth", "")
        if existing_cookie:
            self.auth_entry.config(state="normal")
            self.auth_entry.delete("1.0", tk.END)
            self.auth_entry.insert("1.0", "已登录 (Cookie已保存)")
            self.auth_entry.config(state="disabled")
            self._set_status("已登录，无需重新扫码")
            return

        self._set_status("正在启动登录服务...")

        def start_server():
            from bilibili_login import run_login_server
            run_login_server(51888)

        def check_login():
            try:
                from utils.app_data import APP_DATA_DIR
                cookie_file = APP_DATA_DIR / "login_cookie.txt"
                if cookie_file.exists():
                    cookie = cookie_file.read_text(encoding='utf-8').strip()
                    if cookie:
                        config.set("bili_auth", cookie)
                        self.auth_entry.config(state="normal")
                        self.auth_entry.delete("1.0", tk.END)
                        self.auth_entry.insert("1.0", "登录成功！")
                        self.auth_entry.config(state="disabled")
                        self._set_status("B站登录成功！")
                        try:
                            import requests
                            requests.post("http://127.0.0.1:51888/close", timeout=2)
                        except:
                            pass
                        return True
            except Exception as e:
                self._set_status(f"检查登录状态: {e}")
            return False

        def poll_login():
            for _ in range(120):
                time.sleep(1)
                if check_login():
                    return
            self._set_status("登录超时，请重试")

        server_thread = threading.Thread(target=start_server, daemon=True)
        server_thread.start()

        time.sleep(2)

        try:
            webbrowser.open("http://127.0.0.1:51888")
            self._set_status("请在浏览器中扫码登录")
        except Exception as e:
            self._set_status(f"打开浏览器失败: {e}")

        poll_thread = threading.Thread(target=poll_login, daemon=True)
        poll_thread.start()

    def _show_cookie_input(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("手动输入Cookie")
        dialog.geometry("500x300")

        ttk.Label(dialog, text="请在B站开发者工具中复制cookie值粘贴到下方:").pack(pady=10)

        text = tk.Text(dialog, font=("Consolas", 9))
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        current = config.get("bili_auth", "")
        if current:
            text.insert("1.0", current)

        def save():
            cookie = text.get("1.0", tk.END).strip()
            if cookie:
                config.set("bili_auth", cookie)
                self.auth_entry.config(state="normal")
                self.auth_entry.delete("1.0", tk.END)
                self.auth_entry.insert("1.0", cookie[:50] + "..." if len(cookie) > 50 else cookie)
                self.auth_entry.config(state="disabled")
                self._set_status("Cookie已保存")
            dialog.destroy()

        ttk.Button(dialog, text="保存", command=save).pack(pady=10)

    def _clear_cookie(self):
        config.set("bili_auth", "")
        self.auth_entry.config(state="normal")
        self.auth_entry.delete("1.0", tk.END)
        self.auth_entry.insert("1.0", "未登录")
        self.auth_entry.config(state="disabled")
        self._set_status("已清除登录信息")

    def _show_about(self):
        messagebox.showinfo("关于", "Bilibili AI Client v1.0\n\n自动处理B站视频字幕并生成摘要")

    def _set_status(self, text: str):
        self.status_bar.config(text=text)

    def _on_close(self):
        if self.refresh_job:
            self.root.after_cancel(self.refresh_job)
        geometry = self.root.geometry()
        config.set("window_geometry", geometry)
        self.root.destroy()

    def run(self):
        self.root.mainloop()