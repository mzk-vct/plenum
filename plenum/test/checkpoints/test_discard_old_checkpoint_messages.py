from stp_core.loop.eventually import eventually
from plenum.common.types import Checkpoint
from plenum.test.checkpoints.helper import chkChkpoints
from plenum.test.helper import sendReqsToNodesAndVerifySuffReplies, \
    checkDiscardMsg

TestRunningTimeLimitSec = 150


def testDiscardCheckpointMsgForStableCheckpoint(chkFreqPatched, looper,
                                                txnPoolNodeSet, client1,
                                                wallet1, client1Connected):
    sendReqsToNodesAndVerifySuffReplies(looper, wallet1, client1, chkFreqPatched.CHK_FREQ, 1)
    looper.run(eventually(chkChkpoints, txnPoolNodeSet, 1, 0, retryWait=1))
    node1 = txnPoolNodeSet[0]
    rep1 = node1.replicas[0]
    _, stableChk = rep1.firstCheckPoint
    oldChkpointMsg = Checkpoint(rep1.instId, rep1.viewNo, *_, stableChk.digest)
    rep1.send(oldChkpointMsg)
    recvReplicas = [n.replicas[0] for n in txnPoolNodeSet[1:]]
    looper.run(eventually(checkDiscardMsg, recvReplicas, oldChkpointMsg,
                          "Checkpoint already stable", retryWait=1))
