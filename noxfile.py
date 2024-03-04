# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

from __future__ import annotations

import contextlib
import os
import shlex
from collections.abc import Iterator
from glob import iglob
from pathlib import Path
from types import SimpleNamespace

import nox

IN_CI = "JOB_ID" in os.environ or "CI" in os.environ
ALLOW_EDITABLE = os.environ.get("ALLOW_EDITABLE", str(not IN_CI)).lower() in (
    "1",
    "true",
)

PROJECT = "go_vendor_tools"
SPECFILE = "go-vendor-tools.spec"
LINT_SESSIONS = ("formatters", "codeqa", "typing")
LINT_FILES = (f"src/{PROJECT}", "tests/", "noxfile.py")
INTEGRATION_PACKAGES = ("autorestic", "fzf")

nox.options.sessions = (*LINT_SESSIONS, "test")


# Helpers


def install(session: nox.Session, *args, editable=False, **kwargs):
    if editable and ALLOW_EDITABLE:
        args = ("-e", *args)
    session.install(*args, **kwargs)


def git(session: nox.Session, *args, **kwargs):
    return session.run("git", *args, **kwargs, external=True)


BASE_COVERAGE_COMMAND = ("coverage", "run", "-p", "--source", "go_vendor_tools")
COVERAGE_COMMANDS = SimpleNamespace(
    go_vendor_archive=(
        *BASE_COVERAGE_COMMAND,
        "-m",
        "go_vendor_tools.cli.go_vendor_archive",
    ),
    go_vendor_license=(
        *BASE_COVERAGE_COMMAND,
        "-m",
        "go_vendor_tools.cli.go_vendor_license",
    ),
)


@contextlib.contextmanager
def coverage_run(session: nox.Session) -> Iterator[dict[str, str]]:
    tmp = Path(session.create_tmp())
    covfile = (tmp / ".coverage").resolve()
    cov_env = {
        "COVERAGE_FILE": str(covfile),
        "GO_VENDOR_ARCHIVE": shlex.join(COVERAGE_COMMANDS.go_vendor_archive),
        "GO_VENDOR_LICENSE": shlex.join(COVERAGE_COMMANDS.go_vendor_license),
        **session.env,
    }
    yield cov_env
    combined = map(str, tmp.glob(".coverage.*"))
    session.run("coverage", "combine", *combined, env=cov_env)


# General


@nox.session(python=["3.9", "3.10", "3.11", "3.12"])
def test(session: nox.Session):
    packages: list[str] = [".[test]"]
    env: dict[str, str] = {}
    tmp = Path(session.create_tmp())

    if any(i.startswith("--cov") for i in session.posargs):
        packages.extend(("coverage[toml]", "pytest-cov"))
        env["COVERAGE_FILE"] = str(tmp / ".coverage")

    install(session, *packages, editable=True)
    session.run("pytest", *session.posargs, env=env)


@nox.session
def integration(session: nox.Session) -> None:
    install(session, ".", "coverage[toml]", "fclogr")
    packages_env = session.env.get("PACKAGES")
    packages = shlex.split(packages_env) if packages_env else INTEGRATION_PACKAGES
    with coverage_run(session) as cov_env:
        for package in packages:
            with session.chdir(Path("tests/integration", package)):
                for script in ("integration-archive", "verify-license"):
                    session.run(
                        "bash",
                        "-x",
                        f"../../../contrib/{script}.sh",
                        env=cov_env,
                        external=True,
                    )


@nox.session
def coverage(session: nox.Session):
    install(session, "coverage[toml]")
    session.run("coverage", "combine", "--keep", *iglob(".nox/*/tmp/.coverage"))
    session.run("coverage", "xml")
    session.run("coverage", "html")
    session.run("coverage", "report")


@nox.session(venv_backend="none")
def lint(session: nox.Session):
    """
    Run formatters, codeqa, and typing sessions
    """
    for notify in LINT_SESSIONS:
        session.notify(notify)


@nox.session
def codeqa(session: nox.Session):
    install(session, ".[codeqa]")
    session.run("ruff", *session.posargs, *LINT_FILES)
    session.run("reuse", "lint")


@nox.session
def formatters(session: nox.Session):
    install(session, ".[formatters]")
    posargs = session.posargs
    if IN_CI:
        posargs.append("--check")
    session.run("black", *posargs, *LINT_FILES)
    session.run("isort", *posargs, *LINT_FILES)


@nox.session
def typing(session: nox.Session):
    install(session, ".[typing]", editable=True)
    session.run("mypy", *LINT_FILES)


@nox.session
def bump(session: nox.Session):
    version = session.posargs[0]

    install(session, "releaserr", "fclogr")
    session.run("releaserr", "--version")

    session.run("releaserr", "check-tag", version)
    session.run("releaserr", "ensure-clean")
    session.run("releaserr", "set-version", "-s", "file", version)

    install(session, ".")

    # Bump specfile
    # fmt: off
    session.run(
        "fclogr", "bump",
        "--new", version,
        "--comment", f"Release {version}.",
        SPECFILE,
    )
    # fmt: on

    # Bump changelog, commit, and tag
    git(session, "add", SPECFILE, f"src/{PROJECT}/__init__.py")
    session.run("releaserr", "clog", version, "--tag")
    session.run("releaserr", "build", "--backend", "generic", "--isolated")


@nox.session
def publish(session: nox.Session):
    # Setup
    install(session, "releaserr")
    session.run("releaserr", "--version")

    session.run("releaserr", "ensure-clean")

    # Upload to PyPI
    session.run("releaserr", "upload")

    # Push to git, publish artifacts to sourcehut, and release to copr
    if not session.interactive or input(
        "Push to forge and copr build (Y/n)"
    ).lower() in ("", "y"):
        git(session, "push", "--follow-tags")
        copr_release(session)

    # Post-release bump
    session.run("releaserr", "post-version", "-s", "file")
    git(session, "add", f"src/{PROJECT}/__init__.py")
    git(session, "commit", "-S", "-m", "Post release version bump")


@nox.session
def copr_release(session: nox.Session):
    install(session, "copr-cli", "requests-gssapi")
    session.run(
        "copr-cli", "build", "--nowait", f"gotmax23/{PROJECT}", f"{PROJECT}.spec"
    )


@nox.session
def srpm(session: nox.Session, posargs=None):
    install(session, "fclogr")
    posargs = posargs or session.posargs
    session.run("fclogr", "--debug", "dev-srpm", *posargs, SPECFILE)


@nox.session
def mockbuild(session: nox.Session):
    tmp = Path(session.create_tmp())
    srpm(session, ("-o", tmp, "--keep"))
    margs = [
        "mock",
        "--spec",
        str(Path(tmp, SPECFILE)),
        "--source",
        str(tmp),
        *session.posargs,
    ]
    if not session.interactive:
        margs.append("--verbose")
    session.run(*margs, external=True)


def releaserr(session: nox.Session):
    session.install("releaserr")
    session.run("releaserr", *session.posargs)
