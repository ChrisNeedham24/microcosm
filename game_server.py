from source.networking.event_listener import EventListener
from source.saving.game_save_manager import init_app_data

# The implementation for the multiplayer game server. Ensures that the app data directory exists and listens for events.
init_app_data()
EventListener(is_server=True).run()
