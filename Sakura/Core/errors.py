from pyrogram import Client
from Sakura.Core.logging import logger

@Client.on_error()
async def handle_error(client: Client, exception: Exception) -> None:
    """Handle errors"""
    logger.error(f"💥 Unhandled exception occurred: {exception}", exc_info=True)