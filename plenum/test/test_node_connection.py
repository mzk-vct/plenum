from random import shuffle, randint

import pytest
from ioflo.aid import getConsole

from plenum.common.keygen_utils import initNodeKeysForBothStacks, tellKeysToOthers
from plenum.common.util import randomString
from stp_core.loop.eventually import eventually
from stp_core.common.log import getlogger
from stp_core.loop.looper import Looper
from plenum.common.temp_file_util import SafeTemporaryDirectory
from plenum.common.types import NodeDetail
from plenum.test import waits
from plenum.test.helper import stopNodes
from plenum.test.test_node import TestNode, checkNodesConnected, \
    checkProtocolInstanceSetup
from stp_core.network.port_dispenser import genHa

logger = getlogger()

whitelist = ['discarding message', 'found legacy entry',
             'error while verifying message']


@pytest.fixture()
def nodeReg():
    return {
            'Alpha': NodeDetail(genHa(1), "AlphaC", genHa(1)),
            'Beta': NodeDetail(genHa(1), "BetaC", genHa(1)),
            'Gamma': NodeDetail(genHa(1), "GammaC", genHa(1)),
            'Delta': NodeDetail(genHa(1), "DeltaC", genHa(1))
    }


def initLocalKeys(tdir, nodeReg):
    for nName in nodeReg.keys():
        sigseed = randomString(32).encode()
        initNodeKeysForBothStacks(nName, tdir, sigseed, override=True)
        logger.debug('Created keys for {}'.format(nName))


# Its a function fixture, deliberately
@pytest.yield_fixture()
def tdirAndLooper(nodeReg):
    with SafeTemporaryDirectory() as td:
        logger.debug("temporary directory: {}".format(td))
        with Looper() as looper:
            yield td, looper


@pytest.mark.skip(reason='INDY-75')
def testNodesConnectsWhenOneNodeIsLate(allPluginsPath, tdirAndLooper,
                                       nodeReg):
    tdir, looper = tdirAndLooper
    initLocalKeys(tdir, nodeReg)

    nodes = []
    names = list(nodeReg.keys())
    logger.debug("Node names: {}".format(names))

    def create(name):
        node = TestNode(name, nodeReg, basedirpath=tdir,
                        pluginPaths=allPluginsPath)
        nodes.append(node)
        return node

    for name in names[:3]:
        create(name)

    logger.debug("Creating keys")

    for node in nodes:
        tellKeysToOthers(node, nodes)
        looper.add(node)

    looper.run(checkNodesConnected(nodes))

    # wait for the election to complete with the first three nodes
    looper.runFor(10)

    # create the fourth and see that it learns who the primaries are
    # from the other nodes
    lateNode = create(names[3])
    for node in nodes[:-1]:
        tellKeysToOthers(lateNode, node)
        tellKeysToOthers(node, lateNode)

    looper.add(lateNode)
    # TODO set timeout from 'waits' after the test enabled
    checkProtocolInstanceSetup(looper, nodes, customTimeout=10)
    stopNodes(nodes, looper)


def testNodesConnectWhenTheyAllStartAtOnce(allPluginsPath, tdirAndLooper,
                                           nodeReg):
    tdir, looper = tdirAndLooper
    nodes = []

    initLocalKeys(tdir, nodeReg)

    for name in nodeReg:
        node = TestNode(name, nodeReg, basedirpath=tdir,
                        pluginPaths=allPluginsPath)
        nodes.append(node)

    for node in nodes:
        tellKeysToOthers(node, nodes)

    for node in nodes:
        looper.add(node)

    looper.run(checkNodesConnected(nodes))
    stopNodes(nodes, looper)


# @pytest.mark.parametrize("x10", range(1, 11))
# def testNodesComingUpAtDifferentTimes(x10):
def testNodesComingUpAtDifferentTimes(allPluginsPath, tdirAndLooper,
                                      nodeReg):
    console = getConsole()
    console.reinit(flushy=True, verbosity=console.Wordage.verbose)
    tdir, looper = tdirAndLooper

    initLocalKeys(tdir, nodeReg)

    nodes = []

    names = list(nodeReg.keys())

    shuffle(names)
    waits = [randint(1, 10) for _ in names]
    rwaits = [randint(1, 10) for _ in names]

    for name in names:
        node = TestNode(name, nodeReg, basedirpath=tdir,
                        pluginPaths=allPluginsPath)
        nodes.append(node)

    for node in nodes:
        tellKeysToOthers(node, nodes)

    for i, node in enumerate(nodes):
        looper.add(node)
        looper.runFor(waits[i])
    looper.run(checkNodesConnected(nodes))
    logger.debug("connects")
    logger.debug("node order: {}".format(names))
    logger.debug("waits: {}".format(waits))

    stopNodes(nodes, looper)
    for node in nodes:
        looper.removeProdable(node)

    nodes = []
    for name in names:
        node = TestNode(name, nodeReg, basedirpath=tdir,
                        pluginPaths=allPluginsPath)
        nodes.append(node)
        looper.add(node)
        looper.runFor(rwaits[i])

    looper.run(checkNodesConnected(nodes))
    stopNodes(nodes, looper)
    logger.debug("reconnects")
    logger.debug("node order: {}".format(names))
    logger.debug("rwaits: {}".format(rwaits))


def testNodeConnection(allPluginsPath, tdirAndLooper, nodeReg):
    console = getConsole()
    console.reinit(flushy=True, verbosity=console.Wordage.verbose)
    tdir, looper = tdirAndLooper
    names = ["Alpha", "Beta"]
    nrg = {n: nodeReg[n] for n in names}
    initLocalKeys(tdir, nrg)

    logger.debug(names)
    nodes = []
    for name in names:
        node = TestNode(name, nrg, basedirpath=tdir,
                        pluginPaths=allPluginsPath)
        nodes.append(node)

    for node in nodes:
        tellKeysToOthers(node, nodes)

    A, B = nodes
    looper.add(A)
    looper.runFor(4)
    logger.debug("wait done")
    looper.add(B)
    looper.runFor(4)
    looper.run(checkNodesConnected([A, B]))
    looper.stopall()
    A.start(looper.loop)
    looper.runFor(4)
    B.start(looper.loop)
    looper.run(checkNodesConnected([A, B]))
    stopNodes([A, B], looper)


def testNodeRemoveUnknownRemote(allPluginsPath, tdirAndLooper, nodeReg, conf):
    """
    The nodes Alpha and Beta know about each other so they should connect but
    they should remove remote for C when it tries to connect to them
    """

    tdir, looper = tdirAndLooper
    names = ["Alpha", "Beta"]
    nrg = {n: nodeReg[n] for n in names}
    initLocalKeys(tdir, nrg)
    logger.debug(names)

    nodes = []
    for name in names:
        node = TestNode(name, nrg, basedirpath=tdir,
                        pluginPaths=allPluginsPath)
        nodes.append(node)

    for node in nodes:
        tellKeysToOthers(node, nodes)

    A, B = nodes
    for node in nodes:
        looper.add(node)
    looper.run(checkNodesConnected(nodes))

    initLocalKeys(tdir, {"Gamma": nodeReg["Gamma"]})
    C = TestNode("Gamma", {**nrg, **{"Gamma": nodeReg["Gamma"]}},
                 basedirpath=tdir, pluginPaths=allPluginsPath)
    for node in nodes:
        tellKeysToOthers(node, [C,])

    looper.add(C)
    looper.runFor(5)

    stopNodes([C, ], looper)

    def chk():
        assert C.name not in B.nodestack.nameRemotes
        assert C.name not in A.nodestack.nameRemotes

    timeout = waits.expectedPoolInterconnectionTime(len(nodeReg))
    looper.run(eventually(chk, retryWait=2, timeout=timeout))
    stopNodes([A, B], looper)
