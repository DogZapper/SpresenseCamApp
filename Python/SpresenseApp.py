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


# -------------------------------------------------
# SUBROUTINES
# Define your Python subroutines at the start
# -------------------------------------------------

# User interface image frame sizes are fixed, see sizes below...
# This routine will resize your image to match frame size, if you ask
def show_the_image(location, image_file, resize):
    if location == 'streaming':
        my_ui_image_frame_size = (250, 200)
        image_to_update = '-STREAMING_IMAGE-'
    else:
        my_ui_image_frame_size = (500, 400)
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
# MAIN
# Start up code and main routine starts here
# jpeg_buffer_size = (img_width * img_height * bytes_per_pixel) / jpgbufsize_divisor
# bytes_per_pixel = 2
# -------------------------------------------------
sg.theme('DarkGreen3')
# Some GLOBALS-------------------------------------
my_bg_color = sg.theme_input_background_color()
streaming_width = 96
streaming_height = 64
streaming_jpgbufsize_div = 7
bytes_per_pixel = 2
jpeg_buffers = 1

jpeg_buffer_size = int((streaming_width * streaming_height * bytes_per_pixel) / streaming_jpgbufsize_div)

my_tab1_layout = [
    [sg.Frame('Streaming', [
        [sg.Checkbox('Active'), sg.T('Frame Rate:'),
         sg.Combo(['5 FPS', '6 FPS', '7.5 FPS', '15 FPS', '30 FPS', '60 FPS', '120 FPS'], size=(8, 1),
                  default_value='5 FPS', readonly=True, enable_events=True, key='-PIX_FPS-')],
        [sg.Text('Image size in pixels:')],
        [sg.T('Width:', pad=((12, 5), (0, 0))), sg.Input(streaming_width, s=5, enable_events=True,
                                                         key='-STREAMING_WIDTH-'),
         sg.T('X'),
         sg.T('Height:'), sg.Input(streaming_height, size=5, enable_events=True, key='-STREAMING_HEIGHT-')],
        [sg.T('Format:'), sg.Combo(['RGB565', 'YUV422', 'JPG', 'GRAY', 'NONE'], s=(7, 1), default_value='JPG',
                                   readonly=True, key='-PIX_FMT-')],
        [sg.Frame('JPEG Settings', [
            [sg.T('Div:'), sg.Combo(['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11'],
                                    s=(3, 1), default_value=str(streaming_jpgbufsize_div), readonly=True,
                                    enable_events=True, key='-STREAMING_JPEG_SIZE_DIV-'),
             sg.T('Buffers:'), sg.Combo(['1', '2'], size=(3, 1), default_value=str(jpeg_buffers), readonly=True,
                                        key='-STREAMING_JPEG_SIZE_DIV-')],
            [sg.T('Buffer Size (bytes):'), sg.Text(jpeg_buffer_size, s=(8, 1), expand_x=True, justification='center',
                                                   text_color='black', background_color=my_bg_color,
                                                   key='-STREAMING_JPEG_BUFF_SIZE-')]])],
        [sg.Text('Streaming Filename:')], [sg.Input('my_streaming.jpg', size=(32, 1), disabled=True,
                                                    key='-STREAM_FILENAME-')]])]]


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
    [sg.Text('Streaming Frame - Fixed 250 x 200 pixels', pad=(100, 0))],
    [sg.Image(size=(250, 200), pad=((100, 0), (0, 10)), key='-STREAMING_IMAGE-'),
     sg.Text('Actual:'),
     sg.Text(size=(5, 1), text_color='black', background_color=my_bg_color, key='-FPS-'),
     sg.Text('FPS')],
    [sg.Text('Still Image Frame - Fixed 500 x 400 pixels', pad=(0, 0))],
    [sg.Image(size=(500, 400), pad=((0, 0), (0, 0)), key='-STILL_IMAGE-')],
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

window = sg.Window('Spresense Camera App', layout, margins=(0, 0), finalize=True, titlebar_font='bold')
show_the_image('streaming', 'Spresense_Splash3.JPG', resize=True)  # Show the start up image
show_the_image('still', 'Spresense_Splash3.JPG', resize=True)  # Show the start up image
spresense_not_found = connect_to_spresense()

window['-STREAMING_WIDTH-'].bind('<FocusIn>', 'GOT_FOCUS')   # Used to provide an event when input field gets focus
window['-STREAMING_HEIGHT-'].bind('<FocusIn>', 'GOT_FOCUS')  # Used to provide an event when input field gets focus

while True:  # The Event Loop
    event, values = window.read()
    print('event:', event)        # This print, for debug only
    # print('values:', values)    # This print, for debug only
    if spresense_not_found:
        print('Spresense Comm Port not found')
        window.close()
        break
    if event == sg.WIN_CLOSED or event == 'Exit':
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
        streaming_jpgbufsize_div = int(values['-STREAMING_JPEG_SIZE_DIV-'])
        calculate_jpeg_buffer_size('streaming')


window.close()


# My NOTES.................................................................................................
# Supports three "print" methods to send out information:
# print('Hello World')       # Print to Shell output
# sg.Print('Hello World')    # Prints to a PySimpleGUI Debug Popup Window
# mprint('Hello World')      # Prints to this application's System Information Window, multiline element
