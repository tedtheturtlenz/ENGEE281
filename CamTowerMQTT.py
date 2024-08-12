import cv2 as cv
import sys
import numpy as np
import paho.mqtt.client as paho
#Need to implement a try catch for the print statement at the end
broker="192.168.1.10"					#IP  address should be that of camera tower - default should be 192.168.1.10
port=1883						#Keep this exact port as its defined in mqtt broker configuraion file

def on_publish(client,userdata,result):
	pass
	
	
client1= paho.Client("toSAV")				#Client name can be any name
client1.on_publish = on_publish
client1.connect(broker,port)
transmitMessage = "1111"
oldOldTransmitMessage = "1010"
foundAll = 0



#Predefined Variables
#hue, saturation and variance values as a basis
hueLower = 0
hueUpper = 2
satUpper = 255
satLower = 40	
varUpper = 255
varLower = 30

#The offsets that get changed by the sliders
hueOffset = 0
satOffset = 0
valOffset = 0


#The rough hue values of the colours
green = 58
blue = 112
red = 0
yellow = 19
largeRed = 170

redflag = 0 #flag to tell whether or not we are dealing with red
	

#Limits of the colours
redLLim = np.array([red,50,70])
redULim = np.array([red + 10,255,255])

BIGredLLim = np.array([largeRed - 15,50,70])
BIGredULim = np.array([largeRed + 10,255,255])

yellowLLim = np.array([yellow-4,80,30])
yellowULim = np.array([yellow+4,255,255])

blueLLim = np.array([blue-7,80,30])
blueULim = np.array([blue + 7,255,255])

greenLLim = np.array([green - 13,80,30])
greenULim = np.array([green + 13,255,255])

lowerLim = redLLim
upperLim = redULim


#The two arrays for dropoff and pickup
dropoffIndex = np.array([0])
pickupIndex = np.array([0])

#The sliders and slider functions
cv.namedWindow('Track', cv.WINDOW_NORMAL)




def hue_change(value):
	global hueOffset
	hueOffset = value
	
def sat_change(value):
	global satOffset
	satOffset = value


def val_change(value):
	global valOffset
	valOffset = value



cv.createTrackbar('hue', 'Track', 0, 10, hue_change)
cv.setTrackbarMin('hue', 'Track', -10)
cv.createTrackbar('sat', 'Track', 0, 80, sat_change)
cv.setTrackbarMin('sat', 'Track', -80)
cv.createTrackbar('val', 'Track', 0, 80, val_change)
cv.setTrackbarMin('val', 'Track', -80)










cap = cv.VideoCapture(0)




while(1):
	
	#Get a frame from the camera
	_, img = cap.read()
 
 	#Temporary fix
	#img = cv.imread("img1.jpg")
 
	#Converting BGR to HSV
	hsvImage = cv.cvtColor(img, cv.COLOR_BGR2HSV)

	
	
	
	#cropping the image
	croppedHSVImg = hsvImage[280:480, 0:640]
	croppedBGRImg = img[280:480, 0:640]
	
			
	
	cv.imshow('image', img)


	#x coords of dropoff and pickup zones
	pickupZone = 0
	dropoffZone = 0
	
	
	#The two centroids of the bounding rectangles [x1,x2]
	centroids = np.array([0,0], dtype= np.int32)
	#all the centroids of the zones
	allCentroids = np.array([0,0,0,0,0,0,0,0],dtype = np.int32)

	
	#now updating all the limits with the added offsets from the trackbars
	#Limits of the colours            
	redLLim = np.array([red,50 + satOffset,70 + valOffset])
	redULim = np.array([red + 10 + hueOffset,255,255])
	
	BIGredLLim = np.array([largeRed - 15 + hueOffset,50 + satOffset,70 + valOffset])
	BIGredULim = np.array([largeRed + 10,255,255])
	
	yellowLLim = np.array([yellow-4 + hueOffset,80 + satOffset,30 + valOffset])
	yellowULim = np.array([yellow+4 + hueOffset,255,255])
	
	blueLLim = np.array([blue-7 + hueOffset,80 + satOffset,30 + valOffset])
	blueULim = np.array([blue + 7 + hueOffset,255,255])
	
	greenLLim = np.array([green - 13 + hueOffset,80+ satOffset,30 + valOffset])
	greenULim = np.array([green + 13 + hueOffset,255,255])
	



	

	
	#Now getting all the zone masks
	
	smallRedMask = cv.inRange(croppedHSVImg, redLLim, redULim)
	bigRedMask = cv.inRange(croppedHSVImg, BIGredLLim,BIGredULim)
	greenMask = cv.inRange(croppedHSVImg, greenLLim, greenULim)
	yellowMask = cv.inRange(croppedHSVImg, yellowLLim, yellowULim)
	blueMask = cv.inRange(croppedHSVImg, blueLLim, blueULim)
	allRedMasks = bigRedMask | smallRedMask
	allMasks = [allRedMasks,greenMask,yellowMask,blueMask]
	
	
	

	
	
	
	
	#Now Thresholding the HSV image
	
	#index for storing centroid data
	index = 0
	#making a copy of the cropped BGR image to draw on
	croppedTempImg = croppedBGRImg.copy()
	zonesMask = smallRedMask | bigRedMask | greenMask | yellowMask | blueMask
	cleanZonesMask = bigRedMask
	for m in allMasks:
		#Now cleaning up the mask
		element = cv.getStructuringElement(cv.MORPH_RECT,(7,7),(3,3))
		
		#first erode away to get rid of noise
		cleanM = cv.erode(m,element)
		
		#then dilate to bring back size
		cleanM = cv.dilate(cleanM,element)
		
	
		#Now mask the original image using this mask
		zonesImg = cv.bitwise_and(croppedHSVImg, croppedHSVImg, mask = cleanM)
		
		#for viewing only
		cleanZonesMask = cleanZonesMask | cleanM
		
		#now finding the contours of all the zones
		contours, hierarchy = cv.findContours(cleanM, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)
		
		#and making that into a rectangle outline
		
		for cnt in contours:
			x, y, w, h = cv.boundingRect(cnt)
			if (w > 20 and h > 30 and index < 8 and w < 70 and h < 80 and (h-w) > -10 ):
				cv.rectangle(croppedTempImg, (x, y), (x + w, y + h), (255, 255, 255), 2)
		
				#getting the centroids
				
				allCentroids[index] = ((w/2) + x)
				index = index + 1


	
	#sorting and flipping the array of centroids so that it is from the perspective of the SAV
	#Then trimming any zeros (which means that the dropoff zones are not out yet)
	allCentroids = np.sort(allCentroids)
	allCentroids = np.flip(allCentroids)
	allCentroids = np.trim_zeros(allCentroids)
	print(allCentroids)
	
	
	
	
	
	
	
	#Finding the right coloured zones
	
	#Now Thresholding the HSV image
	mask = cv.inRange(croppedHSVImg, lowerLim, upperLim)
	
	
	
	#special case for red
	if redflag == 1:
	
		print("its red")
		#now or the masks together
		mask = (cv.inRange(croppedHSVImg, redLLim, redULim)) | (cv.inRange(croppedHSVImg, BIGredLLim,BIGredULim))
		
		
		
	#Now cleaning up the mask
	
	#First erode away the noise
	element = cv.getStructuringElement(cv.MORPH_RECT,(7,7),(3,3))
	
	cleanMask = cv.erode(mask,element)
	
	
	#then dilate again to get the size back
	cleanMask = cv.dilate(cleanMask,element)
	cv.imshow("cleanMask",cleanMask)
	
	
	
	#Now mask the original image using this mask, just for viewing
	#res = cv.bitwise_and(zonesImg, zonesImg, mask = mask)
	
	print(redflag)
	
	#now finding the contours to use
	contours, hierarchy = cv.findContours(cleanMask, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)
	
	#and making that into a rectangle outline
	#index for storing centroid data
	index = 0
	for cnt in contours:
		x, y, w, h = cv.boundingRect(cnt)
		if (w > 20 and h > 30 and index < 2 and w < 70 and h < 80 and (h-w) > -10 ):
			cv.rectangle(croppedTempImg, (x, y), (x + w, y + h), (255, 130, 255), 2)
		
			#getting the centroids
			centroids[index] = ((w/2) + x)
			index = index + 1
			
	
	#Calculating what turns to make
	
	#first sort the centroids so that they are in the right order
	centroids = np.sort(centroids)
	
	#The two centroids of the zones
	#if the drop off zones have been put out, there will be two centroids
	try:
		if(len(allCentroids) > 7):
			#because it is sorted, the larger x will be first, and will be the pickup zone
			cen1 = centroids[0]
			cen2 = centroids[1]
			try:
			#working out the pick up and drop off zones
				dropoffIndex = np.where(((allCentroids > (cen1-4)) & (allCentroids < (cen1 + 4))))
				pickupIndex = np.where(((allCentroids > (cen2-4)) & (allCentroids < (cen2 + 4))))
				print("The zones are ")
				print(pickupIndex[0])
				print(dropoffIndex[0])
		
		
        		#Formatting the strings correctly so that they make sense to the SAV
				transmitStringA = '{0:02b}'.format(pickupIndex[0][0])
				transmitStringB = '{0:02b}'.format(dropoffIndex[0][0]-4)
        		#inverting transmitB
				inverseB = ''
				for b in transmitStringB:
					if b == '0':
						inverseB += '1'
					else:
						inverseB += '0'
				transmitStringB = inverseB
				
				oldTransmitMessage = transmitMessage
				transmitMessage = transmitStringA + transmitStringB
				print('The directions')
				print(transmitMessage)
				if(transmitMessage == oldTransmitMessage):
					
					client1.publish("MT280/Group8",transmitMessage)	#Keep topic as MT280/GroupX where X is your team number
				
				
			except:
				print("failed")
         	
	
		#if there is only the pickup zones, just send that
		else:
			cen2 = centroids[1]
			pickupIndex = np.where(((allCentroids > (cen2-4)) & (allCentroids < (cen2 + 4))))
			print("dropoff zones have not been put out yet")
			transmitStringA = '{0:02b}'.format(pickupIndex[0][0])
			print(transmitStringA)
			
			oldTransmitMessage = transmitMessage
			transmitMessage = transmitStringA + "00"
			if(transmitMessage == oldTransmitMessage):
				
				client1.publish("MT280/Group8",transmitMessage)	#Keep topic as MT280/GroupX where X is your team number
				
	except:
		print("failed to find zones")	
	
	
	#showing the images
	cv.imshow('mask',mask)
	cv.imshow('zonesMask',zonesMask)
	#cv.imshow('croppedHSVImg',croppedHSVImg)
	#cv.imshow('ZonesMasked', zonesImg)
	cv.imshow('frame',croppedTempImg)
	#cv.imshow("Original Image", img)
	cv.imshow("cleanZoneMask",cleanZonesMask)
	
	
	col = cv.waitKey(25)
	if col == ord('x'):
		break
	if col == ord('g'):
		lowerLim = greenLLim
		upperLim = greenULim
		#now reset redflag
		redflag = 0
		print('You have chosen Green')
		
	if col == ord('y'):
		lowerLim = yellowLLim
		upperLim = yellowULim
		#now reset redflag
		redflag = 0
		print('You have chosen Yellow')
	
	if col == ord('b'):
		lowerLim = blueLLim
		upperLim = blueULim
		#now reset redflag
		redflag = 0
		print('You have chosen Blue')

	if col == ord('r'):
		lowerLim = redLLim
		upperLim = redULim
		REDlowerLim = BIGredLLim
		REDupperLim = BIGredULim
		redflag = 1
		print('You have chosen Red')
	
	
	
cv.destroyAllWindows()
	






