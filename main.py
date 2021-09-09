from DiscordGroupsManager import DiscordGroupsManager, CreateMode


guild_name = ""

token = ""

role_mode = CreateMode.create
channel_mode = CreateMode.create

a = DiscordGroupsManager(guild_name, token, role_mode, channel_mode)
a.start()
