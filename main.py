# -*- coding:utf-8 -*-

import click

from core import create_ctx
from core.banner import banner


@click.command()
@click.option("--env", default="PRODUCTION", type=str)
@click.option("--config", required=False, type=str)
def main(env, config):
    ctx = create_ctx(config_path=config, config_env=env)
    click.secho(banner % ctx.version, fg="blue")
    ctx.run()


if __name__ == '__main__':
    main()
