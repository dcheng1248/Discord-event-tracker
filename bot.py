# bot.py
import os
import discord
import datetime
from discord.ext import commands
import asyncio
import pickle

TOKEN = 'MTA3NTE2MzM0MTY1MzI4NjkxMw.GLzEFT.OKMSJ3IjdRBv-K3Mke1KygP4rcZVlr0xONxptE'
bot = commands.Bot(intents = discord.Intents.all(), command_prefix = '!', help_command = None)

#each rush
class rush:
	def __init__(self, name, emoji, cycle, start):
		self.name = name
		self.emoji = emoji
		self.cycle = cycle #interval
		self.curr = start #previous occurence
		if self.curr <= datetime.datetime.now(datetime.timezone.utc):
			self.next = start + cycle #next occurence
		else:
			self.next = start
		self.reminder = False
	def update(self, cycle): #update occurences, change cycle
		self.cycle = cycle
		if self.next < datetime.datetime.now(datetime.timezone.utc):
			self.curr = self.next
			self.next = self.next + self.cycle
		else:
			self.next = self.curr + self.cycle
	def modify(self, new_start): #update start time
		self.curr = new_start
		if self.curr <= datetime.datetime.now(datetime.timezone.utc):
			self.next = new_start + self.cycle #next occurence
		else:
			self.next = new_start

class rush_list:
	def __init__(self, names, limit, cycle):
		self.list = []
		self.name = names
		self.emoji = bot.emoji_dict[self.name[0]]
		self.cycle = cycle
		self.limit = limit
		self.full = False
	def add_rush(self, start):
		name = self.name[0]
		self.list.append(rush(name, self.emoji, self.cycle, start))
	def full_check(self):
		if len(self.list) < self.limit:
			self.full = False
		else:
			self.full = True
	def update(self, new_cycle):
		self.cycle = new_cycle
		for item in self.list:
			item.update(new_cycle)

def get_day_hour(timedelta):
	return timedelta.days, timedelta.seconds//3600

def initialize():
	#emoji dictionary
	bot.emoji_dict = {'Fire': '<:Red:1005425349988982886>', 
					'Earth': '<:Green:1005425336080683112>', 
					'Sea': '<:Blue:1005425329260728351>', 
					'Sun': '<:Light:1005425342082715712>',
					'Moon': '<:Dark:1005425330342875207>',
					'Chromatic': '<:Red:1005425349988982886> <:Green:1005425336080683112> <:Blue:1005425329260728351> <:Light:1005425342082715712> <:Dark:1005425330342875207>',
					'Rainbow': ':rainbow:',
					'Dragon': ':dragon_face:',
					'Gold': ':coin:',
					'Talent': '<:TalentRune:1005425358838968391>',
					'Scramble': '<:SilverTalentRune:1005425356137828383>'}
	#cycles
	bot.xp_cycle = None
	bot.resource_cycle = None

	#initiate rush lists
	bot.red = rush_list(['Fire','fire','Red','red'], 2, bot.xp_cycle)
	bot.green = rush_list(['Earth','earth','Green','green'], 2, bot.xp_cycle)
	bot.blue = rush_list(['Sea','sea','Blue','blue'], 2, bot.xp_cycle)
	bot.light = rush_list(['Sun','sun','Light','light'], 2, bot.xp_cycle)
	bot.dark = rush_list(['Moon','moon','Dark','dark'], 2, bot.xp_cycle)
	bot.chromatic = rush_list(['Chromatic','chromatic'], 2, bot.xp_cycle)
	bot.rainbow = rush_list(['Rainbow','rainbow'], 2, bot.xp_cycle)
	bot.dragon = rush_list(['Dragon','dragon'], 2, bot.resource_cycle)
	bot.gold = rush_list(['Gold','gold'], 4, bot.resource_cycle)
	bot.showdown = rush_list(['Talent', 'talent', 'Showdown','showdown'], 3, bot.resource_cycle)
	bot.scramble = rush_list(['Scramble','scramble'], 1, bot.resource_cycle)

	#rush list
	bot.rush_names = ['Fire/Red', 'Earth/Green', 'Sea/Blue', 'Sun/Light', 'Moon/Dark', 'Chromatic', 'Rainbow', 'Dragon', 'Gold', 'Showdown', 'Scramble']
	bot.xp_names = ['Fire/Red', 'Earth/Green', 'Sea/Blue', 'Sun/Light', 'Moon/Dark', 'Chromatic', 'Rainbow']
	bot.resource_names = ['Dragon', 'Gold', 'Showdown', 'Scramble']
	bot.list_of_rush = [bot.red, bot.green, bot.blue, bot.light, bot.dark, bot.chromatic, bot.rainbow, bot.dragon, bot.gold, bot.showdown, bot.scramble]
	bot.list_of_xp_rush = [bot.red, bot.green, bot.blue, bot.light, bot.dark, bot.chromatic, bot.rainbow]
	bot.list_of_resource_rush = [bot.dragon, bot.gold, bot.showdown, bot.scramble]

	#for finding rushes
	bot.all_rush = []
	for item in bot.list_of_rush:
		bot.all_rush += item.name
	bot.xp_rush = []
	for item in bot.list_of_xp_rush:
		bot.xp_rush += item.name
	bot.resource_rush = []
	for item in bot.list_of_resource_rush:
		bot.resource_rush += item.name

	#for tracking upcoming rushes
	bot.upcoming_rush = []
	bot.upcoming_xp_rush = []
	bot.upcoming_resource_rush = []

	#tracking channels with announcements
	bot.announcement_channels = []
	bot.announcement_continues = []

def update():
	#reset upcoming
	bot.upcoming_rush = []
	bot.upcoming_xp_rush = []
	bot.upcoming_resource_rush = []

	for rush in bot.list_of_xp_rush:
		rush.update(bot.xp_cycle)
		rush.list.sort(key=lambda x:x.next)
		bot.upcoming_xp_rush += rush.list
	for rush in bot.list_of_resource_rush:
		rush.update(bot.resource_cycle)
		rush.list.sort(key=lambda x:x.next)
		bot.upcoming_resource_rush += rush.list
	bot.upcoming_rush = bot.upcoming_xp_rush + bot.upcoming_resource_rush

	bot.upcoming_rush.sort(key=lambda x: x.next)
	bot.upcoming_xp_rush.sort(key=lambda x: x.next)
	bot.upcoming_resource_rush.sort(key=lambda x: x.next)
	pickle_data()

def pickle_data():
	#save data into pickle file
	pickle_list = [bot.list_of_rush, bot.list_of_xp_rush, bot.list_of_resource_rush, bot.xp_cycle, bot.resource_cycle]
	with open('data.pkl', 'wb') as f:
		pickle.dump(pickle_list, f)

def unpickle_data():
	with open('data.pkl', 'rb') as f:
		pickle_list = pickle.load(f)

	bot.list_of_rush = pickle_list[0]
	bot.list_of_xp_rush = pickle_list [1]
	bot.list_of_resource_rush = pickle_list[2]
	bot.xp_cycle = pickle_list[3]
	bot.resource_cycle = pickle_list[4]

	bot.red = bot.list_of_rush[0]
	bot.green = bot.list_of_rush[1]
	bot.blue = bot.list_of_rush[2]
	bot.light = bot.list_of_rush[3]
	bot.dark = bot.list_of_rush[4]
	bot.chromatic = bot.list_of_rush[5]
	bot.rainbow = bot.list_of_rush[6]
	bot.dragon = bot.list_of_rush[7]
	bot.gold = bot.list_of_rush[8]
	bot.showdown = bot.list_of_rush[9]
	bot.scramble = bot.list_of_rush[10]
	update()

@bot.event
async def on_ready():
	print(f'{bot.user} has connected to Discord!')
	channel = bot.get_channel(1076667650635206818)
	initialize()
	if os.path.isfile('data.pkl'):
		unpickle_data()
		await channel.send(f'Rush tracker is online. Stored rush data has been loaded. Please use !status to check the data and !announcement to reset announcements. Use !reset if you wish to reset the bot.')
	else:
		await channel.send(f'Rush tracker is online. No stored rush data is found. Please add the rush cycles and rushes.')

#set rush intervals
@bot.command(name = 'set')
async def set(ctx, rush_type, interval):
	day, hour = interval.split("-")
	#xp interval
	if rush_type == 'xp':
		if bot.xp_cycle != None:
			old_day, old_hour = get_day_hour(bot.xp_cycle)
			await ctx.send(f'The XP rush cycle is currently set to {old_day} days {old_hour} hours. Are you sure you want to change it? (yes/no)')
			msg = await bot.wait_for('message', timeout = 60)
			if not(msg.content in ["Yes", "yes"]):
				return
		bot.xp_cycle = datetime.timedelta(days = int(day), hours = int(hour))
		update()
		await ctx.send(f'The XP rush interval is set to {day} days {hour} hours.')
	#resource interval
	if rush_type == 'resource':
		if bot.resource_cycle != None:
			old_day, old_hour = get_day_hour(bot.resource_cycle)
			await ctx.send(f'The resource rush cycle is currently set to {old_day} days {old_hour} hours. Are you sure you want to change it? (yes/no)')
			msg = await bot.wait_for('message', timeout = 60)
			if not(msg.content in ["Yes", "yes"]):
				return
		bot.resource_cycle = datetime.timedelta(days = int(day), hours = int(hour))
		update()
		await ctx.send(f'The resource rush interval is set to {day} days {hour} hours.')

@bot.command(name = 'add')
async def add(ctx, rush_name, *, start):
	#check rush name makes sense
	if not(rush_name in bot.all_rush):
		await ctx.send('Sorry, this rush type is not recognized. The recognized rushes are ' + ', '.join(bot.rush_names) + '.')
		return
	#xp rush
	if rush_name in bot.xp_rush:
		#check xp cycle exists, otherwise ask for it
		if bot.xp_cycle == None:
			await ctx.send('The XP rush interval has not been set. Use the !set command to set the interval first.')
			return
		#convert start time to datetime object
		start_time = datetime.datetime.strptime(start, '%d/%m/%y %H:%M')
		start_time = start_time.replace(tzinfo = datetime.timezone.utc)
		#find object of rush type
		for rush_obj in bot.list_of_xp_rush:
			if rush_name in rush_obj.name:
				break
		#check rush is not already full
		if not rush_obj.full:
			rush_obj.add_rush(start_time)
			rush_obj.full_check()
			await ctx.send(f'A {rush_obj.name[1]} rush starting at {start} UTC has been added.')
		else:
			await ctx.send(f'There are already {rush_obj.limit} cycles recorded for this rush. Please modify a cycle instead.')

	#resource rush
	if rush_name in bot.resource_rush:
		#check xp cycle exists, otherwise ask for it
		if bot.resource_cycle == None:
			await ctx.send('The resource rush interval has not been set. Use the !set command to set the interval first.')
			return
		#convert start time to datetime object
		start_time = datetime.datetime.strptime(start, '%d/%m/%y %H:%M')
		start_time = start_time.replace(tzinfo = datetime.timezone.utc)
		#find object of rush type
		for rush_obj in bot.list_of_resource_rush:
			if rush_name in rush_obj.name:
				break
		#check rush is not already full
		if not rush_obj.full:
			rush_obj.add_rush(start_time)
			rush_obj.full_check()
			await ctx.send(f'A {rush_obj.name[1]} rush starting at {start} UTC has been added.')
		else:
			await ctx.send(f'There are already {rush_obj.limit} cycles recorded for this rush. Please modify a cycle instead.')
	update()

@bot.command(name = 'modify')
async def modify(ctx, rush_name):
	#make sure rush is found
	if not(rush_name in bot.all_rush): 
		await ctx.send('Sorry, this rush type is not recognized. The recognized rushes are ' + ', '.join(bot.rush_names) + '.')
		return
	#identify rush object
	for rush_obj in bot.list_of_rush: 
		if rush_name in rush_obj.name:
			break
	#list recorde rushes and ask for input
	msg = f'Here are the recorded {rush_obj.name[1]} rushes. Enter the numerical code of the rush cycle you wish to modify.\n'
	for i in range(len(rush_obj.list)):
		msg += f"**{i+1}** : {rush_obj.list[i].curr.strftime('%d/%m/%y %H:%M')}\n"
	await ctx.send(msg)
	response = await bot.wait_for('message', timeout = 60)
	item = int(response.content) - 1
	#check input is within range
	if (int(response.content) > len(rush_obj.list)) or (int(response.content) < 1):
		await ctx.send('Sorry, this number is not valid. Please redo the modify command.')
		return
	#wait for new rush start time input and modify instance
	await ctx.send(f'Enter the new start time for this cycle in dd/mm/yy HH:MM format.')
	start = await bot.wait_for('message', timeout = 60)
	start_time = datetime.datetime.strptime(start.content, '%d/%m/%y %H:%M')
	start_time = start_time.replace(tzinfo = datetime.timezone.utc)
	rush_obj.list[item].modify(start_time)
	await ctx.send(f'This cycle has been modified with start time {start.content} UTC.')
	update()

#showing recorded status
@bot.command(name = 'status')
async def status(ctx):
	#show rush intervals
	update()
	msg = "All times displayed in UTC.\n"
	if bot.xp_cycle == None:
		msg += f'**__XP Cycle:__** No XP cycle has been scheduled.\n'
	else:
		msg += f'**__XP Cycle:__** {bot.xp_cycle.days} days {bot.xp_cycle.seconds//3600} hours\n'
	if bot.resource_cycle == None:
		msg +=f'**__Resource Cycle:__** No resource cycle has been scheduled.\n'
	else:
		msg += f'**__Resource Cycle:__** {bot.resource_cycle.days} days {bot.resource_cycle.seconds//3600} hours\n'

	#show xp rush
	msg += '\n'
	for rush in bot.list_of_xp_rush:
		msg += f'**__{rush.name[0]} Rush__** {rush.emoji}\n'
		for item in rush.list:
			msg += f"{item.curr.strftime('%d/%m/%y %A %H:%M')}\n"
		if len(rush.list) < rush.limit:
			msg += f'{rush.limit-len(rush.list)} cycle(s) missing.\n'
	#show resource rush
	msg += '\n'
	for rush in bot.list_of_resource_rush:
		msg += f'**__{rush.name[0]} Rush__** {rush.emoji}\n'
		for item in rush.list:
			msg += f"{item.curr.strftime('%d/%m/%y %A %H:%M')}\n"
		if len(rush.list) < rush.limit:
			msg += f'{rush.limit-len(rush.list)} cycle(s) missing.\n'
	await ctx.send(msg)

#showing next occurence of each rush
@bot.command(name = 'nextrush')
async def nextrush(ctx, rush_name):
	#show xp rush
	update()
	msg = "All times displayed in UTC.\n"
	if rush_name == "all":
		#show resource rush
		for rush in bot.list_of_xp_rush:
			msg += f'**__{rush.name[0]} Rush__** {rush.emoji}\n'
			for item in rush.list:
				msg += f"{item.next.strftime('%d/%m/%y %A %H:%M')}\n"
			if len(rush.list) < rush.limit:
				msg += f'{rush.limit-len(rush.list)} cycle(s) missing.\n'
		#show resource rush
		msg += '\n'
		for rush in bot.list_of_resource_rush:
			msg += f'**__{rush.name[0]} Rush__** {rush.emoji}\n'
			for item in rush.list:
				msg += f"{item.next.strftime('%d/%m/%y %A %H:%M')}\n"
			if len(rush.list) < rush.limit:
				msg += f'{rush.limit-len(rush.list)} cycle(s) missing.\n'
	else:
		for rush_obj in bot.list_of_rush: 
			if rush_name in rush_obj.name:
				break
		msg += f'**__{rush_obj.name[0]} Rush__** {rush_obj.emoji}\n'
		for item in rush_obj.list:
			msg += f"{item.next.strftime('%d/%m/%y %A %H:%M')}\n"
		if len(rush_obj.list) < rush_obj.limit:
			msg += f'{rush_obj.limit-len(rush_obj.list)} cycle(s) missing.\n'
	await ctx.send(msg)

#showing rushes in next 7 days
@bot.command(name = 'nextweek')
async def nextweek(ctx):
	#show xp rush
	update()
	msg = "All times displayed in UTC.\n"
	for i in range(1,8):
		date = datetime.datetime.utcnow().date() + datetime.timedelta(days = i)
		msg += f"**__{date.strftime('%d/%m/%y %A')}__**\n"
		for rush in bot.upcoming_rush:
			if rush.next.date() == date:
				msg += f"{rush.name} Rush {rush.next.strftime('%H:%M')}\n"
	await ctx.send(msg)

#showing upcoming rushes today
@bot.command(name = 'today')
async def nextweek(ctx):
	#show xp rush
	update()
	msg = "All times displayed in UTC. Only upcoming rushes within today are shown.\n"
	date = datetime.datetime.utcnow().date()
	count = 0
	for rush in bot.upcoming_rush:
		if rush.next.date() == date:
			count += 1
			msg += f"{rush.name} Rush {rush.emoji} {rush.next.strftime('%H:%M')}\n"
	if count == 0:
		msg += f'There are no more upcoming rushes today.'
	await ctx.send(msg)

#send rush reminders
async def check_every_hour(channel_idx, time):
	now = datetime.datetime.now(datetime.timezone.utc)
	delay = (now.replace(microsecond = 0, second = 0, minute = 0) + datetime.timedelta(seconds = 3600) - now).total_seconds()
	await asyncio.sleep(delay)
	while bot.announcement_continues[channel_idx]: #need to add break
		update()
		now = datetime.datetime.now(datetime.timezone.utc)
		for rush in bot.upcoming_rush:
			if (rush.next - now <= datetime.timedelta(seconds = time)) and (not rush.reminder):
				await bot.wait_until_ready()
				channel = bot.get_channel(bot.announcement_channels[channel_idx])
				await channel.send(f"{rush.name} Rush {rush.emoji} at <t:{round(rush.next.timestamp())}:t> (approx. <t:{round(rush.next.timestamp())}:R>).")
				rush.reminder = True
		delay = (now.replace(microsecond = 0, second = 0, minute = 0) + datetime.timedelta(seconds = 3600) - now).total_seconds()
		await asyncio.sleep(delay)
	return

#set up announcement
@bot.command(name = 'announcement')
async def nextweek(ctx, hours:int):
	if ctx.channel.id in bot.announcement_channels:
		await ctx.send("Announcements are already set up here. Do you want to change the announcement time? (yes/no)")
		msg = await bot.wait_for('message', timeout = 60)
		if msg.content in ["Yes", "yes"]:
			for i in range(len(bot.announcement_channels)):
				if bot.announcement_channels[i] == ctx.channel.id:
					bot.announcement_continues[i] = False
			bot.announcement_channels.append(ctx.channel.id)
			bot.announcement_continues.append(True)
			await ctx.send(f'Rushes will be announced {hours} hours in advance.')
			await check_every_hour(len(bot.announcement_channels)-1, hours*3600)
	else:
		bot.announcement_channels.append(ctx.channel.id)
		bot.announcement_continues.append(True)
		await ctx.send(f'Rushes will be announced {hours} hours in advance.')
		await check_every_hour(len(bot.announcement_channels)-1, hours*3600)

#reset bot
@bot.command(name = 'reset')
async def nextweek(ctx):
	await ctx.send(f'Are you sure you want to reset the rush schedule? All recorded rush instance and announcement setups will be deleted. (yes/no)')
	msg = await bot.wait_for('message', timeout = 60)
	if msg.content in ["Yes", "yes"]:
		initialize()
		await ctx.send(f'The rush scheudle has been reset.')
	update()

#help
@bot.command(name = 'help')
async def nextweek(ctx):
	msg = f'Here are the possible commands and their respective formatting for this bot.\n'
	msg += f'**!set**:\nset rush intervals.\nFormat !set [xp/resource] [day-hours].\n'
	msg += f'**!add**:\nadd new rush cycle. Time in UTC.\nFormat !add [rush name] [dd/mm/yy HH:MM].\n'
	msg += f'**!modify**:\nmodify existing rush cycle. Time in UTC.\nFormat !modify [rush name]. \n'
	msg += f'**!status**:\nshow status of recorded rushes, including last occurence of each rush. Time in UTC.\nFormat !status.\n'
	msg += f'**!nextrush**:\nquery next occurence of specific or all rushes. Time in UTC.\nFormat !nextrush [rush name/all]. \n'
	msg += f'**!nextweek**:\nshow all rushes in the next 7 days. Time in UTC.\nFormat !nextweek.\n'
	msg += f'**!announcement**:\nset up rush announcement in channel.\nFormat !announcement [number of hours in advance for announcement].\n'
	msg += f'**!reset**:\nclear all recorded data and announcements.\n'
	await ctx.send(msg)

bot.run(TOKEN)