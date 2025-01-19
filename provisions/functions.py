import invoke
from . import printer
from decouple import Config, RepositoryEnv

functions = (
    "key",
    "create_direct_document",
)

BASE_FUNCTION_PATH = "./src/yashl_back/functions/"

@invoke.task
def update_env_vars(context, function_name, path_to_env):
    """
    A wrapper of aws lambda update-function-configuration.
    """
    config = Config(RepositoryEnv(path_to_env))
    env_vars = {} # read from config
    with open(path_to_env) as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                key, _ = line.strip().split('=', 1)
                env_vars[key] = config(key)
    env_vars_str = ','.join(f"{key}={value}" for key, value in env_vars.items())

    environment = "".join([
        "Variables={",
        env_vars_str,
        "}",
    ])
    command = (
        'aws lambda update-function-configuration '
        f'--function-name {function_name} '
        f'--environment "{environment}"'
    )
    printer.info(f"Running: {command}")
    invoke.run(command)


@invoke.task
def update_code(context, function_name):
    """
    A wrapper of aws lambda update-function-code.
    """
    path_to_function = f"{BASE_FUNCTION_PATH}{function_name}"  # use pathlib instead

    if function_name == "captureScreenshot":
        raise NotImplementedError("Not implemented yet")

    with context.cd(path_to_function):
        zip_cmd = f"zip -r {function_name}.zip {function_name}.py"
        printer.info(f"Zipping function: {zip_cmd}")
        context.run(zip_cmd)
        update_code_cmd = (
            'aws lambda update-function-code '
            f'--function-name {function_name} '
            f'--zip-file fileb://{function_name}.zip'
        )
        printer.info("Updating code: {update_code_cmd}")
        context.run(update_code_cmd)
        context.run(f"rm {function_name}.zip")
