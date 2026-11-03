"""Phone Audio Bridge - stream your Android phone's audio to this PC over Wi-Fi (via scrcpy)."""
import json, os, re, subprocess, sys, threading, time, tkinter as tk
from tkinter import ttk
import winreg

APP = "Phone Audio Bridge"
NOWIN = 0x08000000
CFG = os.path.join(os.environ.get("APPDATA", "."), "PhoneAudioBridge", "config.json")
BG, CARD, FG, DIM, ACC, BAD = "#0f1115", "#1a1d24", "#e8eaed", "#8b93a1", "#14d9b5", "#ff5c6c"
RUNKEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def run(*a, t=20):
    return subprocess.run(a, capture_output=True, text=True, timeout=t, creationflags=NOWIN).stdout


def load():
    try:
        return json.load(open(CFG))
    except Exception:
        return {"ip": "", "buffer": 100, "autostart": False, "autostream": False}


def save(c):
    os.makedirs(os.path.dirname(CFG), exist_ok=True)
    json.dump(c, open(CFG, "w"))


def set_autostart(on):
    exe = sys.executable.replace("python.exe", "pythonw.exe")
    cmd = f'"{exe}" "{os.path.abspath(__file__)}" --minimized'
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUNKEY, 0, winreg.KEY_SET_VALUE) as k:
        if on:
            winreg.SetValueEx(k, APP, 0, winreg.REG_SZ, cmd)
        else:
            try: winreg.DeleteValue(k, APP)
            except FileNotFoundError: pass


class App:
    proc = None
    want = False

    def __init__(s, r):
        s.r, s.cfg = r, load()
        r.title(APP); r.geometry("380x600"); r.configure(bg=BG); r.resizable(False, False)
        st = ttk.Style(); st.theme_use("clam")
        st.configure("TScale", background=BG, troughcolor=CARD)
        st.configure("TCheckbutton", background=BG, foreground=FG, focuscolor=BG)
        st.map("TCheckbutton", background=[("active", BG)])
        tk.Label(r, text="Phone Audio Bridge", bg=BG, fg=FG, font=("Segoe UI", 17, "bold")).pack(pady=(20, 0))
        tk.Label(r, text="Android sound  →  this PC, over Wi-Fi", bg=BG, fg=DIM, font=("Segoe UI", 9)).pack()

        s.cv = tk.Canvas(r, width=170, height=170, bg=BG, highlightthickness=0)
        s.cv.pack(pady=18)
        s.ring = s.cv.create_oval(10, 10, 160, 160, outline=CARD, width=6)
        s.disc = s.cv.create_oval(30, 30, 140, 140, fill=CARD, outline="")
        s.icon = s.cv.create_text(85, 82, text="▶", fill=FG, font=("Segoe UI Symbol", 34))
        s.lbl = s.cv.create_text(85, 118, text="START", fill=DIM, font=("Segoe UI", 9, "bold"))
        s.cv.bind("<Button-1>", lambda e: s.toggle()); s.cv.config(cursor="hand2")

        s.status = tk.StringVar(value="Ready")
        tk.Label(r, textvariable=s.status, bg=BG, fg=DIM, font=("Segoe UI", 10), wraplength=340).pack()

        card = tk.Frame(r, bg=CARD); card.pack(fill="x", padx=24, pady=16, ipady=6)
        tk.Label(card, text="Phone IP", bg=CARD, fg=DIM, font=("Segoe UI", 9)).pack(anchor="w", padx=14, pady=(8, 0))
        s.ip = tk.StringVar(value=s.cfg["ip"])
        tk.Entry(card, textvariable=s.ip, bg=BG, fg=FG, insertbackground=FG, relief="flat",
                 font=("Segoe UI", 11)).pack(fill="x", padx=14, ipady=5)
        s.buf = tk.IntVar(value=s.cfg["buffer"])
        s.bl = tk.Label(card, bg=CARD, fg=DIM, font=("Segoe UI", 9)); s.bl.pack(anchor="w", padx=14, pady=(8, 0))
        ttk.Scale(card, from_=20, to=500, variable=s.buf, command=lambda v: s.upd()).pack(fill="x", padx=14)
        s.upd()

        s.a1 = tk.BooleanVar(value=s.cfg["autostart"]); s.a2 = tk.BooleanVar(value=s.cfg["autostream"])
        ttk.Checkbutton(r, text="Launch with Windows", variable=s.a1, command=s.opts).pack(anchor="w", padx=28)
        ttk.Checkbutton(r, text="Start streaming automatically (keeps reconnecting)", variable=s.a2,
                        command=s.opts).pack(anchor="w", padx=28, pady=(4, 0))
        r.protocol("WM_DELETE_WINDOW", s.close)
        if not s.ip.get(): threading.Thread(target=s.detect, daemon=True).start()
        if "--minimized" in sys.argv: r.iconify()
        if s.cfg["autostream"]: s.toggle()

    def upd(s):
        s.bl.config(text=f"Delay buffer: {s.buf.get()} ms (lower = less lag)")

    def opts(s):
        set_autostart(s.a1.get()); s.persist()

    def persist(s):
        save({"ip": s.ip.get().strip(), "buffer": s.buf.get(), "autostart": s.a1.get(), "autostream": s.a2.get()})

    def ui(s, state, text):
        col = {"idle": DIM, "on": ACC, "wait": "#f5b942", "err": BAD}[state]
        s.cv.itemconfig(s.ring, outline=col if state != "idle" else CARD)
        s.cv.itemconfig(s.icon, text="■" if s.want else "▶", fill=col if state != "idle" else FG)
        s.cv.itemconfig(s.lbl, text="STOP" if s.want else "START", fill=col)
        s.status.set(text)

    def post(s, *a): s.r.after(0, lambda: s.ui(*a))

    def detect(s):
        try:
            for l in run("adb", "devices").splitlines()[1:]:
                m = re.match(r"(\d+\.\d+\.\d+\.\d+):\d+\s+device", l)
                if m: s.r.after(0, lambda ip=m.group(1): s.ip.set(ip)); return
            for l in run("adb", "devices").splitlines()[1:]:
                p = l.split()
                if len(p) == 2 and p[1] == "device" and ":" not in p[0]:
                    if "tablet" in run("adb", "-s", p[0], "shell", "getprop", "ro.build.characteristics"): continue
                    m = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", run("adb", "-s", p[0], "shell", "ip", "-f", "inet", "addr", "show", "wlan0"))
                    if m: s.r.after(0, lambda: s.ip.set(m.group(1))); return
        except Exception: pass

    def toggle(s):
        if s.want:
            s.want = False
            if s.proc: s.proc.terminate()
            return s.ui("idle", "Stopped")
        if not s.ip.get().strip():
            return s.ui("err", "Enter the phone IP, or plug it in by USB once")
        s.want = True; s.persist(); s.ui("wait", "Connecting…")
        threading.Thread(target=s.loop, daemon=True).start()

    def loop(s):
        while s.want:
            tgt = s.ip.get().strip() + ":5555"
            try:
                if tgt not in run("adb", "devices"):
                    for l in run("adb", "devices").splitlines()[1:]:
                        p = l.split()
                        if len(p) == 2 and p[1] == "device" and ":" not in p[0]:
                            run("adb", "-s", p[0], "tcpip", "5555"); time.sleep(2); break
                    run("adb", "connect", tgt, t=8)
                s.proc = subprocess.Popen(["scrcpy", "-s", tgt, "--no-video", "--no-control", "--no-window",
                    "--audio-source=output", f"--audio-buffer={s.buf.get()}"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, creationflags=NOWIN)
                s.post("on", "Streaming phone audio to this PC")
                out = s.proc.communicate()[0].strip().splitlines()
                if s.want: s.post("wait", "Lost connection, retrying… " + (out[-1][:80] if out else ""))
            except Exception as e:
                s.post("wait", f"Retrying… {e}"[:100])
            for _ in range(6):
                if not s.want: return
                time.sleep(0.5)

    def close(s):
        s.want = False
        if s.proc: s.proc.terminate()
        s.persist(); s.r.destroy()


r = tk.Tk(); App(r); r.mainloop()
