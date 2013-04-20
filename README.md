StatefulIRC
===========
Traditional IRC frameworks provide a single event handler for the various events: join, leave, channel message, and private message. This works great for very simple bots; they are simple processors that do the same thing every time for a given output, assuming the user has appropriate permissions.

IRC Bots that run games are in actuality finite state automata. The output to a particular event depends on a combination of the input, the user, AND the current state. IRC bots built using these frameworks end up putting a giant switch statement with a lot of program logic instead these event handler functions. Your on_private_message handler has ten different switch options and clutters up your program. This solution makes it very troublesome to add a state and very easy to forget one.

The idea between the StatefulIRC framework is to create a framework for Finite State Machine IRC bots. You program it with a number of states; each state implements its own event handlers for all the various actions that you may care about. When the bot receives an event, it passes that event along to the event handler of the active state.

There is also support for a "master state" that will receive every event. This allows you to, for example, accept debugging commands from the bot's owner regardless of state.


The bot is built on top of the IRCUtils framework available at: http://dev.guardedcode.com/projects/ircutils/. It is designed so you need very minimal understanding of that framework to create a bot.
