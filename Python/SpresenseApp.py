# -------------------------------------------------
# Spresense Camera Application - Python
# Tested OK using:
# Windows10
# Python 3.9.0 (tags/v3.9.0:9cf6752, Oct  5 2020, 15:34:40) [MSC v.1927 64 bit (AMD64)] on win32

# -------------------------------------------------
import PySimpleGUI as sg
from PIL import Image, ImageTk
import serial
from serial.tools import list_ports
import time
import os


# =======================================================================
#  ____  _   _ ____  ____   ___  _   _ _____ ___ _   _ _____ ____
# / ___|| | | | __ )|  _ \ / _ \| | | |_   _|_ _| \ | | ____/ ___|
# \___ \| | | |  _ \| |_) | | | | | | | | |  | ||  \| |  _| \___ \
#  ___) | |_| | |_) |  _ <| |_| | |_| | | |  | || |\  | |___ ___) |
# |____/ \___/|____/|_| \_\\___/ \___/  |_| |___|_| \_|_____|____/
# =======================================================================

# User interface image frame sizes are fixed, see sizes below...
# This routine will resize your image to match frame size, if you ask
def show_the_image(location, image_file, resize):
    if location == 'streaming':
        my_ui_image_frame_size = streaming_ui_image_frame_size
        image_to_update = '-STREAMING_IMAGE-'
    else:
        my_ui_image_frame_size = still_ui_image_frame_size
        image_to_update = '-STILL_IMAGE-'

    im = Image.open(image_file, formats=None)
    if resize:
        im = im.resize(my_ui_image_frame_size, resample=Image.BICUBIC)
    image = ImageTk.PhotoImage(image=im)  # convert to ImageTK image type because PySimpleGUI works on these
    im.close()  # close the opened, original image file
    window[image_to_update].update(data=image)  # Show this image on the UI, streaming image frame (top), still (bottom)


# Prints to this application's System Information Window (Multiline Element Print)
def mprint(*args, **kwargs):
    window['-MY_TERMINAL_WINDOW-'].print(*args, **kwargs)


# ----------------------------------------------------------------------------------
# Check for Spresense board, enumerates as USB comm port, look for Spresense VID/PID
# use this python command:
#    ports = serial.tools.list_ports.comports()
# RETURNS the following (for example):
# port--->COM3
# desc--->Silicon Labs CP210x USB to UART Bridge (COM3)
# hwid--->USB VID:PID=10C4:EA60 SER=6E06937A1D9EE8118C10301338B01545 LOCATION=1-7.4.4
# Returns True if application should abort because Spresense comm port was not found
# ----------------------------------------------------------------------------------
def connect_to_spresense():
    global ser
    my_port = 'com3'
    abort_app = True
    ports = serial.tools.list_ports.comports()
    for port, desc, hwid in sorted(ports):
        if (hwid[12:21]) == '10C4:EA60':  # if vid pid match, Spresense board found
            my_port = port.lower()
            mprint('Spresense found on', my_port)
            mprint('Initialization in progress...')
            abort_app = False
            break

    if abort_app:
        mprint('*** DID NOT FIND SPRESENSE MODULE ***')
        sg.popup_ok('Spresense Module Not Found!\nPlease exit the application', font=('Ariel', 20, 'bold'))
        mprint('*** PLEASE MANUALLY CLOSE WINDOW  ***')
        return abort_app  # returns True
    else:
        ser = serial.Serial(my_port, 1200000, timeout=7)
        time.sleep(3.2)  # Spresense reboots when the com port shows up (and it is slow)
        # get_camera_settings()                                   # Get Spresense default camera parameters
        # parameter_from_spresense()
        mprint('Initialization Complete...')
        return abort_app  # returns False


def handle_user_input_streaming_image_size(dimension):
    global streaming_width
    global streaming_height
    if dimension == 'width':
        try:
            streaming_width = int(values['-STREAMING_WIDTH-'])
        except ValueError:
            streaming_width = 0
        finally:
            if int(streaming_width) < 96:
                window['-STREAMING_WIDTH-'].update(streaming_width, text_color='red')
            elif int(streaming_width) < 2592+1:
                window['-STREAMING_WIDTH-'].update(streaming_width, text_color='black')
                sg.user_settings_set_entry('-STREAMING_WIDTH-', streaming_width)  # value change, save it
            else:
                window['-STREAMING_WIDTH-'].update(streaming_width, text_color='red')
    else:  # must be height
        try:
            streaming_height = int(values['-STREAMING_HEIGHT-'])
        except ValueError:
            streaming_height = 0
        finally:
            if int(streaming_height) < 64:
                window['-STREAMING_HEIGHT-'].update(streaming_height, text_color='red')
            elif int(streaming_height) < 1944+1:
                window['-STREAMING_HEIGHT-'].update(streaming_height, text_color='black')
                sg.user_settings_set_entry('-STREAMING_HEIGHT-', streaming_height)  # value change, save it
            else:
                window['-STREAMING_HEIGHT-'].update(streaming_height, text_color='red')


def calculate_jpeg_buffer_size(which_buffer):
    global jpeg_buffer_size
    if which_buffer == 'streaming':
        jpeg_buffer_size = int((streaming_width * streaming_height * bytes_per_pixel) / streaming_jpgbufsize_div)
        window['-STREAMING_JPEG_BUFF_SIZE-'].update(jpeg_buffer_size)
    # else:   # still image buffer
    #     jpeg_buffer_size = int((streaming_width * streaming_height * bytes_per_pixel) / jpgbufsize_divisor)
    #     window['-STREAMING_JPEG_BUFF_SIZE-'].update(jpeg_buffer_size)


# -------------------------------------------------
# Spresense streaming image mode
# -------------------------------------------------
def camera_streaming_mode(my_window):
    global streaming_enabled
    send_spresense_command('cam_stream_start\n', 5)

    mprint('--- Image Size ---')
    while streaming_enabled:
        start = time.time()  # start time for FPS calculation
        image_size = int(ser.readline())  # get the size (in bytes) of the image
        mprint(image_size)
        if image_size == 0:
            mprint('jpeg buffer overflow')
        if image_size > 0:
            spresense_camera_data = ser.read(size=image_size)  # reads bytes from Spresense
            image_tk = ImageTk.PhotoImage(data=spresense_camera_data)  # read raw array data and creates an imgtk
            im_pil = ImageTk.getimage(image_tk)  # convert it to PIL image so we can resize it
            resized_pil = im_pil.resize(streaming_ui_image_frame_size)  # resize it to fit streaming frame size
            image = ImageTk.PhotoImage(image=resized_pil)  # convert it back to TK_image
            my_window['-STREAMING_IMAGE-'].update(data=image)
            endt = time.time()
            fpsec = 1.0 / (endt - start)
            my_window['-FPS-'].update('%.3f' % fpsec)


# --------------------------------------------------------------------------------
# PC to Spresense command handler
# Spresense response is stored in global varible: spresense_command_response_data
# --------------------------------------------------------------------------------
def send_spresense_command(command, response_lines):
    global spresense_command_response_data
    spresense_command_response_data = ""

    ser.write(command.encode())
    for x in range(response_lines):
        new_response = ser.readline().decode('ascii')
        spresense_command_response_data = spresense_command_response_data + new_response


def get_camera_settings():
    global spresense_command_response_data
    send_spresense_command('cam_info\n', 14)
    mprint()
    mprint(spresense_command_response_data)


# ---------------------------------------------------
# System parameter from Spresense
# use command P-
# Pulls current parameter values from Spresense.ini
# and sends them to Spresense hardware
# ---------------------------------------------------
def parameters_from_spresense():
    # ser.write("P-\n").encode()                  # Get Spresense Parameters
    send_spresense_command('P-\n', 21)
    mprint()
    mprint(spresense_command_response_data)


def parameters_to_spresense():
    # mprint(sg.user_settings_get_entry('-STREAMING_FPS-'))
    # mprint(sg.user_settings_get_entry('-STREAMING_WIDTH-'))
    # mprint(sg.user_settings_get_entry('-STREAMING_HEIGHT-'))
    # mprint(sg.user_settings_get_entry('-STREAMING_PIX_FMT-'))
    # mprint(sg.user_settings_get_entry('-STREAMING_JPEG_SIZE_DIV-'))
    # mprint(sg.user_settings_get_entry('-STREAMING_JPEG_BUFFERS_COUNT-'))
    # mprint(sg.user_settings_get_entry('-STREAMING_FILENAME-'))
    # mprint(settings)
    # mprint(settings.items())
    # mprint(settings.keys())
    # mprint(settings.values())
    # f = open("Spresense.ini", "r")  # read in the ini file
    # ini_file_data = f.read()
    # start = [17,18,22,29,19,18,20,13,14,20,25,16,15,14,12,14,20,20,22,20]
    # # Tells Spresense the ini parameter data is coming next
    # ser.write( ("P+\n").encode() )
    settings = sg.user_settings()
    ser.write(('P+'+'\n').encode())
    mprint()
    new_response = ser.readline().decode('ascii')
    mprint(new_response)
    time.sleep(1)
    ser.write((settings['-STREAMING_FPS-'] + '\n').encode())
    ser.write((settings['-STREAMING_WIDTH-'] + '\n').encode())
    ser.write((settings['-STREAMING_HEIGHT-'] + '\n').encode())
    ser.write((settings['-STREAMING_PIX_FMT-'] + '\n').encode())
    ser.write((settings['-STREAMING_JPEG_SIZE_DIV-'] + '\n').encode())
    ser.write((settings['-STREAMING_JPEG_BUFFERS_COUNT-'] + '\n').encode())
    ser.write((settings['-STREAMING_FILENAME-'] + '\n').encode())
    ser.write(("lizard" + '\n').encode())
    ser.write(("bird" + '\n').encode())
    ser.write(("fish" + '\n').encode())
    ser.write(("bug" + '\n').encode())
    ser.write(("insect" + '\n').encode())
    ser.write(("crab" + '\n').encode())
    ser.write(("toad" + '\n').encode())
    ser.write(("bear" + '\n').encode())
    ser.write(("coyote" + '\n').encode())
    ser.write(("merrkat" + '\n').encode())
    ser.write(("ant" + '\n').encode())
    ser.write(("worm" + '\n').encode())
    ser.write(("praying mantis4" + '\n').encode())
    new_response = ser.readline().decode('ascii')
    mprint(new_response)
    # for x in range(1):
    #     print(ser.readline().decode('ascii'), end='')
    #     time.sleep(1)
    # for line in range(len(start)):
    #     pram = ini_file_data.splitlines()[line]
    #     pram = pram[start[line]:]
    #     update_the_user_interface(line+1, pram)      # update the UI for every parameter sent to Spresence
    #     print(pram)
    #     ser.write((pram + "\n").encode())           # Send the parameter to spresense


# ==========================================================================================================
#     __  __       _          ____             _   _
#    |  \/  | __ _(_)_ __    |  _ \ ___  _   _| |_(_)_ __   ___
#    | |\/| |/ _` | | '_ \   | |_) / _ \| | | | __| | '_ \ / _ \
#    | |  | | (_| | | | | |  |  _ < (_) | |_| | |_| | | | |  __/
#    |_|  |_|\__,_|_|_| |_|  |_| \_\___/ \__,_|\__|_|_| |_|\___|
# ==========================================================================================================
# MAIN
# Start up code and main routine starts here
# jpeg_buffer_size = (img_width * img_height * bytes_per_pixel) / jpgbufsize_divisor
# bytes_per_pixel = 2
# -------------------------------------------------
sg.theme('DarkGreen3')
# Some GLOBALS-------------------------------------
my_bg_color = sg.theme_input_background_color()
bytes_per_pixel = 2
streaming_ui_image_frame_size = (250, 200)
still_ui_image_frame_size = (500, 400)
streaming_enabled = False
sg.user_settings_filename(path='.')   # user_settings_filename = "This_filename.json" in the same directory
spresense_command_response_data = ""

if not sg.user_settings_file_exists():
    sg.user_settings_set_entry('-STREAMING_FPS-', '5 FPS')
    sg.user_settings_set_entry('-STREAMING_WIDTH-', '96')
    sg.user_settings_set_entry('-STREAMING_HEIGHT-', '64')
    sg.user_settings_set_entry('-STREAMING_PIX_FMT-', 'JPG')
    sg.user_settings_set_entry('-STREAMING_JPEG_SIZE_DIV-', '7')
    sg.user_settings_set_entry('-STREAMING_JPEG_BUFFERS_COUNT-', '1')
    sg.user_settings_set_entry('-STREAMING_FILENAME-', 'my_streaming.jpg')  # Streaming image file name

frame_rate = sg.user_settings_get_entry('-STREAMING_FPS-')
streaming_width = int(sg.user_settings_get_entry('-STREAMING_WIDTH-'))
streaming_height = int(sg.user_settings_get_entry('-STREAMING_HEIGHT-'))
streaming_jpgbufsize_div = int(sg.user_settings_get_entry('-STREAMING_JPEG_SIZE_DIV-'))
streaming_buff_cnt = int(sg.user_settings_get_entry('-STREAMING_JPEG_BUFFERS_COUNT-'))
streaming_filename = sg.user_settings_get_entry('-STREAMING_FILENAME-')

jpeg_buffer_size = (streaming_width * streaming_height * bytes_per_pixel) / int(streaming_jpgbufsize_div)

my_tab1_layout = [
    [sg.Frame('Streaming', [
        [sg.Checkbox('Active', default=False, enable_events=True, key='-STREAMING_CHECKBOX-'),
         sg.Text('Frame Rate:'),
         sg.Combo(['5 FPS', '6 FPS', '7.5 FPS', '15 FPS', '30 FPS', '60 FPS', '120 FPS'], size=(8, 1),
                  default_value=frame_rate, readonly=True, enable_events=True, key='-STREAMING_FPS-')],
        [sg.Text('Image size in pixels:')],
        [sg.T('Width:', pad=((12, 5), (0, 0))), sg.Input(streaming_width, s=5, enable_events=True,
                                                         key='-STREAMING_WIDTH-'),
         sg.T('X'),
         sg.T('Height:'), sg.Input(streaming_height, size=5, enable_events=True, key='-STREAMING_HEIGHT-')],
        [sg.T('Format:'), sg.Combo(['RGB565', 'YUV422', 'JPG', 'GRAY', 'NONE'], s=(7, 1), default_value='JPG',
                                   readonly=True, key='-STREAMING_PIX_FMT-')],
        [sg.Frame('JPEG Settings', [
            [sg.T('Div:'), sg.Combo([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
                                    s=(3, 1), default_value=streaming_jpgbufsize_div, readonly=True,
                                    enable_events=True, key='-STREAMING_JPEG_SIZE_DIV-'),
             sg.T('Buffers:'), sg.Combo([1, 2], size=(3, 1), default_value=streaming_buff_cnt, readonly=True,
                                        key='-STREAMING_JPEG_BUFFERS_COUNT-')],
            [sg.T('Buffer Size (bytes):'), sg.Text(jpeg_buffer_size, s=(8, 1), expand_x=True, justification='center',
                                                   text_color='black', background_color=my_bg_color,
                                                   key='-STREAMING_JPEG_BUFF_SIZE-')]])],
        [sg.Text('Streaming Filename:')], [sg.Input(streaming_filename, size=(32, 1), disabled=True,
                                                    key='-STREAMING_FILENAME-')]])],
    [sg.Button('Send settings to Spresence camera', expand_x=True, key='-UPDATE_STREAMING_SETTINGS-')],
    [sg.Button('Get array data from Spresence', expand_x=True, key='-GET_SPRESENSE_ARRAY_DATA-')]
]


my_tab2_layout = []
my_tab3_layout = [
    [sg.Button('Get Versions', key='-VERSIONS-')]
]
my_tabs_group_layout = [
    [sg.Tab('Camera', my_tab1_layout, key='-TAB1-'),
     sg.Tab('Debug', my_tab2_layout, key='-TAB2-'),
     sg.Tab('Misc', my_tab3_layout, key='-TAB3-')]
]

left_column = [
    [sg.Text('System Information Window', size=(40, 1), font=('Ariel', 12, 'bold'), justification='center')],
    [sg.HorizontalSeparator()],
    [sg.Multiline(font='courier', size=(39, 37), autoscroll=True, auto_refresh=True, reroute_stdout=False,
                  do_not_clear=True, disabled=True, key='-MY_TERMINAL_WINDOW-')]
]

middle_column = [
    [sg.Text('Streaming Frame - Fixed pixels:' + str(streaming_ui_image_frame_size), pad=(100, 0))],
    [sg.Image(size=streaming_ui_image_frame_size, pad=((100, 0), (0, 10)), key='-STREAMING_IMAGE-'),
     sg.Text('Actual:'),
     sg.Text(size=(5, 1), text_color='black', background_color=my_bg_color, key='-FPS-'),
     sg.Text('FPS')],
    [sg.Text('Still Image Frame - Fixed pixels:' + str(still_ui_image_frame_size), pad=(0, 0))],
    [sg.Image(size=still_ui_image_frame_size, pad=((0, 0), (0, 0)), key='-STILL_IMAGE-')],
    [sg.Text('Working images above are fixed sizes.', justification='center', expand_x=True)],
    [sg.Text('To view full resolution images, see filenames to the right.', justification='center', expand_x=True)]
]

right_column = [
    [sg.TabGroup(my_tabs_group_layout, expand_x=True, key='-TAB_CHANGE-',
                 enable_events=True, tab_location='topleft')]
]

layout = [
    [sg.VerticalSeparator(),
     sg.Column(left_column),
     sg.VerticalSeparator(),
     sg.Column(middle_column),
     sg.VerticalSeparator(),
     sg.Column(right_column),
     sg.VerticalSeparator()],
    [sg.StatusBar('Status Bar: ...', size=80, key='-STAT_BAR-')]
]

# -----------------------------------------------------------------------------------------------------------
# __        ___           _                 ____        __ _       _ _   _
# \ \      / (_)_ __   __| | _____      __ |  _ \  ___ / _(_)_ __ (_) |_(_) ___  _ __
#  \ \ /\ / /| | '_ \ / _` |/ _ \ \ /\ / / | | | |/ _ \ |_| | '_ \| | __| |/ _ \| '_ \
#   \ V  V / | | | | | (_| | (_) \ V  V /  | |_| |  __/  _| | | | | | |_| | (_) | | | |
#    \_/\_/  |_|_| |_|\__,_|\___/ \_/\_/   |____/ \___|_| |_|_| |_|_|\__|_|\___/|_| |_|
# -----------------------------------------------------------------------------------------------------------
window = sg.Window('Spresense Camera App', layout, margins=(0, 0), finalize=True, titlebar_font='bold',
                   enable_close_attempted_event=True)

show_the_image('streaming', 'Spresense_Splash3.JPG', resize=True)  # Show the start up image
show_the_image('still', 'Spresense_Splash3.JPG', resize=True)  # Show the start up image
spresense_not_found = connect_to_spresense()
window['-STREAMING_WIDTH-'].bind('<FocusIn>', 'GOT_FOCUS')   # Used to generate an event when input field gets focus
window['-STREAMING_HEIGHT-'].bind('<FocusIn>', 'GOT_FOCUS')  # Used to generate an event when input field gets focus

# -------------------------------------------------------
#  _____                 _     _
# | ____|_   _____ _ __ | |_  | |    ___   ___  _ __
# |  _| \ \ / / _ \ '_ \| __| | |   / _ \ / _ \| '_ \
# | |___ \ V /  __/ | | | |_  | |__| (_) | (_) | |_) |
# |_____| \_/ \___|_| |_|\__| |_____\___/ \___/| .__/
#                                              |_|
# ------------------------------------------------------
while True:  # The Event Loop
    event, values = window.read()
    print('event:', event)        # This print, for debug only
    # print('values:', values)    # This print, for debug only
    # if not streaming_video_thread_active:  # only do this once
    #    threading.Thread(target=camera_steaming_mode, args=(window,), daemon=True).start()
    #    streaming_video_thread_active = True
    if spresense_not_found:
        print('Spresense Comm Port not found')
        window.close()
        break
    if event == sg.WINDOW_CLOSE_ATTEMPTED_EVENT or event == 'Exit':
        window['-STREAMING_CHECKBOX-'].update(False)
        send_spresense_command('cam_stream_stop\n', 0)  # tell the Spresense to stop streaming 2nd
        ser.close()
        break
    elif event == '-STREAMING_WIDTH-GOT_FOCUS':
        window['-STAT_BAR-'].update('Status Bar: Streaming Image Width Range: 96-2592 pixels for ISX012 image sensor')
    elif event == '-STREAMING_HEIGHT-GOT_FOCUS':
        window['-STAT_BAR-'].update('Status Bar: Streaming Image Height Range: 64-1944 pixels for ISX012 image sensor')
    elif event == '-STREAMING_WIDTH-':
        handle_user_input_streaming_image_size('width')
        calculate_jpeg_buffer_size('streaming')
    elif event == '-STREAMING_HEIGHT-':
        handle_user_input_streaming_image_size('height')
        calculate_jpeg_buffer_size('streaming')
    elif event == '-STREAMING_JPEG_SIZE_DIV-':
        streaming_jpgbufsize_div = values['-STREAMING_JPEG_SIZE_DIV-']
        calculate_jpeg_buffer_size('streaming')
    elif event == '-STREAMING_CHECKBOX-':
        if values['-STREAMING_CHECKBOX-']:  # if streaming checkbox is checked...
            print('Streaming active...')
            streaming_enabled = True
            window.perform_long_operation(lambda: camera_streaming_mode(window), '-THREAD-')
        else:
            streaming_enabled = False
            print('Streaming NOT active...')
            # send_spresense_command('cam_stream_stop\n', 0)  # tell the Spresense to stop streaming 2nd
            # streaming_enabled = values['-STREAMING_CHECKBOX-']
            # window.start_thread(lambda: my_function_with_parms(10), '-FUNCTION COMPLETED-')
            # send_spresense_command('cam_stream_stop\n', 0)  # tell the Spresense to stop streaming 2nd
    elif event == '-THREAD-':
        mprint('Streaming video stopped')
        send_spresense_command('cam_stream_stop\n', 0)  # tell the Spresense to stop streaming 2nd
    elif event == '-VERSIONS-':
        mprint('---------------------------------------')
        mprint(sg.get_versions())
        mprint('---------------------------------------')
    elif event == '-UPDATE_STREAMING_SETTINGS-':
        parameters_to_spresense()
        get_camera_settings()
    elif event == '-GET_SPRESENSE_ARRAY_DATA-':
        parameters_from_spresense()

window.close()


# My NOTES.................................................................................................
# Supports three "print" methods to send out information:
# print('Hello World')       # Print to Shell output
# sg.Print('Hello World')    # Prints to a PySimpleGUI Debug Popup Window
# mprint('Hello World')      # Prints to this application's System Information Window, multiline element
# send_spresense_command('cam_stream_stop\n', 0)  # tell the Spresense to stop streaming 2nd
# print('CheckBox:', values['-STREAMING_CHECKBOX-'])
