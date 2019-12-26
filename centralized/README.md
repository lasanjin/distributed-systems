## Centralized blackboard

### Description
 - All board show messages in the same order
 - Each post is sent to the leader which distributes it to the network
   - The leader handles multiple posts from different nodes
 - Implemented leader election
   - Ring-based election algorithm
     - Every node should send only to their next neighbor
     - A locally generated random number as a criterion for selecting the leader (e.g. highest wins)
     - The protocol starts running as soon as the nodes are up
     - After the election:
       - The leader is established and everyone agrees on it
       - Nodes send new entries directly to the leader (no ring)
       - The leader serves as a centralized sequencer
         - Decides the correct, global order of all messages and everybody else follows that order
 - Handle dynamic networks:
   - The leader fails while the program is running
     - Elected leader fails after election
       - Failed elected leader is reintroduced to the network
   - A node during the election cannot reach its next neighbor
   - Concurrently delete/modify entries in the blackboard
