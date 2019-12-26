# coding=utf-8
# ------------------------------------------------------------------------------------------------------
# TDA596 - Lab 1
# server/server.py
# Input: self_ip total_number_of_ID
# Student: John Doe
# ------------------------------------------------------------------------------------------------------
import traceback
import sys
import time
import json
import argparse
from threading import Thread

from bottle import Bottle, run, request, template, HTTPResponse, response
import requests

from random import randint
from urllib import urlencode
import urlparse
import Queue
from requests.adapters import HTTPAdapter

# ------------------------------------------------------------------------------------------------------
try:
    # updated templates
    index_template = None
    # template for leader status
    status_template = None
    app = Bottle()
    # to demonstrate that only leader update this resource
    master_id = -1
    board = dict()
    # keep updated list of available vessels in the network
    vessels = dict()
    # candidates for leder election
    results = {}
    # vessel ip
    self_ip = None
    leader_ip = None
    # rand id for leader election
    rand_id = randint(1, 1000)
    # FIFO queue so data don't get lost in case of leader election
    queue = Queue.Queue()
    # lock in case of leader eleciton
    mutex = False
    # number of times we retry contacting a vessel
    RETRANSMISSIONS = 2
    # time we wait for response from vessel
    WAIT_RESPONSE = 5
    # time we wait for new leader to be elected to resend data
    WAIT_LEADER = 5
    # timeout for post requests
    TIMEOUT_REQUESTS = 10

    # ------------------------------------------------------------------------------------------------------
    # BOARD FUNCTIONS
    # ------------------------------------------------------------------------------------------------------
    def add_new_element_to_store(entry_sequence, element):
        global board
        if entry_sequence is not None:

            board[int(entry_sequence)] = element

            print "\nEntry added to store: {}\n".format(element)

    def modify_element_in_store(entry_sequence, modified_element):
        global board
        if entry_sequence is not None:

            if int(entry_sequence) in board:
                board[int(entry_sequence)] = modified_element

                print "\nEntry modified in store: {}\n".format(modified_element)

    def delete_element_from_store(entry_sequence):
        global board
        if entry_sequence is not None:

            if int(entry_sequence) in board:
                print "\nEntry deleted from store: {}\n".format(board[int(entry_sequence)])

                del board[int(entry_sequence)]

    # ------------------------------------------------------------------------------------------------------
    # DISTRIBUTED COMMUNICATIONS FUNCTIONS
    # ------------------------------------------------------------------------------------------------------
    def contact_vessel(ip, path, payload=None, req='POST'):
        time.sleep(1)  # attempt to avoid 'max retries exceeded error'
        success = False
        try:
            if 'POST' in req:
                res = requests.post(
                    'http://{}{}'.format(ip, path), data=payload, timeout=TIMEOUT_REQUESTS)

            elif 'GET' in req:
                res = requests.get(
                    'http://{}{}'.format(ip, path), timeout=TIMEOUT_REQUESTS)

            else:
                print 'Non implemented feature'

            try:
                res.raise_for_status()
            except requests.exceptions.HTTPError:
                print "\nHTTPError: {}\n".format(res.reason)

            status = res.status_code
            # can't get rid of bottle internal server error msg so we have to accept error code 500
            if status == 200 or status == 500:
                success = True

        except Exception as e:
            print e

        return success

    def propagate_to_vessels(path, payload=None, req='POST'):
        global vessels
        for ip in vessels.keys():

            # don't propagate to self
            if ip != self_ip:
                success = contact_vessel(ip, path, payload, req)

                if not success:
                    print "\n\nCould not contact vessel {}\n\n".format(ip[-1:])
                    # delete vessel from list of not reachable
                    if ip in vessels:
                        del vessels[ip]

    # ------------------------------------------------------------------------------------------------------
    # ROUTES
    # ------------------------------------------------------------------------------------------------------
    @app.route('/')
    def index():
        global board
        return template(
            index_template,
            board_title='Vessel {}'.format(self_ip[-1:]),
            board_dict=sorted(board.iteritems()),
            members_name_string='Sanjin & Svante')

    @app.get('/board')
    def get_board():
        global board
        return template(
            'server/boardcontents_template.tpl',
            board_title='Vessel {}'.format(self_ip[-1:]),
            board_dict=sorted(board.iteritems()))

    @app.get('/update')
    def get_board():
        global results
        if leader_ip is not None:
            return template(
                status_template,
                candidates=sorted(results.items()),
                leader=leader_ip)

    @app.get('/status')
    def leader_status():
        if self_ip == leader_ip:
            return HTTPResponse(status=200)

    # ------------------------------------------------------------------------------------------------------
    @app.post('/board')
    def client_add_received():
        try:
            action = request.forms.get('delete')
            entry_id = request.forms.get('id')
            entry_value = request.forms.get('entry')

            print "\nNew entry\n - action:\t{}\n - id:\t\t{}\n - value:\t{}\n".format(
                action, entry_id, entry_value)
            # send to leader who updates the board and propagates to rest
            send_to_leader(action, entry_id, entry_value)

        except Exception as e:
            print e

    @app.post('/board/<element_id:int>/')
    def client_action_received(element_id):
        try:
            action = request.forms.get('delete')
            entry_value = request.forms.get('entry')

            msg = "Modify" if action == "0" else "Delete"
            print "\n{} entry:\t{}\n".format(msg, board[element_id])
            # send to leader who updates the board and propagates to rest
            send_to_leader(action, element_id, entry_value)

        except Exception as e:
            print e

    @app.post('/updateboard')
    def update_board():
        global board
        try:
            data = request.forms.get('board')
            board = dict(urlparse.parse_qsl(data))

        except Exception as e:
            print e

    @app.post('/propagate/<action>/<element_id:int>')
    def propagation_received(action, element_id):
        global vessels
        try:
            client_ip = str(request.environ.get('REMOTE_ADDR'))
            entry_value = request.forms.get('entry')
            # someone that is not current leader has propagated message
            if client_ip == leader_ip:
                update_store(action, element_id, entry_value)
            else:
                # let current leader initiate new election
                if self_ip == leader_ip:
                    # send back current board to sync
                    send_current_board(client_ip)
                    # add failed leader to vessels
                    vessels[client_ip] = -1
                    new_election()
                    # wait for new leader
                    wait()
                    resend_data(action, element_id, entry_value)

        except Exception as e:
            print e

    @app.post('/election')
    def election():
        try:
            data = request.forms.get('candidates')
            candidates = dict(urlparse.parse_qsl(data))
            # update vesseks in case a vessel har crashed/reappeared
            difference = update_vessels(candidates)
            # don't proceed with initial election process if there is a difference
            if difference:
                # make sure to propagate candidates to neighbor
                send_candidates(candidates)
            else:
                # candidates might not propagate during initial election
                elect_leader(candidates)

        except Exception as e:
            print e

    @app.post('/coordination')
    def coordination():
        try:
            global leader_ip, mutex, results, update
            data = request.forms.get('results')
            results = dict(urlparse.parse_qsl(data))
            leader_ip = request.forms.get('ip')
            # release lock after election is over
            mutex = False

            print "\nLeader elected: {}\n".format(leader_ip)

        except Exception as e:
            print e

    # ------------------------------------------------------------------------------------------------------
    # LEADER ELECTION
    # ------------------------------------------------------------------------------------------------------
    def send_candidates(candidates=None):
        global vessels, mutex
        mutex = True
        data = None
        # make sure to send candidates to neighbor in case of new election
        if candidates is not None:
            candidates[self_ip] = rand_id
            data = {'candidates': urlencode(candidates)}
        else:
            # add rand_id to vessels for initial leader election
            vessels[self_ip] = rand_id
            data = {'candidates': urlencode(vessels)}

        neighbor = find_neighbor()

        print "\nNew election\n · ip:\t{}\n · id:\t{}\n".format(
            self_ip, rand_id)

        contact_neighbor(neighbor, '/election', data)

    # find neigbor based on ip addr, worst case ~O(2n)
    def find_neighbor():
        global self_ip
        neighbor = self_ip
        vs = sorted(vessels)
        # if self_ip is max -> send to min ip addr
        if vs[len(vessels) - 1] == neighbor:
            return vs[0]
        else:
            # find ip addr > self_ip
            for v in vs:
                if v > neighbor:
                    neighbor = v
                    break

        return neighbor

    # Worst case O(n)
    def update_vessels(candidates):
        global vessels
        lenc = len(candidates)
        lenv = len(vessels)
        difference = False if lenc == lenv else True

        # vessel has reappeared -> add it to vessels
        if lenc > lenv:
            for ip, rid in candidates.iteritems():
                # remove ip addr that we can not contact
                if ip not in vessels:
                    vessels[ip] = rid
                # do not update self
                elif ip == self_ip:
                    vessels[self_ip] = rid
                else:
                    vessels[ip] = candidates[ip]
        # vessel has crashed -> remoeve it from vessels
        else:
            for ip in vessels.keys():
                if ip not in candidates:
                    # remove ip addr that we can not contact
                    if ip in vessels:
                        del vessels[ip]
                    # add ip addr if vessel has reappeared
                    else:
                        for ipc in candidates.keys():
                            if ipc not in vessels:
                                vessels[ipc] = '-1'
                                new_election()
                # do not update self
                elif ip == self_ip:
                    vessels[self_ip] = rand_id
                    # in case leader has crashed and reappeared
                    if self_ip == leader_ip and candidates[ip] != rand_id:
                        difference = True
                else:
                    vessels[ip] = candidates[ip]

        return difference

    # message cost:
    # initial election: worst case O(n*n), best case: ~O(3n)
    # if leader fails after election: O(n)
    def elect_leader(candidates):
        global leader_ip, results, mutex
        # list of candidates has propagated full circle or more
        if int(candidates.get(self_ip, 0)) == rand_id:
            # pick ip with max rand_id in case of
            # i)  new election
            # ii) max rand_id crashed during election
            leader_ip = max(candidates, key=candidates.get)
            print "\nLeader found: {}\n".format(leader_ip)
            # release lock when leader is elected
            mutex = False
            results = candidates
            data = {'ip': leader_ip, 'results': urlencode(candidates)}
            # propagate leaders ip and election results to others
            propagate('/coordination', data)
        # send candidates to neighbor only if there is a rand_id > self rand_id
        elif int(max(candidates.values())) > rand_id:
            neighbor = find_neighbor()
            # make sure to add self rand_id in case max_id crashes
            candidates[self_ip] = rand_id
            data = {'candidates': urlencode(candidates)}
            # send candidates to neighbor
            contact_neighbor(neighbor, '/election', data)

    def contact_neighbor(ip, path, data):
        thread = build_request_thread(
            contact_neighbor_request, ip, path, data)
        thread.start()

    def contact_leader(ip, path, data):
        global queue, mutex
        if mutex:
            # save data in queue in case of leader election
            # allows us to change ip when new leader is elected
            queue.put((ip, path, data))
        else:
            # lock resource in case of leader election
            mutex = True
            thread = build_request_thread(
                contact_leader_request, ip, path, data)
            thread.start()

    def build_request_thread(function, ip, path, data):
        thread = Thread(target=function,
                        args=(ip, path, data))
        thread.daemon = True
        return thread

    def contact_neighbor_request(ip, path, data):
        global vessels
        count = 0
        # try contacting neighbor
        while count < RETRANSMISSIONS:
            if contact_vessel(ip, path, data):
                break
            else:
                count += 1
                time.sleep(WAIT_RESPONSE)

        if count == RETRANSMISSIONS:
            print "\nCould not contact neighbor: {}".format(ip)
            # delete vessel if not reachable
            if ip in vessels:
                del vessels[ip]
            # find neigbor successor
            neighbor = find_neighbor()
            # send updated vessels
            candidates = {'candidates': urlencode(vessels)}
            contact_neighbor_request(neighbor, '/election', candidates)

            print "\nTry neighbor successor: {}\n".format(neighbor)

    def contact_leader_request(ip, path, data):
        global vessels, mutex, leader_ip
        count = 0
        # try contacting leader
        while count < RETRANSMISSIONS:
            if contact_vessel(ip, path, data):
                # release lock
                update_queue()
                break
            else:
                count += 1
                time.sleep(WAIT_RESPONSE)

        # could not contact leader
        if count == RETRANSMISSIONS:
            print "\nCould not contact leader: {}".format(ip)

            if ip in vessels:
                del vessels[ip]
            # new election
            new_election()
            # wait for leader to get elected
            wait()
            # resend data before queue (if any)
            print "\nResend data to new leader: {}\n".format(leader_ip)
            contact_leader_request(leader_ip, path, data)
            # let queued data propagate
            update_queue()

    def wait():
        while leader_ip is None:
            time.sleep(WAIT_LEADER)

    def update_queue():
        global queue, mutex
        # release next in queue
        if not queue.empty():
            args = queue.get()
            thread = build_request_thread(
                contact_leader_request, leader_ip, args[1], args[2])
            thread.start()
        else:
            mutex = False

    def reset_vessels():
        global vessels
        for ip in vessels.keys():
            vessels[ip] = -1

    def send_to_leader(action, entry_id, entry_value):
        # if leader -> update store and propagate
        if self_ip == leader_ip:
            uid = update_store(action, entry_id, entry_value)
            propagate(action, uid, entry_value)
        # else contact to leader
        else:
            data = build_data(action, entry_id, entry_value)
            contact_leader(leader_ip, '/board', data)

    def new_election():
        global leader_ip
        leader_ip = None
        reset_vessels()
        send_candidates()

    def init_elect_leader():
        # wait for 3 sec to make sure everyone boots
        time.sleep(3)
        send_candidates()

    # ------------------------------------------------------------------------------------------------------
    # HELP FUNCTIONS
    # ------------------------------------------------------------------------------------------------------
    def update_store(action, entry_id, entry_value):
        eid = entry_id

        if action == "0":
            modify_element_in_store(eid, entry_value)

        elif action == "1":
            delete_element_from_store(eid)
        # action == None
        else:
            # only leader generates new entry ids
            if self_ip == leader_ip:
                eid = generate_id(entry_id)

            add_new_element_to_store(eid, entry_value)

        return eid

    def propagate(action, entry_id, entry_value=None):
        path = data = None
        if action == '/coordination':
            path = action
            data = entry_id

        else:
            path = "/propagate/{}/{}".format(action, entry_id)
            data = {'entry': entry_value}

        thread = Thread(target=propagate_to_vessels,
                        args=(path, data))
        thread.daemon = True
        thread.start()

    def generate_id(entry_id):
        global master_id
        # generate id based on time in milliseconds
        uid = millisec() if entry_id == None else entry_id
        return int(max(board.keys()) + 1 if uid in board.keys() else uid)

    def millisec():
        return time.time() * 10**6

    def send_current_board(vessel_ip):
        global board
        data = {'board': urlencode(board)}

        thread = Thread(
            target=contact_vessel,
            args=(vessel_ip, '/updateboard', data))

        thread.daemon = True
        thread.start()

    def resend_data(action, entry_id, entry_value):
        global leader_ip
        data = build_data(action, entry_id, entry_value)
        contact_leader(leader_ip, '/board', data)

    def build_data(action, entry_id, entry_value):
        return {
            'delete': action,
            'id': entry_id,
            'entry': entry_value}

    # ------------------------------------------------------------------------------------------------------
    # REBUILD TEMPLATES FOR LEADER ELECTION
    #
    # rebuilding given templates programically
    # same results should appear for TAs with original templates and this server.py file
    # ------------------------------------------------------------------------------------------------------
    def build_templates():
        global index_template, status_template
        rep1 = '></iframe>'
        rep2 = '<div id="board_form_placeholder">'
        rep3 = 'function update_contents(){'
        rep4 = 'update_contents();'

        # rebuilding original board_frontpage_header_template
        board_frontpage_header_template = file('server/board_frontpage_header_template.tpl').read(
            # hiding constant 'internal server error' that raises when submitting new entries to board
            # originates from bottle ERROR_PAGE_TEMPLATE
        ).replace(
            ' resizable seamless' + rep1, ' style="display:none"' + rep1

            # adding div for leader status
        ).replace(
            rep2, rep2 + '\n\t<div id="status_placeholder"></div>'

            # adding function for updating leader status div
        ).replace(
            rep3, 'function update_status(){\n\t$("#status_placeholder").load("/update #status_content");\n\t}\n\n' + rep3

            # adding update function inside timer function for automatic updates
        ).replace(
            rep4, rep4 + '\n\t\tupdate_status();'
        )

        # removing original board_frontpage_header_template
        index = file('server/index.tpl').read(
        ).replace("% include('server/board_frontpage_header_template.tpl')", '')

        # adding back updated board_frontpage_header_template
        index_template = board_frontpage_header_template + index

        # template for showing leader status
        status_template = '<div id="status_content"><h3>Election:</h3><p>Candidates: {{candidates}}</p><p>Leader: {{leader}}</p></div>'

    # ------------------------------------------------------------------------------------------------------
    # EXECUTION
    # ------------------------------------------------------------------------------------------------------
    def main():
        global vessels, self_ip, app
        build_templates()

        port = 80
        parser = argparse.ArgumentParser(
            description='Your own implementation of the distributed blackboard')

        parser.add_argument('--id', nargs='?', dest='nid',
                            default=1, type=int, help='This server ID')

        parser.add_argument('--vessels', nargs='?', dest='nbv', default=1,
                            type=int, help='The total number of vessels present in the system')

        args = parser.parse_args()
        self_ip = '10.1.0.{}'.format(str(args.nid))

        # init vessels with (key,value) pair where key=ip addr and value=rand_id for leader election
        # keep vessel list updated in case nodes crash
        for i in range(1, args.nbv + 1):
            ip = '10.1.0.{}'.format(str(i))
            vessels[ip] = "-1"
            # s = requests.Session()
            # s.mount(ip, HTTPAdapter(max_retries=100))

        # init leader election when vessel boot
        init_elect_leader()

        try:
            run(app, host=self_ip, port=port)
        except Exception as e:
            print e

    # ------------------------------------------------------------------------------------------------------
    if __name__ == '__main__':
        main()
except Exception as e:
    traceback.print_exc()
    while True:
        time.sleep(60.)
