# coding=utf-8
# ------------------------------------------------------------------------------------------------------
# TDA596 - Lab 1
# server/server.py
# Input: Node_ID total_number_of_ID
# Student: John Doe
# ------------------------------------------------------------------------------------------------------
import traceback
import sys
import time
import json
import argparse
from threading import Thread

from bottle import Bottle, run, request, template
import requests

from ast import literal_eval as make_tuple
# ------------------------------------------------------------------------------------------------------
try:
    app = Bottle()

    board = {}  # {(seq, ip): entry}
    history = {}  # {(seq, ip): (seq, origin), (action, entry)}
    self_seq = -1

    # ------------------------------------------------------------------------------------------------------
    # BOARD FUNCTIONS
    # You will probably need to modify them
    # ------------------------------------------------------------------------------------------------------

    def add_new_element_to_board(origin, seq, action, eid, entry):
        global history, board, self_seq
        if self_seq == seq:
            self_seq = seq

        if eid not in history:
            board[eid] = entry
        # if action == modify
        elif history[eid][1][0] == "0":
            # add modification to board
            board[eid] = history[eid][1][1]

        history[eid] = ((seq, origin), (action, entry))

        print "\nadd_new_element_to_board\n · entry:\t{}\n".format(entry)

    def modify_element_in_board(origin, seq, action, eid, entry):
        global history, board, self_seq
        if self_seq < seq:
            self_seq = seq

        self_seq += 1

        if eid in history and eid in board:
            old = history[eid]
            # IF (history.seq == seq AND history.ip >= origin) OR (history.seq < seq)
            if (old[0][0] == seq and old[0][1] <= origin) or old[0][0] < seq:
                board[eid] = entry

                print "\nmodify_element_in_board\n · entry:\t{}\n".format(entry)

        history[eid] = ((seq, origin), (action, entry))

    def delete_element_from_board(origin, seq, action, eid, entry):
        global history, board, self_seq
        if self_seq < seq:
            self_seq = seq

        if eid in board:
            del board[eid]

        history[eid] = ((seq, origin), (action, entry))

    # ------------------------------------------------------------------------------------------------------
    # DISTRIBUTED COMMUNICATIONS FUNCTIONS
    # ------------------------------------------------------------------------------------------------------

    def contact_vessel(vessel_ip, path, payload=None, req='POST'):
        success = False
        try:
            if 'POST' in req:
                res = requests.post(
                    'http://{}{}'.format(vessel_ip, path), data=payload)

            elif 'GET' in req:
                res = requests.get(
                    'http://{}{}'.format(vessel_ip, path))

            else:
                print 'Non implemented feature!'

            if res.status_code == 200:
                success = True

        except Exception as e:
            print e
        return success

    def propagate_to_vessels(path, payload=None, req='POST'):
        global vessel_list, node_id

        for vessel_id, vessel_ip in vessel_list.items():

            if int(vessel_id) != node_id:
                success = contact_vessel(vessel_ip, path, payload, req)

                if not success:
                    print "\n\nCould not contact vessel {}\n\n".format(vessel_id)

    # ------------------------------------------------------------------------------------------------------
    # ROUTES
    # ------------------------------------------------------------------------------------------------------
    # a single example (index) for get, and one for post
    # ------------------------------------------------------------------------------------------------------
    @app.route('/')
    def index():
        global board, node_id
        return template(
            'server/index.tpl',
            board_title='Vessel {}'.format(node_id),
            board_dict=sorted(board.iteritems()),
            members_name_string='Sanjin & Svante')

    @app.get('/board')
    def get_board():
        global board, node_id
        return template(
            'server/boardcontents_template.tpl',
            board_title='Vessel {}'.format(node_id),
            board_dict=sorted(board.iteritems()))
    # ------------------------------------------------------------------------------------------------------
    @app.post('/board')
    def client_add_received():
        global self_seq
        try:
            entry = get_forms('entry')[0]
            origin = vessel_list[str(node_id)]
            self_seq += 1
            eid = (self_seq, origin)

            print_trace("client_action_received", origin,
                        self_seq, None, eid, entry)

            update_store(origin, self_seq, None, eid, entry)
            propagate(origin, self_seq, None, eid, entry)
        except Exception as e:
            print e

    @app.post('/board/<eid>/')
    def client_action_received(eid):
        global vessel_list, node_id, self_seq

        action, entry = get_forms('delete', 'entry')
        origin = vessel_list[str(node_id)]

        print_trace("client_action_received", origin,
                    self_seq, action, eid, entry)

        update_store(origin, self_seq, action, make_tuple(eid), entry)
        propagate(origin, self_seq, action, eid, entry)
        pass

    @app.post('/propagate')
    def propagation_received():
        origin, seq, action, eid, entry = get_forms(
            'origin', 'seq', 'action', 'eid', 'entry')

        print_trace("propagation_received", origin,
                    seq, action, eid, entry)

        update_store(origin, int(seq), action, make_tuple(eid), entry)
        pass

    # ------------------------------------------------------------------------------------------------------
    # HELP FUNCTIONS
    # ------------------------------------------------------------------------------------------------------
    def get_forms(*elements):
        elems = []
        for elem in elements:
            elems.append(request.forms.get(elem))

        return elems

    def update_store(origin, seq, action, eid, entry):
        # modify entry
        if action == "0":
            modify_element_in_board(origin, seq, action, eid, entry)
        # delete entry
        elif action == "1":
            delete_element_from_board(origin, seq, action, eid, entry)
        # add new entry to store
        else:
            add_new_element_to_board(origin, seq, action, eid, entry)

    def propagate(origin, seq, action, eid, entry):
        path = "/propagate"
        data = {
            'origin': origin,
            'seq': seq,
            'action': action,
            'eid': str(eid),
            'entry': entry}

        thread = Thread(target=propagate_to_vessels,
                        args=(path, data))
        thread.daemon = True
        thread.start()

    def print_trace(function, origin, seq, action, eid, entry):
        print "\n{}\n · origin:\t{}\n · seq:\t\t{}\n · action:\t{}\n · eid:\t\t{}\n · entry:\t{}".format(
            function, origin, seq, action, eid, entry)

    # ------------------------------------------------------------------------------------------------------
    # EXECUTION
    # ------------------------------------------------------------------------------------------------------
    def main():
        global vessel_list, node_id, app

        port = 80
        parser = argparse.ArgumentParser(
            description='Your own implementation of the distributed blackboard')

        parser.add_argument('--id', nargs='?', dest='nid',
                            default=1, type=int, help='This server ID')

        parser.add_argument('--vessels', nargs='?', dest='nbv', default=1,
                            type=int, help='The total number of vessels present in the system')

        args = parser.parse_args()
        node_id = args.nid
        vessel_list = dict()
        # We need to write the other vessels IP, based on the knowledge of their number
        for i in range(1, args.nbv):
            vessel_list[str(i)] = '10.1.0.{}'.format(str(i))

        try:
            run(app, host=vessel_list[str(node_id)], port=port)
        except Exception as e:
            print e
    # ------------------------------------------------------------------------------------------------------
    if __name__ == '__main__':
        main()
except Exception as e:
    traceback.print_exc()
    while True:
        time.sleep(60.)
