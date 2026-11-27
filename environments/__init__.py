"""Environments: the task a swarm works on.

swarm.py runs the episode: rounds and turn order, the board, token budgets, refusals, both backends,
board seeding (written history, late joiners, injections) and the variants that don't depend on the
task (abort, appeal, leader, safety lead, pull_board, no_board). An environment supplies the rest:
the world, each agent's role, brief and task tools, what those tools do, who has solved, and the
outcome fields of summary.json. A config picks one with `environment = "<name>"` (default "ids").
"""

from importlib import import_module

NAMES = {"ids": "environments.ids:Ids", "registry": "environments.registry:Registry",
         "storage": "environments.storage:Storage", "review": "environments.review:Review"}


def get(cfg):
    """The environment class a config uses."""
    module, cls = NAMES[cfg.get("environment", "ids")].split(":")
    return getattr(import_module(module), cls)


def tool(name, description, *args):
    """A tool whose arguments are all required strings."""
    return {
        "name": name,
        "description": description,
        "input_schema": {
            "type": "object",
            "properties": {arg: {"type": "string"} for arg in args},
            "required": list(args),
            "additionalProperties": False,
        },
        "strict": True,
    }


class Environment:
    """What swarm.py needs from a task. Subclasses set roles (and models, to seat models themselves) in
    __init__, and fields: the names injected posts and past_context notes may use ({item}, {url}, ...)."""

    models = None  # agent -> (model, provider), if the environment seats models itself (mixed swarms)
    fields = {}

    def __init__(self, cfg, ids, rng):
        """Build the world for one episode of agents `ids`; rng is the episode's generator."""
        self.cfg, self.ids = cfg, ids
        self.roles = {i: "agent" for i in ids}

    def attach(self, board, log):
        """The episode's board (a list of (sender, text)) and event logger, for tools that use them."""
        self.board, self.log = board, log

    def brief(self, id):
        """(task, restriction, notes): the task paragraph, a line after the board paragraph, and text
        appended after everything swarm.py adds."""
        raise NotImplementedError

    def tools(self, id):
        """The agent's task tools; swarm.py adds post, read_board, abort and appeal."""
        raise NotImplementedError

    def call(self, id, name, inp, rnd):
        """Run a task tool (arguments already checked) and return its result text."""
        raise NotImplementedError

    def solved(self, id):
        raise NotImplementedError

    def setup(self):
        """Fields for the setup event."""
        return {}

    def summary(self):
        """Outcome fields for summary.json."""
        return {}

    @staticmethod
    def report(summary):
        """Extra text for the one-line episode report, after the API refusals."""
        return ""

    @staticmethod
    def past_secrets(setup):
        """Strings in an earlier episode (its setup event) to replace when it's reused as late joiners."""
        return []

    def secrets(self):
        """This episode's secrets, which replacements must avoid."""
        return []

    @staticmethod
    def fresh_secret(rng):
        raise NotImplementedError
