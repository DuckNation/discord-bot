from enum import Enum


class ChatEnums(str, Enum):
    JOIN = 'join'
    LEAVE = 'leave'
    CHAT = 'chat'
    UPDATE = 'update'
    DEATH = 'death'
