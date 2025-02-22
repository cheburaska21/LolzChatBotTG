from os import getenv
from dotenv import load_dotenv

load_dotenv()

FORUM_API_TOKEN = getenv('FORUM_API_TOKEN')
TOKEN_BOT = getenv('TOKEN_BOT')
ID = int(getenv('USER_ID'))