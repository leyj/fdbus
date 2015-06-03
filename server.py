#!/usr/bin/env python
# -*- coding: utf-8 -*-

from threading import Thread
from signal import signal, SIGINT
from select import poll, POLLIN, POLLHUP

from fdbus_h import *
from fd_object import FileDescriptor


class Server(Thread):

    def __init__(self, path):
        super(Server, self).__init__()
        self.clients = {}
        self.server_event_poll = poll()
        self.path = path
        self.running = True
        self.server = self.socket()
        signal(SIGINT, self.server_interrupt)

    def socket(self):
        libc.socket.restype = c_int
        server = libc.socket(AF_UNIX, SOCK_STREAM, PROTO_DEFAULT)
        if (server == -1):
            # raise exception
            print 'Error in socket'
        return server

    @property
    def listen(self):
        return libc.listen(self.server, DEFAULT_CLIENTS)

    @property
    def bind(self):
        server_address = pointer(sockaddr_un(AF_UNIX, self.path))
        self.serv_sk_addr = cast(server_address, POINTER(sockaddr))
        server_size = sizeof(sockaddr_un)
        return libc.bind(self.server, self.serv_sk_addr, server_size)

    def accept(self):
        libc.accept.restype = c_int
        client_size = c_int(sizeof(sockaddr_un))
        client_size_ptr = pointer(client_size)
        client = libc.accept(self.server, self.serv_sk_addr, client_size_ptr)
        if (client == -1):
            # raise exception
            print "Error in accept"
            return -1
        libc.sendmsg(c_int(client), pointer(msghdr(self.test_fd)), c_int(0))
        self.clients[client] = PyCClientWrapper(client)


    def open_fd(self, fname):
        c_fname = create_string_buffer(fname)
        libc.open.restype = c_int
        return libc.open(c_fname, O_RDONLY)
    
    def client_ev(self, client, ev):
        if ev == POLLHUP:
            libc.close(client)
            del self.clients[client]
        else:
            pass # XXX incoming client commands 

    def shutdown(self):
        libc.close(self.test_fd)
        libc.close(self.server)
        libc.unlink(self.path)
        map(libc.close, self.clients)

    def server_interrupt(self, sig, frame):
        self.running = False
        self.shutdown()
        
    def run(self):
        # poll for incoming messages to shutdown
        fd = FileDescriptor('') #XXX test fd obj - random file path
        self.test_fd = fd.fopen()
        if self.bind == -1:
            # raise exception
            print "Error in Bind"
            return -1
        if self.listen == -1:
            # raise exception
            print "Error in Listen"
            return -1
        self.server_event_poll.register(self.server, POLLIN | POLLHUP)
        while self.running:
            events = self.server_event_poll.poll(2)
            if events:
                if events[0][0] == self.server:
                    self.accept()            
                else:
                    self.client_ev(*events[0])
        self.shutdown()

class PyCClientWrapper(object):

    def __init__(self, client_c_fd):
        self.fd = client_c_fd