"""our dev tasks"""

from invoke.tasks import task


@task
def lint(ctx):
    """format and check"""
    ctx.run('ruff format src/', pty=True)
    ctx.run('ruff check src/ --select I --fix', pty=True)


@task
def docs(ctx, view=False):
    """create documentation"""
    ctx.run('pdoc ./src/blueshed/gust -o ./docs', pty=True)
    if view:
        ctx.run('open ./docs/index.html', pty=True)


@task(lint, docs)
def build(ctx):
    """build packages"""
    ctx.run('rm -rf dist')
    ctx.run('python3 -m build --wheel', pty=True)
    ctx.run('python3 -m build --sdist', pty=True)


@task(docs)
def commit(ctx, message):
    """commit to github"""
    ctx.run(f"git add . && git commit -m '{message}'", pty=True)
    ctx.run('git push', pty=True)


@task(lint)
def release(ctx, message, part='patch'):
    """release to pypi"""
    ctx.run(f'bump-my-version bump {part}', pty=True)
    docs(ctx)
    commit(ctx, message)
    build(ctx)
    ctx.run('twine upload dist/*', pty=True)
