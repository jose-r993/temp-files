CS/CE 4390 - Chat Client and Server (Python 3)

FILES
  server.py   chat server
  client.py   chat client

HOW TO RUN (on one of the csa-net01 to csa-net45 machines)
  Nothing to compile, it's Python 3.

  1. Start the server and give it a port:
       python3 server.py 47213

  2. In another terminal, start a client:
       python3 client.py
     It asks for the server hostname or IP (localhost if you're on the same
     machine as the server, otherwise something like csa-net02.utdallas.edu),
     the port, and a username.

  3. Start more clients the same way to chat.

COMMANDS (after you register)
  MESG <message>          send a message to everyone
  PMSG <user> <message>   send a private message to one user
  LIST                    show who's in the chat
  EXIT                    leave the chat

The client prints whatever the server sends (ACK, MSG, ERR). Errors also get a
short explanation.

ERROR CODES (from the table in the assignment)
  0  username taken
  1  invalid username
  2  unknown user for private message
  3  invalid or unexpected message

NOTES
  - There's no list command in the protocol, so the client keeps its own user
    list from the ACK it gets when it registers and the SERVER join/leave
    messages after that.
  - The server log calls each connection goob 1, goob 2, etc.
  - Ctrl-C on a client quits without sending EXIT. The server notices and
    tells everyone else that user left.
