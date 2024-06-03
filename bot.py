# bot.py
import os
import discord
import datetime
from discord.ext import commands, tasks
import asyncio
import pickle
from dotenv import load_dotenv
import itertools

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
bot = commands.Bot(intents = discord.Intents.all(), command_prefix = '!', help_command = None)

#each rush
class event:
	def __init__(self, name, time):
		self.name = name
		self.time = time
		self.reminder = False

	def modify(self, new_start): #update start time
		self.curr = new_start
		if self.curr <= datetime.datetime.now(datetime.timezone.utc):
			self.next = new_start + self.cycle #next occurence
		else:
			self.next = new_start

def get_day_hour(timedelta):
	return timedelta.days, timedelta.seconds//3600

def flatten(nested_list):
	flattened_list = list(itertools.chain.from_iterable(nested_list))
	return(flattened_list)

def pickle_data():
	#save data into pickle file
	pickle_list = [bot.rushes, bot.heroics, bot.reminders]
	with open('data.pkl', 'wb') as f:
		pickle.dump(pickle_list, f)

def update():
	#delete past events
	now = datetime.datetime.now(datetime.timezone.utc)
	remove_list = []
	for event in bot.rushes:
		if now > event.time:
			remove_list.append(event)
	for event in remove_list:
		bot.rushes.remove(event)
	remove_list = []
	for event in bot.heroics:
		if now > event.time:
			remove_list.append(event)
	for event in remove_list:
		bot.heroics.remove(event)

	#sort upcoming events
	bot.rushes.sort(key=lambda x: x.time)
	bot.heroics.sort(key=lambda x: x.time)

	#update reminder time
	if (len(bot.rushes) == 0 and len(bot.heroics) == 0):
		bot.reminder_time = None
	elif (len(bot.rushes) == 0):
		bot.reminder_time = bot.heroics[-1].time
	elif (len(bot.heroics) == 0):
		bot.reminder_time = bot.rushes[-1].time
	else:
		bot.reminder_time = min(bot.rushes[-1].time, bot.heroics[-1].time)

	pickle_data()

def reset_announced():
	for event in bot.rushes:
		event.reminder = False

def unpickle_data():
	with open('data.pkl', 'rb') as f:
		pickle_list = pickle.load(f)

	bot.rushes = pickle_list[0:1]
	bot.heroics = pickle_list[1:2]
	bot.reminders = pickle_list[2:3]

	reset_announced()
	update()

def event_exists(list, new_event_name, new_event_time):
	for event in list:
		if (event.name == new_event_name and event.time == new_event_time):
			return True
	return False

def initialize():
	#initialize rush and heroic lists
	bot.rushes = []
	bot.heroics = []

	#tracking channels with announcements
	bot.announcement = False
	bot.announcement_channel = None
	bot.rush_announcement_time = 6
	bot.heroic_announcement_time = 24

	#tracking list events
	bot.list_events = False
	bot.list_events_channel = None

	#reminders
	bot.reminders = {}
	bot.reminder_time = None

@bot.event
async def on_ready():
	print(f'{bot.user} has connected to Discord!')
	initialize()
	for guild in bot.guilds:
		ready_channel = None
		for channel in guild.channels:
			if channel.name == 'rush-tracker-bot':
				ready_channel = channel
		channel = ready_channel if ready_channel else guild.system_channel
	if os.path.isfile('data.pkl'):
		unpickle_data()
		await channel.send(f'Event tracker is online. Stored event data has been loaded. Please use !status to check the data, !announcement to reset announcements, !listevents to reset dynamic event listing and !remindme to set up reminders. Use !reset if you wish to reset the bot.')
	else:
		await channel.send(f'Event tracker is online. No stored event data is found. Please add events.')

@bot.event
async def on_message(message):
	# Manually get the invocation context from the message
	ctx = await bot.get_context(message)

	# Invoke the command using the earlier defined bot/client/command
	await bot.invoke(ctx)

@tasks.loop(time=[datetime.time(hour=x) for x in range(0, 24)])
async def reminder_loop():
	update()
	now = datetime.datetime.now(datetime.timezone.utc)
	rush_list, heroic_list = [], []
	for event in bot.rushes:
		rush_list.append(event.time)
		if (event.time - now <= datetime.timedelta(hours = bot.rush_announcement_time) and (not event.reminder)):
			await bot.wait_until_ready()
			await bot.announcement_channel.send(f"{event.name} at <t:{round(event.time.timestamp())}:t> (approx. <t:{round(event.time.timestamp())}:R>).")
			event.reminder = True
	for event in bot.heroics:
		heroic_list.append(event.time)
		if (event.time - now <= datetime.timedelta(hours = bot.heroic_announcement_time) and (not event.reminder)):
			await bot.wait_until_ready()
			await bot.announcement_channel.send(f"{event.name} at <t:{round(event.time.timestamp())}:t> (approx. <t:{round(event.time.timestamp())}:R>).")
			event.reminder = True
	if (bot.posted_rushes != rush_list or bot.posted_heroics != heroic_list):
		await send_list(bot.list_events_channel)
		bot.posted_rushes = rush_list
		bot.posted_heroics = heroic_list
	if bot.reminder_time:
		del_users = []
		for user, data in bot.reminders.items():
			if (bot.reminder_time - now <= datetime.timedelta(hours=data['hours'])):
				await bot.wait_until_ready()
				await data['channel'].send(f"{user} the last rush or heroic is in {data['hours']} hours, please update the list.")
				await data['channel'].send('Please run !remindme again after update to get further reminders.')
				del_users.append(user)
		for user in del_users:
			del bot.reminders[user]

@bot.command(name = 'add')
async def add(ctx, *, args):
	#parse argument
	elements = args.split("-")
	event_name = elements[0].replace("!","") #remove ! from event name
	event_time = elements[1][:-3] #remove last three digits from epoch time since discord does not read milliseconds
	event_time = datetime.datetime.fromtimestamp(int(event_time), datetime.UTC) #convert timestamp to datetime
	event_time = event_time.replace(minute = 0, second = 0) #round datetime down to hour

	#add event if it is not already added
	if ("Rush" in event_name or "Scramble" in event_name): #this is a rush
		if (not event_exists(bot.rushes, event_name, event_time)): #check it is not added
			bot.rushes.append(event(event_name, event_time)) 
	else: #this is a heroic
		if (not event_exists(bot.heroics, event_name, event_time)): #check it is not added
			bot.heroics.append(event(event_name, event_time))

	await ctx.send(f'{event_name} starting at {event_time.strftime('%d/%m/%y %H:%M')} UTC has been added.')
	update()

#showing recorded status
@bot.command(name = 'status')
async def status(ctx):
	update()
	msg = "All times displayed in UTC.\n"
	msg += "**Rushes**\n"
	for event in bot.rushes:
		msg += f'{event.name} at {event.time.strftime('%d/%m/%y %A %H:%M')}\n'
	msg += "\n"
	msg += "**Heroics**\n"
	for event in bot.heroics:
		msg += f'{event.name} at {event.time.strftime('%d/%m/%y %A %H:%M')}\n'
	await ctx.send(msg)

#show next rush
@bot.command(name = 'next')
async def next(ctx):
	update()
	if bot.rushes == []:
		await ctx.send(f'There are no events recorded.')
		return
	event = bot.rushes[0]
	msg = f"The next rush is {event.name} at <t:{round(event.time.timestamp())}:d> <t:{round(event.time.timestamp())}:t> (<t:{round(event.time.timestamp())}:R>)."
	await ctx.send(msg)

#set up announcement
@bot.command(name = 'announcement')
async def announcement(ctx, *args):
	if (len(args) == 0):
		bot.announcement = True
		bot.announcement_channel = ctx.channel
		await ctx.send(f'Rushes will be announced 6 hours in advance, heroics will be announced 1 day in advance.')
		return
	if args[0] == "off":
		if (ctx.channel == bot.announcement_channel) and bot.announcement: #turning off
			bot.announcement = False
			bot.announcement_channel = None
			await ctx.send(f'Announcements is turned off in this channel.')
			return
		elif bot.announcement: #off command in wrong channel
			await ctx.send(f'Announcements was turned on at {bot.announcement_channel.mention}. Please turn off announcements there.')
			return
		else: #no announcements turned on
			await ctx.send(f'Announcements has not been turned on.')
			return
	else:
		await ctx.send(f'Sorry, the command format is wrong. Use !announcement to set up announcements and !announcement off to turn them off.')
		

#send list event message
async def send_list(channel):
	await channel.purge()
	msg = "All times in your local time.\n"
	msg += "__**Rushes**__\n"
	for event in bot.rushes:
		msg += f'{event.name}: <t:{round(event.time.timestamp())}:F>\n'
	msg += "\n"
	msg += "__**Heroics**__\n"
	for event in bot.heroics:
		msg += f'{event.name}: <t:{round(event.time.timestamp())}:F>\n'
	await channel.send(msg)

#set up event list
@bot.command(name = 'listevents')
async def listevents(ctx, *args):
	update()
	if len(args) > 0:
		if args[0] == "off":
			if (ctx.channel == bot.list_events_channel) and bot.list_events: #turning off
				bot.list_events = False
				bot.list_events_channel = None
				await ctx.send(f'Event listing is turned off in this channel.')
				return
			elif bot.list_events: #off command in wrong channel
				await ctx.send(f'Event listing was turned on at {bot.list_events_channel.mention}. Please turn off the event listing there.')
				return
			else: #no event listing turned on
				await ctx.send(f'Event listing has not been turned on.')
				return
		else:
			await ctx.send(f'Sorry, this command is not recognized.') #wrong command
			return
	else:
		if (ctx.channel == bot.list_events_channel) and bot.list_events: #event listing already on in channel
			await ctx.send(f'Event listing has already been turned on in this channel.')
			return
		elif bot.list_events: #event listing on in different channel
			await ctx.send(f'Event listing was turned on at {bot.list_events_channel.mention}. This bot only supports event listing in one channel. Please turn event listing off in that channel before you turn it on here.')
			return

	await ctx.send("Turning on event listing will delete all previous messages in this channel. Are you sure you want to turn on event listing here? (yes/no)")
	msg = await bot.wait_for('message', timeout = 60)
	if msg.content in ["Yes", "yes"]:
		bot.list_events = True
		bot.list_events_channel = ctx.channel
		await ctx.send(f'Event listing is turned on in this channel.')
		bot.posted_rushes = [event.time for event in bot.rushes]
		bot.posted_heroics = [event.time for event in bot.heroics]
		await send_list(bot.list_events_channel)
	else:
		await ctx.send(f'Event listing has not been turned on.')
	return

#set up track reminder
@bot.command(name = 'remindme')
async def remind(ctx, *args):
	if (len(args) == 0 or not args[0].isnumeric()):
		await ctx.send(f'Sorry, a numerical argument is needed for this command. Use !remindme followed by the number of hours in advance you want to be reminded.')
		return
	elif (len(bot.rushes) == 0 and len(bot.heroics.length) == 0):
		await ctx.send(f'Sorry, there are no recorded rushes or heroics. Please add at least one rush or heroic.')
		return
	else:
		bot.reminders[ctx.message.author.mention] = {
			'hours': int(args[0]),
			'channel': ctx.channel
		}
		await ctx.send(f'You will be reminded {int(args[0])} hours in advance.')
		update()
		if bot.reminder_time == None:
			if (len(bot.rushes) == 0):
				bot.reminder_time = bot.heroics[-1].time
			elif (len(bot.heroics) == 0):
				bot.reminder_time = bot.rushes[-1].time
			else:
				bot.reminder_time = min(bot.rushes[-1].time, bot.heroics[-1].time)

#reset bot
@bot.command(name = 'reset')
async def reset(ctx):
	await ctx.send(f'Are you sure you want to reset the event schedule? All recorded event instance and announcement setups will be deleted. (yes/no)')
	msg = await bot.wait_for('message', timeout = 60)
	if msg.content in ["Yes", "yes"]:
		initialize()
		await ctx.send(f'The event schedule has been reset.')
	update()

#if command is not found
@bot.event
async def on_command_error(ctx, error):
	if isinstance(error, commands.CommandNotFound):
		await ctx.send("This command is not recognized. Please use !help for command formatting.")  
	elif isinstance(error, commands.MissingRequiredArgument):
		await ctx.send("An argument is missing in this command. Please use !help for command formatting.")
	else:
		await ctx.send("An error occured with the command. Please contact the admins.")

#help
@bot.command(name = 'help')
async def help(ctx):
	msg = f'Here are the possible commands and their respective formatting for this bot.\n'
	msg += f'**__!add__**:\nadd new event cycle. Time in UTC.\nFormat !add [event name] [dd/mm/yy HH:MM].\n'
	msg += f'**__!status__**:\nshow status of recorded events, including last occurence of each event. Time in UTC.\nFormat !status.\n'
	msg += f'**__!next__**:\nshow when is the next rush. Local time displayed.\nFormat !next. \n'
	msg += f'**__!announcement__**:\nset up rush announcement in channel.\nFormat !announcement [number of hours in advance for announcement].\nFormat !announcement off to turn announcements off.\n'
	msg += f'**__!listevents__**:\nset up dynamic event calendar in channel.\nFormat !listevents.\nFormat !listevents off to turn event listing off.\n'
	msg += f'**__!remindme__**:\nget a reminder when rush schedule is almost empty. Specify the number of hours before the last event\nFormat !remindme [##]'
	msg += f'**__!reset__**:\nclear all recorded data and announcements.\n'
	await ctx.send(msg)

bot.run(TOKEN)
