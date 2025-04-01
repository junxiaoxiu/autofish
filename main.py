import cv2
import pyautogui as pg
import time
import sys

import locate
import autofish

def main() : 

    # 定位图标位置
    icon_pos = locate.locate_icon_position()

    # 开始钓鱼
    autofish.fish(icon_pos)

    #pic = cv2.imread("pic/fishing.jpg", cv2.IMREAD_GRAYSCALE)
    #cv2.imwrite("./pic/fishing_gray.jpg", pic)

if __name__ == "__main__" :
    main()

