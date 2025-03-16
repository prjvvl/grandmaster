
import logging
import os
from typing import Dict, Any, Optional, Union, BinaryIO


import traceback
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes


class TelegramClient:
    """Client for interacting with Telegram API."""

    def __init__(self, grandmaster):
        """Initialize the Telegram client."""
        self.grandmaster = grandmaster
        self.logger = logging.getLogger('grandmaster.telegram')

         # Get configuration from environment variables
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.token:
            self.logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        
        self.highborn_channel_id = os.getenv("TELEGRAM_HIGHBORN_CHANNEL_ID") # High priority messages
        self.townsquare_channel_id = os.getenv("TELEGRAM_TOWNSQUARE_CHANNEL_ID") # General messages
        self.smallfolk_channel_id = os.getenv("TELEGRAM_SMALLFOLK_CHANNEL_ID") # Low priority messages

        self.raven_channel_id = os.getenv("TELEGRAM_RAVEN_CHANNEL_ID") # Important Notifications
        self.whispers_channel_id = os.getenv("TELEGRAM_WHISPERS_CHANNEL_ID") # General messages

        self.maester_channel_id = os.getenv("TELEGRAM_MAESTER_CHANNEL_ID") # Admin messages
        self.bunker_channel_id = os.getenv("TELEGRAM_BUNKER_CHANNEL_ID") # Logs and Debugging
        

        # Initialize the Telegram bot
        self.application = Application.builder().token(self.token).build()
        self.bot = self.application.bot

        # Register command handlers
        self._register_handlers()

    def _register_handlers(self):
        """Register command and message handlers."""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self._cmd_start))
        self.application.add_handler(CommandHandler("help", self._cmd_help))

         # Message handler for non-command messages
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))
        
        # Error handler
        self.application.add_error_handler(self._error_handler)

    async def start(self):
        """Start the Telegram bot."""
        self.logger.info("Starting Telegram bot")
        await self.application.initialize()
        await self.application.start()
        self.logger.info("Telegram bot started successfully")
        
        # Test the connection to channels
        try:
            bot_info = await self.bot.get_me()
            self.logger.info(f"Connected as {bot_info.first_name} (@{bot_info.username})")
        except Exception as e:
            self.logger.error(f"Failed to get bot info: {e}")

    async def stop(self):
        """Stop the Telegram bot."""
        self.logger.info("Stopping Telegram bot")
        await self.application.stop()
        await self.application.shutdown()
        self.logger.info("Telegram bot stopped successfully")


    async def send_message(
        self,
        content: str,
        channel: Optional[Union[str, int]] = None,
        media_type: Optional[str] = None,
        media_path: Optional[str] = None,
        parse_mode: Optional[str] = None
    ) -> Optional[Any]:
        """
        Send a message or media to the specified channel.
        
        Args:
            content: Text message or caption for media
            channel: Can be one of:
                    - str: "HIGHBORN", "TOWNSQUARE", "SMALLFOLK", "RAVEN", "MAESTER", "CITADEL", "WHISPERS" for predefined channels
                    - int/str: direct channel ID to send message to
                    - None: Defaults to "WHISPERS"
            media_type: Type of media ("photo", "video", "document", "audio" etc.) if sending media
            media_path: Path to the media file if sending media
            parse_mode: Message parsing mode (default: None)
        
        Returns:
            Message response or None if sending failed
        """
        channel_map = {
            "highborn": self.highborn_channel_id,
            "townsquare": self.townsquare_channel_id,
            "smallfolk": self.smallfolk_channel_id,
            "raven": self.raven_channel_id,
            "maester": self.maester_channel_id,
            "bunker": self.bunker_channel_id,
            "whispers": self.whispers_channel_id,  # Default channel
        }
        
        if isinstance(channel, str):
            target_channel_id = channel_map.get(channel.lower(), channel)
        else:
            target_channel_id = channel if isinstance(channel, int) else self.whispers_channel_id

        
        if not target_channel_id:
            self.logger.warning("No target channel ID available")
            return None
        
        try:
            # Text message
            if media_type is None or media_path is None:
                return await self.bot.send_message(
                    chat_id=target_channel_id,
                    text=content,
                    parse_mode=parse_mode
                )
            
            # Check if media file exists
            if not os.path.exists(media_path):
                self.logger.error(f"Media file not found: {media_path}")
                return None
            
            # Media message - open the file and send
            with open(media_path, 'rb') as media_file:
                media_senders = {
                    "photo": self.bot.send_photo,
                    "video": self.bot.send_video,
                    "document": self.bot.send_document,
                    "audio": self.bot.send_audio,
                    "voice": self.bot.send_voice
                }
                
                send_func = media_senders.get(media_type.lower())
                if send_func:
                    return await send_func(
                        chat_id=target_channel_id,
                        **{media_type: media_file},
                        caption=content,
                        parse_mode=parse_mode
                    )
                else:
                    self.logger.error(f"Unsupported media type: {media_type}")
                    return None
        
        except Exception as e:
            self.logger.error(f"Failed to send message to channel {target_channel_id}: {e}")
            return None


    # Command handlers
    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /start command."""
        await update.message.reply_text(
            "🤖 <b>Grandmaster Bot</b>\n\n"
            "I am your server management assistant. Use /help to see available commands.",
            parse_mode="HTML"
        )
    

    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /help command."""
        help_text = (
            "🤖 <b>Grandmaster Bot Commands</b>\n\n"
            "/status - Show system status\n"
            "/apps - List registered applications\n"
            "/start_app <name> - Start an application\n"
            "/stop_app <name> - Stop an application\n"
            "/restart_app <name> - Restart an application\n"
            "/schedule_app <name> <cron_expression> - Schedule an app (e.g. */10 * * * * for every 10 min)\n"
            "/remove_schedule <name> - Remove schedule from an app\n"
            "/exec <command> - Execute a shell command\n"
            "/help - Show this help message"
        )
        await update.message.reply_text(help_text, parse_mode="HTML")


    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handler for non-command text messages.
        
        Args:
            update: Update object containing message information
            context: Context for this update
        """
        try:
            message = update.message
            user = message.from_user
            chat_id = message.chat_id
            text = message.text
            
            self.logger.info(f"Received message from {user.username or user.first_name} (ID: {user.id}): {text}")

            await message.reply_text("I don't understand this command. Use /help to see available commands.")
            
        except Exception as e:
            self.logger.error(f"Error in message handler: {str(e)}")

    async def _error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Global error handler for the bot.
        
        Args:
            update: Update object that caused the error
            context: Context containing error information
        """
        # Log the error
        self.logger.error(f"Exception while handling an update: {context.error}")
        
        # Extract error details
        error_traceback = "".join(
            traceback.format_exception(
                None, context.error, context.error.__traceback__
            )
        )
        
        # Log detailed error traceback
        self.logger.error(f"Traceback: {error_traceback}")