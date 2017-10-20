
from plenum.common.messages.node_messages import PrePrepare
from plenum.common.util import SortedDict, compare_3PC_keys
from plenum.common.types import f


# SortedDict(lambda k: (k[0], k[1]))
# type: Dict[Tuple[int, int], PrePrepare]
# TODO: make interface for it
class PrePrepares:

    class ErrorCodes:
        CAN_PROCESS = 0
        INVALID_PP_TIME = 1

    def __init__(self):
        by_view_no_and_then_by_seq_no = self._make_pre_prepare_key
        self._pre_prepares = SortedDict(by_view_no_and_then_by_seq_no)

    def register(self, pre_prepare: PrePrepare):
        """
        Registers new PrePrepare
        """
        key = self._make_pre_prepare_key(pre_prepare)
        self._pre_prepares[key] = pre_prepare

    def registered(self, view_no, seq_no) -> bool:
        """
        Checks whether PrePrepare with specified view_no and seq_no
        was registered
        """
        return (view_no, seq_no) in self._pre_prepares

    def get(self, view_no, seq_no):
        return self._pre_prepares.get((view_no, seq_no))

    def unregister_all(self, up_to_view_no, up_to_seq_no):
        # TODO: optimize it
        till_key = up_to_view_no, up_to_seq_no
        unregistered = []
        for key in list(self._pre_prepares.keys()):
            if compare_3PC_keys(till_key, key) <= 0:
                pre_prepare = self._pre_prepares.pop(key)
                unregistered.append((key, pre_prepare))
        return unregistered

    @property
    def latest_received(self):
        """
        Returns registerd PrePrepare and it's key with
        highest view_no and seq_no
        """
        if len(self._pre_prepares) > 0:
            return self._pre_prepares.peekitem(-1)

    @property
    def all_registered_keys(self):
        """
        Returns set of keys of all registered PrePrepares
        """
        return set(self._pre_prepares.keys())

    def can_process_preprepare(self, pre_prepare):
        pass

    @staticmethod
    def _make_pre_prepare_key(pre_prepare):
        seq_no = getattr(pre_prepare, f.PP_SEQ_NO)
        view_no = getattr(pre_prepare, f.VIEW_NO)
        return view_no, seq_no

    def __contains__(self, item):
        assert len(item) == 2
        return self.registered(*item)

    def __getitem__(self, item):
        assert len(item) == 2
        res = self.get(*item)
        if res is None:
            raise ValueError("There is no PrePrepare ({}:{})".format(*item))
        return res

