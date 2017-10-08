from deli_counter.http.app import Application
from deli_counter.http.mounts.root.mount import RootMount

http_app = Application()
http_app.register_mount(RootMount(http_app))
http_app.setup()
application = http_app.wsgi_application
