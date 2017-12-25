# Pi-hole Summary
This Domoticz plugin retrieves data from Pi-hole, a black hole for internet advertisements.
## Prerequisites
You must have Pi-hole installed. See [`https://pi-hole.net/`](https://pi-hole.net/) for more information.
## Description
This plugin is calling the Pi-hole API by using `http://<pihole adrress>/admin/api.php?summaryRaw`. This will return:
```
{"domains_being_blocked":106002,"dns_queries_today":9341,"ads_blocked_today":1812,"ads_percentage_today":19.398352,"unique_domains":1387,"queries_forwarded":5522,"queries_cached":1820,"clients_ever_seen":8,"unique_clients":8,"status":"enabled"}
```
This plugin will create 10 devices. One of them is a switch (if the API Token is filled in) with which you can switch On or Off Pi-hole.
The others devices gives you summary data from Pi-hole.
## Installation
Python version 3.4 or higher required & Domoticz version 3.87xx or greater.
To install:
* Go in your Domoticz directory using a command line and open the plugins directory.
* Run: ```git clone https://github.com/Xorfor/Domoticz-Pi-hole-Plugin.git```
* Restart Domoticz.

In the web UI, navigate to the Hardware page. In the hardware dropdown there will be an entry called "Pi-hole".

## Updating
To update:
* Go in your Domoticz directory using a command line and open the plugins directory then the Domoticz-Pi-hole-Plugin directory.
* Run: ```git pull```
* Restart Domoticz.

## Parameters
| Parameter | Value |
| :--- | :--- |
| **Pi-hole address** | eg. pi-hole, or 192.168.1.231 |
| **Port** | default is 80 |
| **API Token** | required to switch on/off Pi-hole |
| **Debug** | default is False |
### API Token
The API Token can be found in the Pi-hole web interface:
1. Goto your Pi-hole web interface, eg. //192.168.1.231/admin/index.php 
2. Login
3. Goto Settings -> API / Web interface
4. Click on `Show API token`

Or from the command line `more /etc/pihole/setupVars.conf`, and look for the value of `WEBPASSWORD`.
## To do
- [ ] Parameter for interval, with default is 15. Now requesting data every 5 minutes.
- [x] Add Pi-hole images to the devices. For some reason not working yet
- [x] Only the `_today` data is used. Add extra data and devices?
