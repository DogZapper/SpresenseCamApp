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
# Generic Spresence command handler
#-------------------------------------------------
def send_Spresense_command(command,response_lines):
    ser.write((command).encode())  
    for x in range(response_lines):
        print(ser.readline().decode('ascii'),end='')
        
#-------------------------------------------------
# Generic Spresense command handler
#-------------------------------------------------
# def send_Spresense_command(command,response_lines):
#     global spresense_command_response_data
    
#     spresense_command_response_data = ""

#     ser.write((command).encode())  
#     for x in range(response_lines):
#         new_response = ser.readline().decode('ascii')
#         spresense_command_response_data = spresense_command_response_data + new_response
#         print(new_response,end='')
        
#-------------------------------------------------
# get_camera_settings Spresense command routine
#-------------------------------------------------
def get_camera_settings():
    send_Spresense_command('cam_info\n',12)
    #print('TextBox:',spresense_command_response_data)
    #print(spresense_command_response_data.splitlines()[1])      #Prints second response line
    
    
#-------------------------------------------------
# set Spresense into streaming mode
#-------------------------------------------------
def camera_steaming_mode(window,):
    send_Spresense_command('cam_stream_start\n',4)
    
    while streaming_active:
        start=time.time()                                                #start time for FPS calculation
        image_size = int(ser.readline())                                 #get the size (in bytes) of the image
        print(image_size)
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

    send_Spresense_command('cam_stream_stop\n',0)                   # tell the Spresense to stop streaming 2nd
    ser.read_all()                                                  # use this to flush the PC comm port buffer
    window.write_event_value('-THREAD_MESSAGE-','*** STREAM_ENDED ***')     # put a message into queue for GUI
    f = open('my_streaming.jpg','wb')                               #save this last frame into jpg streaming file
    f.write(spresense_camera_data)
    f.close()
    
    
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
              size=(15,1),default_value='3MP_2048',readonly=True,key='-BEG_WID-'),
     sg.Text('Height:'),
     sg.Combo(['QQVGA_120','QVGA_240','VGA_480','HD_720','QUADVGA_960','FULLHD_1080','3MP_1536','5MP_1920'],
              size=(14,1),default_value='3MP_1536',readonly=True,key='-BEG_HEI-'),sg.Text('pixels')],
    [sg.Text('Streaming Video Format:'),
     sg.Combo(['RGB565','YUV422','JPG','GRAY','NONE'],size=(6,1),default_value='JPG',
              readonly=True,key='-PIX_FMT-'),
     sg.Text('JPEG Size Divisor:'), sg.Combo([' 1',' 2',' 3',' 4',' 5',' 6',' 7',' 9','10','11','12','13','14'],
              size=(3,1),default_value='7', readonly=True,key='-PIX_FMT-')],
    [sg.Text('JPEG Buffer Size:'), sg.Text('898,779 bytes',expand_x=True,justification='center',text_color='black',
              background_color=my_bg_color),
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
              readonly=True,key='-PIX_FMT-'),
     sg.Text('JPEG Buffer Size:'),
     sg.Text('898,779 bytes',expand_x=True,justification='center',text_color='black',background_color=my_bg_color)],
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
              size=(16,1),default_value='ISO 320',readonly=True,key='-PIX_ISO-')],
    [sg.Button('Get Settings from Spresense and Update Fields',size=(40,2),expand_x=True,key='-CAM_UPDATE-')]
    ]
my_tab2_layout = [
    [sg.Button('get color',key='-GET_COLOR-')],
    ]
my_tab3_layout = [
    [sg.Button('Hello Spresense',key='-HELLO-'),
     sg.Button('Camera Type',key='-CAM_TYPE-')]
    ]
#-----UI Define the tabs group---------
my_tabs_group_layout = [
        [   sg.Tab('Camera',my_tab1_layout,key='-TAB1-'),
            sg.Tab('Hardware',my_tab2_layout,key='-TAB2-'), 
            sg.Tab('Other',my_tab3_layout,key='-TAB3-')
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
    
# update image in sg.Image
window['-IMAGE-'].update(data=image)

#Fix the serial port at com3 for now...(good for my system)
#This is the com port being used by Spresense to talk with PC (python-PySimpleGui)
#A "+" is defined by Spresense code to mean... take another snap shot
#ser = serial.Serial('com3', 115200, timeout=(70))
#ser = serial.Serial('com3', 230400, timeout=(20))
ser = serial.Serial('com3', 1200000, timeout=(7))    # 3 seconds does not work
                                                     # 4 seconds ok for file < 355kB
                                                     # unfortunately JPEG size is image dependent
num_byte = 0;
streaming_active = False


#---MAIN LOOP-----------------------------
while True:

    event, values = window.read()
    if event == sg.WIN_CLOSED:
        send_Spresense_command('cam_stream_stop\n',0)            # tell the Spresense to stop streaming
        break
    elif event == '-SNAP-':
        #TAKE A PICTURE - STILL IMAGE
        take_a_still_snap_shot()
        
    elif event == '-HELLO-':
        ser.write(("!\n").encode())                   #Say hello to Spresense
        for x in range(6):
            print(ser.readline().decode('ascii'),end='')
        
    elif event == '-CAM_TYPE-':
        ser.write(("device_type\n").encode())                   
        print(ser.readline().decode('ascii'),end='')
            
    #Get the current setting of the Spresense camera
    elif event == '-CAM_UPDATE-':
        get_camera_settings()
        
    elif event == '-PIX_FPS-':
        print('FPS:', values[event])
        if(values[event] == 'STILL'):                                    # STILL Image Mode
            streaming_active = False                                     # Tells Python thread to stop streaming
            print('stop_streaming')                                      # camera_steaming_mode subroutine tells spresense to stop streaming
            window['-SNAP-'].update(disabled=False)                      # Allow still image taking if not active streaming
        else:                                                            # ELSE, Put the Spresense camera into streaming video mode
           if(streaming_active == False):                                # Using has to select 'STILL' to turn off streaming
               streaming_active = True
               threading.Thread(target=camera_steaming_mode, args=(window,), daemon=True).start() 
               window['-SNAP-'].update(disabled=True)                    #Don't allow still image taking if active streaming
        
    #Get the current setting of the Spresense camera
    elif event == '-GET_COLOR-':
        print(sg.theme_input_background_color())
        
    elif event == '-THREAD_MESSAGE-':
        print('thread-->', values[event])
        

print('*** Exit ***')
ser.close()
window.close()
