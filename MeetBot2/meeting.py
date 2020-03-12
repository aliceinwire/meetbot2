import os
import re
import stat
import textwrap
import time

from . import items
from . import writers


class Config(object):
    # Where to store the meeting logs
    logFileDir = '.'
    # The links to the logfiles are given this prefix
    # Example:   logUrlPrefix = 'http://rkd.zgib.net/meetbot/'
    # I feel like we should write the logs to a public html dir, not keep them locally
    # or setup a rsync or something
    logUrlPrefix = ''
    # Give the pattern to save files into here.  Use %(channel)s for
    # channel.  This will be sent through strftime for substituting it
    # times, howover, for strftime codes you must use doubled percent
    # signs (%%).  This will be joined with the directories above.
    filenamePattern = '%(channel)s/%%Y/%(channel)s.%%F-%%H.%%M'
    # Where to say to go for more information about MeetBot
    MeetBotInfoURL = 'https://github.com/dwt2/meetbot2'
    # This is used with the #restrict command to remove permissions from files.
    RestrictPerm = stat.S_IRWXO|stat.S_IRWXG  # g,o perm zeroed
    # RestrictPerm = stat.S_IRWXU|stat.S_IRWXO|stat.S_IRWXG  #u,g,o perm zeroed
    # used to detect #link :
    UrlProtocols = ('http:', 'https:', 'irc:', 'ftp:', 'mailto:', 'ssh:')
    # regular expression for parsing commands.  First group is the cmd name,
    # second group is the rest of the line.
    command_RE = re.compile(r'#([\w]+)[ \t]*(.*)')
    # Regular expression for parsing the startvote command.
    startvote_RE = re.compile(r'(?P<question>.*)\?\s*(?P<choices>.*)')
    # Regular expression for parsing the startvote options.
    choicesSplit_RE = re.compile(r'[^\w+-]+')
    # default voting options if none are given by the user
    defaultVoteOptions = ['Yes', 'No']
    # The channels which won't have date/time appended to the filename.
    specialChannels = ("#meetbot-test", "#meetbot-test2")
    specialChannelFilenamePattern = '%(channel)s/%(channel)s'
    # HTML irc log highlighting style.  `pygmentize -L styles` to list.
    pygmentizeStyle = 'friendly'
    # Timezone setting.  You can use friendly names like 'US/Eastern', etc.
    # Check /usr/share/zoneinfo/ .  Or `man timezone`: this is the contents
    # of the TZ environment variable.
    timeZone = 'UTC'
    # These are the start and end meeting messages, respectively.
    # Some replacements are done before they are used, using the
    # %(name)s syntax.  Note that since one replacement is done below,
    # you have to use doubled percent signs.  Also, it gets split by
    # '\n' and each part between newlines get said in a separate IRC
    # message.
    startMeetingMessage = ("Meeting started %(start_time)s %(timeZone)s "
                           "and is due to finish in %(length)d minutes.  "
                           "The chair is %(chair)s. Information about MeetBot at "
                           "%(MeetBotInfoURL)s.\n"
                           "Useful Commands: #action #agreed #help #info #idea #link "
                           "#topic #startvote.")
    endMeetingMessage = ("Meeting ended %(endtime)s %(timeZone)s.  "
                         "Information about MeetBot at %(MeetBotInfoURL)s . "
                         "(v %(__version__)s)\n"
                         "Minutes:        %(urlBasename)s.html\n"
                         "Minutes (text): %(urlBasename)s.txt\n"
                         "Log:            %(urlBasename)s.log.html")

    # Write out select logfiles
    update_realtime = True
    # CSS configs:
    cssFile_log      = 'default'
    cssEmbed_log     = True
    cssFile_minutes  = 'default'
    cssEmbed_minutes = True

    # This tells which writers write out which to extensions.
    writer_map = {
        '.log.html':writers.HTMLlog,
        '.html': writers.HTML2,
        '.txt': writers.Text,
        }

    def __init__(self,
                 M,
                 write_raw_log=False,
                 safeMode=False,
                 extraConfig={}):
        self.M = M
        self.writers = { }
        # Update config values with anything we may have
        for k,v in list(extraConfig.items()):
            setattr(self, k, v)

        if hasattr(self, "init_hook"):
            self.init_hook()
        if write_raw_log:
            self.writers['.log.txt'] = writers.TextLog(self.M)
        for extension, writer in list(self.writer_map.items()):
            self.writers[extension] = writer(self.M)
        self.safeMode = safeMode

    def filename(self, url=False):
        # provide a way to override the filename.  If it is
        # overridden, it must be a full path (and the URL-part may not
        # work.):
        if getattr(self.M, '_filename', None):
            return self.M._filename
        # names useful for pathname formatting.
        # Certain test channels always get the same name - don't need
        # file prolifiration for them
        if self.M.channel in self.specialChannels:
            pattern = self.specialChannelFilenamePattern
        else:
            pattern = self.filenamePattern
        channel = self.M.channel.strip('# ').lower().replace('/', '')
        network = self.M.network.strip(' ').lower().replace('/', '')
        if self.M._meetingname:
            meetingname = self.M._meetingname.replace('/', '')
        else:
            meetingname = channel
        path = pattern%{'channel':channel, 'network':network,
                        'meetingname':meetingname}
        path = time.strftime(path, self.M.start_time)
        # If we want the URL name, append URL prefix and return
        if url:
            return os.path.join(self.logUrlPrefix, path)
        path = os.path.join(self.logFileDir, path)
        # make directory if it doesn't exist...
        dirname = os.path.dirname(path)
        if not url and dirname and not os.access(dirname, os.F_OK):
            os.makedirs(dirname)
        return path

    @property
    def basename(self):
        return os.path.basename(self.M.config.filename())

    def save(self, realtime_update=False):
        """Write all output files.

        If `realtime_update` is true, then this isn't a complete save,
        it will only update those writers with the update_realtime
        attribute true.  (default update_realtime=False for this method)"""
        if realtime_update and not hasattr(self.M, 'start_time'):
            return
        rawname = self.filename()
        # We want to write the rawlog (.log.txt) first in case the
        # other methods break.  That way, we have saved enough to
        # replay.
        writer_names = list(self.writers.keys())
        results = { }
        if '.log.txt' in writer_names:
            writer_names.remove('.log.txt')
            writer_names = ['.log.txt'] + writer_names
        for extension in writer_names:
            writer = self.writers[extension]
            # Why this?  If this is a realtime (step-by-step) update,
            # then we only want to update those writers which say they
            # should be updated step-by-step.
            if (realtime_update and
                ( not getattr(writer, 'update_realtime', False) or
                  getattr(self, '_filename', None) )
                ):
                continue
            # Parse embedded arguments
            if '|' in extension:
                extension, args = extension.split('|', 1)
                args = args.split('|')
                args = dict([a.split('=', 1) for a in args] )
            else:
                args = { }

            text = writer.format(extension, **args)
            results[extension] = text
            # If the writer returns a string or unicode object, then
            # we should write it to a filename with that extension.
            # If it doesn't, then it's assumed that the write took
            # care of writing (or publishing or emailing or wikifying)
            # it itself.
            if isinstance(text, str):
                text = self.enc(text)
            if isinstance(text, str):
                # Have a way to override saving, so no disk files are written.
                if getattr(self, "dontSave", False):
                    pass
                # ".none" or a single "." disable writing.
                elif extension.lower()[:5] in (".none", "."):
                    pass
                else:
                    filename = rawname + extension
                    self.writeToFile(text, filename)
        if hasattr(self, 'save_hook'):
            self.save_hook(realtime_update=realtime_update)
        return results

    def writeToFile(self, string, filename):
        """Write a given string to a file"""
        # The reason we have this method just for this is to proxy
        # through the _restrictPermissions logic.
        f = open(filename, 'w')
        if self.M._restrictlogs:
            self.restrictPermissions(f)
        f.write(string)
        f.close()

    def restrictPermissions(self, f):
        """Remove the permissions given in the variable RestrictPerm."""
        f.flush()
        newmode = os.stat(f.name).st_mode & (~self.RestrictPerm)
        os.chmod(f.name, newmode)

    def findFile(self, fname):
        """Find template files by searching paths.

        Expand '+' prefix to the base data directory.
        """
        # If `template` begins in '+', then it in relative to the
        # MeetBot source directory.
        if fname[0] == '+':
            basedir = os.path.dirname(__file__)
            fname = os.path.join(basedir, fname[1:])
        # If we don't test here, it might fail in the try: block
        # below, then f.close() will fail and mask the original
        # exception
        if not os.access(fname, os.F_OK):
            raise IOError('File not found: %s'%fname)
        return fname


class MeetingCommands(object):

    def __init__(self):
        self.current_topic = ''
        self.meeting_topic = ''
        self.start_time = ''
        self.expected_end = time.mktime(time_) + self.length * 60

    def do_start_meeting(self, nick, time_, line, **kwargs):
        """Begin a meeting."""
        repl = self.replacements()
        message = self.config.startMeetingMessage%repl
        for messageline in message.split('\n'):
            self.reply(messageline)
        if line.strip():
            self.set_meeting_topic(nick=nick, line=line, time_=time_, **kwargs)
            self.do_meetingname(nick=nick, line=line, time_=time_, **kwargs)

    def do_end_meeting(self, nick, time_, **kwargs):
        """End the meeting."""
        # Chairs can end the meeting early - anyone can end it after the meeting length
        if (not self.isChair(nick)) and (self.expected_end > time.mktime(time_)): return
        if self.old_topic:
            self.topic(self.old_topic)
        self.endtime = time_
        self.config.save()
        repl = self.replacements()
        message = self.config.endMeetingMessage%repl
        for messageline in message.split('\n'):
            self.reply(messageline)
        self.meeting_is_over = True

    def do_set_channel_topic(self, nick, line, **kwargs):
        """Set a new topic in the channel."""
        if not self.isChair(nick):
            return

        self.current_topic = line
        m = items.Topic(nick=nick, line=line, **kwargs)
        self.add_to_minutes(m)
        self.settopic()

    def do_set_meeting_topic(self, nick, line, **kwargs):
        """Set a meeting topic (included in all sub-topics)"""
        if not self.isChair(nick): return
        line = line.strip()
        if line == '' or line.lower() == 'none' or line.lower() == 'unset':
            self.meeting_topic = None
        else:
            self.meeting_topic = line
        self.settopic()

    def do_save(self, nick, time_, **kwargs):
        """Save the config???"""
        if not self.isChair(nick):
            return
        self.end_time = time.localtime()
        self.config.save()

    def do_agreed(self, nick, **kwargs):
        """Add agreement to the minutes - chairs only."""
        if not self.isChair(nick): return
        m = items.Agreed(nick, **kwargs)
        self.add_to_minutes(m)
    do_agree = do_agreed

    def do_accepted(self, nick, **kwargs):
        """Add agreement to the minutes - chairs only."""
        if not self.isChair(nick): return
        m = items.Accepted(nick, **kwargs)
        self.add_to_minutes(m)
    do_accept = do_accepted

    def do_rejected(self, nick, **kwargs):
        """Add agreement to the minutes - chairs only."""
        if not self.isChair(nick): return
        m = items.Rejected(nick, **kwargs)
        self.add_to_minutes(m)
    do_reject = do_rejected

    def do_chair(self, nick, line, **kwargs):
        """Add a chair to the meeting."""
        if not self.isChair(nick): return
        for chair in re.split('[, ]+', line.strip()):
            chair = chair.strip()
            if not chair: continue
            if chair not in self.chairs:
                if self._channelNicks is not None and \
                       ( chair.encode(self.config.input_codec)
                         not in self._channelNicks()):
                    self.reply("Warning: Nick not in channel: %s"%chair)
                self.addnick(chair, lines=0)
                self.chairs.setdefault(chair, True)
        chairs = dict(self.chairs) # make a copy
        chairs.setdefault(self.owner, True)
        self.reply("Current chairs: %s"%(" ".join(sorted(chairs.keys()))))

    def do_unchair(self, nick, line, **kwargs):
        """Remove a chair to the meeting (founder can not be removed)."""
        if not self.isChair(nick): return
        for chair in line.strip().split():
            chair = chair.strip()
            if chair in self.chairs:
                del self.chairs[chair]
        chairs = dict(self.chairs) # make a copy
        chairs.setdefault(self.owner, True)
        self.reply("Current chairs: %s"%(" ".join(sorted(chairs.keys()))))

    def do_undo(self, nick, **kwargs):
        """Remove the last item from the minutes."""
        if not self.isChair(nick): return
        if len(self.minutes) == 0: return
        self.reply("Removing item from minutes: %s"%str(self.minutes[-1]))
        del self.minutes[-1]

    def do_restrict_logs(self, nick, **kwargs):
        """When saved, remove permissions from the files."""
        if not self.isChair(nick): return
        self.restrict_logs = True
        self.reply("Restricting permissions on minutes: -%s on next #save"%\
                   oct(RestrictPerm))

    def do_lurk(self, nick, **kwargs):
        """Don't interact in the channel."""
        if not self.isChair(nick): return
        self._lurk = True

    def do_unlurk(self, nick, **kwargs):
        """Do interact in the channel."""
        if not self.isChair(nick): return
        self._lurk = False

    def do_meetingname(self, nick, time_, line, **kwargs):
        """Set the variable (meetingname) which can be used in save.

        If this isn't set, it defaults to the channel name."""
        meetingname = "_".join(line.strip().lower().split())
        meetingname = re.sub(r'[^a-z0-9]', '_', meetingname)
        self._meetingname = meetingname
        self.reply("The meeting name has been set to '%s'"%meetingname)

    # Commands for Anyone:
    def do_action(self, **kwargs):
        """Add action item to the minutes.

        The line is searched for nicks, and a per-person action item
        list is compiled after the meeting.  Only nicks which have
        been seen during the meeting will have an action item list
        made for them, but you can use the #nick command to cause a
        nick to be seen."""
        m = items.Action(**kwargs)
        self.add_to_minutes(m)

    def do_info(self, **kwargs):
        """Add informational item to the minutes."""
        m = items.Info(**kwargs)
        self.add_to_minutes(m)

    def do_idea(self, **kwargs):
        """Add informational item to the minutes."""
        m = items.Idea(**kwargs)
        self.add_to_minutes(m)

    def do_help(self, **kwargs):
        """Add call for help to the minutes."""
        m = items.Help(**kwargs)
        self.add_to_minutes(m)
    do_halp = do_help

    def do_nick(self, nick, line, **kwargs):
        """Make meetbot aware of a nick which hasn't said anything.

        To see where this can be used, see #action command"""
        nicks = re.split('[, ]+', line.strip())
        for nick in nicks:
            nick = nick.strip()
            if not nick: continue
            self.addnick(nick, lines=0)

    def do_link(self, **kwargs):
        """Add informational item to the minutes."""
        m = items.Link(M=self, **kwargs)
        self.add_to_minutes(m)

    def do_start_vote(self, nick, line, **kwargs):
        """Begin voting on a topic.

        Format of command is #startvote $TOPIC $Options.
        eg #startvote What color should we use? blue, red, green"""
        
        vote_details = self.config.startvote_RE.match(line)
        if not self.isChair(nick):
            self.reply("Only the meeting chair may start a vote.")
            return
        elif self.vote_topic is not None:
            self.reply("Already voting on '%s'" % self.vote_topic)
            return
        elif vote_details is None:
            self.reply("Unable to parse vote topic and options.")
            return
        self.vote_topic = vote_details.group("question")
        voteOptions = vote_details.group("choices")
        if voteOptions == "":
            self._voteOptions = self.config.defaultVoteOptions
        else:
            self._voteOptions = self.config.choicesSplit_RE.split(voteOptions)
        self.reply("Begin voting on: %s? Valid vote options are %s." % \
            (self.vote_topic, ", ".join(self._voteOptions)))
        self.reply("Vote using '#vote OPTION'. Only your last vote counts.")

    def do_endvote(self, nick, line, **kwargs):
        """End voting on topic."""
        if not self.isChair(nick) or self.vote_topic is None: return
        m = 'Voted on "%s?" Results are' % self.vote_topic
        self.reply(m)
        self.do_showvote(**kwargs)
        for k,s in list(self._votes.items()):
            vote = self._voteOptions[list(map(str.lower,
                                        self._voteOptions)).index(k)]
            m += ", %s: %s" % (vote, len(s))
        m = items.Vote(nick=nick, line=m, **kwargs)
        self.add_to_minutes(m)
        self.vote_topic = None
        self._voteOptions = None
        self._votes = { }
        self._voters = { }

    def do_vote(self, nick, line, **kwargs):
        """Vote for specific voting topic option."""
        if self.vote_topic is None: return
        vote = line.lower()
        if vote in list(map(str.lower, self._voteOptions)):
            oldvote = self._voters.get(nick)
            if oldvote is not None:
                self._votes[oldvote].remove(nick)
            self._voters[nick] = vote
            v = self._votes.get(vote, set())
            v.add(nick)
            self._votes[vote] = v
        else:
            m = "%s: %s is not a valid option. Valid options are %s." % \
                (nick, line, ", ".join(self._voteOptions))
            self.reply(m)

    def do_showvote(self, **kwargs):
        """Show intermediate vote results."""
        if self.vote_topic is None: return
        for k, s in list(self._votes.items()):
            # Attempt to print all the names while obeying the 512 character
            # limit. Would probably be better to calculate message overhead and
            # determine wraps()s width argument based on that.
            ms = textwrap.wrap(", ".join(s), 400)
            vote = self._voteOptions[list(map(str.lower,
                                        self._voteOptions)).index(k)]
            for m2 in ms:
                m1 = "%s (%s): " % (vote, len(s))
                self.reply(m1 + m2)

    def do_commands(self, **kwargs):
        commands = [ "#"+x[3:] for x in dir(self) if x[:3]=="do_" ]
        commands.sort()
        self.reply("Available commands: "+(" ".join(commands)))


class Meeting(MeetingCommands, object):
    _lurk = False
    restrict_logs = False

    def __init__(self, channel, owner,
                 old_topic=None,
                 filename=None,
                 write_raw_log=False,
                 setTopic=None,
                 sendReply=None,
                 getRegistryValue=None,
                 safeMode=False,
                 channelNicks=None,
                 extraConfig={},
                 network='nonetwork',
                 length=60):

        if getRegistryValue is not None:
            self._registryValue = getRegistryValue
        if sendReply is not None:
            self._sendReply = sendReply
        if setTopic is not None:
            self._setTopic = setTopic

        self.owner = owner
        self.channel = channel
        self.network = network
        self.length = length
        self.current_topic = ""
        self.config = Config(self, write_raw_log=write_raw_log, safeMode=safeMode,
                            extraConfig=extraConfig)
        if old_topic:
            self.old_topic = old_topic
        else:
            self.old_topic = None
        self.lines = [ ]
        self.minutes = [ ]
        self.attendees = { }
        self.chairs = { }
        self._write_raw_log = write_raw_log
        self.meeting_topic = None
        self._meetingname = ""
        self.meeting_is_over = False
        self._channelNicks = channelNicks
        self.vote_topic = None
        self._votes = { }
        self._voters = { }
        if filename:
            self._filename = filename

    # These commands are callbacks to manipulate the IRC protocol.
    # set self._sendReply and self._setTopic to an callback to do these things.
    def reply(self, x):
        """Send a reply to the IRC channel."""
        if hasattr(self, '_sendReply') and not self._lurk:
            self._sendReply(self.config.enc(x))
        else:
            print(("REPLY:", self.config.enc(x)))

    def topic(self, x):
        """Set the topic in the IRC channel."""
        if hasattr(self, '_setTopic') and not self._lurk:
            self._setTopic(self.config.enc(x))
        else:
            print(("TOPIC:", self.config.enc(x)))

    def settopic(self):
        "The actual code to set the topic"
        if self.meeting_topic:
            topic = '%s (Meeting topic: %s)'%(self.current_topic,
                                              self.meeting_topic)
        else:
            topic = self.current_topic
        self.topic(topic)

    def addnick(self, nick, lines=1):
        """This person has spoken, lines=<how many lines>"""
        self.attendees[nick] = self.attendees.get(nick, 0) + lines

    def isChair(self, nick):
        """Is the nick a chair?"""
        return (nick == self.owner  or  nick in self.chairs)

    def save(self, **kwargs):
        return self.config.save(**kwargs)

    # Primary entry point for new lines in the log:
    def add_line(self, nick, line, time_=None):
        """This is the way to add lines to the Meeting object."""
        linenum = self.addrawline(nick, line, time_)

        if time_ is None:
            time_ = time.localtime()

        # Handle any commands given in the line.
        matches = self.config.command_RE.match(line)
        if matches is not None:
            command, line = matches.groups()
            command = command.lower()
            # to define new commands, define a method do_commandname .
            if hasattr(self, "do_"+command):
                getattr(self, "do_"+command)(nick=nick, line=line,
                                             linenum=linenum, time_=time_)
        else:
            # Detect URLs automatically
            if line.split('//')[0] in self.config.UrlProtocols:
                self.do_link(nick=nick, line=line,
                             linenum=linenum, time_=time_)
        self.save(realtime_update=True)

    def addrawline(self, nick, line, time_=None):
        """This adds a line to the log, bypassing command execution.
        """
        # nick = self.config.dec(nick)
        # line = self.config.dec(line)
        self.addnick(nick)
        line = line.strip(' \x01') # \x01 is present in ACTIONs
        # Setting a custom time is useful when replying logs,
        # otherwise use our current time:
        if time_ is None: time_ = time.localtime()

        # Handle the logging of the line
        if line[:6] == 'ACTION':
            logline = "%s * %s %s"%(time.strftime("%H:%M:%S", time_),
                                 nick, line[7:].strip())
        else:
            logline = "%s <%s> %s"%(time.strftime("%H:%M:%S", time_),
                                 nick, line.strip())
        self.lines.append(logline)
        linenum = len(self.lines)
        return linenum

    def add_to_minutes(self, m):
        """Add an item to the meeting minutes list.
        """
        self.minutes.append(m)
        
    def replacements(self):
        repl = { }
        repl['channel'] = self.channel
        repl['network'] = self.network
        repl['MeetBotInfoURL'] = self.config.MeetBotInfoURL
        repl['timeZone'] = self.config.timeZone
        repl['start_time'] = repl['endtime'] = "None"
        if getattr(self, "start_time", None) is not None:
            repl['start_time'] = time.asctime(self.start_time)
        if getattr(self, "endtime", None) is not None:
            repl['endtime'] = time.asctime(self.endtime)
        repl['length'] = self.length
        repl['__version__'] = __version__
        repl['chair'] = self.owner
        repl['urlBasename'] = self.config.filename(url=True)
        repl['basename'] = os.path.basename(self.config.filename())
        return repl
