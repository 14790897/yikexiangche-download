from PIL import Image, ImageDraw


def create_icon():
    """创建应用图标"""
    # 创建不同尺寸的图标
    sizes = [16, 32, 48, 64, 128, 256]
    images = []
    
    for size in sizes:
        # 创建图像
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # 绘制渐变背景圆形
        for i in range(size):
            alpha = int(255 * (1 - i / size))
            color = (66, 133, 244, alpha)  # Google蓝色
            draw.ellipse([i//4, i//4, size-i//4, size-i//4], fill=color)
        
        # 绘制主圆形
        padding = size // 8
        draw.ellipse([padding, padding, size-padding, size-padding], 
                     fill=(66, 133, 244, 255), outline=(255, 255, 255, 200), width=max(1, size//32))
        
        # 绘制云朵图案（简化的相册图标）
        if size >= 32:
            center_x, center_y = size // 2, size // 2
            
            # 绘制相片框
            photo_size = size // 2
            photo_left = center_x - photo_size // 2
            photo_top = center_y - photo_size // 2
            
            # 白色相框
            draw.rectangle([photo_left, photo_top, photo_left + photo_size, photo_top + photo_size],
                          fill=(255, 255, 255, 255), outline=(200, 200, 200, 255), width=max(1, size//64))
            
            # 绘制山和太阳（相册图标）
            if size >= 48:
                # 太阳
                sun_radius = photo_size // 6
                sun_x = photo_left + photo_size * 3 // 4
                sun_y = photo_top + photo_size // 4
                draw.ellipse([sun_x - sun_radius, sun_y - sun_radius, 
                             sun_x + sun_radius, sun_y + sun_radius],
                            fill=(255, 200, 0, 255))
                
                # 山
                mountain_points = [
                    (photo_left + photo_size // 4, photo_top + photo_size * 3 // 4),
                    (photo_left + photo_size // 2, photo_top + photo_size // 3),
                    (photo_left + photo_size * 3 // 4, photo_top + photo_size * 3 // 4),
                ]
                draw.polygon(mountain_points, fill=(100, 150, 100, 255))
        
        images.append(img)
    
    # 保存为ICO文件
    images[0].save('icon.ico', format='ICO', sizes=[(s, s) for s in sizes], append_images=images[1:])
    
    # 同时保存为PNG（用于预览）
    images[-1].save('icon.png', format='PNG')
    
    print("图标创建完成！")
    print("- icon.ico (多尺寸图标)")
    print("- icon.png (256x256预览)")

if __name__ == '__main__':
    try:
        create_icon()
    except ImportError:
        print("需要安装 Pillow 库: pip install Pillow")
    except Exception as e:
        print(f"创建图标时出错: {e}")
