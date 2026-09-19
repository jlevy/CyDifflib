from __future__ import annotations

import difflib
import os
import re
import sys
import sysconfig
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor

import cydifflib

_PREFIX_RE = re.compile(r"(from|to)\d+_")


def _worker_count() -> int:
    cpus = os.cpu_count() or 4
    return min(32, max(8, cpus * 2))


def _threading_supported() -> bool:
    if sys.platform == "emscripten":
        return False
    try:
        done = threading.Event()
        thread = threading.Thread(target=done.set)
        thread.start()
        thread.join()
        return done.is_set()
    except RuntimeError:
        return False


def _snapshot(isjunk, a, b):
    sm = difflib.SequenceMatcher(isjunk, a, b)
    return (
        sm.ratio(),
        sm.quick_ratio(),
        sm.real_quick_ratio(),
        sm.get_opcodes(),
        sm.get_matching_blocks(),
        sm.find_longest_match(),
    )


def _assert_snapshot(isjunk, a, b, expected) -> None:
    sm = cydifflib.SequenceMatcher(isjunk, a, b)
    assert sm.ratio() == expected[0]
    assert sm.quick_ratio() == expected[1]
    assert sm.real_quick_ratio() == expected[2]
    assert sm.get_opcodes() == expected[3]
    assert sm.get_matching_blocks() == expected[4]
    assert sm.find_longest_match() == expected[5]


def _normalize_prefixes(html: str) -> str:
    return _PREFIX_RE.sub(r"\1N_", html)


class TestConcurrency(unittest.TestCase):
    """Separate instances may run in parallel; one instance is not shared."""

    def setUp(self):
        with cydifflib.HtmlDiff._prefix_lock:
            self._saved_prefix = cydifflib.HtmlDiff._default_prefix

        def restore():
            with cydifflib.HtmlDiff._prefix_lock:
                cydifflib.HtmlDiff._default_prefix = self._saved_prefix

        self.addCleanup(restore)

    def test_gil_stays_disabled(self):
        if not hasattr(sys, "_is_gil_enabled"):
            self.skipTest("sys._is_gil_enabled is unavailable")
        if not sysconfig.get_config_var("Py_GIL_DISABLED"):
            self.skipTest("not a free-threaded build")
        self.assertFalse(sys._is_gil_enabled())

    def test_high_concurrency_matches_stdlib(self):
        if not _threading_supported():
            self.skipTest("interpreter cannot start threads")
        cases = [
            (None, "", ""),
            (None, "a", "a"),
            (None, "a", "b"),
            (None, "abcd" * 20, "abce" * 20),
            (None, "hello world", "hallo w0rld"),
            (None, list("abcabc"), list("abcbac")),
            (None, "café naïve", "cafe naive"),
            (None, "dabcd", "d" * 100 + "abc" + "d" * 100),
            (lambda x: x == " ", "a" * 40 + " " + "b" * 40, "a" * 44 + "b" * 40 + " " * 20),
        ]
        words = ["apple", "apply", "applet", "banana", "bandana", "orange"]
        expected = [_snapshot(isjunk, a, b) for isjunk, a, b in cases]
        expected_close = difflib.get_close_matches("appel", words, n=3, cutoff=0.6)

        workers = _worker_count()
        start = threading.Barrier(workers)

        def worker() -> None:
            start.wait()
            plain = cydifflib.SequenceMatcher()
            junked = cydifflib.SequenceMatcher(lambda x: x == " ")
            for _ in range(20):
                for (isjunk, a, b), gold in zip(cases, expected):
                    _assert_snapshot(isjunk, a, b, gold)
                    reused = junked if isjunk else plain
                    reused.set_seqs(a, b)
                    assert reused.get_opcodes() == gold[3]
                assert cydifflib.get_close_matches("appel", words, n=3, cutoff=0.6) == expected_close
            if hasattr(sys, "_is_gil_enabled") and sysconfig.get_config_var("Py_GIL_DISABLED"):
                assert sys._is_gil_enabled() is False

        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(worker) for _ in range(workers)]
            for future in futures:
                future.result()
        self.assertLess(time.perf_counter() - t0, 30.0)

    def test_concurrent_html_prefixes_are_unique(self):
        if not _threading_supported():
            self.skipTest("interpreter cannot start threads")
        fromlines = ["alpha", "beta gamma", "delta"]
        tolines = ["alpha", "beta gammma", "epsilon"]
        gold = _normalize_prefixes(cydifflib.HtmlDiff().make_table(fromlines, tolines))

        workers = _worker_count()
        start = threading.Barrier(workers)
        htmls: list[str] = []
        lock = threading.Lock()

        def worker() -> None:
            start.wait()
            html = cydifflib.HtmlDiff().make_table(fromlines, tolines)
            with lock:
                htmls.append(html)

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(worker) for _ in range(workers)]
            for future in futures:
                future.result()

        ids = []
        for html in htmls:
            self.assertEqual(_normalize_prefixes(html), gold)
            found = set(re.findall(r"(?:from|to)(\d+)_", html))
            self.assertEqual(len(found), 1)
            ids.append(found.pop())
        self.assertEqual(len(ids), workers)
        self.assertEqual(len(set(ids)), workers)
