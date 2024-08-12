import RPi.GPIO as GPIO
import pigpio
import time
import paho.mqtt.client as mqtt

msg = "1111"
def on_message(client,userdata,message):
    
    global msg
    msg = message.payload.decode("utf-8")
    #print (msg)

broker = "192.168.1.10"			#IP address of cam tower. Default is 192.168.1.10
client = mqtt.Client("local_sav_pi")		#Name of your local client (can be anything)
client.on_message = on_message
client.connect(broker)
client.subscribe("MT280/Group8")		#Keep topic same as in camera tower publisher
client.loop_start()				#Use loop_start() if you are subscribing in a while loop and loop_stop() after you exit the while loop/program
						#(loop_stop not mandatory though!)


try:
    #Declaring a bunch of variables we might want or need
    #The line follow sensors
    FLSen = 1
    FRSen = 1
    RSen = 1
    MRSen = 1
    MLSen = 1
    LSen = 1
    
    #The range sensor
    RangeSen = 0

    #GRAB THIS STUFF



    #PID Stuff
    sensorReadings = [0,0,1,1,0,0]
    setPoint = 25
    lastError = 0
    error = 0
    errorSum = 0
    Kp = 1
    Ki = 0.002
    Kd = 0.01
    baseMotorSpeed = 93
    position = 25
    
    #timer stuff
    lastRunTime = 0




    #DOWN TO HERE
    
    #The Motors
    motorRPHASE = 6
    motorRENABLE = 13
    motorLPHASE = 26
    motorLENABLE = 19
    forward = 1
    reverse = 0
    rightTurnLMSpeed = 76
    rightTurnRMSpeed = 115
    leftTurnLMSpeed = 115
    leftTurnRMSpeed = 76
    turnLMSpeed = leftTurnLMSpeed #default to left turn
    turnRMSpeed = leftTurnRMSpeed #default to left turn
    
    #servo stuff
    mainServoPin = 18 #whatever main servo pin is
    scoopServoPin = 12
    
    
    #The colours
    WHITE = 1
    BLACK = 0
        
    #A variable to tell the state how much energy to do the action with
    level = 1
    
    #Flags that can trip
    runFlag = 1
    pickFlag = 0
    dropFlag = 0
    firstYFlag = 0
    secondYFlag = 0
    forkTimer = 0
    
    #The states
    CONTINUE = 1
    FORK = 10
    STOP = 000
    VEER_R = 100
    VEER_L = 101
    PICKUP = 110
    DROPOFF = 111
    
    #The current state we are actually in
    currentState = CONTINUE
    
    #Get the directions from the camera code
    directions = "1111"    
    
    #Set up the GPIOs
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    pi = pigpio.pi()
    
    #Sets up the control pin for all Reflectance Sensors
    CTRLPIN = 11
    GPIO.setup(CTRLPIN, GPIO.OUT)
    GPIO.output(CTRLPIN, GPIO.HIGH)
    
    #setting Driver mode to PHASE/ENABLE
    GPIO.setup(21, GPIO.OUT)
    GPIO.output(21, GPIO.HIGH)
        
        #Functions
    def irsensor(IRPINS): #function to get value from IR sensor, takes the GPIO pin that the sensor OUT is connected to
        readings = [0,0,0,0,0,0]
        index = 0
        
        for IRPIN in IRPINS:
            GPIO.setup(IRPIN, GPIO.OUT) #Set the pin to an output
            GPIO.output(IRPIN, GPIO.HIGH) #turn on the power 3v to the sensor
            
        time.sleep(0.01) #charge the tiny capacitor on the sensor for 0.1sec
        for IRPIN in IRPINS:
            
            pulse_start = time.time() #start the stopwatch
            GPIO.setup(IRPIN, GPIO.IN) # set pin to input
            while GPIO.input(IRPIN)> 0:
                pass #wait while the capacitor discharges to zero
        
            pulse_end = time.time() #when it hits zero stop the stopwatch
            pulse_duration = pulse_end - pulse_start
            #print(pulse_duration)
            #print ("duration:", pulse_duration) #print the time so you can adjust sensitivity for debugging
            if pulse_duration > 0.0005: #adjust this value to change the sensitivity
                colour_seen = 0 #Black
            else:
                colour_seen = 1 #White
            readings[index] = colour_seen
            index = index + 1
            
        
        return readings
    
    def rngsensor(RNGPIN):
        
        GPIO.setup(RNGPIN, GPIO.IN) #Sets the pin to be input
        if(GPIO.input(RNGPIN)>0):
            return 0 #There is no object
        else:
            return 1 #There is an object
        
    #function that takes the pwm pin and phase pin of a motor, and the desired speed in duty cycle. Speed can be 0 - 255
    def drive(motorPHASE, motorENABLE, direction, speed):
        GPIO.setup(motorENABLE, GPIO.OUT)
        if(direction == 0):
            GPIO.output(motorENABLE, GPIO.LOW)
        else:
            GPIO.output(motorENABLE, GPIO.HIGH)
    
        pi.set_PWM_dutycycle(motorPHASE, speed)
        #print("set pwm")
    
    def Open():
        pi.set_servo_pulsewidth(scoopServoPin, 1050) #open it

        time.sleep(0.5)
        pi.set_servo_pulsewidth(scoopServoPin, 0) #stop it

    def Close():
        pi.set_servo_pulsewidth(scoopServoPin, 750) #close it
        time.sleep(0.7)
        pi.set_servo_pulsewidth(scoopServoPin, 0) #stop it

    def scoopRight():
        for i in range(1425,550, -1):
            pi.set_servo_pulsewidth(mainServoPin, i) #move all the way right
            time.sleep(0.001)
            
        pi.set_servo_pulsewidth(mainServoPin, 0) #stop it

    def scoopLeft():
        for i in range(1425,2350):
            pi.set_servo_pulsewidth(mainServoPin, i) #move all the way left
            time.sleep(0.001)
        
        pi.set_servo_pulsewidth(mainServoPin, 0) #stop it

    def scoopMiddle():
        pi.set_servo_pulsewidth(mainServoPin, 1425)
        time.sleep(0.05)
            
        pi.set_servo_pulsewidth(mainServoPin, 0) #stop it
        
    def scoopForkL():
        for i in range(1425,1700):
            pi.set_servo_pulsewidth(mainServoPin, i) #move all the way right
            time.sleep(0.001)
            
        pi.set_servo_pulsewidth(mainServoPin, 0) #stop it
        
    def scoopForkR():
        for i in range(1425,1100, -1):
            pi.set_servo_pulsewidth(mainServoPin, i) #move all the way right
            time.sleep(0.001)
            
        pi.set_servo_pulsewidth(mainServoPin, 0) #stop it
    
    
    scoopMiddle()
    time.sleep(0.5)
    Close()
    lapStart = time.time()
    directions = msg
    
    while(runFlag):
        
        runtime = time.time()
        #Update all sensors
        sensor_pin_array = [4,27,22,10,9,5]
        sensorReadings = irsensor(sensor_pin_array)
        '''
        MLSen = irsensor(22)
        MRSen = irsensor(10)
        RSen = irsensor(9)
        LSen = irsensor(27)
        FRSen = irsensor(4)
        FLSen = irsensor(5) #does not work? wrong pin?
        '''
        
        #GRAB THIS STUFF

        FLSen = sensorReadings[0] 
        LSen = sensorReadings[1] 
        MLSen = sensorReadings[2] 
        MRSen = sensorReadings[3] 
        RSen = sensorReadings[4] 
        FRSen = sensorReadings[5] 
        
        #DOWN TO HERE





        rsOldRead = RangeSen
        RangeSen = rngsensor(2)#15
        
        
        
        #print(FLSen, "FL")
        #print(FRSen, "FR")
        #print(RSen, "R")
        #print(MRSen, "MR")
        #print(MLSen, "ML")
        #print(LSen, "L")
        print(sensorReadings)
       #print(RangeSen)
        #rest servo position
       
      
        
        
        
            
        #If we get to the end
        if(RangeSen == 1 and firstYFlag == 1 and secondYFlag == 1 and dropFlag == 1): 	#check if we are at a white line across both sensors, and if we have passed both Ys
            time.sleep(0.6)
            currentState = STOP
            break
        
        
                
        
        
        #Check if we are off track
        elif(FLSen == WHITE and FRSen == WHITE and RSen == WHITE and LSen == WHITE and MRSen == WHITE and MLSen == WHITE):
            
            if(forkTimer > 3):
                currentState = STOP #if we have been on white for awhile now, then stop
            else:
                
                #currentState = FORK #If this is the first detection of being off track, or potentially Y join, then start a timer and act as if it is a fork
                if(secondYFlag == 0 and firstYFlag == 1): #if we are exiting the first fork
                    if(directions[0] == '1'): #if we are turning right
                        turnLMSpeed = rightTurnLMSpeed
                        turnRMSpeed = rightTurnRMSpeed
                    else: #we must be turning left
                        turnLMSpeed = leftTurnLMSpeed
                        turnRMSpeed = leftTurnRMSpeed
                    
                else: #else we must be exiting the second Y
                    if(directions[2] == '1'): #if we are turning right
                        turnLMSpeed = rightTurnLMSpeed
                        turnRMSpeed = rightTurnRMSpeed
                    else: #we must be turning left
                        turnLMSpeed = leftTurnLMSpeed
                        turnRMSpeed = leftTurnRMSpeed
                    
                
                drive(motorLPHASE, motorLENABLE, forward, turnLMSpeed)
                drive(motorRPHASE, motorRENABLE, forward, turnRMSpeed)
                time.sleep(0.3)
                scoopMiddle()
                #time.sleep(1)
                
                forkTimer = forkTimer + 1
        
        
        
        #GRAB THIS STUFF
        #Checking if we are at a fork
        elif((FLSen == BLACK and FRSen == BLACK and RSen ==  WHITE and LSen ==  WHITE and MRSen ==  WHITE and MLSen ==  WHITE) or (FLSen == BLACK and FRSen == WHITE and RSen ==  WHITE and LSen ==  WHITE and MRSen ==  WHITE and MLSen ==  WHITE and error<0) or(FLSen == WHITE and FRSen == BLACK and RSen ==  WHITE and LSen ==  WHITE and MRSen ==  WHITE and MLSen ==  WHITE and error > 0)):
            #continue
            
            print("we are at a FORK!!!")
            if(firstYFlag == 0): #if we are at the first Y
                if(directions[0] == '1'): #if we are turning right
                    turnLMSpeed = rightTurnLMSpeed
                    turnRMSpeed = rightTurnRMSpeed
                    print("Turning right at the fist fork")
                    scoopForkL()
                else: #we must be turning left
                    turnLMSpeed = leftTurnLMSpeed
                    turnRMSpeed = leftTurnRMSpeed
                    print("Turning left at the first fork")
                    scoopForkR()
                firstYFlag = 1
                    
                    
            elif(firstYFlag == 1 and secondYFlag == 0): #else we must be at the second Y
                if(directions[2] == '1'): #if we are turning right
                    turnLMSpeed = rightTurnLMSpeed 
                    turnRMSpeed = rightTurnRMSpeed 
                    print("Turning right at the second fork")
                    scoopForkL()
                else: #we must be turning left
                    turnLMSpeed = leftTurnLMSpeed
                    turnRMSpeed = leftTurnRMSpeed
                    print("turning left at the seond fork")
                    scoopForkR()
                secondYFlag = 1
                
            drive(motorLPHASE, motorLENABLE, forward, turnLMSpeed)
            drive(motorRPHASE, motorRENABLE, forward, turnRMSpeed)
            time.sleep(0.2)
        
        elif(FLSen == BLACK and FRSen == BLACK and RSen ==  BLACK and LSen ==  BLACK and MRSen ==  BLACK and MLSen ==  BLACK):
            #continue
            pass
        
        
        else:
            #If none of these, then go to drive state
            #print("Drive State")
            currentState = CONTINUE
            #resetting the off course flag
            forkTimer = 0
            #Driving
            #PID, well PD
            #Weighted sum gives us the right error readings for a binary array
            weightedSum = 1000 * int(sum(sensorReadings[i] * i for i in range(len(sensorReadings))))
            #position is where we are over the line, 2.5 for middle, 0 for too far right, 3 for too far left
            position = int(weightedSum / (100 * sum(sensorReadings)))
            #error is the difference between where we are and where we should be
            error = int(setPoint - position)
            #print("position", position)
            #print(error,"error")

            #Calculating the motor speeds from this
            #actual PD stuff
            motorSpeed = int((Kp * error) + (Kd * (error - lastError)) + (Ki * errorSum))
            #updating last error
            lastError = error
            errorSum = errorSum + error
            #minus because too far right = error of 1.5, means motorSpeed of 7.5, and PWM currently works as smaller numbers = faster, so speed up right motor
            rightMotorSpeed = int(baseMotorSpeed - motorSpeed)
            leftMotorSpeed = int(baseMotorSpeed + motorSpeed)
            #print(rightMotorSpeed - leftMotorSpeed, "motordiff")
            #print(leftMotorSpeed, "left motor")
            #print(rightMotorSpeed, "right motor")
            
            #update motor speeds here using that function.
            drive(motorLPHASE, motorLENABLE, forward, leftMotorSpeed)
            drive(motorRPHASE, motorRENABLE, forward, rightMotorSpeed)


        #DOWN TO HERE
  
        
        
    
        
    
    
    
        #If we get to the a dropoff/pickup zone
        if(RangeSen == 1):
            #We must be at a zone, so check which one
            #is it pickup?
            
            directions = msg
            if(pickFlag == 0 and dropFlag == 0 and firstYFlag == 1):
                #We must be at the pickup zone
                #Turn servo etc
                #Determining to pick up left or right
                zone = directions[1]
                pickFlag = 1
                #stop the SAV
                drive(motorLPHASE, motorLENABLE, forward, 125)
                drive(motorRPHASE, motorRENABLE, forward, 125)
                '''
                #ROLLBACK
                drive(motorLPHASE, motorLENABLE, forward, 160)
                drive(motorRPHASE, motorRENABLE, forward, 160)
                time.sleep(0.2)
                drive(motorLPHASE, motorLENABLE, forward, 125)
                drive(motorRPHASE, motorRENABLE, forward, 125)
                '''
                
                scoopMiddle()
                #pick up on right
                if(zone == '1'):
                    print("Trying to pick up on right")
                    time.sleep(0.5)
                    Open()
                    time.sleep(0.5)
                    scoopRight()
                    time.sleep(0.5)
                    Close()
                    time.sleep(0.5)
                    scoopMiddle()
                    
                #pick up on left
                else:
                    print("Trying to pick up on the left")
                    time.sleep(0.5)
                    Open()
                    time.sleep(0.5)
                    scoopLeft()
                    time.sleep(0.5)
                    Open()
                    time.sleep(0.5)
                    Close()
                    time.sleep(0.5)
                    scoopMiddle()
                #Turn servo etc
            
                #Drive forward a lil so that we are out of the pickup/dropoff zone
                
                #start the SAV again
                drive(motorLPHASE, motorLENABLE, forward, baseMotorSpeed)
                drive(motorRPHASE, motorRENABLE, forward, baseMotorSpeed)
                time.sleep(0.5)

            #must be at dropoff
            elif(pickFlag == 1 and dropFlag == 0 and secondYFlag == 1):
                #Determining to pick up left or right
                zone = directions[3]
                dropFlag = 1
                #dropoff on right
                scoopMiddle()
                #stop the SAV
                drive(motorLPHASE, motorLENABLE, forward, 125)
                drive(motorRPHASE, motorRENABLE, forward, 125)
                #Rollback
                drive(motorLPHASE, motorLENABLE, forward, 160)
                drive(motorRPHASE, motorRENABLE, forward, 160)
                time.sleep(0.15)
                drive(motorLPHASE, motorLENABLE, forward, 125)
                drive(motorRPHASE, motorRENABLE, forward, 125)
                if(zone == '1'):
                    print("Trying to drop off on right")
                    time.sleep(0.5)
                    scoopRight()
                    time.sleep(0.5)
                    Open()
                    time.sleep(0.2)
                    
                    
                    
            
                #dropoff on left
                else:
                    print("Trying to drop off on the left")
                    time.sleep(0.5)
                    scoopLeft()
                    time.sleep(0.5)
                    Open()
                    
            
                #Turn servo etc
                drive(motorLPHASE, motorLENABLE, forward, baseMotorSpeed)
                drive(motorRPHASE, motorRENABLE, forward, baseMotorSpeed)
                time.sleep(0.4)
                
                
                
                
                
                #check for camera tower
                
                        

                    
                    
                
            
        #else we have picked up and dropped off, so just continue
        #time.sleep(0.2)#for testing
        
        
            
            

    
    
    
        #States
                
    
        
    
        #STOP STATE
        elif(currentState == STOP):
            #Stop both motors
            GPIO.setup(26, GPIO.OUT)
            GPIO.output(26, GPIO.LOW)
            GPIO.setup(6, GPIO.OUT)
            GPIO.output(6, GPIO.LOW)
            #drive(motorLPHASE, motorLENABLE, forward, 0)
            #drive(motorRPHASE, motorRENABLE, forward, 0)
            
            print("STOPPING")
            break
            
    

            
            
    
                    
            
            
        #end of program loop
        #print(currentState)
        runTimeTotal = int((time.time()-runtime) * 1000)
        avgRT = int((runTimeTotal + lastRunTime)/2)
        lastRunTime = runTimeTotal
        lapTime = int((time.time() - lapStart))
        
        
        #print(runtime)
    print("program finished")
    drive(motorRPHASE, motorRENABLE, forward, 0)
    drive(motorLPHASE, motorLENABLE, forward, 0)
    GPIO.setup(26, GPIO.OUT)
    GPIO.output(26, GPIO.LOW)
    GPIO.setup(6, GPIO.OUT)
    GPIO.output(6, GPIO.LOW)
    
    
except KeyboardInterrupt:
    print("Keyboard Interrupt - END")
    
except:
    print("Other Exception Occured")

finally:	
    
    drive(motorRPHASE, motorRENABLE, forward, 0)
    drive(motorLPHASE, motorLENABLE, forward, 0)
    pi.set_servo_pulsewidth(scoopServoPin, 0) #stop it
    pi.set_servo_pulsewidth(mainServoPin, 0) #stop it
    GPIO.cleanup() #always good practice to clean-up the GPIO settings at the end
    pi.stop()
    client.loop_stop()
    print("The Average Cycle was ", avgRT, "ms")
    print("The lap time was ", lapTime, "s")
    print("Integral contributed ", (Ki * errorSum), " to the motorSpeed")
    print(directions, " were the directions given")

        
        
    
    
        
        
    
    
    
    
