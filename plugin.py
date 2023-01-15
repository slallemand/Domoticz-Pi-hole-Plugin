#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Pi-hole Python Plugin
#
# Author: Xorfor
#
"""
<plugin key="xfr_pihole" name="Pi-hole summary" author="Xorfor" version="3.0.1" wikilink="https://github.com/Xorfor/Domoticz-Pi-hole-Plugin" externallink="https://pi-hole.net/">
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


class BasePlugin:

    __HEARTBEATS2MIN = 6
    __MINUTES        = 1       # 1 hour or use a parameter

    _API_PATH = "admin/api.php"
    _API_SUMMARY = "summaryRaw"
    _API_RECENTBLOCKED = "recentBlocked"
    _API_ENABLE = "enable"
    _API_DISABLE = "disable"

    # Devices
    _UNITS = {
        "DOMAINS_BLOCKED":      1,
        "DNS_QUERIES":          2,
        "ADS_BLOCKED":          3,
        "ADS_PERCENTAGE":       4,
        "UNIQUE_DOMAINS":       5,
        "QUERIES_FORWARDED":    6,
        "QUERIES_CACHED":       7,
        "CLIENTS_EVER_SEEN":    8,
        "UNIQUE_CLIENTS":       9,
        "RECENTBLOCKED":       10,
        "SWITCH":              11,
    }

    def __init__(self):
        self.__jsonConn = None
        self.__textConn = None
        self.__runAgain = 0
        self.__headers = {}
        self.__url = ""
        self.__pihole_active = False
        self.__blocked = ["", ""]

    def onStart(self):
        Domoticz.Debug("onStart called")
        if Parameters["Mode6"] == "Debug":
            Domoticz.Debugging( 1 )
        else:
            Domoticz.Debugging( 0 )

        # Images
        # Check if images are in database
        if "xfr_pihole" not in Images:
            Domoticz.Image("xfr_pihole.zip").Create()
        image = Images["xfr_pihole"].ID # Get id from database
        Domoticz.Log( "Image created. ID: " + str( image ) )

        # Create devices
        if len(Devices) == 0:
            # Following devices are set on used by default
            Domoticz.Device(Unit=self._UNITS["DOMAINS_BLOCKED"], Name="Blocked domains", TypeName="Custom", Options={"Custom": "1;"}, Used=1, Image=image).Create()
            Domoticz.Device(Unit=self._UNITS["DNS_QUERIES"], Name="DNS queries", TypeName="Custom", Options={"Custom": "1;"}, Used=1, Image=image).Create()
            Domoticz.Device(Unit=self._UNITS["ADS_BLOCKED"], Name="Ads blocked", TypeName="Custom", Options={"Custom": "1;"}, Used=1, Image=image).Create()
            Domoticz.Device(Unit=self._UNITS["ADS_PERCENTAGE"], Name="Ads percentage", TypeName="Custom", Options={"Custom": "1;%"}, Used=1, Image=image).Create()  # Image not working :(
            Domoticz.Device(Unit=self._UNITS["RECENTBLOCKED"], Name="Recent blocked", TypeName="Text", Used=1, Image=image).Create()
            # Following devices are NOT set on used. Can be done by user
            Domoticz.Device(Unit=self._UNITS["UNIQUE_DOMAINS"], Name="Unique domains", TypeName="Custom", Options={"Custom": "1;"}, Image=image).Create()
            Domoticz.Device(Unit=self._UNITS["QUERIES_FORWARDED"], Name="Queries forwarded", TypeName="Custom", Options={"Custom": "1;"}, Image=image).Create()
            Domoticz.Device(Unit=self._UNITS["QUERIES_CACHED"], Name="Queries cached", TypeName="Custom", Options={"Custom": "1;"}, Image=image).Create()
            Domoticz.Device(Unit=self._UNITS["CLIENTS_EVER_SEEN"], Name="Clients ever seen", TypeName="Custom", Options={"Custom": "1;"}, Image=image).Create()
            Domoticz.Device(Unit=self._UNITS["UNIQUE_CLIENTS"], Name="Unique clients", TypeName="Custom", Options={"Custom": "1;"}, Image=image).Create()
            # Create On/Off switch when API Token is defined
            if Parameters["Mode1"]:
                Domoticz.Device(Unit=self._UNITS["SWITCH"], Name="Status", TypeName="Switch", Used=1, Image=image).Create()
        else:
            if not Parameters["Mode1"] and self._UNITS["SWITCH"] in Devices:
                # No API Token, so no reason for an On/Off switch
                Domoticz.Device(Unit=self._UNITS["SWITCH"]).Delete()
            if Parameters["Mode1"] and self._UNITS["SWITCH"] not in Devices:
                Domoticz.Device(Unit=self._UNITS["SWITCH"], Name="Status", TypeName="Switch", Used=1, Image=image).Create()
        Domoticz.Log( "Devices created." )
        DumpConfigToLog()

        # Create connections
        self.__jsonConn = Domoticz.Connection( Name="Summary", Transport="TCP/IP", Protocol="HTTP", Address=Parameters["Address"], Port=Parameters["Port"] )
        self.__textConn = Domoticz.Connection( Name="RecentBlocked", Transport="TCP/IP", Protocol="HTTP", Address=Parameters["Address"], Port=Parameters["Port"] )
        self.__headers = {"Content-Type":   "text/xml; charset=utf-8",\
                          "Connection":     "keep-alive",\
                          "Accept":         "Content-Type: text/html; charset=UTF-8",\
                          "Host":           Parameters["Address"] + ":" + Parameters["Port"],\
                          "User-Agent":     "Domoticz/1.0"
                          }

    def onStop(self):
        Domoticz.Debug( "onStop called" )

    def onConnect( self, Connection, Status, Description ):
        Domoticz.Debug( "onConnect called for " + Connection.Name + "("+str(Status)+"): "+Description)
        # If connection is succesfull, send data depending on the specified url
        if Status == 0:
            if Connection.Name == "Summary":
                sendData = {"Verb": "GET",
                            "URL": self.__url,
                            "Headers": self.__headers
                            }
                Domoticz.Debug( "sendData: " + str( sendData ) )
                self.__jsonConn.Send( sendData )
            elif Connection.Name == "RecentBlocked":
                sendData = { "Verb": "GET",
                             "URL": "/" + self._API_PATH + "?" + "recentBlocked",
                             "Headers": self.__headers
                           }
                Domoticz.Debug( "sendData: " + str( sendData ) )
                self.__textConn.Send( sendData )
        else:
            Domoticz.Error( "Failed to connect (" + str( Status )+") to: "+ Connection.Address + ":" + Connection.Port )

    def onMessage(self, Connection, Data):
        Domoticz.Debug( "onMessage called for " + Connection.Name )
        # Data returned from Send
        strData = Data["Data"].decode( "utf-8", "ignore" )
        Domoticz.Debug( "Data: " + strData )
        if Connection.Name == "Summary":
            jsonData = json.loads( strData )
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
                    UpdateDevice(self._UNITS["SWITCH"], 1, "On", AlwaysUpdate=self.__pihole_active)
                else:
                    self.__pihole_active = False
                    UpdateDevice(self._UNITS["SWITCH"], 0, "Off", AlwaysUpdate=self.__pihole_active)
            # Update summary data
            tag = "domains_being_blocked"
            if tag in jsonData:
                Domoticz.Debug( tag+": " + str(jsonData[tag]))
                if self.__pihole_active:
                    UpdateDevice(self._UNITS["DOMAINS_BLOCKED"], jsonData[tag], str(jsonData[tag]), AlwaysUpdate=True)
                else:
                    UpdateDevice(self._UNITS["DOMAINS_BLOCKED"], 0, str(jsonData[tag]), AlwaysUpdate=True)  # Pi-hole will return "N/A"
            tag = "dns_queries_today"
            if tag in jsonData:
                Domoticz.Debug(tag+": " + str(jsonData[tag]))
                UpdateDevice(self._UNITS["DNS_QUERIES"], jsonData[tag], str(jsonData[tag]))
            tag = "ads_blocked_today"
            if tag in jsonData:
                Domoticz.Debug(tag+": " + str(jsonData[tag]))
                UpdateDevice(self._UNITS["ADS_BLOCKED"], jsonData[tag], str(jsonData[tag]))
            tag = "ads_percentage_today"
            if tag in jsonData:
                perc = round( jsonData[tag], 2 )
                Domoticz.Debug( tag + ": " + str( perc ) )
                UpdateDevice(self._UNITS["ADS_PERCENTAGE"], int(perc), str(perc))
            tag = "unique_domains"
            if tag in jsonData:
                Domoticz.Debug(tag+": " + str(jsonData[tag]))
                UpdateDevice(self._UNITS["UNIQUE_DOMAINS"], jsonData[tag], str(jsonData[tag]))
            tag = "queries_forwarded"
            if tag in jsonData:
                Domoticz.Debug(tag+": " + str(jsonData[tag]))
                UpdateDevice(self._UNITS["QUERIES_FORWARDED"], jsonData[tag], str(jsonData[tag]))
            tag = "queries_cached"
            if tag in jsonData:
                Domoticz.Debug(tag+": " + str(jsonData[tag]))
                UpdateDevice(self._UNITS["QUERIES_CACHED"], jsonData[tag], str(jsonData[tag]))
            tag = "clients_ever_seen"
            if tag in jsonData:
                Domoticz.Debug(tag+": " + str(jsonData[tag]))
                UpdateDevice(self._UNITS["CLIENTS_EVER_SEEN"], jsonData[tag], str(jsonData[tag]), AlwaysUpdate=True)
            tag = "unique_clients"
            if tag in jsonData:
                Domoticz.Debug(tag+": " + str(jsonData[tag]))
                UpdateDevice(self._UNITS["UNIQUE_CLIENTS"], jsonData[tag], str(jsonData[tag]), AlwaysUpdate=True)
        if Connection.Name == "RecentBlocked":
            # Data available in plain text (not in json!)
            if strData != self.__blocked[0]:
                self.__blocked[1] = self.__blocked[0]
                self.__blocked[0] = strData
            UpdateDevice(self._UNITS["RECENTBLOCKED"], 0, self.__blocked[0] + "<br/>" + self.__blocked[1], AlwaysUpdate=self.__pihole_active)
        Connection.Disconnect()

    def onCommand( self, Unit, Command, Level, Hue ):
        Domoticz.Debug( "onCommand called for Unit " + str(Unit) + ": Parameter "" + str(Command) + "", Level: " + str(Level))
        if Unit == self._UNITS["SWITCH"]:
            if Parameters["Mode1"]:
                # User clicked on the On/Off switch. Setup the correct url
                if str( Command ) == "Off":
                    self.__url = "/" + self._API_PATH + "?" + self._API_DISABLE
                elif str( Command ) == "On":
                    self.__url = "/" + self._API_PATH + "?" + self._API_ENABLE
                else:
                    self.__url = None
                # If valid command, add the API token from Pi-hole and send data
                if self.__url:
                    self.__url += "&auth=" + Parameters["Mode1"]
                    self.__jsonConn.Connect()

    def onNotification( self, Name, Subject, Text, Status, Priority, Sound, ImageFile ):
        Domoticz.Debug("Notification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str( Priority) + "," + Sound + "," + ImageFile)

    def onDisconnect( self, Connection ):
        Domoticz.Debug( "onDisconnect called for " + Connection.Name )

    def onHeartbeat( self ):
        Domoticz.Debug( "onHeartbeat called" )
        self.__runAgain -= 1
        if self.__runAgain <= 0:
            self.__runAgain = self.__HEARTBEATS2MIN * self.__MINUTES
            # On heartbeat get summary
            self.__url = "/" + self._API_PATH + "?" + self._API_SUMMARY
            self.__url += "&auth=" + Parameters["Mode1"]
            self.__jsonConn.Connect()
            self.__textConn.Connect()
        else:
            Domoticz.Debug( "onHeartbeat called, run again in " + str( self.__runAgain )+" heartbeats." )


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
            Domoticz.Debug(""" + x + "":"" + str(Parameters[x]) + """)
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       "" + str(Devices[x].ID) + """)
        Domoticz.Debug("Device Name:     "" + Devices[x].Name + """)
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   "" + Devices[x].sValue + """)
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    for x in Settings:
        Domoticz.Debug("Setting:           " + str(x) + " - " + str(Settings[x]))

def UpdateDevice(Unit, nValue, sValue, TimedOut=0, AlwaysUpdate=False):
    # Make sure that the Domoticz device still exists (they can be deleted) before updating it
    if Unit in Devices:
        if Devices[Unit].nValue != nValue or Devices[Unit].sValue != sValue or Devices[Unit].TimedOut != TimedOut or AlwaysUpdate:
            Devices[Unit].Update(nValue=nValue, sValue=str(sValue), TimedOut=TimedOut)
            Domoticz.Debug("Update " + Devices[Unit].Name + ": " + str(nValue) + " - "" + str(sValue) + """)
