## Eventyally consistent blackboard

### Description
 - Balance between strictness of consistency and efficiency/scalability
   - How much consistency is needed depends on the application
 - Messages appear in different order temporarily
 - All replicas eventually converge to the same value
 - Boards are distributed:
   - No centralized leader, no ring topology
   - Each post is updated to the local board, then propagated to other boards
   - All boards are eventually consistent
   - Partial causal order
     - Each post has a sequence number
       - Posts are ordered by sequence numbers
           - If two posts have the same sequence number, lowest IP address is prioritized
       - Sequence number of a new post is last sequence number received + 1
   - Delete and modify is also supported