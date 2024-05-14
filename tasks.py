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
    ctx.run('pdoc ./src/blueshed/gust -o ./docs', pty=True)

@task
def release(ctx, message, part="patch"):
    ctx.run(f'bump-my-version bump {part}', pty=True)
    build(ctx)
    ctx.run(f"git add . && git commit -m '{message}'", pty=True)
    ctx.run('git push', pty=True)
    ctx.run('twine upload dist/*', pty=True)
