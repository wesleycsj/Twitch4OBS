#!/usr/bin/python3

"""
The MIT License (MIT)

Copyright (c) 2020 WesleyCSJ - wesleyjr10@gmail.com

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.

"""

import obspython as obs
import socket
import threading
import re

HOST            = "irc.chat.twitch.tv"    # The remote host 
PINGPONG_SERVER = ":tmi.twitch.tv"
PORT            = 6667         # The same port as used by the server
STOP_SIGNAL     = False
SOCKET          = None

# RESOURCES OF COLUMN AND LINE SIZE
TEXTSOURCE_BUFFER = []

CONNECTBUTTON_RESOURCE = None

COLUMN_RESOURCE   = None
COLUMN_VALUE       = 1

LINE_RESOURCE     = None
LINE_VALUE         = 1

OAUTH_RESOURCE  = None
OAUTH_VALUE     = ""

USERNAME_RESOURCE   = None
USERNAME_VALUE      = ""

CHANNEL_RESOURCE = None
CHANNEL_VALUE   = ""

TEXTSOURCE_VALUE    = ""


def socket_connect(property, obj):
    global SOCKET
    try:
        SOCKET = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        SOCKET.connect((HOST, PORT))
        SOCKET.send(bytes("PASS {}\r\n".format (OAUTH_KEY), "UTF-8"))
        SOCKET.send(bytes("NICK {}\r\n".format (USERNAME_VALUE) , "UTF-8"))
        SOCKET.send(bytes("JOIN #{}\r\n".format(CHANNEL_VALUE) , "UTF-8"))
        start_thread()
    except OSError:
        print("OSError: Transport endpoint not connected")
    except ConnectionRefusedError:
        print("ConnectionRefusedError: Could not connect to Node.js server.")

def start_thread():
    print("Starting Thread")
    global STOP_SIGNAL
    STOP_SIGNAL = True
    try:
        RECEIVE_THREAD.start()
    except:
        print("ERROR: Could not start the chat service.")


def thread_data(name):    
    source = obs.obs_get_source_by_name(TEXTSOURCE_VALUE)
    button = obs.obs_get_source_by_name("btn_connect")

    print("Started the chat service.")

    while STOP_SIGNAL:
        data = None
        try:
            data = SOCKET.recv(1024).decode("utf-8")
            if not data:
                break
        except:
            print("ERROR: Non valid data received to be parsed.")
            break
        #Parses the IRC line and returns a dictionary with the command
        content = parse_message(data)
        if not content['command'] == None:
            if content['command'] == "PING":
                SOCKET.sendall(bytes("PONG {}\r\n".format(PINGPONG_SERVER),"UTF-8"))
            elif content['command'] == "PRIVMSG":
                append_buffer(source, "{}: {}".format(content['username'], content['message']))
    obs.obs_source_release(source)
    print("Stopping the chat service.")

RECEIVE_THREAD = threading.Thread(target=thread_data, args=(1,))

def parse_message(data):
    commandDict = dict()
    msgRAW = data.strip()

    if (msgRAW ==  "PING {}".format(PINGPONG_SERVER)):
        commandDict["command"] = "PING"
        return commandDict

    msgCommand = msgRAW.split(":")[1].split(" ")[1]
    msgContent = msgRAW.split(":")[2]

    if msgCommand == "PRIVMSG":
        username = msgRAW.split(":")[1].split(" ")[0].split("!")[0]
        username = "@{}".format(username)
        commandDict[ "command" ]  = "PRIVMSG"
        commandDict[ "username"]  = username
        commandDict[ "message" ]  = msgContent
    else:
        commandDict["command"]  = None
    return commandDict

def append_buffer(source, data):
    textData = data
    lineBuffer = ""
    if (len(textData) <= COLUMN_SIZE):
        append_fixedSizeText(TEXTSOURCE_BUFFER, textData)
    else:
        iterations = int(len(textData) / COLUMN_SIZE)
        odd_slices = (len(textData) > ((len(textData) % COLUMN_SIZE) * iterations))
        for i in range(0, iterations):
            firstPos   = (i * COLUMN_SIZE)
            lastPos    = (firstPos + COLUMN_SIZE)
            slicedLine = textData[firstPos:lastPos]
            append_fixedSizeText(TEXTSOURCE_BUFFER, slicedLine)
        if (odd_slices):
            firstPos = (iterations * COLUMN_SIZE)
            append_fixedSizeText(TEXTSOURCE_BUFFER, textData[firstPos:])

    while (len(TEXTSOURCE_BUFFER) > LINE_SIZE):
        TEXTSOURCE_BUFFER.pop(0)

    render_textSource(source)

def append_fixedSizeText(array, data):
    fixedData = data.lstrip()
    if (len(fixedData) < COLUMN_SIZE):
        while (len(fixedData) < COLUMN_SIZE):
            fixedData = fixedData + " "
    array.append(fixedData)

def render_textSource(source):
    textData = ""
    for lineCounter in range(0, len(TEXTSOURCE_BUFFER)):
            textData = textData + TEXTSOURCE_BUFFER[lineCounter]
            if (lineCounter != (len(TEXTSOURCE_BUFFER) - 1)):
                textData = textData + "\n"

    settings = obs.obs_data_create()
    obs.obs_data_set_string(settings, "text", textData)
    obs.obs_source_update(source, settings)
    obs.obs_data_release(settings)

# OBS Script Functions
def script_properties():
    global CONNECTBUTTON_RESOURCE
    props = obs.obs_properties_create()
    sources = obs.obs_enum_sources()

    CONNECTBUTTON_RESOURCE = obs.obs_properties_add_button(props, "btn_connect", "Connect", socket_connect)

    source_list = obs.obs_properties_add_list(props, "TEXT_SOURCE", "Text source", obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING)
    
    if sources is not None:
        for source in sources:
            source_id = obs.obs_source_get_unversioned_id(source)
            if source_id == "text_gdiplus" or source_id == "text_ft2_source":
                name = obs.obs_source_get_name(source)
                obs.obs_property_list_add_string(source_list, name, name)
        obs.source_list_release(sources)
   
   
    COLUMN_RESOURCE   = obs.obs_properties_add_int  (props, "COLUMN_SIZE", "Column Size", 1, 100, 1)
    LINE_RESOURCE     = obs.obs_properties_add_int  (props, "LINE_SIZE",   "Line Size", 1, 100, 1)
    USERNAME_RESOURCE = obs.obs_properties_add_text (props, "USERNAME_VALUE", "Username", obs.OBS_TEXT_DEFAULT)
    CHANNEL_RESOURCE = obs.obs_properties_add_text (props, "CHANNEL_VALUE", "Channel", obs.OBS_TEXT_DEFAULT)
    OAUTH_RESOURCE    = obs.obs_properties_add_text (props, "OAUTH_VALUE", "OAUTH Key", obs.OBS_TEXT_PASSWORD)

    return props

def script_update(settings):
    global COLUMN_SIZE
    global LINE_SIZE
    global USERNAME_VALUE
    global CHANNEL_VALUE
    global OAUTH_KEY
    global TEXTSOURCE_VALUE
    COLUMN_SIZE       = obs.obs_data_get_int    (settings,    "COLUMN_SIZE"   )
    LINE_SIZE         = obs.obs_data_get_int    (settings,    "LINE_SIZE"     )
    USERNAME_VALUE    = obs.obs_data_get_string (settings,    "USERNAME_VALUE")
    USERNAME_VALUE    = USERNAME_VALUE.lower()
    CHANNEL_VALUE     = obs.obs_data_get_string (settings,    "CHANNEL_VALUE")
    CHANNEL_VALUE     = CHANNEL_VALUE.lower()
    OAUTH_KEY         = obs.obs_data_get_string (settings,    "OAUTH_VALUE"   ) 
    TEXTSOURCE_VALUE  = obs.obs_data_get_string (settings,    "TEXT_SOURCE"    )

def script_unload():
    global STOP_SIGNAL 
    STOP_SIGNAL = False
    if not SOCKET == None:
        SOCKET.shutdown(0)
        SOCKET.close()
    print("Chat script unload.")
