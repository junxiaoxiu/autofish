import time
import math
import pyautogui as pg
import numpy as np
import cv2

import locate

gray_threshold  = 185    # 判断钓鱼条是否出现的灰度阈值，0-255
judge_interval  = 0.2    # 判断钓鱼条是否出现的时间间隔，单位second
mouse_down_time = 1.65   # 蓄力甩杆鼠标按下的时间，单位second
sample_pt_num   = 35     # 采样点的数量
fishover_mean   = 85     # 判断钓鱼是否结束的平均灰度值

fish_pic       = None    # 全局变量，鱼的图片
fish_position  = 0       # 全局变量，当前鱼在钓鱼条中的位置，具体为采样点的索引，范围 [0, sample_pt_num)
fish_mark_pos  = None    # 全局变量，当前钓鱼条的标记坐标点，格式为 [[x, y] for i in range(0, sample_pt_num)]
prog_mark_pos  = None    # 全局变量，当前钓鱼进度的标记坐标点，格式为 [[x, y] for i in range(0, sample_pt_num)]
fishbar_begend = [0, 0]  # 全局变量，钓鱼条的起始和终止位置，格式为 [begin, end]
screen_shot    = None    # 全局变量，对当前钓鱼条画面的截图

# 校准用参数
bool_mark_debug = False
fish_mark_x_offset = 0
fish_mark_y_offset = 0
prog_mark_x_offset = 0
prog_mark_y_offset = 0


def fish(icon_pos) :
    # 获取钓鱼进度条矩形在屏幕上外界矩形左上和右下的坐标
    bar_region = locate.cal_progress_bar_pos(icon_pos[0], icon_pos[1])
    # 计算钓鱼条和进度条的标记点坐标
    cal_mark_pos(bar_region)
    # 读取fish图像并增广
    load_fishpic_and_augmentation()

    # 先截图查看钓鱼进度条是否出现
    # 出现后进行钓鱼
    while True :
        # 蓄力甩杆
        charge_and_cast(icon_pos, bar_region)
        # 检测钓鱼条是否出现
        progress_bar_is_show(bar_region)
        # 进行钓鱼
        while True :
            # 对钓鱼条区域截图
            get_screenshot_inregion(bar_region)
            # 检测鱼的位置
            detect_fish_pos()
            # 检测当前钓鱼条的位置
            cal_fishbar_len()
            # 调整钓鱼条的位置
            mousedown_or_up()
            # 检测是否完成钓鱼
            if fish_is_over():
                break

        time.sleep(0.5)
        pg.click(button="left")


# 蓄力并抛竿
def charge_and_cast(icon_pos, bar_region) :
    global screen_shot
    time.sleep(0.5)
    print("charge")
    pg.moveTo(icon_pos[0][0], icon_pos[0][1])
    pg.mouseDown(button="left")

    # 阻塞检查最后3个采样点处的像素颜色，判断钓鱼蓄力条的进度
    get_screenshot_inregion(bar_region)
    screen_shot = np.where(screen_shot[..., :] < 150, 0, 255)
    while True:
        if screen_shot[int(prog_mark_pos[sample_pt_num-1][1])][int(prog_mark_pos[sample_pt_num-1][0])] == 255 or \
           screen_shot[int(prog_mark_pos[sample_pt_num-2][1])][int(prog_mark_pos[sample_pt_num-2][0])] == 255 or \
           screen_shot[int(prog_mark_pos[sample_pt_num-3][1])][int(prog_mark_pos[sample_pt_num-3][0])] == 255 :
            break
        get_screenshot_inregion(bar_region)
        screen_shot = np.where(screen_shot[..., :] < 150, 0, 255)

    pg.mouseUp(button="left")
    time.sleep(0.8)


# 检测钓鱼进度条是否出现了，未出现则一直阻塞检查
def progress_bar_is_show(bar_region) :
    # 计算截图的平均灰度，低于特定值则钓鱼进度条未出现
    while True :
        # 对进度条位置进行截图, 每隔judge_interval秒判断一次
        screenshot = pg.screenshot(region=(bar_region[0], bar_region[1], bar_region[2] - bar_region[0], bar_region[3] - bar_region[1]))
        screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGR2GRAY)
        screenshot = np.where(screenshot[..., :] < 150, 0, 255)

        # 此处 gray_threshold 和 judge_interval 可以根据实际情况调整
        if screenshot.mean() < gray_threshold :
            break
        else :
            time.sleep(judge_interval)

    print("begin fish")


# 检测鱼在进度条中的位置
def detect_fish_pos() :
    global fish_pic
    global fish_position

    orb = cv2.ORB_create()
    screenshot_keypt, desp1 = orb.detectAndCompute(screen_shot, None)
    fish_keypt,       desp2 = orb.detectAndCompute(fish_pic, None)

    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    matches = bf.knnMatch(desp1, desp2, 2, None)
    matches = sorted(matches, key = lambda x : x[0].distance)

    # 统计三个匹配点的中心点
    average_pt_x, average_pt_y = 0, 0
    # print(screenshot_keypt[matches[0][0].queryIdx].pt)
    # print(screenshot_keypt[matches[1][0].queryIdx].pt)
    # print(screenshot_keypt[matches[2][0].queryIdx].pt)

    for i in range(3) :
        average_pt_x += screenshot_keypt[matches[i][0].queryIdx].pt[1]
        average_pt_y += screenshot_keypt[matches[i][0].queryIdx].pt[0]
    average_pt_x /= 3
    average_pt_y /= 3

    # print([average_pt_y, average_pt_x])
    # 找到距离中心点最近的采样点
    min_distance = 10000000
    for i in range(sample_pt_num) :
        distance = math.dist(fish_mark_pos[i], [average_pt_y, average_pt_x])
        # 排除被宝箱遮挡时错误的采样点
        if distance < min_distance and distance < screen_shot.shape[0] * 0.1:
            min_distance = distance
            fish_position = i

    # print("min distance = " + str(min_distance))
    # print("fishpos = " + str(fish_position))


# 根据鱼和钓鱼条的位置，松开或按下鼠标左键
def mousedown_or_up() :
    global fish_position
    global fishbar_begend

    # 根据情况调整鼠标做键的按下松开
    mid_position = (fishbar_begend[0] + fishbar_begend[1]) / 2   # 钓鱼条的中心点
    if fish_position > fishbar_begend[1]:
        pg.mouseDown(button="left")
    elif fish_position < fishbar_begend[0]:
        pg.mouseUp(button="left")
    else :
        if fish_position > mid_position:
            pg.mouseDown(button="left")

        else :
            pg.mouseUp(button="left")



# 计算钓鱼进度条标记点的位置
def cal_mark_pos(bar_region) : 
    global fish_mark_pos
    global prog_mark_pos

    fish_mark_pos = [[0, 0] for i in range(1, sample_pt_num + 1)]
    prog_mark_pos = [[0, 0] for i in range(1, sample_pt_num + 1)]

    # 对钓鱼条位置截图，转为灰度图并二值化
    screenshot = pg.screenshot(region=(bar_region[0], bar_region[1], bar_region[2] - bar_region[0], bar_region[3] - bar_region[1]))
    screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGR2GRAY)
    screenshot = np.where(screenshot[..., :] < 150, 0, 255)
    # cv2.imwrite("pic/bar.png", screenshot)

    height, width = screenshot.shape

    # print("width, height = " + str(width) + "," + str(height))
    center_pos = (int(width / 2) + 5, int(height - 1) + 10)
    # print("center_pos = " + str(center_pos[0]) + "," + str(center_pos[1]))

    # 在0°至180°之间均匀采样sample_pt_num个点，记录这些点在截图中的坐标
    for i in range(1, sample_pt_num + 1) :
        sample_pt_x, sample_pt_y = center_pos
        off_len = center_pos[0] * 0.88
        sample_pt_x += off_len * math.cos(math.radians(180 - i * (180 / (sample_pt_num + 1))))
        sample_pt_y -= off_len * math.sin(math.radians(180 - i * (180 / (sample_pt_num + 1))))
        fish_mark_pos[i-1][0] = sample_pt_x + fish_mark_x_offset
        fish_mark_pos[i-1][1] = sample_pt_y + fish_mark_y_offset
        
        screenshot[int(sample_pt_y)][int(sample_pt_x)] = 128

        sample_pt_x, sample_pt_y = center_pos
        sample_pt_y -= height * 0.2
        off_len = center_pos[0] * 0.65
        sample_pt_x += off_len * math.cos(math.radians(180 - i * (180 / (sample_pt_num + 1))))
        sample_pt_y -= off_len * math.sin(math.radians(180 - i * (180 / (sample_pt_num + 1))))
        prog_mark_pos[i-1][0] = sample_pt_x + prog_mark_x_offset
        prog_mark_pos[i-1][1] = sample_pt_y + prog_mark_y_offset

        screenshot[int(sample_pt_y)][int(sample_pt_x)] = 128
    


# 读取fish图片并进行横向增广，将原图与增广图像hstack拼接
def load_fishpic_and_augmentation() :
    # 读取鱼的图片，并转为灰度图
    global fish_pic
    fish_pic = cv2.imread("pic/fish.jpg", cv2.IMREAD_GRAYSCALE)
    fish_pic_aug = fish_pic.copy()
    # print(fish_pic.shape)
    
    # 以数组中轴交换列
    for i in range(0, int(fish_pic.shape[1] / 2)) :
        for j in range(int(fish_pic.shape[0])) :
            fish_pic_aug[j][i], fish_pic_aug[j][fish_pic.shape[1] - i - 1] = fish_pic_aug[j][fish_pic.shape[1] - i - 1], fish_pic_aug[j][i]

    # 数组堆叠增广
    fish_pic = np.hstack([fish_pic, fish_pic_aug])
    # print(fish_pic.shape)


# 计算钓鱼条的起始和终止位置
def cal_fishbar_len() :
    # 对钓鱼条位置截图，转为灰度图并二值化
    screenshot = np.where(screen_shot[..., :] < 150, 0, 255)
    for [x, y] in prog_mark_pos :
        screenshot[int(y)][int(x)] = 255
    # cv2.imwrite("pic/bar.png", screenshot)

    is_black = [0 for i in range(0, len(fish_mark_pos))]
    for index in range(len(fish_mark_pos)) :
        # 统计标记点附近像素的平均灰度，判断是否是纯黑
        # 若是纯黑，表示当前标记点在钓鱼条内
        x = fish_mark_pos[index][0]
        y = fish_mark_pos[index][1]
        total_gray = 0
        for i in range(-3, 4) :
            for j in range(-3, 4) :
                total_gray += screenshot[int(y + j)][int(x + i)]
        average_gray = total_gray / 49
        if average_gray == 255 :
            is_black[index] = 1
    
    # 找到钓鱼条的起始点
    for i in range(len(is_black)) :
        if is_black[i] == 1 :
            fishbar_begend[0] = i
            break

    for i in range(len(is_black)-1, -1, -1) :
        if is_black[i] == 1 :
            fishbar_begend[1] = i
            break

    # 打印检测钓鱼条位置是否正确
    if bool_mark_debug :
        show_str_debug = "\r"
        for i in range(1, 36) :
            if i == fish_position:
                show_str_debug += 'F'
            elif i >= fishbar_begend[0] and i <= fishbar_begend[1] :
                show_str_debug += '#'
            else :
                show_str_debug += '-'
        print(show_str_debug)


pic_index = 0

# 获取钓鱼条区域的截图
def get_screenshot_inregion(bar_region) :
    global screen_shot
    global pic_index
    global bool_mark_debug

    # 先在bar_region区域截图，使用ORB提取特征点检测鱼在截图中可能的位置
    screenshot = pg.screenshot(region=(bar_region[0], bar_region[1], bar_region[2] - bar_region[0], bar_region[3] - bar_region[1]))
    screen_shot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGR2GRAY)

    # 用于标记点的校准
    if bool_mark_debug :
        screenshot = np.where(screen_shot[..., :] < 150, 0, 255)
        for i in range(len(fish_mark_pos)) :
            screenshot[int(fish_mark_pos[i][1])][int(fish_mark_pos[i][0])] = 128
            screenshot[int(prog_mark_pos[i][1])][int(prog_mark_pos[i][0])] = 128

        cv2.imwrite(f"test/{pic_index}_two.jpg", screenshot)
        pic_index += 1


# 通过平均灰度判断钓鱼是否结束
def fish_is_over() :
    if screen_shot.mean() < fishover_mean:
        print("fish is over")
        pg.mouseUp(button="left")
        return True
    else :
        return False