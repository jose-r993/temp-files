#!/usr/bin/env python3
# server.py - chat server for CS/CE 4390
# run it: python3 server.py <port>
#
# one select() loop watches every socket at once so I never get stuck waiting on one person.
# every connection gets a goob number in the log (goob 1, goob 2, ...) so I can tell who's who

import select
import socket
import sys

# error codes from the table in the spec
ERR_USERNAME_TAKEN = 0
ERR_INVALID_USERNAME = 1
ERR_UNKNOWN_USER = 2
ERR_INVALID_MESSAGE = 3

clients = {}     # socket -> {"goob": number, "name": username or None, "buf": bytes that aren't a full line yet}
users = {}       # username -> socket. dicts keep the order things got added, so this is also the join order for ACK
goob_count = 0


def who(sock):
    # "goob 3" or "goob 3 (alice)" for the log
    c = clients[sock]
    if c["name"]:
        return f"goob {c['goob']} ({c['name']})"
    return f"goob {c['goob']}"


def send(sock, line):
    # every protocol message ends in \n. if they're already gone just ignore it,
    # select will tell me they left and I clean them up there
    try:
        sock.sendall((line + "\n").encode())
    except OSError:
        pass


def err(sock, code):
    print(f"{who(sock)} <- ERR {code}")
    send(sock, f"ERR {code}")


def ack(sock):
    # ACK <#users> <userlist>
    send(sock, "ACK " + " ".join([str(len(users))] + list(users)))


def broadcast(line, skip=None):
    # send to every registered user except `skip`
    for sock in list(users.values()):
        if sock is not skip:
            send(sock, line)


def handle_line(sock, line):
    c = clients[sock]
    msg_type, _, rest = line.partition(" ")   # "PMSG bob hey" -> "PMSG", "bob hey"

    if msg_type == "REG":
        if c["name"]:
            err(sock, ERR_INVALID_MESSAGE)    # already registered, nice try. name stays the same
        elif len(rest) < 1 or len(rest) > 32 or " " in rest:
            err(sock, ERR_INVALID_USERNAME)   # spec: 1-32 chars, no spaces
        elif rest in users:
            err(sock, ERR_USERNAME_TAKEN)
        else:
            c["name"] = rest
            users[rest] = sock
            print(f"goob {c['goob']} registered as {rest}")
            ack(sock)                                                     # ACK them first
            broadcast(f"MSG SERVER {rest} has joined the chat", skip=sock)  # then tell everyone else

    elif msg_type == "MESG":
        if not c["name"] or not rest or len(rest) > 512:
            err(sock, ERR_INVALID_MESSAGE)    # not registered, empty, or too much yap
        else:
            print(f"{who(sock)} -> everyone: {rest}")
            broadcast(f"MSG {c['name']} {rest}", skip=sock)

    elif msg_type == "PMSG":
        target, _, text = rest.partition(" ")
        if not c["name"] or not target or not text or len(text) > 512:
            err(sock, ERR_INVALID_MESSAGE)
        elif target not in users:
            err(sock, ERR_UNKNOWN_USER)       # talking to ghosts
        else:
            print(f"{who(sock)} -> {target}: {text}")
            send(users[target], f"MSG {c['name']} {text}")

    elif msg_type == "EXIT":
        if not c["name"] or rest:
            err(sock, ERR_INVALID_MESSAGE)    # never registered (connection stays open), or junk after EXIT
        else:
            name = c["name"]
            del users[name]                   # off the list first
            c["name"] = None
            print(f"goob {c['goob']} ({name}) sent EXIT")
            ack(sock)                         # ACK with the updated list
            broadcast(f"MSG SERVER {name} has left the chat")
            # the client closes the connection after it gets the ACK

    else:
        err(sock, ERR_INVALID_MESSAGE)        # not a real message type


def drop(sock):
    # they disconnected. if they never sent EXIT I have to do the leave message for them
    c = clients.pop(sock)
    sock.close()
    if c["name"]:
        del users[c["name"]]
        print(f"goob {c['goob']} ({c['name']}) dipped without EXIT")
        broadcast(f"MSG SERVER {c['name']} has left the chat")
    else:
        print(f"goob {c['goob']} disconnected")


def main():
    global goob_count

    if len(sys.argv) != 2:
        print("usage: python3 server.py <port>")
        sys.exit(1)
    port = int(sys.argv[1])

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # lets me restart on the same port right away
    listener.bind(("", port))
    listener.listen(5)
    print(f"server listening on {socket.gethostname()} port {port}")

    while True:
        readable, _, _ = select.select([listener] + list(clients), [], [])

        for sock in readable:
            if sock is listener:
                # new goob
                new_sock, addr = listener.accept()
                goob_count += 1
                clients[new_sock] = {"goob": goob_count, "name": None, "buf": b""}
                print(f"goob {goob_count} connected from {addr[0]}")
                continue

            try:
                data = sock.recv(4096)
            except OSError:
                data = b""
            if not data:
                drop(sock)   # empty recv = they closed (EXIT then hang up, ctrl-c, crash, whatever)
                continue

            # TCP doesn't care about my message boundaries, so stash bytes and only
            # handle a message once its \n shows up. one recv could be half a message or 3 of them
            c = clients[sock]
            c["buf"] += data
            while b"\n" in c["buf"]:
                line, c["buf"] = c["buf"].split(b"\n", 1)
                handle_line(sock, line.decode(errors="replace").rstrip("\r"))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("server shutting down")
