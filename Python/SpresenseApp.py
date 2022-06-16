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
import threading
import os


# -------------------------------------------------
# SUBROUTINES
# Define your Python subroutines at the start
# -------------------------------------------------

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
        time.sleep(2.5)  # Spresense reboots when the com port shows up (and it is slow)
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
def camera_streaming_mode(window):
    send_spresense_command('cam_stream_start\n', 5, 'enabled')
    spresense_camera_data = 0

    mprint('--- Image Size ---')
    while values['-STREAMING_CHECKBOX-']:  # The streaming active check_box
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
            window['-STREAMING_IMAGE-'].update(data=image)
            endt = time.time()
            fpsec = 1.0 / (endt - start)
            window['-FPS-'].update('%.3f' % fpsec)
        print('CheckBox:', values['-STREAMING_CHECKBOX-'])

    window.write_event_value('-THREAD-', 'done')
    print('CheckBox:', values['-STREAMING_CHECKBOX-'])


# -------------------------------------------------
# PC to Spresense command handler
# -------------------------------------------------
def send_spresense_command(command, response_lines, print_mode):

    spresense_command_response_data = ""

    ser.write(command.encode())
    for x in range(response_lines):
        new_response = ser.readline().decode('ascii')
        spresense_command_response_data = spresense_command_response_data + new_response


def handle_streaming_active_checkbox():
    time.sleep(1)  # slow down the user, prevent clicking checkbox too fast here...
    if values['-STREAMING_CHECKBOX-']:  # The checkbox is active, CHECKED
        # window['-STREAMING_FPS-'].update(disabled=True)
        # window['-STREAMING_WIDTH-'].update(disabled=True, background_color='gray')
        # window['-STREAMING_HEIGHT-'].update(disabled=True)
        # window['-STREAMING_PIX_FMT-'].update(disabled=True)
        # window['-STREAMING_JPEG_SIZE_DIV-'].update(disabled=True)
        # window['-STREAMING_JPEG_BUFFERS_COUNT-'].update(disabled=True)
        threading.Thread(target=camera_steaming_mode, args=(window, ), daemon=True).start()
        threading_active = True


# -------------------------------------------------
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

current_directory = os.getcwd() + '\\'
python_settings_filename = 'Spresense.json'
sg.user_settings_filename(filename=current_directory + python_settings_filename)  # Python settings file

if not sg.user_settings_file_exists():
    sg.user_settings_set_entry('-STREAMING_CHECKBOX-', False)
    sg.user_settings_set_entry('-STREAMING_FPS-', '5 FPS')
    sg.user_settings_set_entry('-STREAMING_WIDTH-', 96)
    sg.user_settings_set_entry('-STREAMING_HEIGHT-', 64)
    sg.user_settings_set_entry('-STREAMING_JPEG_SIZE_DIV-', 7)
    sg.user_settings_set_entry('-STREAMING_JPEG_BUFFERS_COUNT-', 1)
    sg.user_settings_set_entry('-STREAMING_FILENAME-', 'my_streaming.jpg')  # Streaming image file name

active_checkbox = sg.user_settings_get_entry('-STREAMING_CHECKBOX-')
frame_rate = sg.user_settings_get_entry('-STREAMING_FPS-')
streaming_width = sg.user_settings_get_entry('-STREAMING_WIDTH-')
streaming_height = sg.user_settings_get_entry('-STREAMING_HEIGHT-')
streaming_jpgbufsize_div = sg.user_settings_get_entry('-STREAMING_JPEG_SIZE_DIV-')
streaming_buff_cnt = sg.user_settings_get_entry('-STREAMING_JPEG_BUFFERS_COUNT-')
streaming_filename = sg.user_settings_get_entry('-STREAMING_FILENAME-')

jpeg_buffer_size = int((streaming_width * streaming_height * bytes_per_pixel) / streaming_jpgbufsize_div)

my_tab1_layout = [
    [sg.Frame('Streaming', [
        [sg.Checkbox('Active', default=active_checkbox, enable_events=True, key='-STREAMING_CHECKBOX-'),
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
    [sg.Button('Get Versions', key='-VERSIONS-')]
]


my_tab2_layout = []
my_tab3_layout = []
my_tabs_group_layout = [
    [sg.Tab('Camera', my_tab1_layout, key='-TAB1-'),
     sg.Tab('Debug1', my_tab2_layout, key='-TAB2-'),
     sg.Tab('Debug2', my_tab3_layout, key='-TAB3-')]
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

window = sg.Window('Spresense Camera App', layout, margins=(0, 0), finalize=True, titlebar_font='bold',
                   enable_close_attempted_event=True)
show_the_image('streaming', 'Spresense_Splash3.JPG', resize=True)  # Show the start up image
show_the_image('still', 'Spresense_Splash3.JPG', resize=True)  # Show the start up image
spresense_not_found = connect_to_spresense()

window['-STREAMING_WIDTH-'].bind('<FocusIn>', 'GOT_FOCUS')   # Used to provide an event when input field gets focus
window['-STREAMING_HEIGHT-'].bind('<FocusIn>', 'GOT_FOCUS')  # Used to provide an event when input field gets focus


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
        # time.sleep(2)
        send_spresense_command('cam_stream_stop\n', 0, 'silent')  # tell the Spresense to stop streaming 2nd
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
        print('A:', values['-STREAMING_CHECKBOX-'])
        print('B:', int(values['-STREAMING_CHECKBOX-']))
        if values['-STREAMING_CHECKBOX-']:
            threading.Thread(target=camera_streaming_mode, args=(window,), daemon=True).start()
    elif event == '-THREAD-':
        mprint('Streaming video stopped')
        time.sleep(0.100)
        send_spresense_command('cam_stream_stop\n', 0, 'silent')  # tell the Spresense to stop streaming 2nd
    elif event == '-VERSIONS-':
        mprint('---------------------------------------')
        mprint(sg.get_versions())
        mprint('---------------------------------------')


window.close()


# My NOTES.................................................................................................
# Supports three "print" methods to send out information:
# print('Hello World')       # Print to Shell output
# sg.Print('Hello World')    # Prints to a PySimpleGUI Debug Popup Window
# mprint('Hello World')      # Prints to this application's System Information Window, multiline element
