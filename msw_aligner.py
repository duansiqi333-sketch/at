import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
import cv2
import numpy as np
from PIL import Image
from psd_tools import PSDImage

class MSWAlignerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MSW 动作皮肤纯视觉自动对齐工具 v1.1")
        self.root.geometry("550x300")
        self.root.resizable(False, False)

        self.psd_path = tk.StringVar()
        self.png_path = tk.StringVar()

        # UI 布局
        label_title = tk.Label(root, text="MapleStory Worlds 视觉对齐打包器 (修复版)", font=("Arial", 14, "bold"))
        label_title.pack(pady=15)

        # PSD 选择
        frame1 = tk.Frame(root)
        frame1.pack(fill="x", padx=20, pady=5)
        tk.Label(frame1, text="官方 PSD 模板:", width=12, anchor="w").pack(side="left")
        tk.Entry(frame1, textvariable=self.psd_path, width=40).pack(side="left", padx=5)
        tk.Button(frame1, text="浏览...", command=self.select_psd).pack(side="left")

        # PNG 选择
        frame2 = tk.Frame(root)
        frame2.pack(fill="x", padx=20, pady=5)
        tk.Label(frame2, text="动作全景 PNG/JPG:", width=12, anchor="w").pack(side="left")
        tk.Entry(frame2, textvariable=self.png_path, width=40).pack(side="left", padx=5)
        tk.Button(frame2, text="浏览...", command=self.select_png).pack(side="left")

        # 执行按钮
        tk.Button(root, text="🚀 开始自动切片并对齐 PSD", font=("Arial", 11, "bold"), 
                  bg="#4CAF50", fg="white", height=2, command=self.process_alignment).pack(pady=25)

    def select_psd(self):
        path = filedialog.askopenfilename(filetypes=[("Photoshop files", "*.psd")])
        if path: self.psd_path.set(path)

    def select_png(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.png;*.jpg;*.jpeg")])
        if path: self.png_path.set(path)

    def process_alignment(self):
        psd_p = self.psd_path.get()
        png_p = self.png_path.get()

        if not psd_p or not png_p:
            messagebox.showerror("错误", "请先选择 PSD 模板和动作大图！")
            return

        try:
            # 【核心修复】使用 numpy + imdecode 支持 Windows 下的中文字符串路径读取
            img_array = np.fromfile(png_p, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_UNCHANGED)
            
            if img is None:
                raise Exception("OpenCV 无法解码该图片，请检查文件是否损坏或格式不兼容。")

            # 自动判断通道并进行二值化处理
            if len(img.shape) == 3 and img.shape[2] == 4:
                # 带透明通道的 PNG 皮肤图
                alpha = img[:, :, 3]
                _, thresh = cv2.threshold(alpha, 10, 255, cv2.THRESH_BINARY)
            else:
                # 不带透明通道的 JPG 或普通图片
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                # 智能判断背景是纯白还是纯黑
                if gray[0, 0] > 128:
                    _, thresh = cv2.threshold(gray, 235, 255, cv2.THRESH_BINARY_INV) # 白背景
                else:
                    _, thresh = cv2.threshold(gray, 20, 255, cv2.THRESH_BINARY) # 黑背景

            # 纯视觉检测动作外接矩形
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # 过滤面积过小的噪点像素
            valid_sprites = []
            for c in contours:
                x, y, w, h = cv2.boundingRect(c)
                if w > 15 and h > 15:
                    valid_sprites.append((x, y, w, h))
            
            # 视觉重新排序（从上到下，从左到右）
            valid_sprites = sorted(valid_sprites, key=lambda b: (b[1] // 100, b[0]))

            if not valid_sprites:
                raise Exception("纯视觉检测失败，未能在大图中识别出任何独立的动作角色。")

            # 加载官方 PSD 模板
            psd = PSDImage.open(psd_p)
            output_psd_path = os.path.join(os.path.dirname(png_p), "MSW_Aligned_Output.psd")

            # 视觉重心粗对齐
            x0, y0, w0, h0 = valid_sprites[0]
            base_center_x = x0 + w0 // 2
            base_center_y = y0 + h0 // 2

            sprite_idx = 0
            for layer in psd.descendants():
                if layer.is_group() and any(k in layer.name.lower() for k in ["stand", "walk", "jump", "edit"]):
                    if sprite_idx < len(valid_sprites):
                        sx, sy, sw, sh = valid_sprites[sprite_idx]
                        
                        curr_center_x = sx + sw // 2
                        curr_center_y = sy + sh // 2
                        offset_x = curr_center_x - base_center_x
                        offset_y = curr_center_y - base_center_y

                        layer.left = int(layer.left + offset_x)
                        layer.top = int(layer.top + offset_y)
                        
                        sprite_idx += 1

            # 保存新 PSD
            psd.save(output_psd_path)
            messagebox.showinfo("成功", f"对齐完成！\n已自动生成新模版文件：\n{output_psd_path}")

        except Exception as e:
            messagebox.showerror("处理失败", f"出现未知错误:\n{str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = MSWAlignerApp(root)
    root.mainloop()
