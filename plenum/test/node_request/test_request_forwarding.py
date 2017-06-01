import pytest

from plenum.common.constants import DOMAIN_LEDGER_ID
from plenum.test.delayers import nom_delay, delay_3pc_messages
from plenum.test.helper import sendRandomRequests, \
    waitForSufficientRepliesForRequests
from plenum.test.batching_3pc.conftest import tconf
from plenum.test.pool_transactions.conftest import looper, clientAndWallet1, \
    client1, wallet1, client1Connected
from plenum.test.test_node import ensureElectionsDone
from plenum.test.view_change.helper import ensure_view_change
from stp_core.loop.eventually import eventually


def test_all_replicas_hold_request_keys(looper, txnPoolNodeSet, client1,
                                        wallet1, client1Connected, tconf):
    """
    All replicas whether primary or non primary hold request keys of forwarded
    requests. Once requests are ordered, they request keys are removed from replica.
    """
    delay_3pc_messages(txnPoolNodeSet, 0, 2)
    delay_3pc_messages(txnPoolNodeSet, 1, 2)

    def chk(count):
        # All replicas have same amount of forwarded request keys and all keys
        # are finalised.
        for node in txnPoolNodeSet:
            for r in node.replicas:
                if r.isPrimary is False:
                    assert len(r.requestQueues[DOMAIN_LEDGER_ID]) == count
                    for i in range(count):
                        k = r.requestQueues[DOMAIN_LEDGER_ID][i]
                        assert r.requests[k].finalised
                elif r.isPrimary is True:
                    assert len(r.requestQueues[DOMAIN_LEDGER_ID]) == 0

    reqs = sendRandomRequests(wallet1, client1, tconf.Max3PCBatchSize - 1)
    # Only non primary replicas should have all request keys with them
    looper.run(eventually(chk, tconf.Max3PCBatchSize - 1))
    waitForSufficientRepliesForRequests(looper, client1, requests=reqs, add_delay_to_timeout=2)
    # Replicas should have no request keys with them since they are ordered
    looper.run(eventually(chk, 0))  # Need to wait since one node might not
    # have processed it.

    delay = 1
    for node in txnPoolNodeSet:
        node.nodeIbStasher.delay(nom_delay(delay))

    ensure_view_change(looper, txnPoolNodeSet, client1, wallet1)
    reqs = sendRandomRequests(wallet1, client1, 2 * tconf.Max3PCBatchSize)
    looper.run(eventually(chk, 2 * tconf.Max3PCBatchSize))
    ensureElectionsDone(looper, txnPoolNodeSet)
    waitForSufficientRepliesForRequests(looper, client1, requests=reqs,
                                        add_delay_to_timeout=2)
    looper.run(eventually(chk, 0))
