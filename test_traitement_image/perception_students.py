from __future__ import division
import cv2
import numpy as np

from picamera import PiCamera
from picamera.array import PiRGBArray

resolution_target = (160, 128)

camera = PiCamera(sensor_mode = 2)
camera.resolution = resolution_target
camera.framerate = 32
rawCapture = PiRGBArray(camera, size=camera.resolution)

frame_source = camera.capture_continuous(rawCapture, format="bgr", use_video_port=True)


def perception(feedback = True):

    # Input Image
    image = next(frame_source).array

    if feedback: cv2.imshow("Image non traitée", image)

    # Clear the stream in preparation for the next frame
    rawCapture.truncate(0)
    
    if feedback: # Processing code
            
        # Use the captured frame
        h, w = image.shape[:2]
        # print(w, h)
        # Convert to HSV color space

        blur = cv2.blur(image,(5,5))
        #ret,thresh1 = cv2.threshold(image,127,255,cv2.THRESH_BINARY)
        ret,thresh1 = cv2.threshold(blur,168,255,cv2.THRESH_BINARY)
        hsv = cv2.cvtColor(thresh1, cv2.COLOR_RGB2HSV)

        # Define range of white color in HSV
        lower_white = np.array([0, 0, 168])
        upper_white = np.array([172, 111, 255])
        # Threshold the HSV image
        mask = cv2.inRange(hsv, lower_white, upper_white)
        #cv2.imwrite('out_test.png', mask)
        # Remove noise
        kernel_erode = np.ones((6,6), np.uint8)

        eroded_mask = cv2.erode(mask, kernel_erode, iterations=1)
        kernel_dilate = np.ones((4,4), np.uint8)
        dilated_mask = cv2.dilate(eroded_mask, kernel_dilate, iterations=1)

        # Find the different contours
        contours, hierarchy = cv2.findContours(dilated_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        # Sort by area (keep only the biggest one)
        im2 = cv2.drawContours(image,contours,-1, (0,255,0), 3)

        cv2.imwrite('out_test.png', im2)
        # print (len(contours))
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:1]

        if len(contours) > 0:
            M = cv2.moments(contours[0])
            # Centroid
            cx = int(M['m10']/M['m00'])
            cy = int(M['m01']/M['m00'])
            # print("Centroid of the biggest area: ({}, {})".format(cx, cy))
        else:
            print("No Centroid Found")

        # Location of the centroid
        cv2.circle(im2, (cx, cy), 10, (0, 0, 255), 3)
        # Vertical line in the center
        cv2.line(im2, (w//2, 0), (w//2, h), (255, 0, 0), 2)

        # Distance to the center allowing to turn left or right
        distance = cx - w/2
                
        if distance > 0:
            cv2.putText(im2, f"R {distance}", (cx, cy), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2, cv2.LINE_AA)
        else:
            cv2.putText(im2, f"L {distance}", (cx, cy), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2, cv2.LINE_AA)
            
        cv2.imshow("Image traitée", im2)
        cv2.waitKey(1)



if __name__ == "__main__":
    while True:
        perception(feedback = True)