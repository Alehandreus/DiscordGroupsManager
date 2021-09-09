import discord
from discord.ext import commands
from discord.utils import get as discord_get
from enum import Enum, auto
from time import sleep


naming_formats = {
    "group_member_role": "{}",
    "group_admin_role": "староста",
    "group_category": "группа {}",
}


class CreateMode(Enum):
    create = auto()
    delete = auto()
    nothing = auto()


# ФАМИЛИЯ ИМЯ ОТЧЕСТВО -> Фамилия Имя
def fullname_to_discord_nick(fullname):
    name_1 = fullname.split()[0].capitalize()
    name_2 = fullname.split()[1].capitalize()
    # name_3 = fullname.split()[2].capitalize()
    return f"{name_1} {name_2}"


class DiscordGroupsManager:
    def __init__(self, guild_name, token, role_mode=CreateMode.create, channel_mode=CreateMode.create):
        self.guild_name = guild_name
        self.token = token

        # these params will be set in start func
        self.bot = None
        self.guild = None
        self.groups_data = None
        self.group_member_role_permissions = None
        self.group_admin_role_permissions = None

        self.default_text_channel_name = "основной"
        self.default_voice_channel_name = "основной"

        self.role_mode = role_mode
        self.channel_mode = channel_mode

    def start(self):
        intents = discord.Intents.default()
        intents.members = True
        self.bot = commands.Bot(intents=intents, command_prefix=":")

        @self.bot.event
        async def on_ready():
            print(f'{self.bot.user} has connected to Discord!')
            await self.real_start()

        self.bot.run(self.token)

    async def real_start(self):
        self.guild = discord_get(self.bot.guilds, name=self.guild_name)

        everyone_role = discord.utils.get(self.guild.roles, name="@everyone")
        self.group_member_role_permissions = everyone_role.permissions
        self.group_admin_role_permissions = everyone_role.permissions

        from parse_groupfile import get_groups
        self.groups_data = get_groups("2021.xlsx")

        # main part
        if self.role_mode == CreateMode.create and self.channel_mode == CreateMode.create:
            print("Working in a loop...")
            while True:
                await self.check_group_roles()
                await self.check_group_channels()
                sleep(5)

        elif self.role_mode == CreateMode.delete and self.channel_mode == CreateMode.create:
            print("You cant manage channels without roles")

        else:
            await self.check_group_roles()
            print("Roles done")
            await self.check_group_channels()
            print("Channels done")

        await self.bot.close()

    async def check_group_channels(self):
        group_admin_role_name = naming_formats["group_admin_role"].format()
        group_admin_role = discord_get(self.guild.roles, name=group_admin_role_name)

        for group_data in self.groups_data:
            group_title = group_data["title"]
            group_category_name = naming_formats["group_category"].format(group_title)

            # delete group category with all channels if exists
            if self.channel_mode == CreateMode.delete:
                if group_category := discord_get(self.guild.categories, name=group_category_name):
                    for channel in group_category.channels:
                        await channel.delete()
                    await group_category.delete()

            # create group category and assign permissions
            # if category already exists, check its permissions to be correct
            # and make sure that at least two channels exist
            if self.channel_mode == CreateMode.create:
                group_member_role_name = naming_formats["group_member_role"].format(group_title)
                group_member_role = discord_get(self.guild.roles, name=group_member_role_name)

                # permissions for group category
                group_category_overwrites = {
                    self.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    group_member_role: discord.PermissionOverwrite(read_messages=True),
                    group_admin_role: discord.PermissionOverwrite(read_messages=False, manage_channels=True),
                }

                if not (group_category := discord_get(self.guild.categories, name=group_category_name)):  # category does not exist, need to create
                    group_category = await self.guild.create_category(name=group_category_name, overwrites=group_category_overwrites)
                    text_channel = await group_category.create_text_channel(name=self.default_text_channel_name)
                    voice_channel = await group_category.create_voice_channel(name=self.default_voice_channel_name)

                else:  # category exists, need to check permissions and channels
                    if group_category.overwrites != group_category_overwrites:
                        group_category = await group_category.edit(overwrites=group_category_overwrites)

                    text_channel_exists = False
                    for text_channel in group_category.text_channels:
                        if not text_channel.permissions_synced:
                            await text_channel.edit(sync_permissions=True)
                        text_channel_exists = True
                    if not text_channel_exists:
                        text_channel = await group_category.create_text_channel(name=self.default_text_channel_name)

                    voice_channel_exists = False
                    for voice_channel in group_category.voice_channels:
                        if not voice_channel.permissions_synced:
                            await voice_channel.edit(sync_permissions=True)
                        voice_channel_exists = True
                    if not voice_channel_exists:
                        voice_channel = await group_category.create_voice_channel(name=self.default_voice_channel_name)

    async def check_group_roles(self):
        group_admin_role_name = naming_formats["group_admin_role"].format()
        group_admin_role = discord_get(self.guild.roles, name=group_admin_role_name)

        # delete group admin role
        if self.role_mode == CreateMode.delete:
            if group_admin_role:
                await group_admin_role.delete()

        # create group admin role
        # if role already exists, check its permissions to be correct
        if self.role_mode == CreateMode.create:
            if not group_admin_role:
                group_admin_role = await self.guild.create_role(name=group_admin_role_name, permissions=self.group_member_role_permissions)
            elif group_admin_role.permissions != self.group_admin_role_permissions:
                group_admin_role = await group_admin_role.edit(permissions=self.group_admin_role_permissions)

        for group_data in self.groups_data:
            group_title = group_data["title"]
            group_member_role_name = naming_formats["group_member_role"].format(group_title)

            # delete group member role
            if self.role_mode == CreateMode.delete:
                if group_member_role := discord_get(self.guild.roles, name=group_member_role_name):
                    await group_member_role.delete()

            # create group role and assign it.
            # if role already exists, check its permissions to be correct
            if self.role_mode == CreateMode.create:
                if not (group_member_role := discord_get(self.guild.roles, name=group_member_role_name)):
                    group_member_role = await self.guild.create_role(name=group_member_role_name, permissions=self.group_member_role_permissions)
                elif group_member_role.permissions != self.group_member_role_permissions:
                    group_member_role = await group_member_role.edit(permissions=self.group_member_role_permissions)

                for group_admin_fullname in group_data["admins"]:
                    group_admin_nickname = fullname_to_discord_nick(group_admin_fullname)
                    if user := discord_get(self.guild.members, nick=group_admin_nickname):
                        await user.add_roles(group_admin_role)
                        await user.add_roles(group_member_role)

                for group_member_fullname in group_data["members"]:
                    group_member_nickname = fullname_to_discord_nick(group_member_fullname)
                    if user := discord_get(self.guild.members, nick=group_member_nickname):
                        await user.add_roles(group_member_role)
