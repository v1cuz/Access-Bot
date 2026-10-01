import re
import sqlite3

from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    ContextTypes,
    filters,
)


DB_NAME = "media.db"


# =========================
# Database
# =========================

def init_database():
    connection = sqlite3.connect(DB_NAME)

    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS media (
            chat_id INTEGER NOT NULL,
            message_id INTEGER NOT NULL,
            file_id TEXT NOT NULL,
            media_type TEXT NOT NULL,
            PRIMARY KEY (chat_id, message_id)
        )
    """)

    connection.commit()
    connection.close()


def save_media(chat_id, message_id, file_id, media_type):
    connection = sqlite3.connect(DB_NAME)

    cursor = connection.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO media
        (chat_id, message_id, file_id, media_type)
        VALUES (?, ?, ?, ?)
    """, (
        chat_id,
        message_id,
        file_id,
        media_type
    ))

    connection.commit()
    connection.close()


def get_media(chat_id, message_id):
    connection = sqlite3.connect(DB_NAME)

    cursor = connection.cursor()

    cursor.execute("""
        SELECT file_id, media_type
        FROM media
        WHERE chat_id = ? AND message_id = ?
    """, (
        chat_id,
        message_id
    ))

    result = cursor.fetchone()

    connection.close()

    return result

def delete_media(chat_id, message_id):
    connection = sqlite3.connect(DB_NAME)

    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM media
        WHERE chat_id = ? AND message_id = ?
    """, (
        chat_id,
        message_id
    ))

    deleted = cursor.rowcount

    connection.commit()
    connection.close()

    return deleted > 0

# =========================
# Message link parser
# =========================

def extract_message_link(text):

    pattern = r"https?://t\.me/c/(\d+)/(\d+)"

    match = re.search(pattern, text)

    if not match:
        return None

    chat_id = int("-100" + match.group(1))
    message_id = int(match.group(2))

    return chat_id, message_id


# =========================
# Message handler
# =========================

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = update.effective_message

    if not message:
        return


    # =========================
    # /allow
    # =========================

    if message.text and message.text.strip() == "/allow":

        # Check whether the user is an administrator
        member = await context.bot.get_chat_member(
            chat_id=message.chat_id,
            user_id=message.from_user.id
        )

        if member.status not in ("administrator", "creator"):
            await message.reply_text(
                "❌ Only group administrators can use /allow."
            )
            return

        replied_message = message.reply_to_message

        if not replied_message:

            await message.reply_text(
                "❌ Reply to a media message with /allow"
            )

            return


        # Detect media type

        if replied_message.video:

            file_id = replied_message.video.file_id
            media_type = "video"

        elif replied_message.photo:

            file_id = replied_message.photo[-1].file_id
            media_type = "photo"

        elif replied_message.document:

            file_id = replied_message.document.file_id
            media_type = "document"

        else:

            await message.reply_text(
                "❌ Unsupported media type."
            )

            return


        # Save permanently

        save_media(
            replied_message.chat_id,
            replied_message.message_id,
            file_id,
            media_type
        )


        await message.reply_text(
            f"✅ Approved!\n\n"
            f"Message ID: {replied_message.message_id}\n"
            f"Type: {media_type}\n"
            f"Saved permanently."
        )


        print(
            f"APPROVED | "
            f"chat_id={replied_message.chat_id} | "
            f"message_id={replied_message.message_id} | "
            f"type={media_type}"
        )

        return


    # =========================
    # Message link
    # =========================

    # =========================
    # /deny
    # =========================

    if message.text and message.text.strip() == "/deny":

        # Check whether the user is an administrator
        member = await context.bot.get_chat_member(
            chat_id=message.chat_id,
            user_id=message.from_user.id
        )

        if member.status not in ("administrator", "creator"):
            await message.reply_text(
                "❌ Only group administrators can use /deny."
            )
            return

        replied_message = message.reply_to_message

        if not replied_message:
            await message.reply_text(
                "❌ Reply to an approved media message with /deny"
            )
            return

        deleted = delete_media(
            replied_message.chat_id,
            replied_message.message_id
        )

        if deleted:
            await message.reply_text(
                "🗑️ Download permission removed."
            )

            print(
                f"DENIED | "
                f"chat_id={replied_message.chat_id} | "
                f"message_id={replied_message.message_id}"
            )

        else:
            await message.reply_text(
                "❌ This media wasn't approved."
            )

        return

    if message.text:

        result = extract_message_link(message.text)

        if result:

            chat_id, message_id = result

            media = get_media(
                chat_id,
                message_id
            )


            if not media:

                await message.reply_text(
                    "❌ This media isn't available for download."
                )

                return


            file_id, media_type = media


            # Send the requested media

            if media_type == "video":

                await context.bot.send_video(
                    chat_id=message.chat_id,
                    video=file_id
                )

            elif media_type == "photo":

                await context.bot.send_photo(
                    chat_id=message.chat_id,
                    photo=file_id
                )

            elif media_type == "document":

                await context.bot.send_document(
                    chat_id=message.chat_id,
                    document=file_id
                )

            return


    # =========================
    # Debug output
    # =========================

    print(
        f"Message received | "
        f"chat_id={message.chat_id} | "
        f"message_id={message.message_id}"
    )


# =========================
# Main
# =========================

def main():

    TOKEN = "8967874655:AAHlna6_b7rlxwZ-xej4rKEc5RKTyHegmFQ"

    init_database()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(
        MessageHandler(
            filters.ALL,
            handle_message
        )
    )

    print("Bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()