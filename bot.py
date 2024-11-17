# bot.py
import os
import discord
import datetime
from discord.ext import commands, tasks
import asyncio
import pickle
import pytz
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

class reminder:
	def __init__(self, mention, hours = None, channel = None, enabled = None):
		self.mention = mention
		self.hours = hours
		self.channel = channel
		self.enabled = enabled

	def __eq__(self, value: object):
		if isinstance(value, reminder):
			return self.mention == value.mention
		return False

def get_day_hour(timedelta):
	return timedelta.days, timedelta.seconds//3600

def flatten(nested_list):
	flattened_list = list(itertools.chain.from_iterable(nested_list))
	return(flattened_list)

def pickle_data():
	#save data into pickle file
	pickle_list = {
		'Rushes': bot.rushes,
		'Heroics': bot.heroics,
		'Reminders': bot.reminders,
		'Events': bot.list_events,
		'Events Channel': bot.list_events_channel.id if bot.list_events_channel else None,
		'Announcement': bot.announcement,
		'Announcement Channel': bot.announcement_channel.id if bot.announcement_channel else None,
		'Arena Shop Order': bot.arena_shop_order,
		'Arena Shop Index': bot.arena_shop_index,
		'Arena Shop Announcements': bot.arena_shop_announcements
	}
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

	#enable reminders if needed
	for user in bot.reminders:
		if not user.enabled:
			if (bot.reminder_time - now > datetime.timedelta(hours=user.hours)):
				user.enabled = True

	pickle_data()

def reset_announced():
	for event in bot.rushes:
		event.reminder = False

async def unpickle_data():
	with open('data.pkl', 'rb') as f:
		pickle_list = pickle.load(f)
	if type(pickle_list) is dict:
		bot.rushes = pickle_list.get('Rushes')
		bot.heroics = pickle_list.get('Heroics')
		bot.reminders = pickle_list.get('Reminders')
		bot.list_events = pickle_list.get('Events')
		bot.list_events_channel = await bot.fetch_channel(pickle_list.get('Events Channel')) if pickle_list.get('Events Channel') else None
		bot.announcement = pickle_list.get('Announcement')
		bot.announcement_channel = await bot.fetch_channel(pickle_list.get('Announcement Channel')) if pickle_list.get('Announcement Channel') else None
		bot.arena_shop_order = pickle_list.get('Arena Shop Order', bot.arena_shop_order)
		bot.arena_shop_index = pickle_list.get('Arena Shop Index', 0)
		bot.arena_shop_announcements = pickle_list.get('Arena Shop Announcements', bot.arena_shop_announcements)
	else:
		bot.rushes = pickle_list[0]
		bot.heroics = pickle_list[1]

	reset_announced()
	update()

def event_exists(list, new_event_name, new_event_time):
	for event in list:
		if (event.name == new_event_name and event.time == new_event_time):
			return True
	return False

def initialize(event_only=False):
	#initialize rush and heroic lists
	bot.rushes = []
	bot.heroics = []
	bot.posted_rushes = []
	bot.posted_heroics = []
	bot.arena_shop_order = ('Rainbow Experience', 'Exalted Gear', 'Radiant Amulet', 'Basic AI Book', 'Mythic Dust', 'Brilliant Amulet', 'Radiant Amulet', 'Bronze Pet Rune', 'Legendary Dust', 'Coruscating Amulet', 'Mythic Dust', 'Mythic Codex', 'Bronze Rune', 'Legendary Gear', 'Silver Rune', 'Gold', 'Bronze Rune', 'Basic AI Book', 'Silver Pet Rune', 'Superior AI Book', 'Mythic Gear', 'Exalted Dust', 'Rainbow Experience', 'Silver Rune', 'Gold', 'Brilliant Amulet', 'Mythic Gear', 'Mythic Codex', 'Bronze Pet Rune', 'Superior AI Book', 'Premium Scroll', 'Silver Pet Rune')
	bot.arena_shop_index = 0
	bot.arena_shop_announcements = {
		'Rainbow Experience': False,
		'Exalted Gear': False,
		'Radiant Amulet': False,
		'Basic AI Book': False,
		'Mythic Dust': False,
		'Brilliant Amulet': False,
		'Bronze Pet Rune': False,
		'Legendary Dust': False,
		'Coruscating Amulet': True,
		'Mythic Codex': True,
		'Bronze Rune': False,
		'Legendary Gear': False,
		'Silver Rune': True,
		'Gold': False,
		'Superior AI Book': False,
		'Exalted Dust': False,
		'Premium Scroll': False,
		'Silver Pet Rune': True
	}

	if not event_only:
		#tracking channels with announcements
		bot.announcement = False
		bot.announcement_channel = None
		bot.rush_announcement_time = 6
		bot.heroic_announcement_time = 24

		#tracking list events
		bot.list_events = False
		bot.list_events_channel = None

		#reminders
		bot.reminders = []
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
		await unpickle_data()
		print(f"Arena shop order: {bot.arena_shop_order}")
		print(f"Arena shop index: {bot.arena_shop_index}")
		print(f"Arena shop announcements: {bot.arena_shop_announcements}")
		msg = 'Event tracker is online.\n\n'
		msg += f'Arena shop index is {bot.arena_shop_index}: {bot.arena_shop_order[bot.arena_shop_index]}\n'
		msg += f'Event listing channel is set to {bot.list_events_channel.mention if bot.list_events_channel else None}\n'
		msg += f'Announcement channel set to {bot.announcement_channel.mention if bot.announcement_channel else None}\n\n'
		msg += 'Please use !status to check the data or !reset if you wish to reset the bot.'
		await channel.send(msg)
	else:
		await channel.send(f'Event tracker is online. No stored event data is found. Please add events.')

	#Ensure loops are running
	if not announcement_loop.is_running():
		announcement_loop.start()
	if not arena_loop.is_running():
		arena_loop.start()
	if not listevent_loop.is_running():
		listevent_loop.start()
	if not reminder_loop.is_running():
		reminder_loop.start()

@bot.event
async def on_message(message):
	# Manually get the invocation context from the message
	ctx = await bot.get_context(message)

	# Invoke the command using the earlier defined bot/client/command
	await bot.invoke(ctx)

@tasks.loop(time=[datetime.time(hour=x) for x in range(0, 24)], reconnect=True)
async def announcement_loop():
	# Send announcements to the specified channel
	update()
	if bot.announcement_channel:
		now = datetime.datetime.now(datetime.timezone.utc)
		# Send to announcement channel if it is time and event hasn't already been posted
		for event in bot.rushes:
			if (event.time - now <= datetime.timedelta(hours = bot.rush_announcement_time) and (not event.reminder)):
				await bot.wait_until_ready()
				await bot.announcement_channel.send(f"{event.name} at <t:{round(event.time.timestamp())}:t> (approx. <t:{round(event.time.timestamp())}:R>).")
				event.reminder = True
		for event in bot.heroics:
			if (event.time - now <= datetime.timedelta(hours = bot.heroic_announcement_time) and (not event.reminder)):
				await bot.wait_until_ready()
				await bot.announcement_channel.send(f"{event.name} at <t:{round(event.time.timestamp())}:t> (approx. <t:{round(event.time.timestamp())}:R>).")
				event.reminder = True

@tasks.loop(time=[datetime.time(hour=x, tzinfo=pytz.UTC) for x in [11, 23]], reconnect=True)
async def arena_loop():
	# Send notifications for arena shop items
	bot.arena_shop_index += 1 if bot.arena_shop_index < 31 else -31
	if bot.arena_shop_announcements[bot.arena_shop_order[bot.arena_shop_index]]:
		await bot.wait_until_ready()
		await bot.announcement_channel.send(f"{bot.arena_shop_order[bot.arena_shop_index]} available in arena shop")

@tasks.loop(time=[datetime.time(hour=x) for x in range(0, 24)], reconnect=True)
async def listevent_loop():
	# Send event list to specified channel
	update()
	if bot.list_events_channel:
		# Get current event list
		rush_list = [event.time for event in bot.rushes]
		heroic_list = [event.time for event in bot.heroics]
		# Compare to previously posted list and update if needed
		if (bot.posted_rushes != rush_list or bot.posted_heroics != heroic_list):
			await send_list(bot.list_events_channel)
			# Update posted list
			bot.posted_rushes = rush_list
			bot.posted_heroics = heroic_list

@tasks.loop(time=[datetime.time(hour=x) for x in range(0, 24)], reconnect=True)
async def reminder_loop():
	# Send reminders to users that are signed up for them
	update()
	if bot.reminder_time:
		now = datetime.datetime.now(datetime.timezone.utc)
		for user in bot.reminders:
			# Remind only if it is time and reminder hasn't already been sent
			if user.enabled:
				if (bot.reminder_time - now <= datetime.timedelta(hours=user.hours)):
					channel = bot.fetch_channel(user.channel)
					await bot.wait_until_ready()
					await channel.send(f"{user.mention} the last rush or heroic is in {user.hours} hours, please update the list.")
					# Prevent reminders for this user until events are updated
					user.enabled = False

@bot.command(name = 'add')
async def add(ctx, *, args):
	#parse argument
	elements = args.split("-")
	event_name = elements[0].replace(" Begins!","").replace("!","") #remove extra data from event name
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

@bot.command (name = 'arena')
async def arena(ctx, *args):
	update()
	if (len(args) == 0):
		# print current info
		msg = f"Currently in arena shop: {bot.arena_shop_order[bot.arena_shop_index]}\n"
		msg += f"Next item: {bot.arena_shop_order[bot.arena_shop_index + 1 if bot.arena_shop_index < 31 else 0]}"
		await ctx.send(msg)
		return
	if args[0] == 'listindex':
		# list possible index values
		msg = ""
		for i in range(0,len(bot.arena_shop_order)):
			msg += f"{i}: {bot.arena_shop_order[i]}\n"
		await ctx.send(msg)
		return
	if args[0] == 'setindex':
		# set current shop index
		if args[1] is None:
			await ctx.send('You must specify an index.')
			return
		if any([not args[1].isnumeric(), int(args[1]) < 0, int(args[1]) > 31]):
			await ctx.send('Index must be an integer between 0 and 31.')
			return
		bot.arena_shop_index = int(args[1])
		update()
		await ctx.send(f"Arena index set to {bot.arena_shop_index}: {bot.arena_shop_order[bot.arena_shop_index]}")
	if args[0] == 'cycle':
		#manually cycle to next item and notify if needed
		await arena_loop()

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
		msg += f'{event.name} at {event.time.strftime('%d/%m/%y %A %H:%M')}\n\n'
	msg += f'Arena shop index is {bot.arena_shop_index}: {bot.arena_shop_order[bot.arena_shop_index]}\n'
	msg += f'Event listing channel is set to {bot.list_events_channel.mention if bot.list_events_channel else None}\n'
	msg += f'Announcement channel set to {bot.announcement_channel.mention if bot.announcement_channel else None}'
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
		update()
		return
	if args[0] == "off":
		if (ctx.channel == bot.announcement_channel) and bot.announcement: #turning off
			bot.announcement = False
			bot.announcement_channel = None
			await ctx.send(f'Announcements is turned off in this channel.')
			update()
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
		if args[0] == "update":
			if bot.list_events and bot.list_events_channel: #update event list channel
				await listevent_loop()
				await ctx.send(f'Event listing in {bot.list_events_channel.mention} updated')
				return
			else: #no event listing turned on
				await ctx.send(f'Event listing has not been turned on.')
				return
		elif args[0] == "off":
			if (ctx.channel == bot.list_events_channel) and bot.list_events: #turning off
				bot.list_events = False
				bot.list_events_channel = None
				await ctx.send(f'Event listing is turned off in this channel.')
				update()
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
		update()
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
	elif int(args[0]) == 0:
		if reminder(mention=ctx.message.author.mention) in bot.reminders:
			del bot.reminders[bot.reminders.index(reminder(mention=ctx.message.author.mention))]
			await ctx.send('Your reminder has been deleted')
		else:
			await ctx.send('You do not have a scheduled reminder')
	elif reminder(mention=ctx.message.author.mention) in bot.reminders:
		if bot.reminders[bot.reminders.index(reminder(mention=ctx.message.author.mention))].hours == int(args[0]):
			if not bot.reminders[bot.reminders.index(reminder(mention=ctx.message.author.mention))].enabled:
				bot.reminders[bot.reminders.index(reminder(mention=ctx.message.author.mention))].enabled = True
				await ctx.send(f'You already have a reminder set for {args[0]} hours. Re-enabled it')
			else:
				await ctx.send(f'You already have an enabled reminder set for {args[0]} hours')
		else:
			bot.reminders[bot.reminders.index(reminder(mention=ctx.message.author.mention))].hours = int(args[0])
			bot.reminders[bot.reminders.index(reminder(mention=ctx.message.author.mention))].enabled = True
			await ctx.send(f'Your reminder has been updated to {args[0]} hours')
	else:
		user = reminder(
			mention=ctx.message.author.mention,
			hours=int(args[0]),
			channel=ctx.channel.id,
			enabled= True
		)
		bot.reminders.append(user)
		await ctx.send(f'You will be reminded {user.hours} hours in advance.')
	update()

#reset bot
@bot.command(name = 'reset')
async def reset(ctx, *args):
	if len(args) == 0:
		await ctx.send(f'Are you sure you want to reset the bot data? All recorded event instance and announcement setups will be deleted. (yes/no)')
		msg = await bot.wait_for('message', timeout = 60)
		if msg.content in ["Yes", "yes"]:
			initialize()
			await ctx.send(f'The bot data has been reset.')
		update()
	elif args[0] == 'events':
		await ctx.send(f'Are you sure you want to reset the event schedule? All recorded event instance and announcement setups will be retained. (yes/no)')
		msg = await bot.wait_for('message', timeout = 60)
		if msg.content in ["Yes", "yes"]:
			initialize(event_only=True)
			await ctx.send(f'The event schedule has been reset.')
		update()
	else:
		await ctx.send(f'Invalid argument. Choose \"!reset\" or \"!reset events\"')


#if command is not found
@bot.event
async def on_command_error(ctx, error):
	if isinstance(error, commands.CommandNotFound):
		await ctx.send("This command is not recognized. Please use !help for command formatting.")  
	elif isinstance(error, commands.MissingRequiredArgument):
		await ctx.send("An argument is missing in this command. Please use !help for command formatting.")
	else:
		print(error)
		await ctx.send("An error occured with the command. Please contact the admins.")

#help
@bot.command(name = 'help')
async def help(ctx):
	msg = f'Here are the possible commands and their respective formatting for this bot.\n'
	msg += f'**__!add__**:\nadd new event cycle. Time in UTC.\nFormat !add [event name] [dd/mm/yy HH:MM].\n'
	msg += f'**__!arena__**:\nshow arena shop info or set current index\nFormat !arena listindex.\nFormat !arena setindex [integer].\n'
	msg += f'**__!status__**:\nshow status of recorded events, including last occurence of each event. Time in UTC.\nFormat !status.\n'
	msg += f'**__!next__**:\nshow when is the next rush. Local time displayed.\nFormat !next. \n'
	msg += f'**__!announcement__**:\nset up rush announcement in channel.\nFormat !announcement [number of hours in advance for announcement].\nFormat !announcement off to turn announcements off.\n'
	msg += f'**__!listevents__**:\nset up dynamic event calendar in channel.\nFormat !listevents.\nFormat !listevents off to turn event listing off.\nFormat !listevents update to force an update to the event listing.\n'
	msg += f'**__!remindme__**:\nget a reminder when rush schedule is almost empty. Specify the number of hours before the last event\nFormat !remindme [##]\nFormat !remindme 0 to turn your reminder off.\n'
	msg += f'**__!reset__**:\nclear all recorded data and announcements.\nFormat !reset to reset everything\nFormat !reset events to reset events only'
	await ctx.send(msg)

bot.run(TOKEN)
