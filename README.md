# Distributed Systems

## Description
Lab assignments from Distributed Systems course at Chalmers.

We developed and evaluated a distributed blackboard over a network on Mininet with local virtual machines. We improved the blackboard to make it more consistent, fault-torelant, efficient and reliable by implementing different algorithms. All work was done in the `server.py` files.

### Assignments (in chronological order)
 - [distributed](distributed/README.md)
   - Simple distributed solution
     - No guaranteed order, consistency or fault-tolerance
 - [centralized](centralized/README.md)
   - Optimized ring based leader election solution
     - Guaranteed order (FIFO), consistency and fault-tolerance (leader failure and node failure during election)
 - [eventual consistency](eventuall%20consistency/README.md)
   - Distributed solution
     - Causal order, eventual consistency, no fault-tolerance

### Provided material
 - HTML files
 - Mininet script
   
### How to run
 - [Install Mininet](https://github.com/lasanjin/notes/blob/master/code/TOOLS.md)
 - Run `sudo python lab1.py`
