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

    def __init__(self, irc):
        self.__parent = super(MeetBot2, self)
        self.__parent.__init__(irc)

    def doPrivmsg(self, irc, msg):
        nick = msg.nick
        channel = msg.args[0]
        payload = msg.args[1]
        network = irc.msg.tags['receivedOn']

        # get the meeting object if it already exists
        meeting_key = (channel, network)
        unique_meeting = meeting_cache.get(meeting_key, None)

        # if no meeting is happening, quit
        if unique_meeting is None:
            return

        # add line to our meeting buffer?
        unique_meeting.add_line(nick, payload)

        # end the meeting on demand
        if unique_meeting.meeting_is_over:
            unique_meeting.save()
            unique_meeting.do_end_meeting(nick, unique_meeting.endtime)
            del meeting_cache[meeting_key]


    def startmeeting(self, irc, msg, args, channel):
        print('its a new meeting')
        nick = msg.nick
        channel = msg.args[0]
        payload = msg.args[1]
        network = irc.msg.tags['receivedOn']

        # get the meeting object if it already exists
        meeting_key = (channel, network)
        unique_meeting = meeting_cache.get(meeting_key, None)

        # check if the meeting already exists
        if unique_meeting is not None:
            irc.error("This meeting already exists.")
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
            old_topic=irc.state.channels[channel].topic,
            write_raw_log=True,
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
        while len(recent_meetings) > 9:
            del recent_meetings[0]

        # now add the new meeting to the list
        recent_meetings.append((channel, network, time.ctime()))

        # notify the channel that the meeting started
        irc.reply("Meeting {} started at {}".format(meeting_name, time.localtime()))
    startmeeting = wrap(startmeeting, [('checkCapability', 'admin'), 'something', 'something'])



    def deletemeeting(self, irc, msg, args, channel, network, save):
        """<channel> <network> <save>

        Delete a meeting from the cache. Save is a bool and defaults to True.
        Example: deletemeeting #mychannel freenode False
        """
        meeting_key = (channel, network)
        if meeting_key not in meeting_cache:
            irc.reply("Meeting for {} channel {} is not found".format(network, channel))
            return
        if save:
            unique_meeting = meeting_cache.get(meeting_key, None)
            unique_meeting.endtime = time.localtime()
            unique_meeting.config.save()
        del meeting_cache[meeting_key]
        irc.reply("Deleted meeting on {} {}".format(network, channel))
    deletemeeting = wrap(deletemeeting, ['admin', "channel", "something", optional("boolean", True)])

    def endmeeting(self, irc, msg, args, channel, network):
        """<channel> <network>

        End a meeting. Example: endmeeting #mychannel freenode
        """
        meeting_key = (channel, network)
        if meeting_key not in meeting_cache:
            irc.reply("Meeting for {} channel {} is not found".format(network, channel))
            return

        unique_meeting = meeting_cache.get(meeting_key, None)
        if not unique_meeting.isChair(msg.nick):
            return

        unique_meeting.endtime = time.localtime()
        unique_meeting.config.save()
        del meeting_cache[meeting_key]
        irc.reply("Ended meeting at {}".format(unique_meeting.endtime))
    endmeeting = wrap(endmeeting, [('checkCapability', 'admin'), "something", "something"])


    def listmeetings(self, irc, msg, args):
        """List all active meetings."""
        reply = ""
        reply = ", ".join(str(x) for x in sorted(meeting_cache.keys()))
        if reply.strip() == '':
            irc.reply("No currently active meetings.")
        else:
            irc.reply(reply)
    listmeetings = wrap(listmeetings, ['admin'])

    def outFilter(self, irc, msg):
        """Log outgoing messages from supybot.
        """
        try:
            if msg.command in ('PRIVMSG'):
                nick = irc.nick
                channel = msg.args[0]
                payload = msg.args[1]
                meeting_key = (channel, irc.network)
                unique_meeting = meeting_cache.get(meeting_key, None)
                if unique_meeting is not None:
                    unique_meeting.addrawline(nick, payload)
        except Exception as e:
            print(type(e))
            print(e.args)
            print(e)
        return msg


Class = MeetBot2
