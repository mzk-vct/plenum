from plenum.persistence.leveldb_hash_store import LevelDbHashStore
from plenum.server.pool_manager import TxnPoolManager
from plenum.test.helper import MockClass
from plenum.common.constants import KeyValueStorageType, DOMAIN_LEDGER_ID
import os.path


def init_ledger(path, file):
    os.makedirs(path, exist_ok=True)
    full_path = os.path.join(path, file)
    with open(full_path, "a+") as file:
        print('{"alias":"MockNode","client_ip":"54.233.109.18",'
              '"client_port":9702,"node_ip":"54.233.109.18",'
              '"node_port":9701,"services":["VALIDATOR"]}', file=file)


def test_get_name_by_rank(tdir_for_func):
    print("XXX", tdir_for_func)
    base_dir_path = tdir_for_func

    data_location = os.path.join(base_dir_path, "data")
    os.makedirs(data_location, exist_ok=True)

    pool_transactions_file = "pool_transactions"
    init_ledger(base_dir_path, pool_transactions_file)

    config = MockClass(
        poolStateStorage=KeyValueStorageType.Memory,  # Does this work?
        poolStateDbName=None,
        poolTransactionsFile=pool_transactions_file,
        EnsureLedgerDurability=False,
    )

    node = MockClass(
        name="MockNode",
        config=config,
        basedirpath=base_dir_path,
        dataLocation=data_location,
        states={DOMAIN_LEDGER_ID: "0"},
        initStateFromLedger=lambda a, b, c: None
    )

    pool_manager = TxnPoolManager(node)
