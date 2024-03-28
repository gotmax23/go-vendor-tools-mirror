# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

from __future__ import annotations

import contextlib
import os
import shlex
from collections.abc import Iterator
from glob import iglob
from pathlib import Path
from tempfile import TemporaryDirectory
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
LINT_FILES = (f"src/{PROJECT}", "tests/pytests", "noxfile.py")
INTEGRATION_PACKAGES = ("autorestic", "fzf")
COVERAGE_FAIL_UNDER = os.environ.get("COVERAGE_FAIL_UNDER") or "85"

nox.options.sessions = ("lint", "covtest")


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
    session.run("pytest", "src", "tests/pytests", *session.posargs, env=env)


@nox.session
def integration(session: nox.Session) -> None:
    install(session, ".", "coverage[toml]", "fclogr", editable=True)
    packages_env = session.env.get("PACKAGES")
    packages = shlex.split(packages_env) if packages_env else INTEGRATION_PACKAGES
    with (
        coverage_run(session) as cov_env,
        # askalono does not like that the temporary directory is in the
        # gitignore'd .nox/ directory
        TemporaryDirectory(dir=os.environ.get("TMPDIR")) as tmp,
    ):
        cov_env["TMPDIR"] = str(tmp)
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


@nox.session(name="integration-test-build")
def integration_test_build(session: nox.Session):
    install(session, ".", "coverage[toml]", editable=True)
    with coverage_run(session) as cov_env:
        coverage_command = shlex.join(COVERAGE_COMMANDS.go_vendor_license)
        assert coverage_command[0]
        rpm_eval = Path("rpmeval.sh").resolve()
        with session.chdir("tests/integration/fzf"):
            # fmt: off
            session.run(
                "bash",
                "-x",
                str(rpm_eval),
                "-D", f"__go_vendor_license {coverage_command}",
                "-D", f"_specdir {Path.cwd()}",
                "-D", f"_sourcedir {Path.cwd()}",
                "--nodeps",
                "-ba", "fzf.spec",
                env=cov_env|{"RPM": "rpmbuild"},
            )
            # fmt: on


@nox.session
def coverage(session: nox.Session):
    install(session, "coverage[toml]")
    session.run("coverage", "combine", "--keep", *iglob(".nox/*/tmp/.coverage"))
    session.run("coverage", "xml")
    session.run("coverage", "html")
    session.run("coverage", "report", "--fail-under", COVERAGE_FAIL_UNDER)


@nox.session()
def covtest(session: nox.Session):
    session.run("rm", "-f", *iglob(".nox/*/tmp/.coverage*"), external=True)
    test_sessions = (f"test-{v}" for v in test.python)  # type: ignore[attr-defined]
    for target in test_sessions:
        session.notify(target, ["--cov"])


@nox.session(name="all")
def all_(session: nox.Session):
    lint(session)
    covtest(session)
    session.notify("integration")
    session.notify("integration-test-build")
    session.notify("coverage")


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
    session.run("ruff", "check", *session.posargs, *LINT_FILES)
    session.run("shellcheck", *iglob("contrib/*.sh"))
    session.run(
        "pymarkdownlnt", "scan", *iglob("*.md"), *iglob("docs/**/*.md", recursive=True)
    )
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

    install(session, "build", "releaserr >= 0.1.dev123", "fclogr")
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
    # FIXME(anyone): Temporarily disable twine check.
    # It doesn't understand hatch 2.3 metadata.
    session.run(
        "releaserr", "build", "--backend", "generic", "--isolated", "--no-twine-check"
    )


@nox.session
def publish(session: nox.Session):
    # Setup
    install(session, "twine", "releaserr")
    session.run("releaserr", "--version")

    session.run("releaserr", "ensure-clean")

    # Upload to PyPI
    session.run("releaserr", "upload")

    # Post-release bump
    session.run("releaserr", "post-version", "-s", "file")
    git(session, "add", f"src/{PROJECT}/__init__.py")
    git(session, "commit", "-S", "-m", "Post-release version bump")


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


@nox.session
def releaserr(session: nox.Session):
    session.install("releaserr")
    session.run("releaserr", *session.posargs)


@nox.session
def mkdocs(session: nox.Session) -> None:
    install(session, "-r", "docs-requirements.txt")
    session.run("mkdocs", *(session.posargs if session.posargs else ["build"]))
