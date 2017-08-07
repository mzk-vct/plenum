from plenum.server.replica import Replica
from typing import List, Deque, Optional, Generator
from collections import deque
from plenum.server.monitor import Monitor
import math

from stp_core.common.log import getlogger
logger = getlogger()


class Replicas:

    def __init__(self, onwer_name: str, monitor: Monitor):
        self._onwer_name = onwer_name
        self._monitor = monitor
        self._replicas = []  # type: List[Replica]
        self._messages_to_replicas = []  # type: List[Deque]

    def grow(self) -> int:
        instance_id = self.num_replicas
        is_master = instance_id == 0
        description = "master" if is_master else "backup"
        replica = self._new_replica(instance_id, is_master)
        self._replicas.append(replica)
        self._messages_to_replicas.append(deque())
        self._monitor.addInstance()

        logger.display("{} added replica {} to instance {} ({})"
                       .format(self._onwer_name, replica, instance_id, description),
                       extra={"tags": ["node-replica"]})
        return self.num_replicas

    def shrink(self) -> int:
        replica = self._replicas[-1]
        self._replicas = self._replicas[:-1]
        self._messages_to_replicas = self._messages_to_replicas[:-1]
        self._monitor.removeInstance()
        logger.display("{} removed replica {} from instance {}".
                       format(self._onwer_name, replica, replica.instId),
                       extra={"tags": ["node-replica"]})
        return self.num_replicas

    @property
    def some_replica_has_primary(self) -> bool:
        return self.primary_replica_id is not None

    @property
    def primary_replica_id(self) -> Optional[int]:
        for replica in self._replicas:
            if replica.isPrimary:
                return replica.instId

    def service_inboxes(self, limit: int=None):
        number_of_processed_messages = \
            sum(replica.serviceQueues(limit) for replica in self._replicas)
        return number_of_processed_messages

    def pass_message(self, instance_id, message):
        # TODO: merge it with service_inboxes?
        self._replicas[instance_id].inBox.append(message)

    def get_output(self, limit: int=None) -> Generator:
        if limit is None:
            per_replica = None
        else:
            per_replica = round(limit / self.num_replicas)
            if per_replica == 0:
                logger.warning("{} forcibly setting replica "
                               "message limit to {}"
                               .format(self._onwer_name,
                                       self.num_replicas))
                per_replica = 1
        for replica in self._replicas:
            num = 0
            while replica.outBox:
                yield replica.outBox.popleft()
                num += 1
                if per_replica and num >= per_replica:
                    break

    def take_ordereds_out_of_turn(self) -> tuple:
        """
        Takes all Ordered messages from outbox out of turn
        """
        for replica in self._replicas:
            yield replica.instId, replica._remove_ordered_from_queue()

    def _new_replica(self, instance_id: int, is_master: bool) -> Replica:
        """
        Create a new replica with the specified parameters.
        """
        return Replica(self, instance_id, is_master)

    def __len__(self):
        return self.num_replicas

    @property
    def num_replicas(self):
        return len(self._replicas)

    @property
    def sum_inbox_len(self):
        return sum(len(replica.inBox) for replica in self._replicas)

    @property
    def all_replicas_have_primary(self) -> bool:
        return all(r.primaryName is not None for r in self._replicas)