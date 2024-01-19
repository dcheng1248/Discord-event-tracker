# Event Tracker

This is an event tracker bot for event scheduling and reminders in discord. Currently, the bot is used and maintained for tracking recurrent events for a specific game. 

If you would like to use or modify the bot for your own purposes, you are free to do so under the terms of GNU General Public License v3.0. You will need to set up your own discord application and host server for the bot.

## Setup
All event configurations can be set up in the config.yaml file. An example yaml file is provided in the repo. 

Each item in the yaml file refers to a category of events with the same recurrent interval. For each item, a list of events is provided, with information about the name(s) used to refer to these specific events, emojis related to the event and the upper limit of the number of the events. 

For hosting the bot, in addition to the files in the repo, you will need a .env file that includes the authentication token for the discord application you set up. 

## Usage
A number of commands are available for use in the discord server. 

```!help``` : provides a list of possible commands and the respective formatting. \
```!set``` : sets recurrent intervals for a category. \
```!add``` : add starting occurence of an event to start tracking. \
```!modify``` : modifies previous occurence of an added event to change tracking. \
 ```!status``` : show status of all tracked events. \
 ```!when``` : query next occurence of specific or all events. \
 ```!next``` : show the next immediate event (of all tracked events). \
 ```!nextweek``` : show all upcoming events in the next 7 days in time format local to the viewer. \
 ```!today``` : show all upcmoing events within the next 24 hours. \
 ```!announcement``` : used to set up event reminder announcements (for any event) a custom-defined interval in advance. \
 ```!listevents``` :  set up dynamic event calendar (which shows the next occurence of all events). The calendar auto-updates to the next occurence whenever an event occurs. \
 ```!reset``` : reset the bot, clearing all stored event occurences.




