import gc
import sys

from types import ModuleType, FunctionType, FrameType
import time
import os.path

_black_listed_types = [type(None), ModuleType, FunctionType, type, FrameType]
_default_threshold = 50000  # bytes


def get_objects_sizes(treshold=None, sort=True):
    """
    Returns sizes of all objects in memory.

    :param treshold: min size
    :param sort: sort results (in descending order)

    top_items, items_size, total_size


    :return: Tuple of
    1. (size of objects, its name or some index, type, object itself)
    2. size of collected object
    3. size of all object
    """

    if treshold is None:
        treshold = _default_threshold
    if treshold < 0:
        treshold = 0
    all_objects = _get_objects()
    items = []
    tracked_objects = set()
    total_size = 0
    for name, obj in all_objects:
        if id(obj) in tracked_objects:
            continue
        obj_size = sys.getsizeof(obj)
        total_size += obj_size
        obj_id = id(obj)
        if type(obj) in _black_listed_types:
            continue
        tracked_objects.add(obj_id)
        items.append((obj_size, name, obj_id, type(obj), obj))
    if treshold == 0:
        top_items = items
        items_size = total_size
    else:
        top_items = [item for item in items if item[0] > treshold]
        items_size = sum(item[0] for item in top_items)
    if sort:
        top_items.sort(key=lambda x: x[0], reverse=True)
    return top_items, items_size, total_size


def print_size_of_all(file=sys.stdout):
    items, items_size, total_size = get_objects_sizes()
    print("SIZES OF TOP {} OBJECTS ({} bytes, {}%)"
          .format(len(items),
                  items_size,
                  (items_size / total_size) * 100),
          file=file)
    print("SIZE | NAME | ID | OBJECT ", file=file)
    known = set()
    known.add(id(known))
    for item in items:
        known.add(id(item))
    known.add(id(items))
    for item in items:
        obj = item[-1]
        item = item[:-1]
        print("#", item, file=file)
        referers = _get_referrers(obj, known, level=2)
        _print_referrers(referers, "---|", file=file)


def print_size_of_all_to_some_file(path_to_dir=os.path.curdir):
    file_name = "{}.md".format(int(time.time() * 100))
    file_path = os.path.join(path_to_dir, file_name)
    with open(file_path, "w+") as f:
        print_size_of_all(f)
    return file_name


def _get_objects():
    # return globals().items()
    return enumerate(gc.get_objects())  # index instead of name


def _get_referrers(obj, known: set, level=1):
    if level == 0:
        return []
    referers = []
    for ref in gc.get_referrers(obj):
        if id(ref) in known:
            continue
        known.add(id(ref))
        if type(ref) not in _black_listed_types:
            ref_ref = _get_referrers(ref, known, level - 1)
            referers.append((ref, ref_ref))
    return referers


def _print_referrers(referrers, prefix="*", file=sys.stdout):
    for item in referrers:
        (ref, ref_refs) = item
        ref_type = type(ref)
        try:
            ref_str = str(ref)
            if len(ref_str) > 500:
                ref_str = ref_str[:500] + "..."
            print(" ", prefix, ref_type, " => ", ref_str, file=file)
        except TypeError:
            print(" ", prefix, "TypeError on str of ", ref_type, file=file)
        _print_referrers(ref_refs, prefix=prefix * 2, file=file)
