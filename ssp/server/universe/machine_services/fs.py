from .. import process

class FsService(process.Process):
    async def send_ipc(self, sender, values):
        return None

factory = FsService
