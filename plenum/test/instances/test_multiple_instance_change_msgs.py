import pytest

from stp_core.loop.eventually import eventually
from plenum.common.exceptions import SuspiciousNode
from plenum.common.types import InstanceChange
from plenum.server.node import Node
from plenum.server.suspicion_codes import Suspicions
from plenum.test.helper import getNodeSuspicions
from plenum.test.spy_helpers import getAllArgs
from plenum.test import waits


nodeCount = 7


@pytest.mark.skip(reason="INDY-80. Not yet implemented")
def testMultipleInstanceChangeMsgsMarkNodeAsSuspicious(looper, nodeSet, up):
    maliciousNode = nodeSet.Alpha
    for i in range(0, 5):
        maliciousNode.send(maliciousNode._create_instance_change_msg(i, 0))

    def chk(instId):
        for node in nodeSet:
            if node.name != maliciousNode.name:
                args = getAllArgs(node, Node.processInstanceChange)
                assert len(args) == 5
                for arg in args:
                    assert arg['frm'] == maliciousNode.name

    numOfNodes = len(nodeSet)
    instanceChangeTimeout = waits.expectedPoolViewChangeStartedTimeout(numOfNodes)

    for i in range(0, 5):
        looper.run(eventually(chk, i, retryWait=1, timeout=instanceChangeTimeout))

    def g():
        for node in nodeSet:
            if node.name != maliciousNode.name:
                frm, reason, code = getAllArgs(node, Node.reportSuspiciousNode)
                assert frm == maliciousNode.name
                assert isinstance(reason, SuspiciousNode)
                suspectingNodes = \
                    getNodeSuspicions(node,
                                      Suspicions.FREQUENT_INST_CHNG.code)
                assert len(suspectingNodes) == 13

    timeout = waits.expectedTransactionExecutionTime(numOfNodes)
    looper.run(eventually(g, retryWait=1, timeout=timeout))
