from collections import defaultdict
from .. import process
from .. import idlist


class FsService(process.Process):
    RET_OKAY = 0
    RET_BAD_CMD = 1
    RET_BAD_PARAMS = 2
    RET_BAD_PATH = 3
    RET_ALREADY_OPEN = 4
    RET_BAD_HANDLE = 5

    def __init__(self, machine, pid, ppid):
        super().__init__(machine, pid, ppid)

        self._filesys = FileSystem()
        self._handles = defaultdict(ProcessHandles)

    async def send_ipc(self, sender, values):
        response = None

        handlers = {
            # open filepath -> handle, retcode
            'open': self._open,
            # write handle data -> retcode
            'write': self._write,
            # read handle -> data, retcode
            'read': self._read,
            # close handle -> retcode
            'close': self._close,
        }

        if len(values) > 0:
            cmd = values[0].lower()
        else:
            cmd = None
        args = values[1:]

        handler = handlers.get(cmd, None)
        if handler is not None:
            response = handler(sender, args)
        else:
            response = [FsService.RET_BAD_CMD]
        
        return response

    def _open(self, sender, args):
        response = None

        if len(args) != 2:
            return [-1, FsService.RET_BAD_PARAMS]
            
        filepath = args[0]
        mode = args[1]

        proc_handles = self._handles[sender]
        
        try:
            fs_obj = self._filesys.open(filepath, mode)
            return [proc_handles.new_handle_for(fs_obj), FsService.RET_OKAY]
        except FsBadPath as ex:
            self.logger.debug('fs bad path: {}'.format(ex))
            return [-1, FsService.RET_BAD_PATH]
        except FsAlreadyOpen as ex:
            self.logger.debug('fs already open: {}'.format(ex))
            return [-1, FsService.RET_ALREADY_OPEN]

    def _write(self, sender, args):
        response = None

        if len(args) != 2:
            return [-1, FsService.RET_BAD_PARAMS]

        handle = args[0]
        data = args[1]

        proc_handles = self._handles[sender]

        if not proc_handles.is_valid_handle(handle):
            return [-1, FsService.RET_BAD_HANDLE]
        
        file_obj = proc_handles.lookup(handle)

        try:
            file_obj.write(data)
        except FsBadParam as ex:
            self.logger.debug('fs bad param: {}'.format(ex))
            return FsService.RET_BAD_PARAM

        return FsService.RET_OKAY

    def _read(self, sender, args):
        pass

    def _close(self, sender, args):
        pass


class ProcessHandles(object):

    def __init__(self):
        self._handles = idlist.IdList(use_free_list=True)

    def is_valid_handle(self, handle):
        return handle in self._handles

    def new_handle_for(self, file_obj):
        return self._handles.add(file_obj)

    def lookup(self, handle):
        return self._handles.get(handle)


class FsBadPath(Exception): pass
class FsBadParam(Exception): pass
class FsAlreadyOpen(Exception): pass


class FileSystem(object):

    def __init__(self):
        self._root = Folder('/')
        self._open = set()

    def open(self, filepath, mode):
        if filepath in self._open:
            raise FsAlreadyOpen("{} already open".format(filepath))
        create_file = 'w' == mode
        found = self._lookup(filepath, create_file=create_file)
        if found:
            self._open.add(filepath)
        else:
            raise FsBadPath("{} not a valid path".format(filepath))
        return found

    def _lookup(self, filepath, create_file=False):
        folder = self._root
        parts = filepath.split("/")
        for folder_name in parts[:-1]:
            folder = folder.lookup_folder(folder_name)
            if not folder: return None
        return folder.lookup(parts[-1], create_file=create_file)


class FsEntity(object):

    def __init__(self, name):
        self._name = name

    @property
    def name(self): return self._name

    def read(self): raise Exception("unimplemented")
    def write(self, contents): raise Exception("unimplemented")
    def is_file(self): raise Exception("unimplemented")
    def is_dir(self): raise Exception("unimplemented")


class Folder(FsEntity):
    
    def __init__(self, name):
        super().__init__(name)

        self._subdirs = {}
        self._files = {}

    @property
    def name(self): return self._name

    def read(self):
        return [
            list(self._subdirs.keys()),
            list(self._files.keys())
        ]

    def write(self, data):
        if data not in self._subdirs:
            if not isinstance(data, str):
                raise FsBadParam("folder name must be string, got: '{}'".format(data))
            self._subdirs[data] = Folder(data)

    def is_file(self): return False
    def is_dir(self): return True

    def lookup_folder(self, name):
        return self._subdirs.get(name, None)

    def lookup_file(self, name, create_file=False):
        result = self._files.get(name, None)
        if result is None:
            result = File(name)
        return result

    def lookup(self, name, create_file=False):
        return self.lookup_folder(name) or self.lookup_file(name, create_file)


class File(FsEntity):

    def __init__(self, name, content=None):
        super().__init__(name)

        self._content = content

    def read(self): return self._content
    def write(self, data): self._content = data

    def is_file(self): return True
    def is_dir(self): return False


factory = FsService

