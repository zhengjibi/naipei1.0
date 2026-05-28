# -*- coding: utf-8 -*-
"""
Naipei 桌面宠物
点击: 弹跳+狗叫 | 拖拽: 移动(>8px触发)+松手掉落
滚轮: 缩放 | 双击: 开心 | 右键: 语音对话
快速连点≥8次/3秒: 红温 | 拖到顶部: 退出
"""
import tkinter as tk
import random, math, os, time, threading, ctypes
from collections import deque
from PIL import Image, ImageTk, ImageEnhance

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PET_IMG = os.path.join(SCRIPT_DIR, "assets", "pet.png")
TRANS_COLOR = "#FF00FF"
GRAVITY = 0.6
FPS = 30
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

# ============================================================
# 狗叫 (pygame 播放 MP3/WAV)
# ============================================================
import pygame
pygame.mixer.init()

# 优先用用户提供的 MP3，其次用 WAV
_mp3 = os.path.join(SCRIPT_DIR, "assets", "dog.mp3")
_wav = os.path.join(SCRIPT_DIR, "bark.wav")
if os.path.exists(_mp3) and os.path.getsize(_mp3) > 1000:
    _bark_sound = pygame.mixer.Sound(_mp3)
elif os.path.exists(_wav) and os.path.getsize(_wav) > 1000:
    _bark_sound = pygame.mixer.Sound(_wav)
else:
    _bark_sound = None

def play_bark():
    try:
        if _bark_sound:
            _bark_sound.play()
    except Exception:
        pass

# ============================================================
# TTS (每次新建 engine 避免阻塞)
# ============================================================
import pyttsx3

def speak(text, angry=False):
    def _do():
        try:
            engine = pyttsx3.init()
            engine.setProperty('rate', 130 if angry else 180)
            engine.setProperty('volume', 1.0)
            engine.say(text)
            engine.runAndWait()
            engine.stop()
            del engine
        except Exception:
            pass
    t = threading.Thread(target=_do, daemon=True)
    t.start()

# ============================================================
# 语音识别 (每次新建 recognizer 避免状态残留)
# ============================================================
os.environ["http_proxy"] = "http://127.0.0.1:7897"
os.environ["https_proxy"] = "http://127.0.0.1:7897"

import speech_recognition as sr

def deepseek_chat(user_text):
    if not DEEPSEEK_API_KEY: return "API Key 未设置，汪！"
    try:
        import requests
        resp = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "你是桌面宠物狗奈陪(Naipei)，活泼可爱。回答不超过50字，语气萌，加'汪！'结尾。不用markdown。"},
                    {"role": "user", "content": user_text}
                ], "max_tokens": 120, "temperature": 0.9
            }, timeout=15
        )
        if resp.status_code == 200: return resp.json()["choices"][0]["message"]["content"]
        return "唔... 出错了汪"
    except Exception: return "网络好像不太好，汪！"

def voice_chat(pet):
    def _do():
        pet.show_bubble("正在听...")
        try:
            rec = sr.Recognizer()
            rec.energy_threshold = 300
            rec.dynamic_energy_threshold = True
            with sr.Microphone() as source:
                rec.adjust_for_ambient_noise(source, duration=0.3)
                pet.show_bubble("说话中...")
                audio = rec.listen(source, timeout=3, phrase_time_limit=4)
        except sr.WaitTimeoutError:
            pet.hide_bubble(); speak("没听到声音，汪！"); return
        except Exception:
            pet.hide_bubble(); speak("麦克风出问题了，汪！"); return

        pet.show_bubble("识别中...")
        try:
            text = rec.recognize_google(audio, language="zh-CN")
        except sr.UnknownValueError:
            pet.hide_bubble(); speak("没听清楚，汪！"); return
        except sr.RequestError:
            pet.hide_bubble(); speak("识别服务连不上，汪！"); return

        text = text.strip()
        if not text: pet.hide_bubble(); return
        pet.show_bubble(f"{text[:25]}...")
        reply = deepseek_chat(text)
        pet.show_bubble(reply[:40])
        pet.root.after(2500, pet.hide_bubble)
        speak(reply)
    t = threading.Thread(target=_do, daemon=True)
    t.start()

# ============================================================
class NaipeiPet:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.screen_w = self.root.winfo_screenwidth()
        self.screen_h = self.root.winfo_screenheight()

        self.base_image = Image.open(PET_IMG).convert("RGBA")
        self.scale = 1.0
        self.w = int(self.base_image.width * self.scale)
        self.h = int(self.base_image.height * self.scale)

        self.x = self.screen_w - self.w - 40
        self.y = self.screen_h - self.h - 100
        self.base_y = self.y
        self.target_x, self.target_y = self.x, self.y

        self.vel_y = 0.0
        self.grounded = True
        self.bounce_count = 0
        self.state = "idle"
        self.state_timer = 0
        self.anim_tick = 0
        self.frame_idx = 0
        self.walk_dir = "right"

        # 拖动
        self._click_x = self._click_y = 0
        self._moved = False  # 是否产生过位移
        self.dragging = False
        self.drag_off_x = self.drag_off_y = 0

        # 红温
        self.click_history = deque()
        self.rage_until = 0
        self._rage_cooldown = 0

        # 窗口
        self.root.geometry(f"{self.w}x{self.h}+{self.x}+{self.y}")
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.configure(bg=TRANS_COLOR)
        self.root.wm_attributes('-transparentcolor', TRANS_COLOR)
        hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
        style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
        ctypes.windll.user32.SetWindowLongW(hwnd, -20, style | 0x00000080)

        self.frames = {}
        self._rebuild_all_frames()

        self.canvas = tk.Canvas(self.root, width=self.w, height=self.h,
                                bg=TRANS_COLOR, highlightthickness=0)
        self.canvas.pack()
        self.sprite = self.canvas.create_image(self.w//2, self.h//2,
                                               image=self.frames["idle"][0], anchor=tk.CENTER)
        self.bubble_id = self.bubble_text_id = None

        self.canvas.bind("<Button-1>", self.on_down)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_up)
        self.canvas.bind("<Double-Button-1>", self.on_double)
        self.canvas.bind("<Button-3>", self.on_right)
        self.canvas.bind("<MouseWheel>", self.on_scroll)

        self.canvas.bind("<Button-2>", self.on_middle)     # 滚轮键: 狗叫

        self.root.deiconify()
        self.update_loop()
        self.behavior_loop()
        self.root.mainloop()

    # ============================================================
    def _make_tkframe(self, img):
        f = Image.new("RGBA", (self.w, self.h), (255,0,255,255))
        f.paste(img, (0,0), img if img.mode=="RGBA" else None)
        return ImageTk.PhotoImage(f)

    def _redden(self, img):
        r,g,b,a = img.split()
        return Image.merge("RGBA", (
            ImageEnhance.Brightness(r).enhance(1.8),
            ImageEnhance.Brightness(g).enhance(0.25),
            ImageEnhance.Brightness(b).enhance(0.25), a))

    def _rebuild_all_frames(self):
        base = self.base_image
        w, h = self.w, self.h
        s = base if self.scale==1.0 else base.resize((w,h), Image.LANCZOS)
        rs = self._redden(s)
        for pf, src in [("", s), ("rage_", rs)]:
            dr=lambda img,a: img.rotate(a, Image.BICUBIC, expand=False, fillcolor=(0,0,0,0))
            self.frames[pf+"idle"]=[self._make_tkframe(dr(src,a)) for a in [0,2,0,-2]]
            dxs=[0,max(1,int(2*self.scale)),max(2,int(4*self.scale)),max(1,int(2*self.scale))]
            self.frames[pf+"walk_right"]=[]; self.frames[pf+"walk_left"]=[]
            for dx in dxs:
                a=Image.new("RGBA",(w+4,h),(0,0,0,0)); a.paste(src,(dx,0))
                self.frames[pf+"walk_right"].append(self._make_tkframe(a.crop((0,0,w,h))))
                b=Image.new("RGBA",(w+4,h),(0,0,0,0)); b.paste(src,(-dx,0))
                self.frames[pf+"walk_left"].append(self._make_tkframe(b.crop((0,0,w,h))))
            self.frames[pf+"jump"]=[]; self.frames[pf+"happy"]=[]
            for r in [0.85,0.92,1.12,1.0]:
                nw,nh=int(w*r),int(h*r); bg=Image.new("RGBA",(w,h),(0,0,0,0))
                bg.paste(src.resize((nw,nh),Image.LANCZOS),((w-nw)//2,(h-nh)//2))
                self.frames[pf+"jump"].append(self._make_tkframe(bg))
            for r in [1.1,1.0,1.08,1.0]:
                nw,nh=int(w*r),int(h*r); bg=Image.new("RGBA",(w,h),(0,0,0,0))
                bg.paste(src.resize((nw,nh),Image.LANCZOS),((w-nw)//2,(h-nh)//2))
                self.frames[pf+"happy"].append(self._make_tkframe(bg))
            self.frames[pf+"clicked"]=[self._make_tkframe(ImageEnhance.Brightness(src).enhance(1.15))]

    def _raging(self): return time.time() < self.rage_until
    def _get_frames(self, name):
        return self.frames["rage_"+name] if self._raging() else self.frames[name]

    def _register_click(self):
        now=time.time()
        self.click_history.append(now)
        while self.click_history and self.click_history[0] < now-3.0:
            self.click_history.popleft()
        if now<self._rage_cooldown: return
        if len(self.click_history)>=8 and not self._raging():
            self.rage_until=now+3.5; self._rage_cooldown=now+6.0
            speak("别再搞我了！", angry=True)
            self.show_bubble("别搞了!!")
            self.root.after(2000, self.hide_bubble)

    # ============================================================
    def on_scroll(self, event):
        d=0.1 if event.delta>0 else -0.1; ns=max(0.4,min(2.5,self.scale+d))
        if abs(ns-self.scale)<0.01: return
        cx,cy=self.x+self.w//2,self.y+self.h//2
        self.scale=ns; self.w=int(self.base_image.width*self.scale); self.h=int(self.base_image.height*self.scale)
        self.x,self.y=cx-self.w//2,cy-self.h//2
        self.base_y=self.y; self.target_x,self.target_y=self.x,self.y
        self._rebuild_all_frames()
        self.canvas.config(width=self.w,height=self.h)
        self.canvas.coords(self.sprite,self.w//2,self.h//2)
        self.root.geometry(f"{self.w}x{self.h}+{self.x}+{self.y}")

    def show_bubble(self, text):
        self.hide_bubble()
        bw,bh=min(len(text)*14+20,280),36; bx,by=self.w//2,-10
        self.bubble_id=self.canvas.create_rectangle(bx-bw//2,by-bh,bx+bw//2,by,fill="white",outline="#555",width=2)
        self.bubble_text_id=self.canvas.create_text(bx,by-bh//2,text=text[:35],fill="#333",font=("Microsoft YaHei",9),anchor=tk.CENTER)

    def hide_bubble(self):
        if self.bubble_id: self.canvas.delete(self.bubble_id); self.canvas.delete(self.bubble_text_id)
        self.bubble_id=self.bubble_text_id=None

    # ============================================================
    def on_down(self, event):
        self._register_click()
        self._click_x, self._click_y = event.x_root, event.y_root
        self._moved = False
        self.dragging = False
        if self.state in ("idle","walking"):
            self.state="clicked"; self.state_timer=0; self.frame_idx=0

    def on_drag(self, event):
        dx, dy = event.x_root-self._click_x, event.y_root-self._click_y
        if abs(dx)>=8 or abs(dy)>=8:
            self._moved = True
            if not self.dragging:
                self.dragging=True
                self.drag_off_x=event.x_root-self.x; self.drag_off_y=event.y_root-self.y
            self.x=event.x_root-self.drag_off_x; self.y=event.y_root-self.drag_off_y
            self.base_y=self.y; self.target_x,self.target_y=self.x,self.y
            self.root.geometry(f"+{self.x}+{self.y}")
            self.show_bubble("松开退出") if self.y<25 else self.hide_bubble()

    def on_up(self, event):
        if self._moved or self.dragging:
            self.dragging=False; self.hide_bubble()
            if self.y<35: self.root.destroy(); return
            # 释放掉落: 落到屏幕底部附近
            self.grounded=False
            self.base_y = self.screen_h - self.h - 60  # 地面 = 屏幕底部
            self.vel_y = 3  # 给一个向下的初速度
            self.bounce_count = 0
        else:
            # 纯点击: 小弹跳
            self.grounded=False; self.vel_y=-8
            self.bounce_count=0
        self.state="jump"; self.state_timer=0; self.frame_idx=0

    def on_double(self, event):
        self.state="happy"; self.state_timer=0; self.frame_idx=0
        self.grounded=False; self.vel_y=-8

    def on_middle(self, event):
        """滚轮键: 狗叫"""
        play_bark()

    def on_right(self, event):
        voice_chat(self)

    # ============================================================
    def update_loop(self):
        self.anim_tick+=1; self.state_timer+=1
        if not self.grounded and not self.dragging:
            self.vel_y+=GRAVITY; self.y+=int(self.vel_y)
            if self.y>=self.base_y:
                self.y=self.base_y; self.bounce_count+=1
                if self.bounce_count<=2 and abs(self.vel_y)>2: self.vel_y*=-0.45
                else: self.vel_y=0; self.bounce_count=0; self.grounded=True
                if self.state in ("jump","clicked","happy"): self.state="idle"
        if self.state=="walking" and not self.dragging:
            dx,dy=self.target_x-self.x,self.target_y-self.y
            dist=math.hypot(dx,dy)
            if dist>3:
                sp=max(1.5,2.5*self.scale)
                self.x+=int(dx/dist*sp); self.y+=int(dy/dist*sp)
                self.walk_dir="right" if dx>=0 else "left"; self.base_y=self.y
            else: self.state="idle"
        self.x=max(-20,min(self.screen_w-self.w+20,self.x))
        self.y=max(0,min(self.screen_h-self.h+10,self.y))
        if self.grounded: self.base_y=self.y
        spd={"idle":16,"walking":6,"jump":6,"clicked":5,"happy":5}
        self.frame_idx=self.anim_tick//spd.get(self.state,10)
        to={"clicked":12,"happy":24,"jump":30}
        if self.state in to and self.state_timer>to[self.state] and self.grounded: self.state="idle"
        fn={"idle":"idle","walking":f"walk_{self.walk_dir}","jump":"jump","clicked":"clicked","happy":"happy"}.get(self.state,"idle")
        frames=self._get_frames(fn)
        self.canvas.itemconfig(self.sprite,image=frames[self.frame_idx%len(frames)])
        self.root.geometry(f"{self.w}x{self.h}+{self.x}+{self.y}")
        self.root.after(1000//FPS,self.update_loop)

    def behavior_loop(self):
        if self.state=="idle" and not self.dragging and not self._raging():
            r=random.random()
            if r<0.04:
                self.state="jump"; self.state_timer=0; self.frame_idx=0
                self.bounce_count=0; self.grounded=False; self.vel_y=-10
            elif r<0.09:
                m=60; self.target_x=random.randint(m,self.screen_w-self.w-m); self.target_y=self.y
                if random.random()<0.3: self.target_y=random.randint(m,self.screen_h-self.h-m)
                self.walk_dir="right" if self.target_x>=self.x else "left"
                self.state="walking"; self.state_timer=0
        self.root.after(random.randint(2000,5000),self.behavior_loop)

if __name__=="__main__":
    os.chdir(SCRIPT_DIR)
    NaipeiPet()
