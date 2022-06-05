#-----------------------------------------------------
# Sony Spresense Functional Test Application
# Primary Software Tool: PySimpleGUI
# Created on Sat Apr 16 19:22:18 2022
# @author: DogZapper50
# Tested ok using Python 3.7.10 and PySimpleGUI 4.55.1
#-----------------------------------------------------
import threading
#from tkinter import *
from PIL import Image, ImageTk
import PySimpleGUI as sg
import serial
import winsound
import time
import serial.tools.list_ports

#import numpy as np
#import io

my_UI_image_frame_size = (500, 400)


#-------------------------------------------------
# Routine to reload image file/viewer
#-------------------------------------------------
def my_update_image(image_file, resize):
    # User interface screen fixed to 500 x 400
    # This routine will resize the image if you ask
    im = Image.open(image_file, formats=None)
    if resize == True:
        im = im.resize(my_UI_image_frame_size, resample=Image.BICUBIC)
    return im

        
#-------------------------------------------------
# Generic Spresense command handler
#-------------------------------------------------
def send_Spresense_command(command,response_lines,print_mode):
    global spresense_command_response_data
    
    spresense_command_response_data = ""

    ser.write((command).encode())  
    for x in range(response_lines):
        new_response = ser.readline().decode('ascii')
        spresense_command_response_data = spresense_command_response_data + new_response
        if(print_mode == 'enabled' ):
            print(new_response,end='')
        
    
#-------------------------------------------------
# set Spresense into streaming mode
#-------------------------------------------------
def camera_steaming_mode(window,):
    send_Spresense_command('cam_stream_start\n',5,'enabled')
    
    while streaming_active:
        start=time.time()                                                #start time for FPS calculation
        image_size = int(ser.readline())                                 #get the size (in bytes) of the image
        print(image_size)
        if(image_size == 0):
            print('jpeg buffer overflow')
        if(image_size > 0):
            spresense_camera_data = ser.read(size = image_size)              #reads bytes from Spresense
            image_tk = ImageTk.PhotoImage(data = spresense_camera_data)      #read raw array data and creates an imgtk
            im_PIL = ImageTk.getimage(image_tk)                              #convert it to PIL image so we can resize it
            resized_PIL = im_PIL.resize(my_UI_image_frame_size)              #resize it to fit the fixed UI image size of 500 x 400
            image = ImageTk.PhotoImage(image=resized_PIL)                    #convert it back to TK_image
    
            if(event == '-STOP_STREAMING-'):                                 # tell PC to stop streaming first!
                break
            if event == sg.WIN_CLOSED:                                       # if user closes application during streaming
                break
            window['-IMAGE-'].update(data=image)
            endt=time.time()
    
            fpsec = 1.0/(endt-start)
            window['-FPS-'].update('%.3f' % fpsec)

    send_Spresense_command('cam_stream_stop\n',0,'silent')         # tell the Spresense to stop streaming 2nd
    ser.read_all()                                                  # use this to flush the PC comm port buffer
    window.write_event_value('-THREAD_MESSAGE-','*** STREAM_ENDED ***')     # put a message into queue for GUI
    f = open('my_streaming.jpg','wb')                               #save this last frame into jpg streaming file
    f.write(spresense_camera_data)
    f.close()
    
#-------------------------------------------------
# Spresense still camera shot routine
#-------------------------------------------------
def take_a_still_snap_shot():
    
    winsound.PlaySound('camera.wav', winsound.SND_FILENAME)
    ser.write(("+\n").encode())                                      #Tells Spresense to take a still image, snap shot
    start=time.time()                                                #start time for FPS calculation
    image_size = int(ser.readline())                                 #get the size (in bytes) of the image
    print('image_size:',image_size)
    spresense_camera_data = ser.read(size = image_size)              #reads bytes from Spresense
    image_tk = ImageTk.PhotoImage(data = spresense_camera_data)      #read raw array data and creates an imgtk
    im_PIL = ImageTk.getimage(image_tk)                              #convert it to PIL image so we can resize it
    resized_PIL = im_PIL.resize(my_UI_image_frame_size)              #resize it to fit the fixed UI image size of 500 x 400
    image = ImageTk.PhotoImage(image=resized_PIL)                    #convert it back to TK_image

    f = open('my_snap_shot.jpg','wb')                                #save this frame into jpg file
    f.write(spresense_camera_data)
    f.close()
    window['-IMAGE-'].update(data=image)
    
    endt=time.time()
    fpsec = 1.0/(endt-start)
    window['-FPS-'].update('%.3f' % fpsec)
    
#-------------------------------------------------
# Python GUI EXIT ROUTINE
#-------------------------------------------------
def exit_routine():

    print('*** Exit ***')
    if found_it == True:    #only do this is serial port was found
        ser.close()
        
    window.close()
    
#---------------------------------------------------
# System parameter from Spresense
# use command P-
# Pulls current parameter values from Spresense.ini
# and sends them to Spresense hardware
#---------------------------------------------------
def parameter_from_spresense():
    ser.write(("P-\n").encode())                   #Get Spresense Parameters
    for x in range(21):
        print(ser.readline().decode('ascii'),end='')


#-------------------------------------------------
# get_camera_settings Spresense command routine
#-------------------------------------------------
def get_camera_settings():
    send_Spresense_command('cam_info\n',12,'enabled')
    print()
    
    #Get Streaming Width
    width = spresense_command_response_data.splitlines()[1]
    width_num = width.split(':')[1]
    #print('Streaming Width:',width_num)      
    if width_num == '320':    
        window['-STREAM_WIDTH-'].update(value = 'QVGA_320')
    
    #Get Streaming Height
    height = spresense_command_response_data.splitlines()[2]
    height_num = height.split(':')[1]      
    if height_num == '240':
        window['-STREAM_HEIGHT-'].update(value = 'QVGA_240')
        
    #Get JPEG Size Divider
    jpeg_size_div = spresense_command_response_data.splitlines()[5]
    jpeg_size_div = jpeg_size_div.split(':')[1]    
    window['-STREAMING_JPEG_VID-'].update(value = jpeg_size_div)
        
    #Get JPEG Buffer Size
    jpeg_buffer_size = spresense_command_response_data.splitlines()[10]
    jpeg_buffer_size = jpeg_buffer_size.split(':')[1]
    print('jpeg_buffer_size:',jpeg_buffer_size)      
    window['-STREAMING_JPEG_BUFF_SIZE-'].update(value = str(jpeg_buffer_size)+' bytes')
    
#-------------------------------------------------------------------------------
# Get system parameters from file named to "Spresense.ini". This INI file should 
# be located in the same directory as this file "SpresenseApp.py"
# Write these parameters to Spresense and update the user interface selections
# Uses the command "P+" to Spresense.
# See Spresense.ini file for current settings
#-------------------------------------------------------------------------------
def parameter_to_spresense():
    f = open("Spresense.ini", "r")  #read in the ini file
    ini_file_data = f.read()
    start = [17,18,22,29,19,18,20,13,14,20,25,16,15,14,12,14,20,20,22,20]
    #Tells Spresense the ini parameter data is coming next
    ser.write(("P+\n").encode())   
    for x in range(1):
        print(ser.readline().decode('ascii'),end='')   
        time.sleep(1)                                
    for line in range(len(start)):
        pram = ini_file_data.splitlines()[line]
        pram = pram[start[line]:]
        update_the_user_interface(line+1,pram)      #update the UI for every parameter sent to Spresence
        print(pram)
        ser.write((pram + "\n").encode())           #Send the parameter to spresense
        
def update_the_user_interface(line_num,ini_pram):
    #Line 1: streaming_width:
    #['QQVGA_160','QVGA_320','VGA_640','HD_1280','QUADVGA_1280','FULLHD_1920','3MP_2048','5MP_2560'],
    #establish a default condition
    UI_field = '-STREAM_WIDTH-'
    UI_value = 'QQVGA_160'
    if(line_num == 1):
        if(ini_pram == '160'):
            UI_value = 'QQVGA_160'
        elif(ini_pram == '320' ):
            UI_value = 'QVGA_320'
        elif(ini_pram == '640' ):
            UI_value = 'VGA_640'
        elif(ini_pram == '1280' ):
            UI_value = 'HD_1280'
        elif(ini_pram == '1280' ):
            UI_value = 'QUADVGA_1280'
        elif(ini_pram == '1920' ):
            UI_value = 'FULLHD_1920'
        elif(ini_pram == '2048' ):
            UI_value = '3MP_2048'
        elif(ini_pram == '2560' ):
            UI_value = '5MP_2560'
        window[UI_field].update(value = UI_value)               #update the UI field
        return
    
    #Line 2: streaming_height:
    #['QQVGA_120','QVGA_240','VGA_480','HD_720','QUADVGA_960','FULLHD_1080','3MP_1536','5MP_1920']
    #establish a default condition
    UI_field = '-STREAM_HEIGHT-'
    UI_value = 'QQVGA_120'
    if(line_num == 2):
        if(ini_pram == '120'):
            UI_value = 'QQVGA_120'
        elif(ini_pram == '240' ):
            UI_value = 'QVGA_240'
        elif(ini_pram == '480' ):
            UI_value = 'VGA_480'
        elif(ini_pram == '720' ):
            UI_value = 'HD_720'
        elif(ini_pram == '960' ):
            UI_value = 'QUADVGA_960'
        elif(ini_pram == '1080' ):
            UI_value = 'FULLHD_1080'
        elif(ini_pram == '1536' ):
            UI_value = '3MP_1536'
        elif(ini_pram == '1920' ):
            UI_value = '5MP_1920'
        window[UI_field].update(value = UI_value)               #update the UI field
        return
    
    #Line 3: streaming_vid_format:
    #['RGB565','YUV422','JPG','GRAY','NONE']
    #establish a default condition
    UI_field = '-STREAM_PIX_FMT-'
    UI_value = 'JPG'
    if(line_num == 3):
        UI_value = ini_pram
        window[UI_field].update(value = UI_value)               #update the UI field
        return
    
    #Line 4: streaming_JPEG_size_divisor:
    #[' 1',' 2',' 3',' 4',' 5',' 6',' 7',' 9','10','11','12','13','14']
    #establish a default condition
    UI_field = '-STREAMING_JPEG_SIZE_DIV-'
    UI_value = ' 7'
    if(line_num == 4):
        UI_value = ini_pram
        window[UI_field].update(value = UI_value)               #update the UI field
        return
    
    #Line 6: frame_per_second:
    #['STILL','5 FPS','6 FPS','7.5 FPS','15 FPS','30 FPS','60 FPS','120 FPS']
    #establish a default condition
    #-----ALWAYS DEFAULT THIS PARAMETER TO 'STILL' ON APPLICATION STARTUP------
    
    #Line 8: still_image_width:
    #['QQVGA_160','QVGA_320','VGA_640','HD_1280','QUADVGA_1280','FULLHD_1920','3MP_2048','5MP_2560'],
    #establish a default condition
    UI_field = '-STREAM_WIDTH-'
    UI_value = 'QQVGA_160'
    if(line_num == 1):
        if(ini_pram == '160'):
            UI_value = 'QQVGA_160'
        elif(ini_pram == '320' ):
            UI_value = 'QVGA_320'
        elif(ini_pram == '640' ):
            UI_value = 'VGA_640'
        elif(ini_pram == '1280' ):
            UI_value = 'HD_1280'
        elif(ini_pram == '1280' ):
            UI_value = 'QUADVGA_1280'
        elif(ini_pram == '1920' ):
            UI_value = 'FULLHD_1920'
        elif(ini_pram == '2048' ):
            UI_value = '3MP_2048'
        elif(ini_pram == '2560' ):
            UI_value = '5MP_2560'
        window[UI_field].update(value = UI_value)               #update the UI field
        return
    
    #Line 9: still_image_height:
    #['QQVGA_120','QVGA_240','VGA_480','HD_720','QUADVGA_960','FULLHD_1080','3MP_1536','5MP_1920']
    #establish a default condition
    UI_field = '-STREAM_HEIGHT-'
    UI_value = 'QQVGA_120'
    if(line_num == 2):
        if(ini_pram == '120'):
            UI_value = 'QQVGA_120'
        elif(ini_pram == '240' ):
            UI_value = 'QVGA_240'
        elif(ini_pram == '480' ):
            UI_value = 'VGA_480'
        elif(ini_pram == '720' ):
            UI_value = 'HD_720'
        elif(ini_pram == '960' ):
            UI_value = 'QUADVGA_960'
        elif(ini_pram == '1080' ):
            UI_value = 'FULLHD_1080'
        elif(ini_pram == '1536' ):
            UI_value = '3MP_1536'
        elif(ini_pram == '1920' ):
            UI_value = '5MP_1920'
        window[UI_field].update(value = UI_value)               #update the UI field
        return

#-------------------------------------------------
# Start up code and main routine here
#-------------------------------------------------
#---START UP CODE---------------------------------
terminal_line_list = []     #list that holds the terminal window data
im = my_update_image("Spresense_Splash3.JPG",resize=True)
sg.theme('DarkGreen3')
my_bg_color = sg.theme_input_background_color()

#-----UI Define the tabs---------
#TAB 1 - IMAGE RELATED INFORMATION
my_tab1_layout = [
    [sg.Text('Streaming Video Setup:'),sg.Text('        Measured Frames/second:'),
     sg.Text(expand_x=True,justification='center',text_color='black', background_color=my_bg_color, key='-FPS-'),
     sg.Text('FPS')],
    [sg.Text('Width:'),
     sg.Combo(['QQVGA_160','QVGA_320','VGA_640','HD_1280','QUADVGA_1280','FULLHD_1920','3MP_2048','5MP_2560'],
              size=(15,1),default_value='3MP_2048',readonly=True,key='-STREAM_WIDTH-'),
     sg.Text('Height:'),
     sg.Combo(['QQVGA_120','QVGA_240','VGA_480','HD_720','QUADVGA_960','FULLHD_1080','3MP_1536','5MP_1920'],
              size=(14,1),default_value='3MP_1536',readonly=True,key='-STREAM_HEIGHT-'),sg.Text('pixels')],
    [sg.Text('Streaming Video Format:'),
     sg.Combo(['RGB565','YUV422','JPG','GRAY','NONE'],size=(8,1),default_value='JPG',
              readonly=True,key='-STREAM_PIX_FMT-'),
     sg.Text('JPEG Size Divisor:'), sg.Combo([' 1',' 2',' 3',' 4',' 5',' 6',' 7',' 9','10','11','12','13','14'],
              size=(3,1),default_value='7', readonly=True,key='-STREAMING_JPEG_SIZE_DIV-')],
    [sg.Text('JPEG Buffer Size:'), sg.Text('',expand_x=True,justification='center',text_color='black',
              background_color=my_bg_color, key='-STREAMING_JPEG_BUFF_SIZE-'),
     sg.Text('Frames/second:'), sg.Combo(['STILL','5 FPS','6 FPS','7.5 FPS','15 FPS','30 FPS','60 FPS','120 FPS'],size=(8,1),
              default_value='STILL',readonly=True,enable_events=True,key='-PIX_FPS-')],
    [sg.Text('Streaming Filename:'), sg.Input('my_streaming.jpg',size=(24,1),disabled=True,key='-STREAM_FILENAME-')],
    [sg.HorizontalSeparator()],
    [sg.Text('Still Image Setup:')],
    [sg.Text('Width:'),sg.Input(size=(10,1),key='-PIX_WID-'),
     sg.Text('Height:'),sg.Input(size=(10,1),key='-PIX_HEI-'),sg.Text('pixels')],
    [sg.Text('Still Image Format:'),
     sg.Combo(['RGB565','YUV422','JPG','GRAY','NONE'],size=(6,1),default_value='JPG',
              readonly=True,key='-PIX_FMT-')],
    [sg.Text('JPEG Size Divisor:'),
     sg.Combo([' 1',' 2',' 3',' 4',' 5',' 6',' 7',' 9','10','11','12','13','14'],size=(3,1),default_value='7',
              readonly=True,key='-STILL_PIX_FMT-'),
     sg.Text('JPEG Buffer Size:'),
     sg.Text('',expand_x=True,justification='center',text_color='black',background_color=my_bg_color)],
    [sg.Text('Still Image Filename:'), sg.Input('my_snap_shot.jpg', size=(24,1),disabled=True,key='-STILL_FILENAME-'),
     sg.Button('Take still picture',expand_x=True,key='-SNAP-'),],
    [sg.HorizontalSeparator()],
    [sg.Text('Generic Camera Settings:')],
    [sg.Text('White Balance:'),
     sg.Combo(['AUTO','INCANDESCENT','FLUORESCENT', 'DAYLIGHT', 'FLASH', 'CLOUDY', 'SHADE' ],
              size=(16,1),default_value='FLUORESCENT',readonly=True,key='-PIX_WB-'),
     sg.Text('JPEG Quality:'), sg.Text('80',size=(4,1),justification='center',text_color='black',background_color=my_bg_color)],
    [sg.Text('Scene Mode:'),
     sg.Combo(['DISABLED','BACKLIGHT','BEACH_SNOW','CANDLE_LIGHT','DAWN_DUSK','FALL_COLORS','FIREWORKS',
              'LANDSCAPE','NIGHT','PARTY_INDOOR','PORTRAIT','SPORTS','SUNSET'],size=(12,1),
              default_value='DISABLED',readonly=True,disabled=True,key='-PIX_SCENE-'),
     sg.Text('Color Effects:'),
     sg.Combo(['NONE','B&W','SEPIA','NEGATIVE','EMBOSS','SKETCH','SKY_BLUE','GRASS_GREEN','SKIN_WHITEN',
              'VIVID','AQUA','ART_FREEZE','SILHOUETTE','SOLARIZE','ANTIQUE','SET_CBR','PASTEL'],size=(15,1),
              default_value='NONE',readonly=True,key='-PIX_COL-')],
    [sg.Text('High Dynamic Range (HDR):'),
     sg.Combo(['OFF','AUTO','ON',],size=(6,1),
              default_value='OFF',readonly=True,key='-PIX_HDR-')],
    [sg.Checkbox('Automatic Exposure Time  '),
    sg.Text('Manual Exp Time:'),sg.Input(size=(10,1),key='-PIX_EXP-'),sg.Text('msec')],
    [sg.Text('ISO Setting:'),
     sg.Combo(['AUTO','ISO 25 (Sunny)','ISO 32','ISO 40','ISO 50','ISO 64','ISO 80','ISO 100','ISO 125','ISO 160',
              'ISO 200','ISO 250','ISO 320','ISO 400','ISO 500','ISO 640','ISO 800','ISO 1000','ISO 1250','ISO 1600 (Dark)'],
              size=(16,1),default_value='ISO 320',readonly=True,key='-PIX_ISO-')]
    ]
my_tab2_layout = [
    [sg.Button('get color',key='-GET_COLOR-')],
    [sg.Button('get camera parameters',key='-GET_SPRESENSE_PARAMETERS-')],
    [sg.Button('send parameters',key='-SEND_SPRESENSE_PARAMETERS-')],
    ]
my_tab3_layout = [
    [sg.Button('Hello Spresense',key='-HELLO-'),
     sg.Button('Camera Type',key='-CAM_TYPE-')]
    ]
#-----UI Define the tabs group---------
my_tabs_group_layout = [
        [   sg.Tab('Camera',my_tab1_layout,key='-TAB1-'),
            sg.Tab('Debug1',my_tab2_layout,key='-TAB2-'), 
            sg.Tab('Debug2',my_tab3_layout,key='-TAB3-')
        ]
]

left_column = [
        [sg.Text('System Information Window',size=(40,1),font=('Ariel',12,'bold'),justification='center')],
        [sg.HorizontalSeparator()],
        [sg.Multiline(font='courier',size=(39,24),autoscroll=True,auto_refresh=True,reroute_stdout=True,
            do_not_clear=True,key='-MY_TEXT_BOX-')]
]
middle_column = [
        [sg.Text('Working image below is fixed at 500 x 400 pixels',justification='center',expand_x=True)],
        [sg.Image(size=(500, 400), key='-IMAGE-')],
        [sg.Text('To view full resolution image, see filenames to the right.',justification='center',expand_x=True)],
]
right_column = [
        [sg.TabGroup(my_tabs_group_layout,expand_x=True,key='-TAB_CHANGE-',
                    enable_events=True, tab_location='topleft')],
]

layout = [
    [sg.Column(left_column),
     sg.VSeperator(),
     sg.Column(middle_column),
     sg.VSeperator(),
     sg.Column(right_column),
     sg.VSeperator()]
]


window = sg.Window('Spresense Camera App', layout, margins=(0, 0), finalize=True, titlebar_font=('bold'))

# Convert im to ImageTk.PhotoImage after window finalized
image = ImageTk.PhotoImage(image=im)
im.close()

# Check for Spresense board plugged into PC comm port
# use this python command:
#    ports = serial.tools.list_ports.comports()
# RETURNS the following:
# port--->COM3
# desc--->Silicon Labs CP210x USB to UART Bridge (COM3)
# hwid--->USB VID:PID=10C4:EA60 SER=6E06937A1D9EE8118C10301338B01545 LOCATION=1-7.4.4
# Look for Spresense Comm Port
found_it = False
ports = serial.tools.list_ports.comports()
for port , desc, hwid in sorted(ports):
    if(hwid[12:21])=='10C4:EA60':           #if vid pid match Spresense board then you found it
        my_port = port.lower()
        print('Spresense found on',my_port)
        print('Initialization in progress...')
        found_it = True
        break
    
if found_it == False:
    #print('*** DID NOT FIND CONNECTED SPRESENSE MODULE ***')
    sg.popup('Spresense Module Not Found!',font=('Ariel',20,'bold'),keep_on_top=True,text_color='red')
    exit_routine()
        
#This is the com port being used by Spresense to talk with PC (python-PySimpleGui)
#A "+" is defined by Spresense code to mean... take another snap shot
#ser = serial.Serial('com3', 115200, timeout=(70))
#ser = serial.Serial('com3', 230400, timeout=(20))
ser = serial.Serial(my_port, 1200000, timeout=(7))      # 3 seconds timeout does not work
                                                        # 4 seconds ok for file size < 355kB
                                                        # unfortunately JPEG size is image dependent
time.sleep(2.5)                                         # Spresense reboots when the com port shows up (and it is slow) 
start_up = True
#get_camera_settings()                                   # Get Spresense default camera parameters 
#parameter_from_spresense()
print('Initialization Complete...')
        

# update image in sg.Image
window['-IMAGE-'].update(data=image)
num_byte = 0;
streaming_active = False

#---MAIN LOOP-----------------------------
while True:

    event, values = window.read()
    if event == sg.WIN_CLOSED:
        send_Spresense_command('cam_stream_stop\n',0,'silent')            # tell the Spresense to stop streaming
        break
    elif event == '-SNAP-':
        #TAKE A PICTURE - STILL IMAGE
        take_a_still_snap_shot()
        
    elif event == '-HELLO-':
        ser.write(("!\n").encode())                   #Say hello to/from Spresense
        for x in range(6):
            print(ser.readline().decode('ascii'),end='')
            
    elif event == '-GET_SPRESENSE_PARAMETERS-':
        parameter_from_spresense()
        
    elif event == '-SEND_SPRESENSE_PARAMETERS-':
        parameter_to_spresense()
        
    elif event == '-CAM_TYPE-':
        ser.write(("device_type\n").encode())                   
        print(ser.readline().decode('ascii'),end='')
        
    elif event == '-PIX_FPS-':
        if(values[event] == 'STILL'):                                    # STILL Image Mode
            streaming_active = False                                     # Tells Python thread to stop streaming
            print('stop_streaming')                                      # camera_steaming_mode subroutine tells spresense to stop streaming
            window['-SNAP-'].update(disabled=False)                      # Allow still image taking if not active streaming
        else:                                                            # ELSE, Put the Spresense camera into streaming video mode
           if(streaming_active == False):                                # Using has to select 'STILL' to turn off streaming
               streaming_active = True                                   # Enable streaming mode
               threading.Thread(target=camera_steaming_mode, args=(window,), daemon=True).start() 
               window['-SNAP-'].update(disabled=True)                    #Don't allow still image taking if active streaming
        
    #Get the current setting of the Spresense camera
    elif event == '-GET_COLOR-':
        print(sg.theme_input_background_color())
        
    elif event == '-THREAD_MESSAGE-':
        print('thread-->', values[event])
        
        
exit_routine()
