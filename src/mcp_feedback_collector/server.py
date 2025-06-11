import io
import base64
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from PIL import Image, ImageTk
import threading
import queue
from pathlib import Path
from datetime import datetime
import os

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.utilities.types import Image as MCPImage

# 创建MCP服务器
mcp = FastMCP(
    "交互式反馈收集器",
    dependencies=["pillow", "tkinter"]
)

# 配置超时时间（秒）
DEFAULT_DIALOG_TIMEOUT = 300  # 5分钟
DIALOG_TIMEOUT = int(os.getenv("MCP_DIALOG_TIMEOUT", DEFAULT_DIALOG_TIMEOUT))

class FeedbackDialog:
    def __init__(self, work_summary: str = "", timeout_seconds: int = DIALOG_TIMEOUT):
        self.result_queue = queue.Queue()
        self.root = None
        self.work_summary = work_summary
        self.timeout_seconds = timeout_seconds
        self.selected_images = []  # 改为支持多张图片
        self.image_preview_frame = None
        self.text_widget = None
        
    def show_dialog(self):
        """在新线程中显示反馈收集对话框"""
        def run_dialog():
            self.root = tk.Tk()
            self.root.title("🎯 工作完成汇报与反馈收集")

            self.root.resizable(True, True)
            self.root.configure(bg="#f5f5f5")
            
            # 设置窗口图标和样式
            try:
                self.root.iconbitmap(default="")
            except:
                pass
            
            # 居中显示窗口，但向上偏移一些避免被状态栏挡住
            self.root.update_idletasks()  # 确保窗口尺寸已计算
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            window_width = 700
            window_height = 900

            # 计算居中位置，但向上偏移50像素
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2 - 50

            # 确保窗口不会超出屏幕顶部
            if y < 0:
                y = 0

            self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
            
            # 创建界面
            self.create_widgets()
            
            # 运行主循环
            self.root.mainloop()
            
        # 在新线程中运行对话框
        dialog_thread = threading.Thread(target=run_dialog)
        dialog_thread.daemon = True
        dialog_thread.start()
        
        # 等待结果
        try:
            result = self.result_queue.get(timeout=self.timeout_seconds)
            return result
        except queue.Empty:
            return None
            
    def create_widgets(self):
        """创建美化的界面组件"""
        # 主框架
        main_frame = tk.Frame(self.root, bg="#f5f5f5")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # 标题
        title_label = tk.Label(
            main_frame,
            text="🎯 工作完成汇报与反馈收集",
            font=("Microsoft YaHei", 16, "bold"),
            bg="#f5f5f5",
            fg="#2c3e50"
        )
        title_label.pack(pady=(0, 20))
        
        # 1. 工作汇报区域
        report_frame = tk.LabelFrame(
            main_frame, 
            text="📋 AI工作完成汇报", 
            font=("Microsoft YaHei", 12, "bold"),
            bg="#ffffff",
            fg="#34495e",
            relief=tk.RAISED,
            bd=2
        )
        report_frame.pack(fill=tk.X, pady=(0, 15))
        
        report_text = tk.Text(
            report_frame, 
            height=5, 
            wrap=tk.WORD, 
            bg="#ecf0f1", 
            fg="#2c3e50",
            font=("Microsoft YaHei", 10),
            relief=tk.FLAT,
            bd=5,
            state=tk.DISABLED
        )
        report_text.pack(fill=tk.X, padx=15, pady=15)
        
        # 显示工作汇报内容
        report_text.config(state=tk.NORMAL)
        report_text.insert(tk.END, self.work_summary or "本次对话中完成的工作内容...")
        report_text.config(state=tk.DISABLED)
        
        # 2. 用户反馈文本区域
        feedback_frame = tk.LabelFrame(
            main_frame, 
            text="💬 您的文字反馈（可选）", 
            font=("Microsoft YaHei", 12, "bold"),
            bg="#ffffff",
            fg="#34495e",
            relief=tk.RAISED,
            bd=2
        )
        feedback_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # 文本输入框
        self.text_widget = scrolledtext.ScrolledText(
            feedback_frame, 
            height=6, 
            wrap=tk.WORD,
            font=("Microsoft YaHei", 10),
            bg="#ffffff",
            fg="#2c3e50",
            relief=tk.FLAT,
            bd=5,
            insertbackground="#3498db"
        )
        self.text_widget.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        self.text_widget.insert(tk.END, "请在此输入您的反馈、建议或问题...")
        self.text_widget.bind("<FocusIn>", self.clear_placeholder)
        
        # 3. 图片选择区域
        image_frame = tk.LabelFrame(
            main_frame, 
            text="🖼️ 图片反馈（可选，支持多张）", 
            font=("Microsoft YaHei", 12, "bold"),
            bg="#ffffff",
            fg="#34495e",
            relief=tk.RAISED,
            bd=2
        )
        image_frame.pack(fill=tk.X, pady=(0, 15))
        
        # 图片操作按钮
        btn_frame = tk.Frame(image_frame, bg="#ffffff")
        btn_frame.pack(fill=tk.X, padx=15, pady=10)
        
        # 美化的按钮样式
        btn_style = {
            "font": ("Microsoft YaHei", 10, "bold"),
            "relief": tk.FLAT,
            "bd": 0,
            "cursor": "hand2",
            "height": 2
        }
        
        tk.Button(
            btn_frame,
            text="📁 选择图片文件",
            command=self.select_image_file,
            bg="#3498db",
            fg="white",
            width=15,
            **btn_style
        ).pack(side=tk.LEFT, padx=(0, 8))
        
        tk.Button(
            btn_frame,
            text="📋 从剪贴板粘贴",
            command=self.paste_from_clipboard,
            bg="#2ecc71",
            fg="white",
            width=15,
            **btn_style
        ).pack(side=tk.LEFT, padx=4)
        
        tk.Button(
            btn_frame,
            text="❌ 清除所有图片",
            command=self.clear_all_images,
            bg="#e74c3c",
            fg="white",
            width=15,
            **btn_style
        ).pack(side=tk.LEFT, padx=8)
        
        # 图片预览区域（支持滚动）
        preview_container = tk.Frame(image_frame, bg="#ffffff")
        preview_container.pack(fill=tk.X, padx=15, pady=(0, 15))
        
        # 创建滚动画布
        canvas = tk.Canvas(preview_container, height=120, bg="#f8f9fa", relief=tk.SUNKEN, bd=1)
        scrollbar = tk.Scrollbar(preview_container, orient="horizontal", command=canvas.xview)
        self.image_preview_frame = tk.Frame(canvas, bg="#f8f9fa")
        
        self.image_preview_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.image_preview_frame, anchor="nw")
        canvas.configure(xscrollcommand=scrollbar.set)
        
        canvas.pack(side="top", fill="x")
        scrollbar.pack(side="bottom", fill="x")
        
        # 初始提示
        self.update_image_preview()
        
        # 4. 操作按钮
        button_frame = tk.Frame(main_frame, bg="#f5f5f5")
        button_frame.pack(fill=tk.X, pady=(15, 0))
        
        # 主要操作按钮
        submit_btn = tk.Button(
            button_frame,
            text="✅ 提交反馈",
            command=self.submit_feedback,
            font=("Microsoft YaHei", 12, "bold"),
            bg="#27ae60",
            fg="white",
            width=18,
            height=2,
            relief=tk.FLAT,
            bd=0,
            cursor="hand2"
        )
        submit_btn.pack(side=tk.LEFT, padx=(0, 15))
        
        cancel_btn = tk.Button(
            button_frame,
            text="❌ 取消",
            command=self.cancel,
            font=("Microsoft YaHei", 12),
            bg="#95a5a6",
            fg="white",
            width=18,
            height=2,
            relief=tk.FLAT,
            bd=0,
            cursor="hand2"
        )
        cancel_btn.pack(side=tk.LEFT)
        
        # 说明文字
        info_label = tk.Label(
            main_frame,
            text="💡 提示：您可以只提供文字反馈、只提供图片，或者两者都提供（支持多张图片）",
            font=("Microsoft YaHei", 9),
            fg="#7f8c8d",
            bg="#f5f5f5"
        )
        info_label.pack(pady=(15, 0))
        
    def clear_placeholder(self, event):
        """清除占位符文本"""
        if self.text_widget.get(1.0, tk.END).strip() == "请在此输入您的反馈、建议或问题...":
            self.text_widget.delete(1.0, tk.END)
            
    def select_image_file(self):
        """选择图片文件（支持多选）"""
        file_types = [
            ("图片文件", "*.png *.jpg *.jpeg *.gif *.bmp *.webp"),
            ("PNG文件", "*.png"),
            ("JPEG文件", "*.jpg *.jpeg"),
            ("所有文件", "*.*")
        ]
        
        file_paths = filedialog.askopenfilenames(
            title="选择图片文件（可多选）",
            filetypes=file_types
        )
        
        for file_path in file_paths:
            try:
                # 读取并验证图片
                with open(file_path, 'rb') as f:
                    image_data = f.read()
                
                img = Image.open(io.BytesIO(image_data))
                self.selected_images.append({
                    'data': image_data,
                    'source': f'文件: {Path(file_path).name}',
                    'size': img.size,
                    'image': img
                })
                
            except Exception as e:
                messagebox.showerror("错误", f"无法读取图片文件 {Path(file_path).name}: {str(e)}")
                
        self.update_image_preview()
                
    def paste_from_clipboard(self):
        """从剪贴板粘贴图片"""
        try:
            from PIL import ImageGrab, Image

            # 方法1: 使用PIL ImageGrab
            clipboard_content = ImageGrab.grabclipboard()
            img = None

            print(f"调试: 剪贴板内容类型: {type(clipboard_content)}")

            if clipboard_content is not None:
                # 如果是列表，检查是否包含文件路径
                if isinstance(clipboard_content, list):
                    print(f"调试: 剪贴板包含列表，长度: {len(clipboard_content)}")
                    if len(clipboard_content) > 0:
                        first_item = clipboard_content[0]
                        print(f"调试: 列表第一个元素类型: {type(first_item)}")
                        print(f"调试: 列表第一个元素内容: {first_item}")

                        # 如果是字符串，可能是文件路径
                        if isinstance(first_item, str):
                            # 检查是否是图片文件路径
                            if any(first_item.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']):
                                try:
                                    img = Image.open(first_item)
                                    print("调试: 成功从文件路径加载图片")
                                except Exception as e:
                                    print(f"调试: 无法从路径加载图片: {e}")
                            else:
                                print("调试: 字符串不是图片文件路径")
                        else:
                            # 可能是图片对象
                            img = first_item
                else:
                    # 直接是图片对象
                    img = clipboard_content
                    print("调试: 剪贴板直接包含图片对象")

            # 检查PIL方法是否成功
            if img and hasattr(img, 'save'):
                print("调试: PIL方法成功获取图片")
                buffer = io.BytesIO()
                img.save(buffer, format='PNG')
                image_data = buffer.getvalue()

                self.selected_images.append({
                    'data': image_data,
                    'source': '剪贴板',
                    'size': img.size,
                    'image': img
                })

                self.update_image_preview()
                return

            # 方法2: 尝试使用win32clipboard直接获取位图数据
            print("调试: PIL方法失败，尝试win32clipboard方法")
            try:
                import win32clipboard
                import win32con

                win32clipboard.OpenClipboard()

                # 检查是否有位图格式
                if win32clipboard.IsClipboardFormatAvailable(win32con.CF_DIB):
                    print("调试: 发现CF_DIB格式")
                    dib_data = win32clipboard.GetClipboardData(win32con.CF_DIB)
                    win32clipboard.CloseClipboard()

                    # 将DIB数据转换为PIL图像
                    try:
                        # DIB数据包含BITMAPINFOHEADER + 像素数据
                        # 我们需要跳过头部信息
                        import struct

                        # 读取BITMAPINFOHEADER
                        header_size = struct.unpack('<I', dib_data[:4])[0]
                        width = struct.unpack('<I', dib_data[4:8])[0]
                        height = struct.unpack('<I', dib_data[8:12])[0]
                        planes = struct.unpack('<H', dib_data[12:14])[0]
                        bit_count = struct.unpack('<H', dib_data[14:16])[0]

                        print(f"调试: DIB信息 - 宽度:{width}, 高度:{height}, 位深:{bit_count}")

                        # 计算像素数据偏移
                        pixel_offset = header_size
                        if bit_count <= 8:
                            # 有调色板
                            colors_used = struct.unpack('<I', dib_data[32:36])[0]
                            if colors_used == 0:
                                colors_used = 1 << bit_count
                            pixel_offset += colors_used * 4

                        # 提取像素数据
                        pixel_data = dib_data[pixel_offset:]

                        # 创建PIL图像
                        if bit_count == 24:
                            # BGR格式，需要转换为RGB
                            img = Image.frombytes('RGB', (width, abs(height)), pixel_data, 'raw', 'BGR', 0, -1 if height > 0 else 1)
                        elif bit_count == 32:
                            # BGRA格式
                            img = Image.frombytes('RGBA', (width, abs(height)), pixel_data, 'raw', 'BGRA', 0, -1 if height > 0 else 1)
                        else:
                            print(f"调试: 不支持的位深度: {bit_count}")
                            img = None

                        if img:
                            print("调试: 成功从DIB数据创建图片")

                    except Exception as dib_error:
                        print(f"调试: DIB数据处理失败: {dib_error}")
                        img = None

                elif win32clipboard.IsClipboardFormatAvailable(win32con.CF_BITMAP):
                    print("调试: 发现CF_BITMAP格式")
                    win32clipboard.CloseClipboard()
                    messagebox.showwarning("提示", "检测到位图格式，但需要更复杂的处理")
                    return

                else:
                    # 显示剪贴板中可用的格式
                    formats = []
                    format_id = 0
                    while True:
                        format_id = win32clipboard.EnumClipboardFormats(format_id)
                        if format_id == 0:
                            break
                        try:
                            format_name = win32clipboard.GetClipboardFormatName(format_id)
                            formats.append(f"{format_id}: {format_name}")
                        except:
                            formats.append(f"{format_id}: (标准格式)")
                    win32clipboard.CloseClipboard()

                    print(f"调试: 剪贴板中的格式: {formats}")
                    messagebox.showwarning("警告", f"剪贴板中没有支持的图片格式\n\n可用格式:\n" + "\n".join(formats[:5]))
                    return

            except ImportError:
                print("调试: win32clipboard不可用")
            except Exception as win32_error:
                print(f"调试: win32clipboard方法出错: {win32_error}")
                try:
                    win32clipboard.CloseClipboard()
                except:
                    pass

            # 如果win32方法成功了
            if img and hasattr(img, 'save'):
                print("调试: win32方法成功获取图片")
                buffer = io.BytesIO()
                img.save(buffer, format='PNG')
                image_data = buffer.getvalue()

                self.selected_images.append({
                    'data': image_data,
                    'source': '剪贴板',
                    'size': img.size,
                    'image': img
                })

                self.update_image_preview()
                messagebox.showinfo("成功", "已从剪贴板添加图片")
                return

            # 所有方法都失败了
            messagebox.showwarning("警告", "剪贴板中没有有效的图片数据\n\n请尝试:\n1. 重新截图或复制图片\n2. 使用'选择图片文件'功能\n3. 确保复制的是图片而不是文件路径")

        except Exception as e:
            print(f"调试: 异常详情: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("错误", f"无法从剪贴板获取图片: {str(e)}")
            
    def clear_all_images(self):
        """清除所有选择的图片"""
        self.selected_images = []
        self.update_image_preview()
        
    def update_image_preview(self):
        """更新图片预览显示"""
        # 清除现有预览
        for widget in self.image_preview_frame.winfo_children():
            widget.destroy()
            
        if not self.selected_images:
            # 显示未选择图片的提示
            no_image_label = tk.Label(
                self.image_preview_frame,
                text="未选择图片",
                bg="#f8f9fa",
                fg="#95a5a6",
                font=("Microsoft YaHei", 10)
            )
            no_image_label.pack(pady=20)
        else:
            # 显示所有图片预览
            for i, img_info in enumerate(self.selected_images):
                try:
                    # 创建单个图片预览容器
                    img_container = tk.Frame(self.image_preview_frame, bg="#ffffff", relief=tk.RAISED, bd=1)
                    img_container.pack(side=tk.LEFT, padx=5, pady=5)
                    
                    # 创建缩略图
                    img_copy = img_info['image'].copy()
                    img_copy.thumbnail((100, 80), Image.Resampling.LANCZOS)
                    
                    # 转换为tkinter可用的格式
                    photo = ImageTk.PhotoImage(img_copy)
                    
                    # 图片标签
                    img_label = tk.Label(img_container, image=photo, bg="#ffffff")
                    img_label.image = photo  # 保持引用
                    img_label.pack(padx=5, pady=5)
                    
                    # 图片信息
                    info_text = f"{img_info['source']}\n{img_info['size'][0]}x{img_info['size'][1]}"
                    info_label = tk.Label(
                        img_container,
                        text=info_text,
                        font=("Microsoft YaHei", 8),
                        bg="#ffffff",
                        fg="#7f8c8d"
                    )
                    info_label.pack(pady=(0, 5))
                    
                    # 删除按钮
                    del_btn = tk.Button(
                        img_container,
                        text="×",
                        command=lambda idx=i: self.remove_image(idx),
                        font=("Arial", 10, "bold"),
                        bg="#e74c3c",
                        fg="white",
                        width=3,
                        relief=tk.FLAT,
                        cursor="hand2"
                    )
                    del_btn.pack(pady=(0, 5))
                    
                except Exception as e:
                    print(f"预览更新失败: {e}")
                    
    def remove_image(self, index):
        """删除指定索引的图片"""
        if 0 <= index < len(self.selected_images):
            self.selected_images.pop(index)
            self.update_image_preview()
            
    def submit_feedback(self):
        """提交反馈"""
        # 获取文本内容
        text_content = self.text_widget.get(1.0, tk.END).strip()
        if text_content == "请在此输入您的反馈、建议或问题...":
            text_content = ""
            
        # 检查是否有内容
        has_text = bool(text_content)
        has_images = bool(self.selected_images)
        
        if not has_text and not has_images:
            messagebox.showwarning("警告", "请至少提供文字反馈或图片反馈")
            return
            
        # 准备结果数据
        result = {
            'success': True,
            'text_feedback': text_content if has_text else None,
            'images': [img['data'] for img in self.selected_images] if has_images else None,
            'image_sources': [img['source'] for img in self.selected_images] if has_images else None,
            'has_text': has_text,
            'has_images': has_images,
            'image_count': len(self.selected_images),
            'timestamp': datetime.now().isoformat()
        }
        
        self.result_queue.put(result)
        self.root.destroy()
        
    def cancel(self):
        """取消操作"""
        self.result_queue.put({
            'success': False,
            'message': '用户取消了反馈提交'
        })
        self.root.destroy()


@mcp.tool()
def collect_feedback(work_summary: str = "", timeout_seconds: int = DIALOG_TIMEOUT) -> list:
    """
    收集用户反馈的交互式工具。AI可以汇报完成的工作，用户可以提供文字和/或图片反馈。
    
    Args:
        work_summary: AI完成的工作内容汇报
        timeout_seconds: 对话框超时时间（秒），默认300秒（5分钟）
        
    Returns:
        包含用户反馈内容的列表，可能包含文本和图片
    """
    dialog = FeedbackDialog(work_summary, timeout_seconds)
    result = dialog.show_dialog()
    
    if result is None:
        raise Exception(f"操作超时（{timeout_seconds}秒），请重试")
        
    if not result['success']:
        raise Exception(result.get('message', '用户取消了反馈提交'))
    
    # 构建返回内容列表
    feedback_items = []
    
    # 添加文字反馈
    if result['has_text']:
        from mcp.types import TextContent
        feedback_items.append(TextContent(
            type="text", 
            text=f"用户文字反馈：{result['text_feedback']}\n提交时间：{result['timestamp']}"
        ))
        
    # 添加图片反馈
    if result['has_images']:
        for image_data, source in zip(result['images'], result['image_sources']):
            feedback_items.append(MCPImage(data=image_data, format='png'))
        
    return feedback_items


@mcp.tool()
def pick_image() -> MCPImage:
    """
    弹出图片选择对话框，让用户选择图片文件或从剪贴板粘贴图片。
    用户可以选择本地图片文件，或者先截图到剪贴板然后粘贴。
    """
    # 使用简化的对话框只选择图片
    dialog = FeedbackDialog()
    dialog.work_summary = "请选择一张图片"
    
    # 创建简化版本的图片选择对话框
    def simple_image_dialog():
        root = tk.Tk()
        root.title("选择图片")
        root.geometry("400x300")
        root.resizable(False, False)
        root.eval('tk::PlaceWindow . center')
        
        selected_image = {'data': None}
        
        def select_file():
            file_path = filedialog.askopenfilename(
                title="选择图片文件",
                filetypes=[("图片文件", "*.png *.jpg *.jpeg *.gif *.bmp *.webp")]
            )
            if file_path:
                try:
                    with open(file_path, 'rb') as f:
                        selected_image['data'] = f.read()
                    root.destroy()
                except Exception as e:
                    messagebox.showerror("错误", f"无法读取图片: {e}")
                    
        def paste_clipboard():
            try:
                from PIL import ImageGrab
                clipboard_content = ImageGrab.grabclipboard()

                # 处理不同类型的剪贴板内容
                img = None
                if clipboard_content is not None:
                    # 如果是列表，取第一个元素
                    if isinstance(clipboard_content, list):
                        if len(clipboard_content) > 0:
                            img = clipboard_content[0]
                        else:
                            messagebox.showwarning("警告", "剪贴板中的图片列表为空")
                            return
                    else:
                        # 直接是图片对象
                        img = clipboard_content

                if img and hasattr(img, 'save'):
                    buffer = io.BytesIO()
                    img.save(buffer, format='PNG')
                    selected_image['data'] = buffer.getvalue()
                    root.destroy()
                else:
                    messagebox.showwarning("警告", "剪贴板中没有有效的图片数据")
            except Exception as e:
                messagebox.showerror("错误", f"剪贴板操作失败: {e}")
                
        def cancel():
            root.destroy()
            
        # 界面
        tk.Label(root, text="请选择图片来源", font=("Arial", 14, "bold")).pack(pady=20)
        
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=20)
        
        tk.Button(btn_frame, text="📁 选择图片文件", font=("Arial", 12), 
                 width=20, height=2, command=select_file).pack(pady=10)
        tk.Button(btn_frame, text="📋 从剪贴板粘贴", font=("Arial", 12), 
                 width=20, height=2, command=paste_clipboard).pack(pady=10)
        tk.Button(btn_frame, text="❌ 取消", font=("Arial", 12), 
                 width=20, height=1, command=cancel).pack(pady=10)
        
        root.mainloop()
        return selected_image['data']
    
    image_data = simple_image_dialog()
    
    if image_data is None:
        raise Exception("未选择图片或操作被取消")
        
    return MCPImage(data=image_data, format='png')


@mcp.tool()
def get_image_info(image_path: str) -> str:
    """
    获取指定路径图片的信息（尺寸、格式等）
    
    Args:
        image_path: 图片文件路径
    """
    try:
        path = Path(image_path)
        if not path.exists():
            return f"文件不存在: {image_path}"
            
        with Image.open(path) as img:
            info = {
                "文件名": path.name,
                "格式": img.format,
                "尺寸": f"{img.width} x {img.height}",
                "模式": img.mode,
                "文件大小": f"{path.stat().st_size / 1024:.1f} KB"
            }
            
        return "\n".join([f"{k}: {v}" for k, v in info.items()])
        
    except Exception as e:
        return f"获取图片信息失败: {str(e)}"


def main():
    """Main entry point for the mcp-feedback-collector command."""
    try:
        mcp.run()
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序运行出错: {e}")


if __name__ == "__main__":
    main()
