ABOUT
~~~~~
MeetBot2 work in progress

Inspired by the original MeetBot, by Holger Levsen, which was itself a
derivative of Mootbot (https://wiki.ubuntu.com/ScribesTeam/MootBot),
by the Ubuntu Scribes team.


INSTALLATION
~~~~~~~~~~~~

Requirements
------------
limnoria


Install the MeetBot plugin
--------------------------

* Move the MeetBot2 directory into your ``plugins`` directory of
  Limnoria.

* Use the command ``load MeetBot`` to load the plugin.
  You can check the command ``config plugins`` to check what is
  loaded.


DESIGN DECISIONS
~~~~~~~~~~~~~~~~
The MeetBot plugin doesn't operate like a regular supybot plugin.  It
bypasses the normal command system.  Instead it listens for all lines
(it has to log them all anyway) and if it sees a command, it acts on it.

- Separation of meeting code and plugin code.  This should make it
  easy to port to other bots, and perhaps more importantly make it
  easier to maintain, or rearrange, the structure within supybot.
- MeetBot2 will not bypass the normal Limonia command system.
