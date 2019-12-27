## Distributed blackboard with centralized communication

### Description
We implemented a ring-based leader election where all data is sent to a central leader which distributes it to the network. The leader is be able to handle multiple posts from different nodes.

 - All boards show messages in the same order
 - Each post is sent to the leader which distributes it to the network
   - The leader handles multiple posts from different nodes
 - Implemented leader election
   - Ring-based election algorithm
     - Every node sends only to their next neighbor
     - Highest locally generated random number wins as a criterion for selecting the leader
     - The protocol starts running as soon as the nodes are up
     - After the election:
       - A leader is established and everyone agrees on it
       - Nodes send new entries directly to the leader (no ring)
       - The leader serves as a centralized sequencer
         - Decides the correct, global order of all messages and everybody else follows that order
 - Handles dynamic networks:
   - The leader fails while the program is running
     - Failed elected leader is reintroduced to the network
   - A node during the election cannot reach its next neighbor
   - Concurrently deleted/modified entries in the blackboard
