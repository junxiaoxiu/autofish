import cv2
import time
import math
import numpy as np
import pyautogui as pg
import autofish

# 屏幕缩放系数
screen_scale = 1

# 待识别图像的路径
fishing_reel_path = "pic/fishing_reel.jpg"
handle_path       = "pic/handle.jpg"
bait_path         = "pic/bait.jpg"
prop_path         = "pic/prop.jpg"
use_path          = "pic/use.jpg"
fishing_gear_path = "pic/fishing_gear.jpg"


# 获取各个图标的位置，便于后期定位点击
def locate_icon_position() :
    # 获取屏幕宽高
    screen_width, screen_height = pg.size()
    # print("screen_size:" + str(screen_width) + ", " + str(screen_height))

    # 截屏，可以转为灰度图提高识别速度，但会损失精度
    screen_shot = pg.screenshot()
    screen_shot = np.array(screen_shot)
    #screen_shot = cv2.imread("pic/screenshot.png")
    # screen_shot = cv2.resize(screen_shot, (int(screen_width / screen_scale), int(screen_height / screen_scale)))

    # 依次获取渔线轮、把手、鱼饵、道具和渔具图标的位置
    fishing_reel_pos = detect_icon_position(screen_shot, fishing_reel_path)
    handle_pos       = detect_icon_position(screen_shot, handle_path)
    bait_pos         = detect_icon_position(screen_shot, bait_path)
    prop_pos         = detect_icon_position(screen_shot, prop_path)
    fishing_gear_pos = detect_icon_position(screen_shot, fishing_gear_path)

    # 获取使用按钮的位置
    pg.click(prop_pos[0], prop_pos[1], button="left")
    time.sleep(0.5)
    # 再次截图
    screen_shot = np.array(pg.screenshot())
    use_pos          = detect_icon_position(screen_shot, use_path)
    pg.click(fishing_gear_pos[0], fishing_gear_pos[1], button="left")
    time.sleep(0.5)

    return (fishing_reel_pos, handle_pos, bait_pos, prop_pos, fishing_gear_pos, use_pos)


# 识别图标的位置
def detect_icon_position(screen_shot, pic_path) :
    # 适配不同分辨率，不能直接采用模板匹配
    pic = cv2.imread(pic_path) 
    # 将截图与待匹配图标都转为灰度图
    # cv2.cvtColor(pic, pic, cv2.COLOR_BGR2GRAY)
    # cv2.cvtColor(screen_shot, screen_shot, cv2.COLOR_BGR2GRAY)

    res = cv2.matchTemplate(screen_shot, pic, cv2.TM_CCOEFF_NORMED)
    center_pos = cal_center_pos(res, pic.shape[1], pic.shape[0])
    # print("pos = " + str(center_pos))
    return center_pos


# 计算处图标中心点
def cal_center_pos(res, icon_width, icon_height) :
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

    # 根据最大值判断屏幕上是否存在图标
    #if max_val >= 0.5 :
    center_X = (max_loc[0] + icon_width / 2)
    center_Y = (max_loc[1] + icon_height / 2)
    return (center_X, center_Y)
    #else :
        #print("icon not found")
        #return (0, 0)


# 根据钓鱼轮和把手的位置计算钓鱼进度条的相对位置
def cal_progress_bar_pos(fishing_reel_pos, handle_pos) : 
    # 计算钓鱼进度条的外接矩形
    toppt_x = int(fishing_reel_pos[0] - 1.8 * (fishing_reel_pos[1] - handle_pos[1]))
    toppt_y = int(handle_pos[1] - 1.2 * (fishing_reel_pos[1] - handle_pos[1]))
    btmpt_x = int(fishing_reel_pos[0] + 1.8 * (fishing_reel_pos[1] - handle_pos[1]))
    btmpt_y = int(handle_pos[1] + 0.5 * (fishing_reel_pos[1] - handle_pos[1]))

    # print(toppt_x, toppt_y, btmpt_x - toppt_x, btmpt_y - toppt_y)

    # 返回外接矩形的左上角和右下角坐标
    return (toppt_x, toppt_y, btmpt_x, btmpt_y)

    
