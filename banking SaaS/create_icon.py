from PIL import Image, ImageDraw

def create_bank_icon():
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    images = []
    
    for size in sizes:
        w, h = size
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Rounded background rectangle in deep navy blue
        corner_radius = int(w * 0.2)
        bg_color = (15, 30, 60, 255)
        accent_color = (212, 175, 55, 255) # Gold
        white_color = (240, 244, 250, 255)
        
        draw.rounded_rectangle([0, 0, w - 1, h - 1], radius=corner_radius, fill=bg_color)
        
        # Bank Pediment (Roof triangle)
        roof_top = (w // 2, int(h * 0.22))
        roof_left = (int(w * 0.2), int(h * 0.38))
        roof_right = (int(w * 0.8), int(h * 0.38))
        draw.polygon([roof_top, roof_left, roof_right], fill=accent_color)
        
        # Architrave / beam under roof
        draw.rectangle([int(w * 0.2), int(h * 0.39), int(w * 0.8), int(h * 0.44)], fill=white_color)
        
        # 3 Pillars
        p_w = max(1, int(w * 0.1))
        p_y1 = int(h * 0.46)
        p_y2 = int(h * 0.72)
        
        # Pillar 1
        draw.rectangle([int(w * 0.24), p_y1, int(w * 0.24) + p_w, p_y2], fill=accent_color)
        # Pillar 2 (Center)
        draw.rectangle([int(w * 0.5) - p_w // 2, p_y1, int(w * 0.5) + p_w - p_w // 2, p_y2], fill=accent_color)
        # Pillar 3
        draw.rectangle([int(w * 0.76) - p_w, p_y1, int(w * 0.76), p_y2], fill=accent_color)
        
        # Base steps
        draw.rectangle([int(w * 0.18), int(h * 0.74), int(w * 0.82), int(h * 0.79)], fill=white_color)
        draw.rectangle([int(w * 0.14), int(h * 0.80), int(w * 0.86), int(h * 0.85)], fill=accent_color)
        
        images.append(img)
        
    images[0].save("app_icon.ico", format="ICO", sizes=[(im.width, im.height) for im in images])
    print("Icon generated successfully: app_icon.ico")

if __name__ == "__main__":
    create_bank_icon()
