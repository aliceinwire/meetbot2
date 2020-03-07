from . import meeting
from supybot import utils, plugins, ircmsgs, ircutils, callbacks
from supybot.commands import *
import time

try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('MeetBot2')
except ImportError:
    _ = lambda x: x

try:
    meeting_cache
except NameError:
    meeting_cache = {}
try:
    recent_meetings
except NameError:
    recent_meetings = []


class MeetBot2(callbacks.Plugin):
    """MeetBot Reborn"""
    threaded = True

    def capture_private_messages(self, irc, msg):
        self.__parent = super(MeetBot2, self)
        self.__parent.__init__(irc)

        nick = msg.nick
        channel = msg.args[0]
        payload = msg.args[1]
        network = irc.msg.tags['receivedOn']

        # get the meeting object if it already exists
        meeting_key = (channel, network)
        unique_meeting = meeting_cache.get(meeting_key, None)

        # start a meeting if that's what the request is
        if payload[13:] == '#startmeeting':

            # check if the meeting already exists
            if unique_meeting is not None:
                irc.error("Cannot start a new meeting while one is already in progress.")
                return

            # if a meeting doesn't exist, check that there is a meeting name set
            meeting_name = payload[13:].strip()
            if not meeting_name:
                irc.error("A meeting name is required to start a meeting.")
                return

            # if we passed our checks, let's set up the meeting
            # This callback is used to send data to the channel

            def _set_topic(x):
                irc.sendMsg(ircmsgs.topic(channel, x))

            def _send_reply(x):
                irc.sendMsg(ircmsgs.privmsg(channel, x))

            def _channel_nicks():
                return irc.state.channels[channel].users

            # create the meeting
            unique_meeting = meeting.Meeting(
                channel=channel,
                owner=nick,
                oldtopic=irc.state.channels[channel].topic,
                writeRawLog=True,
                setTopic=_set_topic,
                sendReply=_send_reply,
                getRegistryValue=self.registryValue,
                safeMode=True,
                channelNicks=_channel_nicks,
                network=network,
                )

            # add the meeting to the meeting list cache
            meeting_cache[meeting_key] = unique_meeting

            # keep the recent meetings list at no more than 10
            if len(recent_meetings) > 10:
                while len(recent_meetings) > 9:
                    del recent_meetings[0]

            # then add the current meeting to the list
            recent_meetings.append((channel, network, time.ctime()))

            # if no meeting is happening, quit
            if unique_meeting is None: return

            # add line to our meeting buffer?
            unique_meeting.addline(nick, payload)

            # end the meeting on demand
            if unique_meeting.meeting_is_over:
                unique_meeting.save()
                del meeting_cache[meeting_key]


Class = MeetBot2
