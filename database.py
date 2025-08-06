import aiosqlite
from typing import Final
from telebot import types
from datetime import datetime, timezone, timedelta
import pytz



# GLOBAL VARS
DBNAME : Final[str] = "database.db"



# EXPORT FUNCTIONS
async def init_db():
    async with aiosqlite.connect(DBNAME) as database:
        await database.executescript("""
            CREATE TABLE IF NOT EXISTS Users  (
                user_id INTEGER PRIMARY KEY,
                nickname TEXT,
                username TEXT,
                realname TEXT NOT  NULL
            );

            CREATE TABLE IF NOT EXISTS Works (
                work_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message TEXT,
                dt DATETIME,
                FOREIGN KEY (user_id) REFERENCES Users(chat_id) ON DELETE SET NULL
            );
        """)
        await database.commit()



async def is_user_registred(user_id: int) -> bool:
    async with aiosqlite.connect(DBNAME) as database:
        db_coursor = await database.cursor()

        await db_coursor.execute(
            "SELECT 1 FROM Users WHERE user_id = ?",
            (user_id,)
        )
        return not (await db_coursor.fetchone() is None)



async def register_user(user_message: types.Message) -> None:
    async with aiosqlite.connect(DBNAME) as database:
        db_coursor = await database.cursor()

        await db_coursor.execute(
            """INSERT INTO Users (user_id, nickname, username, realname)
                VALUES (?, ?, ?, ?)""",
            (
                user_message.from_user.id,
                user_message.from_user.full_name,
                user_message.from_user.username,
                user_message.text
            )
        )
        
        await database.commit()


async def register_work(user_message: types.Message) -> int:
    async with aiosqlite.connect(DBNAME) as database:
        db_coursor = await database.cursor()

        await db_coursor.execute(
            "INSERT INTO Works (user_id, message, dt) VALUES (?, ?, ?)",
            (
                user_message.from_user.id,
                str(user_message.caption)[:256],
                datetime.now(pytz.timezone("Europe/Moscow"))
            )
        )
        await database.commit()

        data = await db_coursor.execute("SELECT last_insert_rowid()")
        work_id = (await data.fetchone())[0]

        return work_id



async def get_user_works(user_message: types.Message):
    async with aiosqlite.connect(DBNAME) as database:
        db_coursor = await database.cursor()

        await db_coursor.execute(
            "SELECT work_id, strftime('%H:%M %d.%m.%Y', dt), message FROM Works WHERE user_id = ?",
            (user_message.from_user.id,)
        )

        return await db_coursor.fetchall()


async def get_page_data():
    async with aiosqlite.connect(DBNAME) as database:
        db_coursor = await database.cursor()

        await db_coursor.execute(
            """SELECT w.work_id, strftime('%d.%m.%Y %H:%M:%S', w.dt), w.message, u.nickname, u.username, u.realname
                FROM works w LEFT JOIN Users u ON w.user_id = u.user_id
                ORDER BY w.work_id ASC"""
        )

        return await db_coursor.fetchall()
