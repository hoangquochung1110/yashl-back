from invoke.collection import Collection

from provisions import functions

ns = Collection(functions)


# Configurations for run command
ns.configure(
    {
        "run": {
            "pty": True,
            "echo": True,
        },
    },
)
