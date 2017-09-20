"""
3/15/17
Needed
- calibration.dat
- logs/%s.txt
- util does not like to be called like this - -is it the correct module?


"""

import os

import time

import collections

import datetime



import serial

import numpy as np

import cv2

import pylab

import util

SOURCE = 1

WINDOW = 10

PLOTSIZE = 1000

BOX = (210,100), (640-250,480-150)

CALTARGET = 2.0 # square size 

PREFIX = datetime.datetime.strftime(datetime.datetime.now(),"%y%m%d-%H%M%S")

#SERIAL = "/dev/ttyUSB1"
#SERIAL = "/dev/ttyUSB\VID-1778&PID_0204&REV_1012"

SERIAL_SPEED = "9600"



def dump_state():

    global dataqueue

    global outfile, frames_saved, PREFIX

    global grayimage, timestamp, calibration

    global running



    if not running:

        return



    meltrate = np.median(dataqueue) * calibration * 60/10

    frames_saved += 1



    # save frame as image file

    cv2.imwrite("stored-images/%s/%09d.png" % (PREFIX, frames_saved), grayimage)



    # save data to log file

    outfile.write("%d\t%f\t%f\n" % (frames_saved, timestamp, meltrate))

    

    # print to screen

    print "Meltrate: %.1f" % meltrate



    # write to serial port

    if serial_port:

        serial_port.write("%.1f\n" %  meltrate)



imgqueue =  collections.deque(maxlen=WINDOW)

dataqueue = collections.deque(maxlen=15)

frames_saved = 0

#calibration = float(file("calibration.dat").read())

#outfile = file("logs/%s.txt" % PREFIX, "w")

#os.mkdir("stored-images/%s" % PREFIX)

cap = cv2.VideoCapture(SOURCE)



os.system("v4l2-ctl -c power_line_frequency=1 -d /dev/video%d" % SOURCE) # Command line call

os.system("v4l2-ctl -c focus_auto=0 -d /dev/video%d" % SOURCE)



def focus(f):

    os.system("v4l2-ctl -c focus_absolute=%d -d /dev/video%d" % (f, SOURCE))



focus_val = 40

focus(focus_val)



try:

    serial_port = serial.Serial(SERIAL, SERIAL_SPEED)

except:

    print "WARNING: Serial port not found"

    serial_port = False



#cancel_repeat = python_utils.call_repeatedly(1, dump_state)
 


running = False

pylab.ion()



PLOTSIZE = 1000

Y = collections.deque([np.nan]*PLOTSIZE, maxlen=PLOTSIZE)

X = range(PLOTSIZE)

plot, = pylab.plot(X, Y, '.')



while True:

    ret, frame = cap.read()

    timestamp = time.time()



    grayimage = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    grayimage = grayimage[BOX[0][1]:BOX[1][1],BOX[0][0]:BOX[1][0]]

    image = np.sqrt(np.sum(np.power(np.gradient(grayimage.astype('f')),2), axis=0))

    image /= 25

    image[image > 1] = 1

    image *= 255

    image = image.astype('uint8')



    if len(imgqueue) == imgqueue.maxlen:

        running = True

        ptimestamp, pimage = imgqueue.popleft()

        transformation = cv2.estimateRigidTransform(pimage, image, False)



        if transformation is not None:     

            xy = transformation[:,2] 

            x, y = xy / (timestamp-ptimestamp)



            dataqueue.append(y)

            #meltrate = np.median(dataqueue) * calibration * 60/10

            Y.append(meltrate)



            match = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)



            cv2.putText(match, "Meltrate", (55, 100), cv2.FONT_HERSHEY_DUPLEX, 1, (0,0,255))

            cv2.putText(match, "%.1f cm/min" % meltrate, (25, 180), cv2.FONT_HERSHEY_DUPLEX, 1, (0,0,255))



            cv2.imshow('Match', match)



            plot.set_data(X, Y)

            pylab.xlim((0,PLOTSIZE))

            pylab.ylim((0, 10))

            pylab.draw()





        framecopy = frame.copy()

        cv2.rectangle(framecopy, BOX[0], BOX[1], (255,0,0), 2)

        cv2.imshow('Webcam capture', framecopy)



    key = cv2.waitKey(1) & 0xFF

    

    if key == ord('q'):

        break



    if key == ord('-'):

         focus_val -= 1

         focus(focus_val)



    if key == ord('+'):

         focus_val += 1

         focus(focus_val)



    if key == ord('c'):

        found, points = cv2.findChessboardCorners(frame, (7,7))



        if found:

            grayframe = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            term = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_COUNT, 30, 0.1)

            cv2.cornerSubPix(grayframe, points, (5, 5), (-1, -1), term)

        

            points = np.array(points)

            points = points.reshape((7,7,2))



            res1 = np.sqrt(np.sum(np.power(np.diff(points, axis=0), 2),axis=2)).flatten()

            res2 = np.sqrt(np.sum(np.power(np.diff(points, axis=1), 2),axis=2)).flatten()

            resolution = np.mean([res1, res2])

            calibration = CALTARGET / resolution



            with file("calibration.dat", "w") as cf:

                cf.write("%f" % calibration)



            print "CALIBRATION COMPLETED", calibration

        else:

            print "CALIBRATION FAILED"







    imgqueue.append((timestamp, image))



cap.release()

cv2.destroyAllWindows()

cancel_repeat()

outfile.close()

