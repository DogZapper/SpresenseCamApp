import PySimpleGUI as sg      

sg.theme('DarkAmber')    # Keep things interesting for your users

layout = [[sg.Text('Persistent window')],      
          [sg.Input(key='-IN-')],      
          [sg.Button('Read', key='-READ-'), sg.Exit()]]

window = sg.Window('Window that stays open', layout)      

while True:                             # The Event Loop
    event, values = window.read() 
    print(event, values)       
    if event == sg.WIN_CLOSED or event == 'Exit':
        break
    elif event == '-READ-':
        print('You typed:', values)
        sg.popup_error(title='You typed something', line_width=20, no_titlebar=False)

window.close()
