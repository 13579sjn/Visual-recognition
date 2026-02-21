
from maix import camera, display, image, app, uart, pinmap, time
import struct

# ====================== 初始化配置 ======================
# 串口配置
device = "/dev/ttyS0"
serial0 = uart.UART(device, 115200)
# 清空串口缓存（避免脏数据）
serial0.read(timeout=100)

# 摄像头/显示屏初始化
cam = camera.Camera(320, 240)  # 320x240分辨率，识别速度快
disp = display.Display()

# 颜色阈值配置（HSV范围）：[H_min, H_max, S_min, S_max, V_min, V_max]
# 红/绿：发送字节形式的数字1/2；蓝：保持原字符串输出
color_configs = {
    "red": {"threshold": [0, 80, 40, 80, 10, 80], "code": b'\x01', "line_color": image.COLOR_RED},  # 字节1（对应十进制1）
    "green": {"threshold": [0, 80, -120, -10, 0, 30], "code": b'\x02', "line_color": image.COLOR_GREEN}, # 字节2（对应十进制2）
    "blue": {"threshold": [0, 80, 30, 100, -120, -60], "code": b'3', "line_color": image.COLOR_BLUE}     # 蓝色保持原逻辑（可自定义）
}

# 识别阈值（过滤小噪点）
AREA_THRESHOLD = 1000  # 色块最小面积
PIXEL_THRESHOLD = 1000 # 色块最小像素数

# 防抖配置：避免短时间重复发送
LAST_SEND_COLOR = None  # 上一次发送的颜色
SEND_INTERVAL = 500     # 发送间隔（毫秒）
LAST_SEND_TIME = 0      # 上一次发送时间

# ====================== 主循环 ======================
while True:
    # 1. 读取摄像头图像
    img = cam.read()
    current_time = time.ticks_ms()  # 获取当前时间（毫秒）
    current_color = None            # 本次识别到的颜色

    # 2. 遍历识别红、绿、蓝三种颜色
    for color_name, config in color_configs.items():
        # 查找对应颜色的色块
        blobs = img.find_blobs(
            [config["threshold"]],
            area_threshold=AREA_THRESHOLD,
            pixels_threshold=PIXEL_THRESHOLD
        )

        # 3. 如果识别到该颜色的色块
        if blobs:
            current_color = color_name
            # 绘制色块矩形框
            for b in blobs:
                corners = b.corners()
                for i in range(4):
                    img.draw_line(
                        corners[i][0], corners[i][1],
                        corners[(i + 1) % 4][0], corners[(i + 1) % 4][1],
                        config["line_color"], 2  # 线条颜色+宽度
                    )
            break  # 识别到一种颜色即可，优先顺序：红>绿>蓝

    # 4. 串口发送逻辑（防抖处理）
    if current_color and (current_time - LAST_SEND_TIME) > SEND_INTERVAL:
        send_data = color_configs[current_color]["code"]
        # 发送对应数据（红：字节1，绿：字节2，蓝：字节3）
        serial0.write(send_data)
        # 打印日志（调试用）
        print(f"识别到{current_color}，发送串口数据（十进制）：{ord(send_data) if isinstance(send_data, bytes) else send_data}")
        # 更新防抖参数
        LAST_SEND_COLOR = current_color
        LAST_SEND_TIME = current_time

    # 5. 显示识别结果
    disp.show(img)

