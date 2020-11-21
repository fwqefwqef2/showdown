import asyncio
import websockets
import requests
import json
import time
import config
import sys
import time

from showdown.engine.evaluate import Scoring
from showdown.battle import Pokemon
from showdown.battle import LastUsedMove
from showdown.battle_modifier import async_update_battle

from threading import Thread
from multiprocessing import Process

import logging
logger = logging.getLogger(__name__)

class LoginError(Exception):
    pass


class SaveReplayError(Exception):
    pass


class PSWebsocketClient:

    websocket = None
    address = None
    login_uri = None
    username = None
    password = None
    last_message = None
    last_challenge_time = 0

    @classmethod
    async def create(cls, username, password, address):
        self = PSWebsocketClient()
        self.username = username
        self.password = password
        self.address = "ws://{}/showdown/websocket".format(address)
        self.websocket = await websockets.connect(self.address)
        self.login_uri = "https://play.pokemonshowdown.com/action.php"
        return self

    async def receive_message(self):
        message = await self.websocket.recv()
        return message

    async def send_message(self, room, message_list):
        message = room + "|" + "|".join(message_list)
        await self.websocket.send(message)
        self.last_message = message

    async def get_id_and_challstr(self):
        while True:
            message = await self.receive_message()
            split_message = message.split('|')
            if split_message[1] == 'challstr':
                return split_message[2], split_message[3]

    async def login(self):
        logger.debug("Logging in...")
        client_id, challstr = await self.get_id_and_challstr()
        if self.password:
            response = requests.post(
                self.login_uri,
                data={
                    'act': 'login',
                    'name': self.username,
                    'pass': self.password,
                    'challstr': "|".join([client_id, challstr])
                }
            )

        else:
            response = requests.post(
                self.login_uri,
                data={
                    'act': 'getassertion',
                    'userid': self.username,
                    'challstr': '|'.join([client_id, challstr]),
                }
            )

        if response.status_code == 200:
            if self.password:
                response_json = json.loads(response.text[1:])
                assertion = response_json.get('assertion')
            else:
                assertion = response.text

            message = ["/trn " + self.username + ",0," + assertion]
            logger.debug("Successfully logged in")
            await self.send_message('', message)
			##keep the room alive
            await self.send_message('', ["/avatar 178"])
            logger.debug("Changed Avatar")
            await self.send_message('', ["/join lobby"]) 
            await self.send_message('lobby', ["/join groupchat-srbot-sinnohremakes"])
            logger.debug("joined srchat")
            await self.send_message('groupchat-srbot-sinnohremakes', ["This message was sent to prevent the chat from dying."])
            await self.send_message('groupchat-srbot-sinnohremakes', ["/hidetext SRbot"])

        else:
            logger.error("Could not log-in\nDetails:\n{}".format(response.content))
            raise LoginError("Could not log-in")

    async def receive_pm(self):
        logger.debug("awating pms")
        loopnum = 0 #for the inactive timer
        while True:
            msg = await self.receive_message()
            #logger.debug(msg)
            split_msg = msg.split('|')
            #logger.debug(split_msg)
			
            if split_msg[1] == 'pm' and split_msg[2] != '!SRbot' and split_msg[2] != ' SRbot':
                await self.send_message("groupchat-srbot-sinnohremakes", ["/invite"+split_msg[2]])
            if split_msg[0] == '>groupchat-srbot-sinnohremakes\n':
                #reset timer
                loopnum = 0	
				
            if split_msg[0] == '>groupchat-srbot-sinnohremakes\n' and split_msg[1] == 'c:' and split_msg[2] != '!SRbot' and split_msg[2] != ' SRbot': #chat msg
                if '-say' in split_msg[4]: #-say /cood
                    #say the thing after -say
                    await self.send_message("groupchat-srbot-sinnohremakes", [split_msg[4][5:len(split_msg[4])]])
					
            loopnum += 1
            logger.debug(str(loopnum))
			
            if loopnum == 2000:
                await self.send_message('groupchat-srbot-sinnohremakes', ["This message was sent to prevent the chat from dying."])
                await self.send_message('groupchat-srbot-sinnohremakes', ["/hidetext SRbot"])
                logger.debug("prevented chat death")
                loopnum = 0
			
    async def accept_challenge(self):
        await self.receive_pm()
