# Pi-hole Python Plugin
#
# Author: Xorfor
#
"""
<plugin key="xfr_pihole" name="Pi-hole summary" author="Xorfor" version="2.0.2" wikilink="https://github.com/Xorfor/Domoticz-Pi-hole-Plugin" externallink="https://pi-hole.net/">
    <params>
        <param field="Address" label="Pi-hole address" width="200px" required="true" default="pi.hole"/>
        <param field="Port" label="Port" width="30px" required="true" default="80"/>
        <param field="Mode1" label="API token" width="600px"/>
        <param field="Mode6" label="Debug" width="75px">
            <options>
                <option label="True" value="Debug"/>
                <option label="False" value="Normal" default="true"/>
            </options>
        </param>
    </params>
</plugin>
"""
import Domoticz
import json

_HEARTBEATS = 6 * 60  # 5 minutes

_API_PATH = "admin/api.php"
_API_SUMMARY = "summaryRaw"
_API_ENABLE = "enable"
_API_DISABLE = "disable"

# Devices
_DOMAINS_BLOCKED_UNIT = 1
_DNS_QUERIES_UNIT = 2
_ADS_BLOCKED_UNIT = 3
_ADS_PERCENTAGE_UNIT = 4
_UNIQUE_DOMAINS_UNIT = 5
_QUERIES_FORWARDED_UNIT = 6
_QUERIES_CACHED_UNIT = 7
_CLIENTS_EVER_SEEN_UNIT = 8
_UNIQUE_CLIENTS_UNIT = 9
# Switch
_PIHOLE_SWITCH = 10


class BasePlugin:

    def __init__(self):
        self.__jsonConn = None
        self.__runAgain = 0
        self.__headers = {}
        self.__url = ""
        self.__pihole_active = False

    def onStart(self):
        Domoticz.Debug("onStart called")
        if Parameters["Mode6"] == "Debug":
            Domoticz.Debugging(1)

        # Images
        # Check if images are in database
        if "xfr_pihole" not in Images:
            Domoticz.Image("xfr_pihole.zip").Create()
        image = Images["xfr_pihole"].ID
        Domoticz.Log("Image created. ID: "+str(image))

        # Create devices
        if len(Devices) == 0:
            # Use Custom. Counter Incremental gives kWh!!!
            # Following devices are set on used by default
            Domoticz.Device(Unit=_DOMAINS_BLOCKED_UNIT, Name="Domains Blocked", TypeName="Custom", Options={"Custom": "1;"}, Used=1, Image=image).Create()
            Domoticz.Device(Unit=_DNS_QUERIES_UNIT, Name="DNS Queries", TypeName="Custom", Options={"Custom": "1;"}, Used=1, Image=image).Create()
            Domoticz.Device(Unit=_ADS_BLOCKED_UNIT, Name="Ads Blocked", TypeName="Custom", Options={"Custom": "1;"}, Used=1, Image=image).Create()
            # Domoticz.Device(Unit=_ADS_PERCENTAGE_UNIT, Name="Ads Percentage", TypeName="Percentage", Used=1, Image=image).Create()  # Image not working :(
            Domoticz.Device(Unit=_ADS_PERCENTAGE_UNIT, Name="Ads Percentage", TypeName="Custom", Options={"Custom": "1;%"}, Used=1, Image=image).Create()  # Image not working :(
            # Following devices are NOT set on used. Can be done by user
            Domoticz.Device(Unit=_UNIQUE_DOMAINS_UNIT, Name="Unique Domains", TypeName="Custom", Options={"Custom": "1;"}, Image=image).Create()
            Domoticz.Device(Unit=_QUERIES_FORWARDED_UNIT, Name="Queries Forwarded", TypeName="Custom", Options={"Custom": "1;"}, Image=image).Create()
            Domoticz.Device(Unit=_QUERIES_CACHED_UNIT, Name="Queries Cached", TypeName="Custom", Options={"Custom": "1;"}, Image=image).Create()
            Domoticz.Device(Unit=_CLIENTS_EVER_SEEN_UNIT, Name="Clients Ever Seen", TypeName="Custom", Options={"Custom": "1;"}, Image=image).Create()
            Domoticz.Device(Unit=_UNIQUE_CLIENTS_UNIT, Name="Unique Clients", TypeName="Custom", Options={"Custom": "1;"}, Image=image).Create()
            # Create On/Off switch when API Token is defined
            if Parameters["Mode1"]:
                Domoticz.Device(Unit=_PIHOLE_SWITCH, Name="On/Off", TypeName="Switch", Used=1, Image=image).Create()
        else:
            if not Parameters["Mode1"] and _PIHOLE_SWITCH in Devices:
                # No API Token, so no reason for an On/Off switch
                Domoticz.Device(Unit=_PIHOLE_SWITCH).Delete()
            if Parameters["Mode1"] and _PIHOLE_SWITCH not in Devices:
                Domoticz.Device(Unit=_PIHOLE_SWITCH, Name="On/Off", TypeName="Switch", Used=1, Image=image).Create()

        Domoticz.Log("Devices created.")
        DumpConfigToLog()
        # Create connection
        self.__jsonConn = Domoticz.Connection(Name="Pi-hole", Transport="TCP/IP", Protocol="HTTP", Address=Parameters["Address"], Port=Parameters["Port"])
        self.__headers = {'Content-Type': 'text/xml; charset=utf-8',\
                                          'Connection': 'keep-alive',\
                                          'Accept': 'Content-Type: text/html; charset=UTF-8',\
                                          'Host': Parameters["Address"] + ":" + Parameters["Port"],\
                                          'User-Agent': 'Domoticz/1.0'}

    def onStop(self):
        Domoticz.Debug("onStop called")

    def onConnect(self, Connection, Status, Description):
        Domoticz.Debug("onConnect called ("+str(Status)+"): "+Description)
        # If connection is succesfull, send data depending on the specified url
        if Status == 0:
            sendData = {'Verb': 'GET',
                        'URL': self.__url,
                        'Headers': self.__headers
                        }
            Domoticz.Debug("sendData: " + str(sendData))
            self.__jsonConn.Send(sendData)

    def onMessage(self, Connection, Data):
        Domoticz.Debug("onMessage called")
        # Data returned from Send
        strData = Data["Data"].decode("utf-8", "ignore")
        Domoticz.Debug("Data: " + strData)
        jsonData = json.loads(strData)
        # Format:
        # {
        #   "domains_being_blocked":106541,
        #   "dns_queries_today":9795,
        #   "ads_blocked_today":2371,
        #   "ads_percentage_today":24.206228,
        #   "unique_domains":1477,
        #   "queries_forwarded":4705,
        #   "queries_cached":2420,
        #   "clients_ever_seen":8,
        #   "unique_clients":8,
        #   "status":"enabled"
        # }
        # Check first the status of Pi-hole
        tag = "status"
        if tag in jsonData:
            Domoticz.Debug(tag+": " + str(jsonData[tag]))
            if str(jsonData[tag]) == "enabled":
                self.__pihole_active = True
                UpdateDevice(_PIHOLE_SWITCH, 1, "On", AlwaysUpdate=self.__pihole_active)
            else:
                self.__pihole_active = False
                UpdateDevice(_PIHOLE_SWITCH, 0, "Off", AlwaysUpdate=self.__pihole_active)
        # Update summary data
        tag = "domains_being_blocked"
        if tag in jsonData:
            Domoticz.Debug(tag+": " + str(jsonData[tag]))
            if self.__pihole_active:
                UpdateDevice(_DOMAINS_BLOCKED_UNIT, jsonData[tag], str(jsonData[tag]), AlwaysUpdate=True)
            else:
                UpdateDevice(_DOMAINS_BLOCKED_UNIT, 0, str(jsonData[tag]), AlwaysUpdate=True)  # Pi-hole will return 'N/A'
        tag = "dns_queries_today"
        if tag in jsonData:
            Domoticz.Debug(tag+": " + str(jsonData[tag]))
            UpdateDevice(_DNS_QUERIES_UNIT, jsonData[tag], str(jsonData[tag]))
        tag = "ads_blocked_today"
        if tag in jsonData:
            Domoticz.Debug(tag+": " + str(jsonData[tag]))
            UpdateDevice(_ADS_BLOCKED_UNIT, jsonData[tag], str(jsonData[tag]))
        tag = "ads_percentage_today"
        if tag in jsonData:
            Domoticz.Debug(tag+": " + str(jsonData[tag]))
            UpdateDevice(_ADS_PERCENTAGE_UNIT, int(jsonData[tag]), str(jsonData[tag]))

        tag = "unique_domains"
        if tag in jsonData:
            Domoticz.Debug(tag+": " + str(jsonData[tag]))
            UpdateDevice(_UNIQUE_DOMAINS_UNIT, jsonData[tag], str(jsonData[tag]))
        tag = "queries_forwarded"
        if tag in jsonData:
            Domoticz.Debug(tag+": " + str(jsonData[tag]))
            UpdateDevice(_QUERIES_FORWARDED_UNIT, jsonData[tag], str(jsonData[tag]))
        tag = "queries_cached"
        if tag in jsonData:
            Domoticz.Debug(tag+": " + str(jsonData[tag]))
            UpdateDevice(_QUERIES_CACHED_UNIT, jsonData[tag], str(jsonData[tag]))
        tag = "clients_ever_seen"
        if tag in jsonData:
            Domoticz.Debug(tag+": " + str(jsonData[tag]))
            UpdateDevice(_CLIENTS_EVER_SEEN_UNIT, jsonData[tag], str(jsonData[tag]), AlwaysUpdate=True)
        tag = "unique_clients"
        if tag in jsonData:
            Domoticz.Debug(tag+": " + str(jsonData[tag]))
            UpdateDevice(_UNIQUE_CLIENTS_UNIT, jsonData[tag], str(jsonData[tag]), AlwaysUpdate=True)

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Debug(
            "onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))
        if Unit == _PIHOLE_SWITCH:
            # User clicked on the On/Off switch. Setup the correct url
            if str(Command) == "Off":
                self.__url = "/" + _API_PATH + "?" + _API_DISABLE
            elif str(Command) == "On":
                self.__url = "/" + _API_PATH + "?" + _API_ENABLE
            else:
                self.__url = ""
            # If valid command, add the API token from Pi-hole and send data
            if self.__url:
                self.__url += "&auth="+Parameters["Mode1"]
                self.__jsonConn.Connect()
            self.__runAgain = 0 # Request for a new summary to get updated results

    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Debug("Notification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(
            Priority) + "," + Sound + "," + ImageFile)

    def onDisconnect(self, Connection):
        Domoticz.Debug("onDisconnect called")

    def onHeartbeat(self):
        Domoticz.Debug("onHeartbeat called")
        self.__runAgain -= 1
        if self.__runAgain <= 0:
            # Run command
            self.__url = '/' + _API_PATH + '?' + _API_SUMMARY
            self.__jsonConn.Connect()
            self.__runAgain = _HEARTBEATS
        else:
            Domoticz.Debug("onHeartbeat called, run again in "+str(self.__runAgain)+" heartbeats.")


global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

################################################################################
# Generic helper functions
################################################################################
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug("'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))

def UpdateDevice(Unit, nValue, sValue, TimedOut=0, AlwaysUpdate=False):
    # Make sure that the Domoticz device still exists (they can be deleted) before updating it
    if Unit in Devices:
        if Devices[Unit].nValue != nValue or Devices[Unit].sValue != sValue or Devices[Unit].TimedOut != TimedOut or AlwaysUpdate:
            Devices[Unit].Update(nValue=nValue, sValue=str(sValue), TimedOut=TimedOut)
            Domoticz.Debug("Update " + Devices[Unit].Name + ": " + str(nValue) + " - '" + str(sValue) + "'")
