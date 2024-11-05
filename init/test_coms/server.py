#########################################################################
# CENTRALESUPELEC : ST5 Integration teaching
#
# Communication server
#   This program receives messages from all clients (control and robots).
#   It forwards messages from the control to all robots.
#   Each robot filters out messages that are not meant for it.
#
#########################################################################
# Authors : Philippe Benabes & Koen de Turck
# Modifications by Morgan Roger & Erwan Libessart
# TBD : nodes is not declared as global
# TBD : replace 'key' with 'last_key_hit' ?
#########################################################################

import zmq
import sys

server_ip = "192.168.137.1"
verbose_mode = False
nodes = list()
global key  # last key hit ?
key = ""


def main():
    repsock = create_connection_interface(server_ip)
    while True:
        msg = repsock.recv_pyobj()
        reply = process_msg(msg)
        repsock.send_pyobj(reply)
        if verbose_mode:
            print("received: {}".format(msg))
            print("reply: {}".format(reply))


def process_msg(msg):
    global key
    default_reply = {"all": "is fine"}

    msg_type = {
        "new node registering": ((msg["cmd"] == "log") and msg["from"] not in nodes),
        "known node registering": ((msg["cmd"] == "log") and msg["from"] in nodes),
        "from control": (msg["from"] == "control"),
        "key request from robot": (
            (msg["from"] != "control") and (msg["cmd"] == "key")
        ),
    }

    if msg_type["new node registering"]:
        print("new node signing in, adding {} to nodes".format(msg["from"]))
        nodes.append(msg["from"])
        if verbose_mode:
            print(nodes)
        reply = default_reply

    elif msg_type["known node registering"]:
        print("node {} already known".format(msg["from"]))
        if verbose_mode:
            print(nodes)
        reply = {"already": "registered"}

    elif msg_type["from control"]:
        print("from control")
        if verbose_mode:
            print(msg)
        if msg["cmd"] == "key":
            key = msg["key"]
            print(key)
        reply = default_reply

    elif msg_type["key request from robot"]:
        print("key request from {}".format(msg["from"]))
        reply = {"key": key}
        key = ""

    else:
        print("invalid message")
        reply = {"message": "is invalid"}

    if verbose_mode:
        print(reply)
    return reply


def create_connection_interface(ip):
    ctx = zmq.Context()
    repsock = ctx.socket(zmq.REP)
    repaddr = "tcp://{}:5005".format(ip)
    repsock.bind(repaddr)

    return repsock


if __name__ == "__main__":
    main()
