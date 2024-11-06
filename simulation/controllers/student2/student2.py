from controller import Robot
from controller import Camera

import numpy as np
import cv2

import random
import math
import time
# new random seed
random.seed(int(time.time()))
order = None
#####################
# Robot setup
#####################

#####################
# Robot control state machine
#####################

# Diagram of the robot

#      sensors
# wheels[0] wheels[1]
# wheels[2] wheels[3]


speed_constant = 5  # Speed constant to control the speed of the robot
tube_x = 60

LEFT_THRESHOLD = -tube_x - 10
RIGHT_THRESHOLD = tube_x + 10

# pos : Relative position to the line
# intersection : Relative position to the intersection
current_state = {'pos':'CENTER','intersection':'NONE', 'intersection_noted' : False, 'stop': False, 'possibilities' : []}
orders = ['RIGHT', 'LEFT']

def update_turn(distance):
    
    if current_state['pos'] == 'CENTER':
        if distance > RIGHT_THRESHOLD:
            current_state['pos'] = 'RIGHT'
        elif distance < LEFT_THRESHOLD:
            current_state['pos'] = 'LEFT'
    elif current_state['pos'] == 'RIGHT':
        if distance < tube_x:
            current_state['pos'] = 'CENTER'
    elif current_state['pos'] == 'LEFT':
        if distance > -tube_x:
            current_state['pos'] = 'CENTER'

def update_intersection(max_white):
    # Check if the max value is above a certain threshold
    if max_white > 40000: # Value to be adjusted
        
        pos_intersection = np.argmax(histogram)
        current_state['intersection'] = True
        
        cv2.line(im2, (0, pos_intersection), (w, pos_intersection), (0, 0, 255), 2)
        
        if pos_intersection > h - h//4:
            current_state['intersection'] = 'NEAR'
        else:
            current_state['intersection'] = 'DETECTED'
        
    else:
        current_state['intersection'] = 'NONE'

def set_wheel_velocities(current_state, speed_constant):
    global timeout
    global order
    
    if not current_state['stop']:
        
        # Intersection near that has not been noted and that is not a dead end
        if current_state['intersection'] == 'NEAR' and not current_state['intersection_noted'] and current_state['possibilities'] != []:
            
            # Stop and go
            # current_state['stop'] = True
            # print("Stop at intersection or sharp corner")
            # time.sleep(1)
            # current_state['stop'] = False
            
            # Random turn at intersection
            print(current_state['possibilities'])
            order = random.choice(current_state['possibilities'])
            timeout = 0
            
            if order == 'RIGHT':
                wheels[0].setVelocity(1 * speed_constant)
                wheels[1].setVelocity(0 * speed_constant)
                wheels[2].setVelocity(1 * speed_constant)
                wheels[3].setVelocity(0 * speed_constant)
            elif order == 'LEFT':
                wheels[0].setVelocity(0 * speed_constant)
                wheels[1].setVelocity(1 * speed_constant)
                wheels[2].setVelocity(0 * speed_constant)
                wheels[3].setVelocity(1 * speed_constant)
            else:  # CENTER
                wheels[0].setVelocity(1 * speed_constant)
                wheels[1].setVelocity(1 * speed_constant)
                wheels[2].setVelocity(1 * speed_constant)
                wheels[3].setVelocity(1 * speed_constant)
            
            current_state['intersection_noted'] = True
            print('Noted intersection')
        
        # Intersection near that has been noted, keep turning until timeout
        elif current_state['intersection'] == 'NEAR' and current_state['intersection_noted']:
            if timeout < 500:
                timeout += 1
                if order == 'RIGHT':
                    wheels[0].setVelocity(1 * speed_constant)
                    wheels[1].setVelocity(0 * speed_constant)
                    wheels[2].setVelocity(1 * speed_constant)
                    wheels[3].setVelocity(0 * speed_constant)
                elif order == 'LEFT':
                    wheels[0].setVelocity(0 * speed_constant)
                    wheels[1].setVelocity(1 * speed_constant)
                    wheels[2].setVelocity(0 * speed_constant)
                    wheels[3].setVelocity(1 * speed_constant)
                else:  # CENTER
                    wheels[0].setVelocity(1 * speed_constant)
                    wheels[1].setVelocity(1 * speed_constant)
                    wheels[2].setVelocity(1 * speed_constant)
                    wheels[3].setVelocity(1 * speed_constant)
            else:
                current_state['intersection_noted'] = False
                current_state['intersection'] = 'NONE'
                current_state['possibilities'] = []
        # Intersection not detected or far, reset of the noted state variable
        elif current_state['intersection'] != 'NEAR': 
            current_state['intersection_noted'] = False
            if current_state['pos'] == 'RIGHT':
                wheels[0].setVelocity(1 * speed_constant)
                wheels[1].setVelocity(0.1 * speed_constant)
                wheels[2].setVelocity(1 * speed_constant)
                wheels[3].setVelocity(0.1 * speed_constant)
            elif current_state['pos'] == 'LEFT':
                wheels[0].setVelocity(0.1 * speed_constant)
                wheels[1].setVelocity(1 * speed_constant)
                wheels[2].setVelocity(0.1 * speed_constant)
                wheels[3].setVelocity(1 * speed_constant)
            else:  # CENTER
                wheels[0].setVelocity(1 * speed_constant)
                wheels[1].setVelocity(1 * speed_constant)
                wheels[2].setVelocity(1 * speed_constant)
                wheels[3].setVelocity(1 * speed_constant)
        else:
            if current_state['pos'] == 'RIGHT':
                wheels[0].setVelocity(1 * speed_constant)
                wheels[1].setVelocity(0.1 * speed_constant)
                wheels[2].setVelocity(1 * speed_constant)
                wheels[3].setVelocity(0.1 * speed_constant)
            elif current_state['pos'] == 'LEFT':
                wheels[0].setVelocity(0.1 * speed_constant)
                wheels[1].setVelocity(1 * speed_constant)
                wheels[2].setVelocity(0.1 * speed_constant)
                wheels[3].setVelocity(1 * speed_constant)
            else:  # CENTER
                wheels[0].setVelocity(1 * speed_constant)
                wheels[1].setVelocity(1 * speed_constant)
                wheels[2].setVelocity(1 * speed_constant)
                wheels[3].setVelocity(1 * speed_constant)
    else:
        wheels[0].setVelocity(0)
        wheels[1].setVelocity(0)
        wheels[2].setVelocity(0)
        wheels[3].setVelocity(0)

#####################
# Webots setup
#####################

TIME_STEP = 64
robot = Robot()

# Enable camera
camera = robot.getDevice('camera')
camera.enable(TIME_STEP)

# Listing the wheels
wheels = []
wheels_names = ['wheel1', 'wheel2', 'wheel3', 'wheel4']
for i in range(len(wheels_names)):
    wheels.append(robot.getDevice(wheels_names[i]))
    wheels[i].setPosition(float('inf'))
    wheels[i].setVelocity(0.0)


#####################
# Main loop
#####################

while robot.step(TIME_STEP) != -1:
    
    print(current_state)
    
    #
    # Image processing
    #
    
    # Read image from webots camera
    cameraData = camera.getImage()
    image = np.frombuffer(cameraData, np.uint8).reshape((camera.getHeight(), camera.getWidth(), 4))
    
    # Read/Write issue
    image = np.copy(image)
    h, w = image.shape[:2]
    
    # Convert to HSV color space
    blur = cv2.blur(image,(5,5))
    ret,thresh1 = cv2.threshold(blur,168,255,cv2.THRESH_BINARY)
    hsv = cv2.cvtColor(thresh1, cv2.COLOR_RGB2HSV)

    # Define range of white color in HSV
    lower_white = np.array([0, 0, 168])
    upper_white = np.array([172, 111, 255])
    
    # Threshold the HSV image
    mask = cv2.inRange(hsv, lower_white, upper_white)
    
    # Remove noise
    kernel_erode = np.ones((6,6), np.uint8)
    eroded_mask = cv2.erode(mask, kernel_erode, iterations=1)
    kernel_dilate = np.ones((4,4), np.uint8)
    dilated_mask = cv2.dilate(eroded_mask, kernel_dilate, iterations=1)

    # 
    # Line following
    #
    
    # Find the different contours and draw them
    contours, hierarchy = cv2.findContours(dilated_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    im2 = cv2.drawContours(image,contours,-1, (0,255,0), 3)
    # Sort by area (keep only the biggest one)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:1]

    # Only proceed if at least one contour was found
    if len(contours) > 0:
        
        M = cv2.moments(contours[0])
        # Centroid
        cx = int(M['m10']/M['m00'])
        cy = int(M['m01']/M['m00'])
        
        # Location of the centroid
        cv2.circle(im2, (cx, cy), 10, (0, 0, 255), 3)
        
        # Distance to the center allowing to turn left or right
        distance = cx - w/2

        cv2.putText(im2, f"{distance}", (cx, cy), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2, cv2.LINE_AA)  

        update_turn(distance)
        
    else:
        print("No Centroid Found")
    
    #
    # Intersection detection
    #
    
    # Compute horizontal histogram of the white pixels in dilated_mask
    histogram = np.sum(dilated_mask, axis=1)
    max_white = np.max(histogram)
    update_intersection(max_white)
    
    # Detect which turns are possible by looking at the presence of white pixels
    # Two vertical histograms are made at w//8 and 7w//8
    # One horizontal histogram is made at 7h//8 (on top to detect in the robot can go straight)
    if current_state['intersection'] in ['DETECTED','NEAR']:
        left_histogram = np.sum(dilated_mask[:, :w//8], axis=1)
        right_histogram = np.sum(dilated_mask[:, 7*w//8:], axis=1)
        top_histogram = np.sum(dilated_mask[:h//8, :], axis=0)
        
        if np.max(left_histogram) > 10000:
            current_state['possibilities'].append('LEFT') if 'LEFT' not in current_state['possibilities'] else None
        if np.max(right_histogram) > 10000:
            current_state['possibilities'].append('RIGHT') if 'RIGHT' not in current_state['possibilities'] else None
        if np.max(top_histogram) > 10000:
            current_state['possibilities'].append('STRAIGHT') if 'STRAIGHT' not in current_state['possibilities'] else None
        elif 'STRAIGHT' in current_state['possibilities']: # This condition should be useless for left and right
            current_state['possibilities'].remove('STRAIGHT')
    else:
        current_state['possibilities'] = []
    
    
    set_wheel_velocities(current_state, speed_constant)
    
    #
    # Overlay
    #

    # Vertical line in the center
    cv2.line(im2, (w//2, 0), (w//2, h), (0, 255, 0), 2)
    # Two vertical lines, one at 100px from the center, the other at -100px
    cv2.line(im2, (w//2 + tube_x, 0), (w//2 + tube_x, h), (255, 0, 0), 2)
    cv2.line(im2, (w//2 - tube_x, 0), (w//2 - tube_x, h), (255, 0, 0), 2)

    # Two vertical lines indicating the thresholds
    cv2.line(im2, (w//2 + RIGHT_THRESHOLD, 0), (w//2 + RIGHT_THRESHOLD, h), (0, 0, 255), 2)
    cv2.line(im2, (w//2 + LEFT_THRESHOLD, 0), (w//2 + LEFT_THRESHOLD, h), (0, 0, 255), 2)
    
    # Turn line
    cv2.line(im2, (0, h - h//4), (w, h - h//4), (0, 255, 0), 2)
    
    # Top text
    cv2.putText(im2, f"{current_state['pos']} INTER {current_state['intersection']} {max_white}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
    
    # Bottom text
    cv2.putText(im2, f"TRAJ {current_state['possibilities']}", (50, h - 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
    
    cv2.imshow("Image traitee", im2)
    cv2.waitKey(1)
