import rt
from rt import AuthorizationError, APISyntaxError
from hostel.settings import RT_URL, RT_QUEUE, RT_USER, RT_PASS


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Rt(metaclass=Singleton):

    APISyntaxError = APISyntaxError

    class LoginError(Exception):
        pass

    def __init__(self):
        print('Initializing RT...')
        self.tracker = rt.Rt(RT_URL, RT_USER, RT_PASS)
        self.login()

    def login(self):
        for i in range(1, 4):
            if self.tracker.login():
                return
        raise self.LoginError('Unable to login RT after 3 attempts')

    def create_ticket(self, **kwargs):
        if not kwargs.get('Queue'):
            kwargs['Queue'] = RT_QUEUE
        return self.action_with_relogin(self.tracker.create_ticket, **kwargs)

    def edit_ticket(self, ticket_id, **kwargs):
        self.action_with_relogin(self.tracker.edit_ticket, ticket_id, **kwargs)

    def reply(self, ticket_id, **kwargs):
        self.action_with_relogin(self.tracker.reply, ticket_id, **kwargs)

    def comment(self, ticket_id, **kwargs):
        self.action_with_relogin(self.tracker.comment, ticket_id, **kwargs)

    def edit_link(self, ticket_id, link_type, parent_id):
        self.action_with_relogin(self.tracker.edit_link, ticket_id, link_type, parent_id)

    def action_with_relogin(self, action, *args, **kwargs):
        try:
            return action(*args, **kwargs)
        except AuthorizationError:
            self.login()
        return action(*args, **kwargs)
