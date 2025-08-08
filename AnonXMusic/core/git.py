import asyncio
import shlex
from typing import Tuple

from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError
import shutil

import config
from ..logging import LOGGER


def install_req(cmd: str) -> Tuple[str, str, int, int]:
    async def install_requirements():
        args = shlex.split(cmd)
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        return (
            stdout.decode("utf-8", "replace").strip(),
            stderr.decode("utf-8", "replace").strip(),
            process.returncode,
            process.pid,
        )

    return asyncio.get_event_loop().run_until_complete(install_requirements())


def git():
    # Check if git binary exists in this environment
    if not shutil.which("git"):
        LOGGER(__name__).warning("Git binary not found. Skipping Git setup.")
        return

    try:
        repo = Repo()
        LOGGER(__name__).info("Git repository found. Skipping init.")
    except InvalidGitRepositoryError:
        LOGGER(__name__).info("No valid Git repo found, initializing...")
        try:
            repo = Repo.init()
            REPO_LINK = config.UPSTREAM_REPO
            if config.GIT_TOKEN:
                GIT_USERNAME = REPO_LINK.split("com/")[1].split("/")[0]
                TEMP_REPO = REPO_LINK.split("https://")[1]
                UPSTREAM_REPO = f"https://{GIT_USERNAME}:{config.GIT_TOKEN}@{TEMP_REPO}"
            else:
                UPSTREAM_REPO = config.UPSTREAM_REPO

            if "origin" in repo.remotes:
                origin = repo.remote("origin")
            else:
                origin = repo.create_remote("origin", UPSTREAM_REPO)
            origin.fetch()

            repo.create_head(
                config.UPSTREAM_BRANCH,
                origin.refs[config.UPSTREAM_BRANCH],
            )
            repo.heads[config.UPSTREAM_BRANCH].set_tracking_branch(
                origin.refs[config.UPSTREAM_BRANCH]
            )
            repo.heads[config.UPSTREAM_BRANCH].checkout(True)

            try:
                repo.create_remote("origin", config.UPSTREAM_REPO)
            except BaseException:
                pass

            nrs = repo.remote("origin")
            nrs.fetch(config.UPSTREAM_BRANCH)
            try:
                nrs.pull(config.UPSTREAM_BRANCH)
            except GitCommandError:
                repo.git.reset("--hard", "FETCH_HEAD")

            LOGGER(__name__).info("Fetched updates from upstream repository.")
        except Exception as e:
            LOGGER(__name__).error(f"Git init failed: {e}")
    except GitCommandError as e:
        LOGGER(__name__).error(f"Git command error: {e}")
