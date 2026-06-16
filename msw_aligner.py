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
        self.root.title("MSW 动作皮肤纯视觉自动对齐工具 v1.0")
        self.root.geometry("550x300")
        self.root.resizable(False, False)

        self.psd_path = tk.StringVar()
        self.png_path = tk.StringVar()

        # UI 布局
        label_title = tk.Label(root, text="MapleStory Worlds 视觉对齐打包器", font=("Arial", 14, "bold"))
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
        tk.Label(frame2, text="动作全景 PNG:", width=12, anchor="w").pack(side="left")
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
            messagebox.showerror("错误", "请先选择 PSD 模板和动作 PNG 图片！")
            return

        try:
            # 1. 读取动作大图并识别所有独立的动作物体
            img = cv2.imread(png_p, cv2.IMREAD_UNCHANGED)
            if img is None:
                raise Exception("无法加载输入的动作图片。")

            # 如果没有 Alpha 通道，转为灰度并二值化以识别黑/白背景
            if img.shape[2] == 4:
                alpha = img[:, :, 3]
                _, thresh = cv2.threshold(alpha, 10, 255, cv2.THRESH_BINARY)
            else:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV) if gray[0,0] > 128 else cv2.threshold(gray, 15, 255, cv2.THRESH_BINARY)

            # 纯视觉检测动作外接矩形
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # 过滤掉太小的杂质噪点像素
            valid_sprites = []
            for c in contours:
                x, y, w, h = cv2.boundingRect(c)
                if w > 15 and h > 15:
                    valid_sprites.append((x, y, w, h))
            
            # 按从上到下、从左到右对识别到的动作进行视觉排序
            valid_sprites = sorted(valid_sprites, key=lambda b: (b[1] // 100, b[0]))

            if not valid_sprites:
                raise Exception("纯视觉检测失败，未在大图中找到独立的动作帧。")

            # 2. 加载官方 PSD 模板
            psd = PSDImage.open(psd_p)
            output_psd_path = os.path.join(os.path.dirname(png_p), "MSW_Aligned_Output.psd")

            # 3. 视觉重心粗对齐核心算法
            # 以大图检测到的第一个独立动作（通常是 Stand 状态）作为标准重心锚点
            x0, y0, w0, h0 = valid_sprites[0]
            base_center_x = x0 + w0 // 2
            base_center_y = y0 + h0 // 2

            sprite_idx = 0
            # 遍历 PSD 模板中所有标有动作性质的图层或图层组
            for layer in psd.descendants():
                if layer.is_group() and ("stand" in layer.name.lower() or "walk" in layer.name.lower() or "jump" in layer.name.lower() or "edit" in layer.name.lower()):
                    if sprite_idx < len(valid_sprites):
                        sx, sy, sw, sh = valid_sprites[sprite_idx]
                        
                        # 计算当前动作相对于标准基准动作的视觉偏移
                        curr_center_x = sx + sw // 2
                        curr_center_y = sy + sh // 2
                        offset_x = curr_center_x - base_center_x
                        offset_y = curr_center_y - base_center_y

                        # 粗对齐逻辑：根据偏移量自动调整 PSD 对应图层组的位置
                        layer.left = int(layer.left + offset_x)
                        layer.top = int(layer.top + offset_y)
                        
                        sprite_idx += 1

            # 4. 导出新 PSD
            psd.save(output_psd_path)
            messagebox.showinfo("成功", f"对齐完成！\n已自动生成新模版文件：\n{output_psd_path}")

        except Exception as e:
            messagebox.showerror("处理失败", f"出现未知错误:\n{str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = MSWAlignerApp(root)
    root.mainloop()
