import PySimpleGUI as sg
from PIL import Image, ImageTk

#-------------------------------------------------
# SUBROUTINES
# Define your Python subroutines at the start
#-------------------------------------------------

def show_the_image(location,image_file, resize):
    # User interface image frame sizes are fixed, see sizes below...
    # This routine will resize your image to match frame size, if you ask
    if(location == 'streaming'):
        my_UI_image_frame_size = (250, 200)
        image_to_update = '-STREAMING_IMAGE-'
    else:
        my_UI_image_frame_size = (500, 400)
        image_to_update = '-STILL_IMAGE-'

    im = Image.open(image_file, formats=None)
    if resize == True:
        im = im.resize(my_UI_image_frame_size, resample=Image.BICUBIC)
    image = ImageTk.PhotoImage(image=im)            # convert to ImageTK image type because PySimpleGUI works on these
    im.close()                                      # close the opened, original image file
    window[image_to_update].update(data=image)      # Show this image on the UI, streaming image frame (top), still (bottom)

def mprint(*args, **kwargs):  #Prints to this application's System Information Window
    window['-MY_TERMINAL_WINDOW-'].print(*args, **kwargs)

#-------------------------------------------------
# MAIN
# Start up code and main routine starts here
#-------------------------------------------------
sg.theme('DarkGreen3')

my_tab1_layout = []
my_tab2_layout = []
my_tab3_layout = []

my_tabs_group_layout = [
    [sg.Tab('Camera',my_tab1_layout,key='-TAB1-'),
     sg.Tab('Debug1',my_tab2_layout,key='-TAB2-'), 
     sg.Tab('Debug2',my_tab3_layout,key='-TAB3-')]
]

left_column = [
    [sg.Text('System Information Window',size=(40,1),font=('Ariel',12,'bold'),justification='center')],
    [sg.HorizontalSeparator()],
    [sg.Multiline(font='courier',size=(39,37),autoscroll=True,auto_refresh=True,reroute_stdout=False,
     do_not_clear=True,disabled=True,key='-MY_TERMINAL_WINDOW-')]
]
middle_column = [
    [sg.Text('Streaming Image Buffer')],
    [sg.Image(size=(250, 200), key='-STREAMING_IMAGE-')],
    [sg.Text('Still Image Buffer')],
    [sg.Image(size=(500, 400), key='-STILL_IMAGE-')],
    [sg.Text('Working images above are fixed sizes.',justification='center',expand_x=True)],
    [sg.Text('To view full resolution images, see filenames to the right.',justification='center',expand_x=True)],
]
right_column = [
        [sg.TabGroup(my_tabs_group_layout,expand_x=True,key='-TAB_CHANGE-',
                    enable_events=True, tab_location='topleft')]
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
show_the_image('streaming','Spresense_Splash3.JPG',resize=True)     # Show the start up image
show_the_image('still','Spresense_Splash3.JPG',resize=True)         # Show the start up image

#Support for three ways to send out information:
#print('Hello World')       #Print to Shell output
#sg.Print('Hello World')    #Prints to a Debug Popup Window
mprint('Hello World')       #Prints to this application's System Information Window

while True:                                             # The Event Loop
    event, values = window.read() 
    print(event, values)       
    if event == sg.WIN_CLOSED or event == 'Exit':
        break       

window.close()
