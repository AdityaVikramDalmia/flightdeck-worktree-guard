import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

CLI = Path(__file__).resolve().parents[1] / "bin" / "worktree-guard"


class WorktreeGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="worktree guard ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "main repo"
        self.lane = self.root / "linked worktree"
        self.env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        self.env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_TERMINAL_PROMPT="0", GIT_AUTHOR_NAME="Example",
                        GIT_AUTHOR_EMAIL="example@example.test", GIT_COMMITTER_NAME="Example",
                        GIT_COMMITTER_EMAIL="example@example.test")
        self.git("init", "-b", "main", str(self.repo), cwd=self.root)
        self.git("config", "core.hooksPath", os.devnull)
        self.git("config", "commit.gpgsign", "false")
        (self.repo / "tracked.txt").write_text("first\n")
        (self.repo / ".gitignore").write_text("cache/\n")
        self.git("add", ".")
        self.git("commit", "-m", "initial")
        self.git("worktree", "add", "-b", "task", str(self.lane))

    def git(self, *args, cwd=None, allowed=(0,)):
        proc = subprocess.run(["git", "-C", str(cwd or self.repo), *args], env=self.env,
                              capture_output=True, check=False)
        if proc.returncode not in allowed:
            self.fail(proc.stderr.decode(errors="replace"))
        return proc.stdout.decode().strip()

    def check(self, operation="remove-check", path=None, *args, env=None):
        proc = subprocess.run([str(CLI), operation, str(path or self.lane), "--json", *args],
                              env=env or self.env, capture_output=True, text=True)
        self.assertNotIn("Traceback", proc.stderr)
        return proc.returncode, json.loads(proc.stdout)

    def codes(self, data):
        return {row["code"] for row in data.get("reasons", [])}

    def commit_lane(self):
        (self.lane / "tracked.txt").write_text("task result\n")
        self.git("add", ".", cwd=self.lane)
        self.git("commit", "-m", "task", cwd=self.lane)

    def test_clean_linked_worktree_at_base_is_ready(self):
        code, data = self.check()
        self.assertEqual(code, 0)
        self.assertEqual(data["status"], "ready")
        self.assertTrue(self.lane.exists())

    def test_unmerged_commit_is_refused_then_merged_is_ready(self):
        self.commit_lane()
        code, data = self.check()
        self.assertEqual(code, 3)
        self.assertIn("unmerged", self.codes(data))
        self.git("merge", "--ff-only", "task")
        self.assertEqual(self.check()[0], 0)

    def test_tracked_unstaged_changes_refused(self):
        (self.lane / "tracked.txt").write_text("not committed")
        code, data = self.check()
        self.assertEqual(code, 3)
        self.assertIn("dirty", self.codes(data))

    def test_staged_changes_refused(self):
        (self.lane / "tracked.txt").write_text("staged")
        self.git("add", ".", cwd=self.lane)
        self.assertIn("dirty", self.codes(self.check()[1]))

    def test_untracked_nested_and_newline_filename_is_preserved(self):
        folder = self.lane / "new dir"
        folder.mkdir()
        (folder / "report\nresult.txt").write_text("important")
        code, data = self.check()
        self.assertEqual(code, 3)
        self.assertIn("new dir/report\nresult.txt", [x["path"] for x in data["changes"]])

    def test_ignored_files_require_explicit_allowance(self):
        (self.lane / "cache").mkdir()
        (self.lane / "cache" / "artifact").write_text("local data")
        self.assertIn("ignored_files", self.codes(self.check()[1]))
        code, data = self.check("remove-check", self.lane, "--allow-ignored")
        self.assertEqual(code, 0)
        self.assertTrue(data["allow_ignored"])

    def test_main_worktree_refused(self):
        code, data = self.check(path=self.repo)
        self.assertEqual(code, 3)
        self.assertIn("main_worktree", self.codes(data))

    def test_subdirectory_refused(self):
        sub = self.lane / "sub"
        sub.mkdir()
        code, data = self.check(path=sub)
        self.assertEqual(code, 3)
        self.assertIn("not_worktree_root", self.codes(data))

    def test_locked_worktree_refused(self):
        self.git("worktree", "lock", "--reason", "active process", str(self.lane))
        code, data = self.check()
        self.assertEqual(code, 3)
        self.assertIn("locked", self.codes(data))

    def test_self_base_refused(self):
        self.commit_lane()
        code, data = self.check("remove-check", self.lane, "--base", "task")
        self.assertEqual(code, 3)
        self.assertIn("self_base", self.codes(data))

    def test_missing_ref_returns_error_not_ready(self):
        self.assertEqual(self.check("remove-check", self.lane, "--base", "missing")[0], 2)

    def test_raw_commit_base_is_not_a_retained_branch(self):
        commit = self.git("rev-parse", "HEAD")
        self.assertEqual(self.check("remove-check", self.lane, "--base", commit)[0], 2)

    def test_detached_merged_worktree_is_supported(self):
        self.git("checkout", "--detach", cwd=self.lane)
        code, data = self.check()
        self.assertEqual(code, 0)
        self.assertIsNone(data["branch"])

    def test_symlink_to_main_is_still_refused(self):
        link = self.root / "alias"
        link.symlink_to(self.repo, target_is_directory=True)
        self.assertIn("main_worktree", self.codes(self.check(path=link)[1]))

    def test_rename_status_is_parsed(self):
        self.git("mv", "tracked.txt", "renamed file.txt", cwd=self.lane)
        code, data = self.check()
        self.assertEqual(code, 3)
        row = next(row for row in data["changes"] if row["code"].startswith("R"))
        self.assertEqual(row["path"], "renamed file.txt")
        self.assertEqual(row["source"], "tracked.txt")

    def test_git_environment_cannot_redirect_inspection(self):
        other = dict(self.env, GIT_DIR=str(self.repo / ".git"), GIT_WORK_TREE=str(self.repo))
        code, data = self.check(env=other)
        self.assertEqual(code, 0)
        self.assertEqual(data["path"], str(self.lane.resolve()))

    def test_active_operation_refused(self):
        path = self.git("rev-parse", "--git-path", "CHERRY_PICK_HEAD", cwd=self.lane)
        Path(path).write_text(self.git("rev-parse", "HEAD") + "\n")
        self.assertIn("operation_in_progress", self.codes(self.check()[1]))

    def test_merge_check_accepts_main_on_base_with_incoming_changes(self):
        self.commit_lane()
        before = self.git("rev-parse", "HEAD")
        code, data = self.check("merge-check", self.repo, "--branch", "task")
        self.assertEqual(code, 0)
        self.assertEqual(data["status"], "ready")
        self.assertEqual(self.git("rev-parse", "HEAD"), before)

    def test_merge_from_linked_tree_refused(self):
        code, data = self.check("merge-check", self.lane, "--branch", "main")
        self.assertEqual(code, 3)
        self.assertIn("linked_worktree", self.codes(data))
        self.assertIn("wrong_branch", self.codes(data))

    def test_merge_into_self_refused(self):
        code, data = self.check("merge-check", self.repo, "--branch", "main")
        self.assertEqual(code, 3)
        self.assertIn("self_merge", self.codes(data))

    def test_already_merged_refused(self):
        code, data = self.check("merge-check", self.repo, "--branch", "task")
        self.assertEqual(code, 3)
        self.assertIn("already_merged", self.codes(data))

    def test_missing_directory_and_non_repo_return_errors(self):
        self.assertEqual(self.check(path=self.root / "missing")[0], 2)
        self.assertEqual(self.check(path=self.root)[0], 2)

    def test_option_like_reference_does_not_execute_git_option(self):
        self.assertEqual(self.check("remove-check", self.lane, "--base=--help")[0], 2)

    def test_assume_unchanged_cannot_hide_tracked_edits(self):
        self.git("update-index", "--assume-unchanged", "tracked.txt", cwd=self.lane)
        (self.lane / "tracked.txt").write_text("important hidden edit")
        code, data = self.check()
        self.assertEqual(code, 3)
        self.assertIn("unchecked_index_entries", self.codes(data))

    def test_skip_worktree_cannot_hide_tracked_edits(self):
        self.git("update-index", "--skip-worktree", "tracked.txt", cwd=self.lane)
        (self.lane / "tracked.txt").write_text("important hidden edit")
        code, data = self.check()
        self.assertEqual(code, 3)
        self.assertIn("unchecked_index_entries", self.codes(data))

    def test_incoming_revision_expression_is_not_a_branch(self):
        self.commit_lane()
        (self.lane / "second.txt").write_text("next")
        self.git("add", ".", cwd=self.lane)
        self.git("commit", "-m", "next", cwd=self.lane)
        for value in ("task~1", "task^{commit}", "task@{0}"):
            with self.subTest(value=value):
                code, data = self.check("merge-check", self.repo, "--branch", value)
                self.assertEqual(code, 2)
                self.assertEqual(data["status"], "error")

    def test_worktree_root_ending_in_newline_is_preserved(self):
        moved = self.root / "linked worktree\n"
        self.git("worktree", "move", str(self.lane), str(moved))
        self.lane = moved
        code, data = self.check()
        self.assertEqual(code, 0, data)
        self.assertEqual(data["path"], str(moved.resolve()))

    def make_submodule(self):
        source = self.root / "module source"
        self.git("init", "-b", "main", str(source), cwd=self.root)
        self.git("config", "commit.gpgsign", "false", cwd=source)
        self.git("config", "core.hooksPath", os.devnull, cwd=source)
        (source / "module.txt").write_text("module contents")
        self.git("add", ".", cwd=source)
        self.git("commit", "-m", "module fixture", cwd=source)
        self.git("-c", "protocol.file.allow=always", "submodule", "add", str(source), "module")
        self.git("commit", "-am", "add submodule")
        self.git("merge", "--ff-only", "main", cwd=self.lane)
        self.git("-c", "protocol.file.allow=always", "submodule", "update", "--init", cwd=self.lane)
        return self.lane / "module"

    def test_initialized_submodule_blocks_removal_even_when_clean(self):
        self.make_submodule()
        code, data = self.check()
        self.assertEqual(code, 3)
        self.assertIn("initialized_submodules", self.codes(data))
        self.assertEqual(data["initialized_submodules"], ["module"])

    def test_dirty_submodule_cannot_be_hidden_by_ignore_config(self):
        module = self.make_submodule()
        (module / "module.txt").write_text("uncommitted module edit")
        self.git("config", "submodule.module.ignore", "all", cwd=self.lane)
        code, data = self.check()
        self.assertEqual(code, 3)
        self.assertIn("dirty", self.codes(data))
        self.assertIn("module", [row["path"] for row in data["changes"]])

    def test_read_only_check_preserves_index_bytes_and_timestamp(self):
        index = Path(self.git("rev-parse", "--git-path", "index", cwd=self.lane))
        before = (index.read_bytes(), index.stat().st_mtime_ns)
        self.assertEqual(self.check()[0], 0)
        self.assertEqual((index.read_bytes(), index.stat().st_mtime_ns), before)

    def split_index_files(self, path):
        gitdir = Path(self.git("rev-parse", "--absolute-git-dir", cwd=path))
        shared = list(gitdir.glob("sharedindex.*"))
        self.assertTrue(shared, "real split-index setup must produce a shared index")
        for file in shared:
            os.utime(file, ns=(1_000_000_000_000_000_000, 1_000_000_000_000_000_000))
        return [gitdir / "index", *shared]

    def assert_index_files_unchanged(self, files, before):
        self.assertEqual({str(path): (path.read_bytes(), path.stat().st_mtime_ns) for path in files}, before)

    def test_active_split_index_remove_check_never_touches_shared_mtimes(self):
        self.git("update-index", "--split-index", cwd=self.lane)
        for setting in ("true", "false"):
            with self.subTest(core_split_index=setting):
                self.git("config", "core.splitIndex", setting, cwd=self.lane)
                files = self.split_index_files(self.lane)
                before = {str(path): (path.read_bytes(), path.stat().st_mtime_ns) for path in files}
                code, result = self.check()
                self.assertEqual(code, 2)
                self.assertEqual(result["status"], "error")
                self.assertIn("split-index", result["error"])
                self.assert_index_files_unchanged(files, before)

    def test_active_split_index_merge_check_never_touches_shared_mtimes(self):
        self.commit_lane()
        self.git("update-index", "--split-index", cwd=self.repo)
        self.git("config", "core.splitIndex", "false", cwd=self.repo)
        files = self.split_index_files(self.repo)
        before = {str(path): (path.read_bytes(), path.stat().st_mtime_ns) for path in files}
        code, result = self.check("merge-check", self.repo, "--branch", "task")
        self.assertEqual(code, 2)
        self.assertIn("split-index", result["error"])
        self.assert_index_files_unchanged(files, before)

    def test_configured_split_index_is_refused_before_artifact_creation(self):
        self.git("config", "core.splitIndex", "true", cwd=self.lane)
        gitdir = Path(self.git("rev-parse", "--absolute-git-dir", cwd=self.lane))
        self.assertEqual(list(gitdir.glob("sharedindex.*")), [])
        index = gitdir / "index"
        before = (index.read_bytes(), index.stat().st_mtime_ns)
        code, result = self.check()
        self.assertEqual(code, 2)
        self.assertIn("split-index", result["error"])
        self.assertEqual((index.read_bytes(), index.stat().st_mtime_ns), before)
        self.assertEqual(list(gitdir.glob("sharedindex.*")), [])

    def test_submodule_split_index_is_detected_before_parent_status(self):
        module = self.make_submodule()
        self.git("update-index", "--split-index", cwd=module)
        self.git("config", "core.splitIndex", "false", cwd=module)
        files = self.split_index_files(module)
        before = {str(path): (path.read_bytes(), path.stat().st_mtime_ns) for path in files}
        code, result = self.check()
        self.assertEqual(code, 2)
        self.assertIn("split-index", result["error"])
        self.assert_index_files_unchanged(files, before)

    def test_nested_submodule_split_index_preserves_shared_mtimes(self):
        module = self.make_submodule()
        self.git("-c", "protocol.file.allow=always", "submodule", "add",
                 str(self.root / "module source"), "nested", cwd=module)
        nested = module / "nested"
        self.git("update-index", "--split-index", cwd=nested)
        self.git("config", "core.splitIndex", "false", cwd=nested)
        files = self.split_index_files(nested)
        before = {str(path): (path.read_bytes(), path.stat().st_mtime_ns) for path in files}
        code, result = self.check()
        self.assertEqual(code, 2)
        self.assertIn("initialized submodule", result["error"])
        self.assertIn("split-index", result["error"])
        self.assert_index_files_unchanged(files, before)

    def test_stale_shared_index_artifacts_are_conservatively_refused(self):
        self.git("update-index", "--split-index", cwd=self.lane)
        self.git("update-index", "--no-split-index", cwd=self.lane)
        self.git("config", "core.splitIndex", "false", cwd=self.lane)
        files = self.split_index_files(self.lane)
        before = {str(path): (path.read_bytes(), path.stat().st_mtime_ns) for path in files}
        code, result = self.check()
        self.assertEqual(code, 2)
        self.assertIn("sharedindex.* artifacts", result["error"])
        self.assert_index_files_unchanged(files, before)

    def test_sequencer_state_blocks_removal(self):
        folder = Path(self.git("rev-parse", "--git-path", "sequencer", cwd=self.lane))
        folder.mkdir()
        (folder / "todo").write_text("pick fixture pending")
        code, data = self.check()
        self.assertEqual(code, 3)
        self.assertIn("operation_in_progress", self.codes(data))

    def test_install_path_with_spaces_runs_independently(self):
        prefix = self.root / "installed tool"
        result = subprocess.run(["make", "install", "PREFIX=" + str(prefix)], cwd=CLI.parents[1],
                                env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        result = subprocess.run([str(prefix / "bin/worktree-guard"), "remove-check", str(self.lane), "--json"],
                                cwd=self.root, env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "ready")

    def orphan_lane_commit(self):
        tree = self.git("rev-parse", "HEAD^{tree}")
        orphan = self.git("commit-tree", tree, "-m", "independent orphan")
        self.git("reset", "--hard", orphan, cwd=self.lane)
        return orphan, tree

    def test_replacement_objects_cannot_fabricate_retained_ancestry(self):
        orphan, tree = self.orphan_lane_commit()
        original = self.git("rev-parse", "main")
        replacement = self.git("commit-tree", tree, "-p", orphan, "-m", "fabricated ancestry")
        self.git("replace", original, replacement)
        # Normal Git sees the replacement's parent, but the guard must inspect real history.
        self.git("merge-base", "--is-ancestor", orphan, "main")
        code, data = self.check()
        self.assertEqual(code, 3)
        self.assertIn("unmerged", self.codes(data))

    def test_legacy_grafts_cannot_fabricate_retained_ancestry(self):
        orphan, _ = self.orphan_lane_commit()
        original = self.git("rev-parse", "main")
        grafts = self.repo / ".git/info/grafts"
        grafts.write_text(original + " " + orphan + "\n")
        code, data = self.check()
        self.assertEqual(code, 2)
        self.assertIn("grafts", data["error"])

    def mock_status(self, payload, exit_code):
        import shutil
        import sys
        actual = shutil.which("git")
        folder = self.root / "git wrapper"
        folder.mkdir()
        wrapper = folder / "git"
        wrapper.write_text("#!" + sys.executable + "\n" +
                           "import os,sys\n" +
                           "if 'status' in sys.argv[1:]:\n" +
                           "    sys.stdout.buffer.write(" + repr(payload) + ")\n" +
                           "    sys.exit(" + repr(exit_code) + ")\n" +
                           "os.execv(" + repr(actual) + ", [" + repr(actual) + "] + sys.argv[1:])\n")
        wrapper.chmod(0o755)
        return dict(self.env, PATH=str(folder) + os.pathsep + self.env["PATH"])

    def test_failed_git_status_is_error_never_ready(self):
        code, data = self.check(env=self.mock_status(b"", 128))
        self.assertEqual(code, 2)
        self.assertEqual(data["status"], "error")

    def test_truncated_git_status_is_error_never_ready(self):
        code, data = self.check("remove-check", self.lane, "--allow-ignored",
                                env=self.mock_status(b"!! incomplete", 0))
        self.assertEqual(code, 2)
        self.assertEqual(data["status"], "error")


if __name__ == "__main__":
    unittest.main()
