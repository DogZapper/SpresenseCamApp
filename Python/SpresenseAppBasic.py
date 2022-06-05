import PySimpleGUI as sg
from PIL import Image, ImageTk

#-------------------------------------------------
# SUBROUTINES
# Define your Python subroutines at the start
#-------------------------------------------------

def show_the_image(image_file, resize):
    # User interface image frame size is fixed, see size below...
    # This routine will resize your image to match that window, if you ask
    my_UI_image_frame_size = (500, 400)
    im = Image.open(image_file, formats=None)
    if resize == True:
        im = im.resize(my_UI_image_frame_size, resample=Image.BICUBIC)
    image = ImageTk.PhotoImage(image=im)       # convert to ImageTK image type because PySimpleGUI works on these
    im.close()                                 # close the open, original image file
    window['-IMAGE-'].update(data=image)       # Show this image on the UI

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
    ]
middle_column = [
        [sg.Text('Working image below is fixed at 500 x 400 pixels',justification='center',expand_x=True)],
        [sg.Image(size=(500, 400), key='-IMAGE-')],
        [sg.Text('To view full resolution image, see filenames to the right.',justification='center',expand_x=True)],
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
show_the_image("Spresense_Splash3.JPG",resize=True)     #Show the start up image

while True:                             # The Event Loop
    event, values = window.read() 
    print(event, values)       
    if event == sg.WIN_CLOSED or event == 'Exit':
        break       

window.close()
