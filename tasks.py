from invoke import task

@task
def lint(ctx):
    """format and check"""
    ctx.run('ruff format', pty=True)
    ctx.run('ruff check --select I --fix', pty=True)


@task(lint)
def build(ctx):
    """ build packages """
    ctx.run('rm -rf dist')
    ctx.run('python3 -m build --wheel', pty=True)
    ctx.run('python3 -m build --sdist', pty=True)

@task
def release(ctx, part="patch"):
    ctx.run(f'bump-my-version bump {part}', pty=True)
    build(ctx)
    ctx.run('twine upload dist/*', pty=True)
