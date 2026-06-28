"""Discord adapter — a `/request` slash command + plain DMs to the bot.

Lazy-imports discord.py (2.x). Normalizes each interaction/message into a
Request whose `reply` answers on the same channel, then funnels through the
shared pipeline.
"""

from __future__ import annotations

import logging

from ..config import Config
from ..models import Channel, MediaType, Request
from ..pipeline import handle

log = logging.getLogger("intake_bot.discord")


async def run(cfg: Config) -> None:
    import discord  # lazy
    from discord import app_commands

    intents = discord.Intents.default()
    intents.message_content = True  # to read DM text as requests
    client = discord.Client(intents=intents)
    tree = app_commands.CommandTree(client)

    @tree.command(
        name="request",
        description="Request a movie or show (e.g. 'Dune Part Two 2024')",
    )
    @app_commands.describe(
        title="Title (optionally with year)",
        tracker="Optional: pin a specific tracker/indexer",
    )
    async def request_cmd(
        interaction: "discord.Interaction", title: str, tracker: str | None = None
    ):
        await interaction.response.defer(thinking=True)

        async def reply(text: str) -> None:
            await interaction.followup.send(text)

        req = Request(
            channel=Channel.DISCORD,
            user=str(interaction.user.id),
            text=title,
            reply=reply,
            pinned_indexer=tracker,
        )
        await handle(req, cfg)

    @client.event
    async def on_ready():
        await tree.sync()
        log.info("discord ready as %s", client.user)

    @client.event
    async def on_message(message: "discord.Message"):
        # Respond to DMs only (avoid reacting to every guild message).
        if message.author == client.user:
            return
        if message.guild is not None:
            return
        if not message.content.strip():
            return

        async def reply(text: str) -> None:
            await message.channel.send(text)

        req = Request(
            channel=Channel.DISCORD,
            user=str(message.author.id),
            text=message.content,
            reply=reply,
        )
        await handle(req, cfg)

    log.info("starting discord adapter")
    await client.start(cfg.discord_bot_token)
