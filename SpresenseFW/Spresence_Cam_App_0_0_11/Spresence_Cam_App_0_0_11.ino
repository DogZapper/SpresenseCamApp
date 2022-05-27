//-------------------------------------------------------------
// Spresense Firmware
// Terry Carpenter
// 04/16/2022
//-------------------------------------------------------------
//Includes
//-----------------------
#include <SDHCI.h>
#include <stdio.h>
#include <Camera.h>
#include <RTC.h>

SDClass theSD;
#define MAX_PICTURE_COUNT     (10)  //900 images = 15 minutes, SD holds 20,000 images
#define TIME_HEADER 'T'             // Header tag for serial time sync message
char inbuffer[50];                  //used for holding incoming serial commands from host computer
char *in_ptr;                       //pointer to next empty spot in inbuffer
bool command_available;             //flag to indicate a command is pending
bool False = 0;
bool True  = 1;
int led_delay = 50;                //used to scan Spresence row of leds (to monitor activity)

//======GLOBAL CAMERA SYTEM SETTING VARIABLES=======================================================
CAM_DEVICE_TYPE     camera_device_type;                                     //request identification at startup
int                 bytes_per_pixel     = 2;                                //16 bit pixels
int                 still_img_width     = CAM_IMGSIZE_3M_H;                 //2048 Horizontal/Width  
int                 still_img_height    = CAM_IMGSIZE_3M_V;                 //1536 Vertical/Height 
CAM_IMAGE_PIX_FMT   still_img_format    = CAM_IMAGE_PIX_FMT_JPG;            //JPEG IMAGE COMPRESSION
int                 jpgbufsize_divisor  = 7;                                //Part of JPEG Buffer Size Formula: (already defined in camera.h)
                                                                            //jpeg_buffer_size = (still_img_width * still_img_height * bytes_per_pixel) / jpgbufsize_divisor
                                                                            //jpeg_buffer_size = (        2048    *       1536       *        2       ) /         (7)
                                                                            //jpeg_buffer_size = 898,779 bytes
CAM_WHITE_BALANCE   white_balance_mode  = CAM_WHITE_BALANCE_FLUORESCENT ;   //Default Current white balance mode setting 
CAM_SCENE_MODE      camera_scene_mode   = CAM_SCENE_MODE_NONE;              //Default camera scene mode (NOT SUPPORTED)
CAM_COLOR_FX        camera_color_fx     = CAM_COLOR_FX_NONE;                //Default camera fx mode
CAM_HDR_MODE        camera_hdr_mode     = CAM_HDR_MODE_OFF;                 //Default is camera_hdr_mode off
int                 camera_buff_num     = 1;                                //Default number of video stream buffers
CAM_VIDEO_FPS       camera_frm_per_sec  = CAM_VIDEO_FPS_60;                 //Default will be 30 fps
int                 camera_video_width  = CAM_IMGSIZE_QVGA_H;               //Default video horizontal width is VGA (640)
int                 camera_video_height = CAM_IMGSIZE_QVGA_V;               //Default video vertical height  is VGA (480)
CAM_IMAGE_PIX_FMT   camera_video_format = CAM_IMAGE_PIX_FMT_JPG;            //Default = CAM_IMAGE_PIX_FMT_JPG

//------------------------------------------------
// Spresence Camera Application 
// Hardware Initialization Routine
//------------------------------------------------
void    spresenseInitialization()
{
    CamErr err;
    in_ptr = inbuffer;          //initialize buffer pointer
    command_available = False;
        
    pinMode(LED0, OUTPUT);
    pinMode(LED1, OUTPUT);
    pinMode(LED2, OUTPUT);
    pinMode(LED3, OUTPUT);
//  Serial.begin(115200);     //For testing only
//  Serial.begin(2000000);    //invalid, my computer spresence combo would not run at this speed!
//  Serial.begin(1000000);    //OK to use, supported by Arduino serial monitor
    Serial.begin(1200000);    //FASTEST ONE...NOT supported by Arduino serial monitor

    err = theCamera.begin(
        camera_buff_num,                //default = 1
        camera_frm_per_sec,             //default = CAM_VIDEO_FPS_5
        camera_video_width,             //default = CAM_IMGSIZE_QVGA_H (320)
        camera_video_height,            //default = CAM_IMGSIZE_QVGA_V (240)
        camera_video_format,            //default = CAM_IMAGE_PIX_FMT_JPG
        jpgbufsize_divisor              //default = 7 
        );                        
    if (err != CAM_ERR_SUCCESS)
    {
        printf("Camera Error:%d\n",err);
    }

    //Maximum Still Image Resolution
    err = theCamera.setStillPictureImageFormat(
        still_img_width,                           //2048 Horz Pixels
        still_img_height,                          //1536 Vert Pixels
        still_img_format,                          //default = CAM_IMAGE_PIX_FMT_JPG
        jpgbufsize_divisor);
        
//    if (err != CAM_ERR_SUCCESS)
//    {
//        f("Camera Error:%d\n",err);
//        if(err == -4)   printf("CAM_ERR_NOT_INITIALIZED:%d\n",err);
//        if(err == -7)   printf("CAM_ERR_INVALID_PARAM:%d\n",err);
//        if(err == -8)   printf("CAM_ERR_NO_MEMORY:%d\n",err);
//    }
//    else
//        //Serial.println("Camera ready for taking still images.");

    theCamera.setAutoWhiteBalanceMode(white_balance_mode);      //default to CAM_WHITE_BALANCE_AUTO
    //theCamera.setSceneMode(camera_scene_mode);                //NOT SUPPORTED
    theCamera.setColorEffect(camera_color_fx);                  //default to none
    camera_hdr_mode = theCamera.getHDR();                       //get default HDR mode at startup, put in global variable
    camera_device_type = theCamera.getDeviceType();                       //get the default camera sensor type
    
    // Transfer the PC's time and date to the Spresence hardware
    // Initialize RTC at first
    RTC.begin();
    
    // Set the temporary RTC time from the PC at compile time (close enough!!!)
    RtcTime compiledDateTime(__DATE__, __TIME__);
    RTC.setTime(compiledDateTime);
}

void send_spresence_banner()
{
    printf("------------------------\n");
    printf("-  Spresense Firmware  -\n");
    printf("-   Terry Carpenter    -\n");
    printf("- Compiled Date, Time: -\n");
//  printf("- May  8 2022,16:27:31 -\n");
    printf("- %s,%s -\n",__DATE__,__TIME__);
    printf("------------------------\n");
}


//--------------------------
//Handle Serial Input
//--------------------------
void handleSerial() 
{
    while (Serial.available() > 0) 
    {
        char incomingCharacter = Serial.read();
        if(incomingCharacter == 0x0a)
        {
            *in_ptr = 0;                    //null terminator
            command_available = True;
            in_ptr = inbuffer;              //re-initialize buffer pointer
        }
        else
        {
            *in_ptr++ = incomingCharacter;   //put the character into the buffer
        }
    }
}

//------------------------------------------------------
// Handle Input Commands
// An input command is in the following format:
// 
//  command
//  string   num1 num2 num3 null
//  
//  commandx #### #### ####<0x00>
// 
//  Note:
//   1. Numbers following the command word are optional
//   2. Limit numbers to three per command
//   3. Command and numbers separated with space (0x20)
//------------------------------------------------------
void handleCommand() 
{
    CAM_DEVICE_TYPE type;
    long byte_counter;
    size_t image_size;
    uint8_t *byte_ptr;
    uint8_t byteVal;
    CamImage theImage;

    while (command_available)
    {
        //---multiple letter commands--------------------
        if(!strcmp(inbuffer,"+"))
        {
            //new way
            theImage = theCamera.takePicture();                         //one still snapshot image taken here... data stored in global "img" file
            image_size = theImage.getImgSize();
            //Serial.write(image_size);
            printf("%i\n",image_size);
            Serial.write(theImage.getImgBuff() , image_size);

            //old way
            // CamImage theImage = theCamera.takePicture();             //one still snapshot image taken here... data stored in global "img" file
            // size_t image_size = theImage.getImgSize();
            // printf("%i\n",image_size);
            // byte_ptr = theImage.getImgBuff();
            // for(byte_counter = 0; byte_counter < image_size; byte_counter++)
            // {
            //     byteVal = *byte_ptr++;
            //     Serial.print(byteVal);
            // }
        }
        else if(!strcmp(inbuffer,"!"))
        {
            //Exclamation Point...Echo Hello/Welcome Banner
            send_spresence_banner();
        }

        else if(!strcmp(inbuffer,"device_type"))
        {
            //go get the camera device type and echo the result
            type = theCamera.getDeviceType();
            if(type==CAM_DEVICE_TYPE_UNKNOWN)
                printf("CAMERA DEVICE TYPE UNKNOWN\n");
            else if(type==CAM_DEVICE_TYPE_ISX012)
                printf("CAMERA DEVICE TYPE ISX012\n");
            else if(type==CAM_DEVICE_TYPE_ISX019)
                printf("CAMERA DEVICE TYPE ISX019\n");
        }

        else if(!strcmp(inbuffer,"cam_info"))
        {
            printf("--- Camera Info ---\n");            //Parameter #1 - Title
            get_camera_info();
        }

        else if(!strcmp(inbuffer,"cam_stream_start"))
        {
            cam_streaming(True);
        }

        else if(!strcmp(inbuffer,"cam_stream_stop"))
        {
            //cam_streaming(False);
            theCamera.startStreaming(false,CamCB);    //STOP THE SONY CAMERA STREAMING
            //Reset the UART
            Serial.begin(1200000);                    //UART RESET
            led_delay = 50;                           //video streaming complete... toggle LEDS at slower speed
        }
            
    command_available = False;
    }
}

//------------------------------------------------------
// Camera Streaming Video Mode Routine
//------------------------------------------------------
void cam_streaming(bool stream_active)
{
    CamErr err;
    led_delay = 0;                                          //during video streaming mode toggle LEDS at max speed

    if(stream_active == True)
    {
        printf("--- Camera Streaming Mode ---\n");          //Host PC serial line #1
        camera_video_format = CAM_IMAGE_PIX_FMT_JPG;
        printf("video_format = JPG\n");                     //Host PC serial linee #2
        
        err = theCamera.begin(
            camera_buff_num,                //default = 1
            camera_frm_per_sec,             //default = CAM_VIDEO_FPS_120
            camera_video_width,             //default = CAM_IMGSIZE_QQVGA_H
            camera_video_height,            //default = CAM_IMGSIZE_QQVGA_V
            camera_video_format,            //default = CAM_IMAGE_PIX_FMT_JPG
            jpgbufsize_divisor              //default = 7 
            ); 
        camera_check_for_errors(err);                       //Host PC serial line #3
    
        err = theCamera.startStreaming(True,CamCB);         //CamCB is my call back routine, I get one of theses every video frame (I think?)
        camera_check_for_errors(err);                       //Host PC serial line #4
    }
    else
    {
        Serial.flush(); 
        //printf("Disable Camera Streaming...\n");            //Host PC serial line #1
        //err = theCamera.startStreaming(false,CamCB);
        //camera_check_for_errors(err);                       //Host PC serial line #2
    }
}




/****************************************************************************
 * Callback from Camera library when video frame is captured.
 * Notes:
 * CamImage img is the streaming video capture buffer
 ****************************************************************************/
void CamCB(CamImage img)
{
    long byte_counter;
    char* byte_ptr;
    char byteVal;
    size_t image_size;

  /* Check the img instance is available or not. */
    if (img.isAvailable()) 
    {
        image_size = img.getImgSize();
        printf("%i\n",image_size);
        //Serial.write(image_size);
        byte_ptr = img.getImgBuff();
        //Serial.write(img.getImgBuff() , image_size);
        for(byte_counter = 0; byte_counter < image_size; byte_counter++)
        {
            byteVal = *byte_ptr++;
            Serial.print(byteVal);
        }
    }
}

//----------------------------------------------------------
// Reports camera error status.
// Sends one print statement (line) to Host PC
//-----------------------------------------------------------
void camera_check_for_errors(CamErr error)
{
    switch(error)
    {
        case CAM_ERR_SUCCESS:
            printf("CAMERA READY...\n");
            break; 
        case CAM_ERR_NO_DEVICE:
            printf("NO CAMERA FOUND...\n");
            break;
        case CAM_ERR_ILLEGAL_DEVERR:
            printf("CAMERA SENSOR ERROR...\n");
            break;
        case CAM_ERR_ALREADY_INITIALIZED:
            printf("CAM_LIB ALREADY INITIALIZED...\n");
            break;   
        case CAM_ERR_NOT_INITIALIZED:
            printf("CAM_LIB IS NOT INITIALIZED...\n");
            break;
        case CAM_ERR_NOT_STILL_INITIALIZED:
            printf("STILL_PIC IS NOT INITIALIZED...\n");
            break;     
        case CAM_ERR_CANT_CREATE_THREAD:
            printf("CAM THREAD NOT CREATED...\n");
            break;   
        case CAM_ERR_INVALID_PARAM:
            printf("INVALID CAM PARAMETER...\n");
            break;
        case CAM_ERR_NO_MEMORY:
            printf("OUT OF CAM MEMORY...\n");
            break; 
        case CAM_ERR_USR_INUSED:
            printf("CAM BUFFER IN USE...\n");
            break; 
        case CAM_ERR_NOT_PERMITTED:
            printf("CAM REQUEST NOT PERMITTED...\n");
            break;      
    }
}

//------------------------------------------------------
// Get Camera global settings and send to PC
//------------------------------------------------------
void get_camera_info()
{
    char string_return[40];

    printf("camera_video_width:%i\n",camera_video_width);        //Parameter #2 - image_format
    printf("camera_video_height:%i\n",camera_video_height);      //Parameter #3 - image_format

    switch(camera_device_type)
    {
        case CAM_DEVICE_TYPE_UNKNOWN:
            strcpy(string_return,"UNKNOWN");
            break;
        case CAM_DEVICE_TYPE_ISX012:
            strcpy(string_return,"ISX012");
            break;
        case CAM_DEVICE_TYPE_ISX019:
            strcpy(string_return,"ISX019");
            break;
    }
    printf("image_format:%s\n",string_return);                  //Parameter #4 - image_format
    
    switch(still_img_format)
    {
        case CAM_IMAGE_PIX_FMT_RGB565:
            strcpy(string_return,"RGB565");
            break;
        case CAM_IMAGE_PIX_FMT_YUV422:
            strcpy(string_return,"YUV422");
            break;
        case CAM_IMAGE_PIX_FMT_JPG:
            strcpy(string_return,"JPG");
            break;
        case CAM_IMAGE_PIX_FMT_GRAY:
            strcpy(string_return,"GRAY");
            break;
        case CAM_IMAGE_PIX_FMT_NONE :
            strcpy(string_return,"NONE");
            break;
    }
    printf("still_image_format:%s\n",string_return);            //Parameter #5 - image_format
    printf("jpgbufsize_divisor:%d\n",jpgbufsize_divisor);       //Parameter #6 - jpgbufsize_divisor
    switch(white_balance_mode)
    {
        case CAM_WHITE_BALANCE_AUTO:
            strcpy(string_return,"AUTO");
            break;
        case CAM_WHITE_BALANCE_INCANDESCENT:
            strcpy(string_return,"INCANDESCENT");
            break;
        case CAM_WHITE_BALANCE_FLUORESCENT:
            strcpy(string_return,"FLUORESCENT");
            break;
        case CAM_WHITE_BALANCE_DAYLIGHT:
            strcpy(string_return,"DAYLIGHT");
            break;
        case CAM_WHITE_BALANCE_FLASH :
            strcpy(string_return,"FLASH");
            break;
        case CAM_WHITE_BALANCE_CLOUDY:
            strcpy(string_return,"CLOUDY");
            break;
        case CAM_WHITE_BALANCE_SHADE :
            strcpy(string_return,"SHADE");
            break;
    }
    printf("white_balance_mode:%s\n",string_return);            //Parameter #7 - white_balance_mode
    printf("jpeg_quality:%d\n",theCamera.getJPEGQuality());     //Parameter #8 - jpeg_quality
    switch(camera_scene_mode)
    {
        case CAM_SCENE_MODE_NONE:           //NOT SUPPORTED
            strcpy(string_return,"NONE");
            break;
    }
    printf("scene_mode:%s\n",string_return);                    //Parameter #9 - camera_scene_mode
    switch(camera_color_fx)
    {
        case CAM_COLOR_FX_NONE :           
            strcpy(string_return,"NONE");
            break;
        case CAM_COLOR_FX_BW :           
            strcpy(string_return,"B&W");
            break;
        case CAM_COLOR_FX_SEPIA :           
            strcpy(string_return,"SEPIA");
            break;
        case CAM_COLOR_FX_NEGATIVE :           
            strcpy(string_return,"NEGATIVE");
            break;
        case CAM_COLOR_FX_EMBOSS :           
            strcpy(string_return,"EMBOSS");
            break;
        case CAM_COLOR_FX_SKETCH :           
            strcpy(string_return,"SKETCH");
            break;
        case CAM_COLOR_FX_SKY_BLUE :           
            strcpy(string_return,"SKY_BLUE");
            break;
        case CAM_COLOR_FX_GRASS_GREEN :           
            strcpy(string_return,"GRASS_GREEN");
            break;   
        case CAM_COLOR_FX_SKIN_WHITEN :           
            strcpy(string_return,"WHITEN");
            break; 
        case CAM_COLOR_FX_VIVID :           
            strcpy(string_return,"VIVID");
            break;   
        case CAM_COLOR_FX_AQUA :           
            strcpy(string_return,"AQUA");
            break;
        case CAM_COLOR_FX_ART_FREEZE:           
            strcpy(string_return,"ART_FREEZE");
            break;   
        case CAM_COLOR_FX_SILHOUETTE :           
            strcpy(string_return,"SILHOUETTE");
            break; 
        case CAM_COLOR_FX_SOLARIZATION :           
            strcpy(string_return,"SOLARIZATION");
            break;   
        case CAM_COLOR_FX_ANTIQUE :           
            strcpy(string_return,"ANTIQUE");
            break;  
        CAM_COLOR_FX_SET_CBCR  :           
            strcpy(string_return,"SET_CBCR");
            break;     
        case CAM_COLOR_FX_PASTEL  :           
            strcpy(string_return,"PASTEL");
            break;                                         
    }
    printf("camera_fx:%s\n",string_return);                 //Parameter #10 - camera_fx
    int32_t jpeg_buffer_size = (still_img_width * still_img_height * bytes_per_pixel) / jpgbufsize_divisor;
    printf("jpeg_buffer_size:%i\n",jpeg_buffer_size);       //Parameter #11 - jpeg_buffer_size
    
    switch(camera_hdr_mode)
    {
        case CAM_HDR_MODE_OFF :           
            strcpy(string_return,"OFF");
            break;
        case CAM_HDR_MODE_AUTO :           
            strcpy(string_return,"AUTO");
            break;
        case CAM_HDR_MODE_ON  :           
            strcpy(string_return,"ON");
            break;
    }
    printf("high_dyn_range_mode:%s\n",string_return);       //Parameter #12 - high_dyn_range_mode

//    int32_t cam_exposure = theCamera.getAbsoluteExposure();
//        printf("Exposure Time:%7.3f ms\n",cam_exposure/100.0);
//    int cam_ISO = theCamera.getISOSensitivity();
//        printf("ISO Sensitivity:%i\n",cam_ISO);
}



//--------------------------
//Handle the LEDS scanning
//--------------------------
void handleLeds()  
{
    digitalWrite(LED0, HIGH);
    delay(led_delay);
    digitalWrite(LED1, HIGH);
    delay(led_delay);
    digitalWrite(LED2, HIGH);
    delay(led_delay);
    digitalWrite(LED3, HIGH);
    delay(led_delay);
    digitalWrite(LED0, LOW);
    delay(led_delay);
    digitalWrite(LED1, LOW);
    delay(led_delay);
    digitalWrite(LED2, LOW);
    delay(led_delay);
    digitalWrite(LED3, LOW);
    delay(led_delay);
}


//----------------------
//Arduino Setup Routine
//----------------------
void setup() 
{
    spresenseInitialization();
}

//--------------------------
//Arduino Main Loop Routine
//--------------------------
void loop() 
{
    handleSerial();     //process incomming characters one at a time
    handleCommand();    //this means we have a command to process
    handleLeds();       //this takes X seconds
}





 
