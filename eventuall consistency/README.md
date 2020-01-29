## Eventually consistent blackboard

### Description
We implemented a solution with balance between strictness of consistency (centralized leader) and efficiency/scalability.

### Solution
 - Messages appear temporarily in different order
 - All blackboards eventually converge to the same value
 - Boards are distributed:
   - No centralized leader, no ring topology
   - Each post is updated on the local board, then propagated to other boards
   - All boards are eventually consistent
   - Partial causal order
     - Each post has a sequence number
       - Posts are ordered by sequence numbers
           - If two posts have the same sequence number, lowest IP address is prioritized
       - Sequence number of a new post is the last sequence number received + 1
   - Delete and modify is also supported
