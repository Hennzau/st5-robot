import cv2
import numpy as np

img = cv2.imread("C:\\Users\\11874\\Desktop\\VehicleIntelligent\\EI\\premiers-tests-du-robot-2024\\test_traitement_image\\photo_carrefour1.jpg")

# Get height and width of the image
height, width, _ = img.shape
print(height)
hmin = round(height*0.6)
hmax = round(height*0.8)

gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

_, binary = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)  # 240 是白色像素的阈值

white_counts = np.sum(binary == 255, axis=1)

# find max white pixel line
max_white_col = np.argmax(white_counts)
print(max_white_col)

# detect if the max white pixel is enough close
if max_white_col <= hmax and max_white_col >= hmin:
    print("Intersection !")

# draw horizontal line
cv2.line(img, (0, max_white_col), (img.shape[1], max_white_col), (0, 0, 255), 2) 
cv2.line(img, (0,hmin), (img.shape[1], hmin), (0, 255, 0), 5)
cv2.line(img, (0,hmax), (img.shape[1], hmax), (0, 255, 0), 5)
# save the result
cv2.imshow('Result', img)
cv2.imwrite('output_image.jpg', img)
cv2.waitKey(0)
cv2.destroyAllWindows()