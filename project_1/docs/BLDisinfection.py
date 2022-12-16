"""
--------------------------------------------------------------------------
Blue Light Disinfection System
--------------------------------------------------------------------------
License:   
Copyright 2022 <Ariadna Gomez>

Redistribution and use in source and binary forms, with or without 
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this 
list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, 
this list of conditions and the following disclaimer in the documentation 
and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors 
may be used to endorse or promote products derived from this software without 
specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE 
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE 
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE 
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL 
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR 
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER 
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, 
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE 
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
--------------------------------------------------------------------------
Use the following hardware components to build a programmable blue light disinfection system:
  - HT16K33 Display
  - Button
  - USB Camera
  - microUSB to USB connector
  - Blue light LEDs 

Software API:
  - OpenCV 
  
  
--------------------------------------------------------------------------
Background Information: 
 

        
"""
import cv2
import numpy as np
import time

import Adafruit_BBIO.GPIO as GPIO

import ht16k33 as HT16K33


# ------------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------------


# ------------------------------------------------------------------------
# Global variables
# ------------------------------------------------------------------------

# None

# ------------------------------------------------------------------------
# Functions / Classes
# ------------------------------------------------------------------------

class BLD():
    """ BlueLightDisinfectionSystem"""
    start_time      = None
    button          = None
    LED_ctrl        = None
    camera          = None
    display         = None
    num_cultures    = None

    def __init__(self, button="P2_2", LED_ctrl="P2_1",
                       camera="P1_9",
                       i2c_bus=1, i2c_address=0x70):
        """ Initialize variables and set up display """
        self.button     = button
        self.LED_ctrl   = LED_ctrl
        self.camera     = Camera.Camera(camera)
        self.display    = HT16K33.HT16K33(i2c_bus, i2c_address)
        
        self._setup()
    
    # End def

    def _setup(self):
        """Setup the hardware components."""

        # Initialize Display
        self.set_display_dash()

        # Initialize Button
        GPIO.setup(self.button, GPIO.IN)
        
        # Initialize LEDs
        GPIO.setup(self.LED_ctrl, GPIO.OUT)
        

    # End def
    
    def button_press(self, function=None):
        """Button press
               - Optional function to execute while waiting for the button to be pressed
                 - Returns the last value of the function when the button was pressed
               - Waits for a full button press
               - Returns the time the button was pressed as tuple
        """
        button_press_time            = 0.0                 # Time button was pressed (in seconds)
        ret_val                      = None                # Optional return value for provided function

        # Optinally execute function pointer that is provided
        #   - This is so that function is run at least once in case of a quick button press
        
        if function is not None:
            ret_val = function()
        
        # Wait for button press
        while(GPIO.input(self.button) == 1):
            # Optinally execute function pointer that is provided
            if function is not None:
                ret_val = function()

            # Sleep for a short period of time to reduce CPU load
            time.sleep(0.1)

        # Record time
        button_press_time = time.time()

        # Wait for button release
        while(GPIO.input(self.button) == 0):
            # Sleep for a short period of time to reduce CPU load
            time.sleep(0.1)

        # Compute button press time
        button_press_time = time.time() - button_press_time

        # Return button press time and optionally ret_val
        if function is not None:
            return (button_press_time, ret_val)
        else:
            return (button_press_time)

    # End def    
    

    def take_a_pic(self, image_file, image_name, debug=False, verbose=False):
    ret_val = None
    
    if (verbose):
        print('Processing Image file:  {0}'.format(image_file))        
        start_time = time.time():

    # Reads image of contaminated agar plate / Would be when camera would take the first picture
    img = cv2.imread(image_file)
    
    # Convert image to Grayscale
    if (True):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        if (debug):
            print('Convert Grayscale image')
            cv2.imwrite('{0}_01_gray.png'.format(image_name), gray)
    else:
        gray = cv2.imread(image_file, cv2.IMREAD_GRAYSCALE)

        # Blur image to reduce background noise
    if (True):
        blur = cv2.medianBlur(gray, 5)
        
        if (debug):
            print('Bluring image')
            cv2.imwrite('{0}_02_blur.png'.format(image_name), blur)
    else:
        blur = gray
        
        # Calculates the number of cultures present by detecting the Hough Circles
    if (True):
        candidate_circles = []
        minDist           = blur.shape[0] / 4
        minRadius         = int(blur.shape[0] / 3)
        maxRadius         = int(blur.shape[0])
    
        # cv2.HoughCircles(image, method, dp, minDist[, circles[, param1[, param2[, minRadius[, maxRadius]]]]])         
        circles = cv2.HoughCircles(blur, cv2.HOUGH_GRADIENT, 2, minDist,
                                   param1=200, param2=100, 
                                   minRadius=minRadius, maxRadius=maxRadius)

        if circles is not None:
            circles = np.uint16(np.around(circles))
        
            for i in circles[0,:]:
                # Check circle is completely within picture
                #     NOTE:  Upper left corner is (0,0)
                radius = int(i[2])
                north  = int(i[1]) - radius
                east   = int(i[0]) + radius
                south  = int(i[1]) + radius
                west   = int(i[0]) - radius
                y_max  = blur.shape[0]
                x_max  = blur.shape[1]

                if ((north > 0) and (east < x_max) and (south < y_max) and (west > 0)):
                    # Append to candidate circle list
                    candidate_circles.append((i[0], i[1], i[2]))
                    
                    # draw the outer circle
                    cv2.circle(img, (i[0], i[1]), i[2], (0, 255, 0), 2)
                    
                    # draw the center of the circle
                    cv2.circle(img, (i[0], i[1]), 2, (0, 0, 255), 3)
            
            if (len(candidate_circles) == 1):
                # Crop Image
                #     NOTE: its img[y: y + h, x: x + w] and *not* img[x: x + w, y: y + h]
                circle = (candidate_circles[0][0], candidate_circles[0][1], candidate_circles[0][2])
                
                radius = int(circle[2])
                north  = int(circle[1]) - radius
                west   = int(circle[0]) - radius
                size   = ((2 * radius), (2 * radius))

                crop   = blur[north:(north + (2 * radius)), west:(west + (2 * radius))]
                img    = img[north:(north + (2 * radius)), west:(west + (2 * radius))]
                
                if (debug):
                    cv2.imwrite('{0}_03_02_crop.png'.format(image_name), crop)
                              
                mask   = np.zeros(size, dtype=np.int8)
                mask   = cv2.circle(mask, (radius, radius), radius, 1, thickness=-1)
                face   = cv2.bitwise_and(crop, crop, mask=mask)

                # Update circle to new cropped image
                circle = (radius, radius, radius)
                circles = num_cultures
                
                if (debug):
                    cv2.imwrite('{0}_03_03_mask.png'.format(image_name), face)
            else:
                print("    WARNING: Found {0} candidate circles.".format(len(candidate_circles)))
            
            if (debug):
                print('Hough Circles image')
                cv2.imwrite('{0}_03_01_houghcircles.png'.format(image_name), img)            
        else:
            print("    WARNING: No circles detected")
            exit(0)
    else:
        face   = blur
        circle = None
    
    # Return value
        return num_cultures
    
        # End def 
    
    
    def run(self):
        default_time = 900
        min_cultures = 3
        sleep_time   = 30
        
        # Sets up display
        self.set_display_dash()
        
        # Wait for button press
        button_press_time = self.button_press()
        
        
        self.take_a_pic()
        
        # Set LEDs
        GPIO.output(self.LED_ctrl, GPIO.HIGH) #turn on LEDs
        
        
        
        
    # End def        
        
    def update_display(self):
        """Update display with new time countdown """
        self.display.text("")        
        
    # End def        
        
        
    def set_display_dash(self):
        """Set display to word "----" """
        self.display.text("----")        
        
    # End def

    def cleanup(self):
        """Cleanup the hardware components."""
        
        # Set Display to something fun to show program is complete
        self.display.text("DEAD")
        self.display.set_colon(False)

        # Clean up GPIOs
        GPIO.output(self.LED_ctrl, GPIO.LOW)

        # Clean up GPIOs
        GPIO.cleanup()

    # End def

# End class







# ------------------------------------------------------------------------
# Main script
# ------------------------------------------------------------------------


if __name__ == '__main__':

    print("Program Start")

    # Create instantiation of the disinfection system cycle
    bld = BLD()

    try:
        # Run the blue light disinfection system
        bld.run()

    except KeyboardInterrupt:
        # Clean up hardware when exiting
        bld.cleanup()

    print("Program Complete")
