from __future__ import division

import cv2
import numpy as np

# Input Image
image = cv2.imread("photo_test.jpg")
h, w = image.shape[:2]
print(w, h)

# Convert to HSV color space

blur = cv2.blur(image, (5, 5))
# ret,thresh1 = cv2.threshold(image,127,255,cv2.THRESH_BINARY)
ret, thresh1 = cv2.threshold(blur, 168, 255, cv2.THRESH_BINARY)
hsv = cv2.cvtColor(thresh1, cv2.COLOR_RGB2HSV)

# Define range of white color in HSV
lower_white = np.array([0, 0, 168])
upper_white = np.array([172, 111, 255])
# Threshold the HSV image
mask = cv2.inRange(hsv, lower_white, upper_white)
# cv2.imwrite('out_test.png', mask)
# Remove noise
kernel_erode = np.ones((6, 6), np.uint8)

eroded_mask = cv2.erode(mask, kernel_erode, iterations=1)
kernel_dilate = np.ones((4, 4), np.uint8)
dilated_mask = cv2.dilate(eroded_mask, kernel_dilate, iterations=1)

# Find the different contours
contours, hierarchy = cv2.findContours(
    dilated_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
)
# Sort by area (keep only the biggest one)
im2 = cv2.drawContours(image, contours, -1, (0, 255, 0), 3)

cv2.imwrite("out_test.png", im2)
print(len(contours))
contours = sorted(contours, key=cv2.contourArea, reverse=True)[:1]

if len(contours) > 0:
    M = cv2.moments(contours[0])
    # Centroid
    cx = int(M["m10"] / M["m00"])
    cy = int(M["m01"] / M["m00"])
    print("Centroid of the biggest area: ({}, {})".format(cx, cy))
else:
    print("No Centroid Found")
