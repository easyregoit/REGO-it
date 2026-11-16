import json
import os
from pathlib import Path
import discord
from discord.ext import commands

TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "").strip()

CHANNEL_ID = 1571263054451052786              # #welcome-and-rules channel ID
MESSAGE_ID = 1571281810086957126              # Welcome post message ID
ANNOUNCEMENT_CHANNEL_ID = 1571296900324401333 # #beta-tester-promotion channel ID

BETA_ROLE_NAME = "Beta Tester"
MOD_ROLE_NAME = "REGO MODs"
VERIFIED_ROLE_NAME = "Member"
PROGRESS_FILE = Path(__file__).with_name("beta_progress.json")

# Highest-to-lowest priority order (keep highest role & strip lower roles when promoted)
RANK_HIERARCHY = [MOD_ROLE_NAME, BETA_ROLE_NAME, VERIFIED_ROLE_NAME]

LANGUAGE_ROLES = {"🗣️ EN", "🗣️ FR", "🗣️ DE", "🗣️ ES", "🗣️ PT", "🗣️ RU"}
REGION_ROLES = {"🌍 NA", "🌍 SA", "🌍 EU", "🌍 AF", "🌍 AS", "🌍 OC"}
PLATFORM_ROLES = {"💻 Web / Desktop", "🍎 IOS", "📱 Android"}
CATEGORY_GROUPS = [LANGUAGE_ROLES, REGION_ROLES, PLATFORM_ROLES]

TASK_LABELS: dict[str, str] = {
    "bug-reports": "Add a bug report in any #bug-reports channel",
    "feature-requests": "Add a feature request in #feature-requests",
    "preview-renders": "Share a screenshot in #preview-renders",
    "completed-builds": "Share a build photo in #completed-builds",
}
IMAGE_REQUIRED_TASKS = {"preview-renders", "completed-builds"}
READ_ONLY_CHANNELS = {"announcements", "how-to-order-bricks", "beta-tester-promotion"}
PRIVATE_STAFF_CHANNELS = {"bot-update"}

EMOJI_TO_ROLES: dict[str, list[str]] = {
    "🇬🇧": ["🗣️ EN"],
    "🇫🇷": ["🗣️ FR"],
    "🇩🇪": ["🗣️ DE"],
    "🇪🇸": ["🗣️ ES"],
    "🇵🇹": ["🗣️ PT"],
    "🇷🇺": ["🗣️ RU"],
    "🌎": ["🌍 NA"],
    "🌴": ["🌍 SA"],
    "🌍": ["🌍 EU"],
    "🦁": ["🌍 AF"],
    "🌏": ["🌍 AS"],
    "🏝️": ["🌍 OC"],
    "💻": ["💻 Web / Desktop"],
    "🍎": ["🍎 IOS"],
    "📱": ["📱 Android"],
}

intents = discord.Intents.default()
intents.members = True
intents.reactions = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


def load_progress() -> dict[str, list[str]]:
    if PROGRESS_FILE.exists():
        try:
            return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_progress(data: dict[str, list[str]]) -> None:
    PROGRESS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def format_checklist(completed: list[str]) -> str:
    return "\n".join(
        f"{'✅' if key in completed else '⬜'} {label}"
        for key, label in TASK_LABELS.items()
    )


def get_task_key(channel_name: str) -> str | None:
    if channel_name.startswith("bug-reports"):
        return "bug-reports"
    if channel_name in TASK_LABELS:
        return channel_name
    return None


def has_all_three_categories(member: discord.Member) -> bool:
    names = {r.name for r in member.roles}
    return bool(names & LANGUAGE_ROLES) and bool(names & REGION_ROLES) and bool(names & PLATFORM_ROLES)


async def get_or_dedupe_role(guild: discord.Guild, role_name: str, reason: str) -> discord.Role | None:
    """
    Finds existing roles matching role_name, migrates members off duplicates,
    deletes duplicate roles with the same name so no extra roles accumulate,
    and only creates the role if zero exist.
    """
    matching = [r for r in guild.roles if r.name == role_name and not r.managed]
    if not matching:
        matching = [r for r in guild.roles if r.name == role_name]

    if not matching:
        try:
            return await guild.create_role(name=role_name, reason=reason)
        except discord.HTTPException as exc:
            print(f"Could not create '{role_name}': {exc}")
            return None

    # Prefer the highest-position role as the single canonical role
    matching.sort(key=lambda r: r.position, reverse=True)
    primary = matching[0]

    for dup in matching[1:]:
        if dup.managed:
            continue
        for m in list(dup.members):
            try:
                if primary not in m.roles:
                    await m.add_roles(primary, reason=f"Consolidated duplicate {role_name}")
                await m.remove_roles(dup, reason=f"Removed duplicate {role_name}")
            except discord.HTTPException:
                pass
        try:
            await dup.delete(reason=f"Removed duplicate {role_name} role")
            print(f"Deleted duplicate '{role_name}' role (ID: {dup.id})")
        except discord.HTTPException as exc:
            print(f"Could not delete duplicate '{role_name}': {exc}")

    return primary


async def enforce_single_highest_rank(guild: discord.Guild, member: discord.Member) -> None:
    """
    Keeps only the highest rank role a member has earned from RANK_HIERARCHY
    (REGO MODs > Beta Tester > Member) and strips lower rank roles.
    """
    member_role_names = {r.name for r in member.roles}
    highest_rank_name: str | None = None
    for rank_name in RANK_HIERARCHY:
        if rank_name in member_role_names:
            highest_rank_name = rank_name
            break

    if not highest_rank_name:
        return

    roles_to_remove = [
        r for r in member.roles
        if r.name in RANK_HIERARCHY and r.name != highest_rank_name and not r.managed
    ]
    if roles_to_remove:
        try:
            await member.remove_roles(
                *roles_to_remove,
                reason=f"Stripped lower rank roles in favor of highest role '{highest_rank_name}'",
            )
        except discord.HTTPException as exc:
            print(f"Could not strip lower roles for {member.display_name}: {exc}")


async def sync_verified_access(guild: discord.Guild, member: discord.Member) -> None:
    verified_role = discord.utils.get(guild.roles, name=VERIFIED_ROLE_NAME)
    beta_role = discord.utils.get(guild.roles, name=BETA_ROLE_NAME)
    mod_role = discord.utils.get(guild.roles, name=MOD_ROLE_NAME)
    if verified_role is None:
        return

    has_higher_rank = any(r and r in member.roles for r in (beta_role, mod_role))

    if has_all_three_categories(member):
        if not has_higher_rank and verified_role not in member.roles:
            await member.add_roles(verified_role, reason="Picked all 3 welcome role categories")
    else:
        if verified_role in member.roles:
            await member.remove_roles(verified_role, reason="Missing one of the 3 welcome role categories")

    await enforce_single_highest_rank(guild, member)


async def configure_server_gate(guild: discord.Guild, verified_role: discord.Role | None) -> None:
    if verified_role is None:
        return

    everyone = guild.default_role

    for channel in guild.text_channels:
        try:
            if channel.id == CHANNEL_ID or channel.name == "welcome-and-rules":
                await channel.set_permissions(
                    everyone,
                    view_channel=True,
                    read_message_history=True,
                    add_reactions=True,
                    send_messages=False,
                )
            elif channel.name in PRIVATE_STAFF_CHANNELS:
                await channel.set_permissions(everyone, view_channel=False)
                await channel.set_permissions(verified_role, view_channel=False)
            else:
                await channel.set_permissions(everyone, view_channel=False)
                is_read_only = channel.name in READ_ONLY_CHANNELS
                await channel.set_permissions(
                    verified_role,
                    view_channel=True,
                    read_message_history=True,
                    send_messages=not is_read_only,
                )
        except discord.HTTPException as exc:
            print(f"Could not update permissions on #{channel.name}: {exc}")


async def grant_beta_and_announce(guild: discord.Guild, member: discord.Member, reason: str) -> bool:
    beta_role = discord.utils.get(guild.roles, name=BETA_ROLE_NAME)
    if beta_role is None:
        return False

    if beta_role not in member.roles:
        await member.add_roles(beta_role, reason=reason)

    updated_member = await guild.fetch_member(member.id)
    await enforce_single_highest_rank(guild, updated_member)

    beta_members = sorted(beta_role.members, key=lambda m: m.display_name.lower())
    if updated_member not in beta_members:
        beta_members.append(updated_member)
    all_beta_mentions = ", ".join(m.mention for m in beta_members) or updated_member.mention

    if ANNOUNCEMENT_CHANNEL_ID:
        target_channel = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID) or await bot.fetch_channel(ANNOUNCEMENT_CHANNEL_ID)
        if target_channel:
            await target_channel.send(
                f"🎉 **New Beta Tester:** {updated_member.mention} is now a **{BETA_ROLE_NAME}**!\n"
                f"**All Beta Testers ({len(beta_members)}):** {all_beta_mentions}"
            )
    return True


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    progress = load_progress()

    for guild in bot.guilds:
        verified_role = await get_or_dedupe_role(
            guild, VERIFIED_ROLE_NAME, "Single gate role for verified members"
        )
        beta_role = await get_or_dedupe_role(
            guild, BETA_ROLE_NAME, "Single Beta Tester role"
        )
        await configure_server_gate(guild, verified_role)

        async for member in guild.fetch_members(limit=None):
            if member.bot:
                continue
            if beta_role and beta_role in member.roles:
                if len(progress.get(str(member.id), [])) < 2:
                    mod_role = discord.utils.get(guild.roles, name=MOD_ROLE_NAME)
                    is_mod = mod_role is not None and mod_role in member.roles
                    if not is_mod:
                        try:
                            await member.remove_roles(beta_role, reason="Stripped unearned Beta Tester role")
                        except discord.HTTPException:
                            pass
            await sync_verified_access(guild, member)

    if CHANNEL_ID and MESSAGE_ID:
        try:
            channel = bot.get_channel(CHANNEL_ID) or await bot.fetch_channel(CHANNEL_ID)
            msg = await channel.fetch_message(MESSAGE_ID)
            for emoji in EMOJI_TO_ROLES:
                try:
                    await msg.add_reaction(emoji)
                except discord.HTTPException as exc:
                    print(f"Could not add {emoji}: {exc}")

            for reaction in msg.reactions:
                role_names = EMOJI_TO_ROLES.get(str(reaction.emoji))
                if not role_names:
                    continue
                roles = [discord.utils.get(channel.guild.roles, name=n) for n in role_names]
                roles = [r for r in roles if r is not None]
                if not roles:
                    continue
                async for user in reaction.users():
                    if user.bot:
                        continue
                    member = channel.guild.get_member(user.id) or await channel.guild.fetch_member(user.id)
                    missing = [r for r in roles if r not in member.roles]
                    if missing:
                        await member.add_roles(*missing, reason="Synced reaction clicked while offline")
                    updated_member = await channel.guild.fetch_member(user.id)
                    await sync_verified_access(channel.guild, updated_member)

            print("Server gate configured, duplicate roles cleaned, and welcome reactions synced.")
        except discord.HTTPException as exc:
            print(f"Could not access welcome message: {exc}")


@bot.event
async def on_member_join(member: discord.Member):
    beta_role = discord.utils.get(member.guild.roles, name=BETA_ROLE_NAME)
    verified_role = discord.utils.get(member.guild.roles, name=VERIFIED_ROLE_NAME)
    roles_to_strip = [r for r in (beta_role, verified_role) if r and r in member.roles and not r.managed]
    if roles_to_strip:
        try:
            await member.remove_roles(*roles_to_strip, reason="New join must start as @everyone only")
        except discord.HTTPException:
            pass


@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.user_id == bot.user.id or payload.guild_id is None:
        return
    if MESSAGE_ID and payload.message_id != MESSAGE_ID:
        return

    role_names = EMOJI_TO_ROLES.get(str(payload.emoji))
    if not role_names:
        return

    guild = bot.get_guild(payload.guild_id)
    if guild is None:
        return

    member = payload.member or await guild.fetch_member(payload.user_id)
    roles = [discord.utils.get(guild.roles, name=n) for n in role_names]
    roles = [r for r in roles if r is not None]
    if roles:
        # Remove older selection in the same category so only 1 role per category stays
        for r in roles:
            for group in CATEGORY_GROUPS:
                if r.name in group:
                    old_same_cat = [
                        existing for existing in member.roles
                        if existing.name in group and existing.name != r.name and not existing.managed
                    ]
                    if old_same_cat:
                        try:
                            await member.remove_roles(*old_same_cat, reason="Replaced previous role in same category")
                        except discord.HTTPException:
                            pass

        await member.add_roles(*roles, reason="REGO welcome reaction role")
        updated_member = await guild.fetch_member(payload.user_id)
        await sync_verified_access(guild, updated_member)


@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    if payload.user_id == bot.user.id or payload.guild_id is None:
        return
    if MESSAGE_ID and payload.message_id != MESSAGE_ID:
        return

    role_names = EMOJI_TO_ROLES.get(str(payload.emoji))
    if not role_names:
        return

    guild = bot.get_guild(payload.guild_id)
    if guild is None:
        return

    member = await guild.fetch_member(payload.user_id)
    roles = [discord.utils.get(guild.roles, name=n) for n in role_names]
    roles = [r for r in roles if r is not None]
    if roles:
        await member.remove_roles(*roles, reason="Removed welcome reaction role")
        updated_member = await guild.fetch_member(payload.user_id)
        await sync_verified_access(guild, updated_member)


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or message.guild is None:
        return

    if isinstance(message.channel, discord.TextChannel) and not message.content.startswith("!"):
        task_key = get_task_key(message.channel.name)
        if task_key:
            has_image = bool(message.attachments)
            if task_key not in IMAGE_REQUIRED_TASKS or has_image:
                progress = load_progress()
                user_key = str(message.author.id)
                completed = progress.get(user_key) or []

                if task_key not in completed:
                    completed.append(task_key)
                    progress[user_key] = completed
                    save_progress(progress)

                    try:
                        await message.add_reaction("✅")
                    except discord.HTTPException:
                        pass

                    if len(completed) >= 2 and isinstance(message.author, discord.Member):
                        await grant_beta_and_announce(
                            message.guild,
                            message.author,
                            reason="Completed 2/4 Beta Tester checklist tasks",
                        )

    await bot.process_commands(message)


@bot.command(name="checklist")
async def checklist(ctx: commands.Context, member: discord.Member | None = None):
    target = member or ctx.author
    progress = load_progress()
    completed = progress.get(str(target.id), [])
    status = "🎉 **Beta Tester Unlocked!**" if len(completed) >= 2 else f"**{len(completed)}/2 boxes checked**"
    await ctx.send(
        f"**{target.display_name}'s Beta Checklist ({status}):**\n{format_checklist(completed)}"
    )


@bot.command(name="promote_beta")
async def promote_beta(ctx: commands.Context, member: discord.Member):
    if ctx.guild is None:
        return

    mod_role = discord.utils.get(ctx.guild.roles, name=MOD_ROLE_NAME)
    is_authorized = ctx.author.guild_permissions.administrator or (
        mod_role is not None and mod_role in ctx.author.roles
    )
    if not is_authorized:
        await ctx.send(f"Only `{MOD_ROLE_NAME}` or administrators can promote Beta Testers.", delete_after=10)
        return

    progress = load_progress()
    user_key = str(member.id)
    if len(progress.get(user_key, [])) < 2:
        progress[user_key] = ["bug-reports", "preview-renders"]
        save_progress(progress)

    ok = await grant_beta_and_announce(ctx.guild, member, reason="Manual promotion by moderator")
    if not ok:
        await ctx.send(f"Role `{BETA_ROLE_NAME}` was not found.", delete_after=10)

async def sync_reactions_for_removed_roles(
    guild: discord.Guild,
    member: discord.Member,
    removed_role_names: set[str],
) -> None:
    """
    When roles are manually removed from a member in Discord, remove that member's
    corresponding reaction emoji on the welcome message so their reaction state resets.
    """
    if not removed_role_names or not CHANNEL_ID or not MESSAGE_ID:
        return

    try:
        channel = bot.get_channel(CHANNEL_ID) or await bot.fetch_channel(CHANNEL_ID)
        msg = await channel.fetch_message(MESSAGE_ID)
    except discord.HTTPException as exc:
        print(f"Could not fetch welcome message for reaction reset: {exc}")
        return

    for emoji, mapped_roles in EMOJI_TO_ROLES.items():
        if any(role_name in removed_role_names for role_name in mapped_roles):
            try:
                await msg.remove_reaction(emoji, member)
            except discord.HTTPException as exc:
                print(f"Could not reset reaction {emoji} for {member.display_name}: {exc}")


@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    if after.bot or after.guild is None:
        return

    before_ids = {r.id for r in before.roles}
    after_ids = {r.id for r in after.roles}
    removed_ids = before_ids - after_ids

    if not removed_ids:
        return

    removed_names = {r.name for r in before.roles if r.id in removed_ids}
    await sync_reactions_for_removed_roles(after.guild, after, removed_names)

    updated_member = await after.guild.fetch_member(after.id)
    await sync_verified_access(after.guild, updated_member)

if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("Set DISCORD_BOT_TOKEN before running role_bot.py")
    bot.run(TOKEN)