from .. import process

class SysService(process.Process):
    async def send_ipc(self, sender, values):
        return None

factory = SysService
