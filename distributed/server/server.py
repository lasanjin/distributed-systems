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
# ------------------------------------------------------------------------------------------------------
try:
    app = Bottle()

    # store entries as (id,value) pairs
    board = {}

    # ------------------------------------------------------------------------------------------------------
    # BOARD FUNCTIONS
    # You will probably need to modify them
    # ------------------------------------------------------------------------------------------------------

    def add_new_element_to_store(entry_sequence, element, is_propagated_call=False):
        global board, node_id
        success = False
        try:
            # map ids to entries
            board[entry_sequence] = element
            print "\nadd_new_element_to_store\n · entry:\t{}\n".format(element)

            success = True
        except Exception as e:
            print e
        return success

    def modify_element_in_store(entry_sequence, modified_element, is_propagated_call=False):
        global board, node_id
        success = False
        try:
            board[entry_sequence] = modified_element
            print "\nmodify_element_from_store\n · entry:\t{}\n".format(modified_element)

            success = True
        except Exception as e:
            print e
        return success

    def delete_element_from_store(entry_sequence, is_propagated_call=False):
        global board, node_id
        success = False
        try:
            del board[entry_sequence]
            print "\ndelete_element_from_store\n · id:\t{}\n".format(entry_sequence)

            success = True
        except Exception as e:
            print e
        return success

    # ------------------------------------------------------------------------------------------------------
    # DISTRIBUTED COMMUNICATIONS FUNCTIONS
    # ------------------------------------------------------------------------------------------------------
    def contact_vessel(vessel_ip, path, payload=None, req='POST'):
        # Try to contact another server (vessel) through a POST or GET, once
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
            # result is in res.text or res.json()
            # print(res.text)
            if res.status_code == 200:
                success = True
        except Exception as e:
            print e
        return success

    def propagate_to_vessels(path, payload=None, req='POST'):
        global vessel_list, node_id

        for vessel_id, vessel_ip in vessel_list.items():

            if int(vessel_id) != node_id:  # don't propagate to yourself
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
        global board, node_id
        try:
            # get values from elements in form
            action, entry_id, entry_value = get_forms('action', 'id', 'entry')

            # get unique, chronologically ordered, id for each entry
            uid = get_id(entry_id)

            print_trace("client_add_received", action, uid, entry_value)

            # add entry to store
            add_new_element_to_store(uid, entry_value)

            # propagate new entry
            propagate(action, uid, entry_value)

            return True
        except Exception as e:
            print e
        return False

    @app.post('/board/<element_id:int>/')
    def client_action_received(element_id):
        # get values from elements in form
        action, entry_value = get_forms('delete', 'entry')
        print_trace("client_action_received", action, element_id, entry_value)

        # update store and propagate change to store
        update_store(action, element_id, entry_value)
        propagate(action, element_id, entry_value)
        pass

    @app.post('/propagate/<action>/<element_id>')
    def propagation_received(action, element_id):
        entry_value = get_forms('entry')[0]
        print_trace("propagation_received", action, element_id, entry_value)

        # update store
        update_store(action, element_id, entry_value)
        pass

    # ------------------------------------------------------------------------------------------------------
    # HELP FUNCTIONS
    # ------------------------------------------------------------------------------------------------------
    def get_forms(*elements):
        elems = []
        for elem in elements:
            elems.append(request.forms.get(elem))

        return elems

    def update_store(action, entry_id, entry_value):
        # entry_id in board as int
        int_id = int(entry_id)

        # modify entry
        if action == "0":
            modify_element_in_store(int_id, entry_value)
        # delete entry
        elif action == "1":
            delete_element_from_store(int_id)
        # add new entry to store
        else:
            add_new_element_to_store(int_id, entry_value)

    def propagate(action, entry_id, entry_value):
        # generate path and format entry_value for POST request
        path = "/propagate/{}/{}".format(action, entry_id)
        data = {'entry': entry_value}

        # create thread to not block
        thread = Thread(target=propagate_to_vessels,
                        args=(path, data))
        thread.daemon = True
        thread.start()

    def get_id(entry_id):
        # generate id based on time in milliseconds
        uid = int(time.time() * 10**6 if entry_id == None else entry_id)

        return int(max(board.keys()) + 1 if uid in board.keys() else uid)

    def print_trace(function, action, entry_id, entry_value):
        print "\n{}\n · action:\t{}\n · id:\t\t{}\n · entry:\t{}".format(function, action, entry_id, entry_value)

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
