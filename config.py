from os import getenv
from dotenv import load_dotenv

load_dotenv()

FORUM_API_TOKEN = getenv('FORUM_API_TOKEN')
XF_TOKEN = getenv('XF_TOKEN')
TOKEN_BOT = getenv('TOKEN_BOT')
ID = int(getenv('USER_ID'))
USER_FORUM_ID = int(getenv('USER_FORUM_ID'))