# General imports

import numpy as np
import cv2

# Specific imports for Webots

from controller import Robot
from controller import Camera

#####################
# Robot setup and control
#####################

speed_constant = 50  # Speed constant to control the speed of the robot
tube_x = 100

LEFT_THRESHOLD = -tube_x - 70
RIGHT_THRESHOLD = tube_x + 70

current_state = "CENTER"


def update_state(distance):
    global current_state
    if current_state == "CENTER":
        if distance > RIGHT_THRESHOLD:
            current_state = "RIGHT"
        elif distance < LEFT_THRESHOLD:
            current_state = "LEFT"
    elif current_state == "RIGHT":
        if distance < tube_x:
            current_state = "CENTER"
    elif current_state == "LEFT":
        if distance > -tube_x:
            current_state = "CENTER"


# wheels[0] wheels[1]
# wheels[2] wheels[3]


def set_wheel_velocities(state, speed_constant):
    if state == "RIGHT":
        wheels[0].setVelocity(1 * speed_constant)
        wheels[1].setVelocity(0.1 * speed_constant)
        wheels[2].setVelocity(1 * speed_constant)
        wheels[3].setVelocity(0.1 * speed_constant)
    elif state == "LEFT":
        wheels[0].setVelocity(0.1 * speed_constant)
        wheels[1].setVelocity(1 * speed_constant)
        wheels[2].setVelocity(0.1 * speed_constant)
        wheels[3].setVelocity(1 * speed_constant)
    else:  # CENTER
        wheels[0].setVelocity(1 * speed_constant)
        wheels[1].setVelocity(1 * speed_constant)
        wheels[2].setVelocity(1 * speed_constant)
        wheels[3].setVelocity(1 * speed_constant)


#####################
# Webots setup
#####################

TIME_STEP = 64
robot = Robot()

# Enable camera
camera = robot.getDevice("camera")
camera.enable(TIME_STEP)

# Listing the wheels
wheels = []
wheels_names = ["wheel1", "wheel2", "wheel3", "wheel4"]
for i in range(len(wheels_names)):
    wheels.append(robot.getDevice(wheels_names[i]))
    wheels[i].setPosition(float("inf"))
    wheels[i].setVelocity(0.0)


#####################
# Main loop
#####################

while robot.step(TIME_STEP) != -1:
    #####################
    # Image processing
    #####################

    # Read image from webots camera

    cameraData = camera.getImage()
    image = np.frombuffer(cameraData, np.uint8).reshape(
        (camera.getHeight(), camera.getWidth(), 4)
    )

    # Read/Write issue
    image = np.copy(image)
    h, w = image.shape[:2]

    # Convert to HSV color space
    blur = cv2.blur(image, (5, 5))
    ret, thresh1 = cv2.threshold(blur, 168, 255, cv2.THRESH_BINARY)
    hsv = cv2.cvtColor(thresh1, cv2.COLOR_RGB2HSV)

    # Define range of white color in HSV
    lower_white = np.array([0, 0, 168])
    upper_white = np.array([172, 111, 255])

    # Threshold the HSV image
    mask = cv2.inRange(hsv, lower_white, upper_white)

    # Remove noise
    kernel_erode = np.ones((6, 6), np.uint8)
    eroded_mask = cv2.erode(mask, kernel_erode, iterations=1)
    kernel_dilate = np.ones((4, 4), np.uint8)
    dilated_mask = cv2.dilate(eroded_mask, kernel_dilate, iterations=1)

    # Find the different contours and draw them
    contours, hierarchy = cv2.findContours(
        dilated_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
    )
    im2 = cv2.drawContours(image, contours, -1, (0, 255, 0), 3)
    # Sort by area (keep only the biggest one)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:1]

    # Only proceed if at least one contour was found
    if len(contours) > 0:
        M = cv2.moments(contours[0])
        # Centroid
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])

        # Location of the centroid
        cv2.circle(im2, (cx, cy), 10, (0, 0, 255), 3)
        # Vertical line in the center
        cv2.line(im2, (w // 2, 0), (w // 2, h), (0, 255, 0), 2)

        # Two vertical lines, one at 100px from the center, the other at -100px
        cv2.line(im2, (w // 2 + tube_x, 0), (w // 2 + tube_x, h), (255, 0, 0), 2)
        cv2.line(im2, (w // 2 - tube_x, 0), (w // 2 - tube_x, h), (255, 0, 0), 2)

        # Two vertical lines indicating the thresholds
        cv2.line(
            im2,
            (w // 2 + RIGHT_THRESHOLD, 0),
            (w // 2 + RIGHT_THRESHOLD, h),
            (0, 0, 255),
            2,
        )
        cv2.line(
            im2,
            (w // 2 + LEFT_THRESHOLD, 0),
            (w // 2 + LEFT_THRESHOLD, h),
            (0, 0, 255),
            2,
        )

        # Distance to the center allowing to turn left or right
        distance = cx - w / 2
        if distance > tube_x:
            direction = ">"
        elif distance < -tube_x:
            direction = "<"
        else:
            direction = "^"

        cv2.putText(
            im2,
            f"{direction} {distance}",
            (cx, cy),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (255, 0, 0),
            2,
            cv2.LINE_AA,
        )

        update_state(distance)
        set_wheel_velocities(current_state, speed_constant)

    else:
        print("No Centroid Found")

    cv2.imshow("Image traitee", im2)
    cv2.waitKey(1)
