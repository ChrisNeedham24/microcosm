from source.networking.event_listener import EventListener
from source.saving.game_save_manager import init_app_data

init_app_data()
EventListener(is_server=True).run()
