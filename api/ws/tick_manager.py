class TickManager:
    def __init__(self):
        self.running = False

    async def start(self):
        """Tick manager disabled"""
        print("⏳ TickManager DISABLED")
        return

    def stop(self):
        """Зупиняє тікер"""
        self.running = False
        print("⏹️ TickManager STOPPED")


tick_manager = TickManager()