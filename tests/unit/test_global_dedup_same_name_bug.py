"""
Test for bug: global_dedup should deduplicate files with same name and content.

Bug description:
When using --global-dedup (without --deduplicate), two identical files
with the SAME NAME in different subdirectories are NOT deduplicated.
Instead, one is renamed (e.g., test.md -> test_1.md).

Expected behavior:
With --global-dedup, the second file should be detected as a duplicate
(because the content already exists in the destination) and deleted,
not renamed.

Root cause:
In FileMover.move_files(), the content duplicate check only runs when
`deduplicate=True`, and the global dedup check only runs when
`existing_dest.exists()` is False. When --global-dedup is used without
--deduplicate, and a file with the same name already exists at destination,
neither check runs.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from folder_extractor.core.file_operations import FileMover, FileOperations


class TestGlobalDedupSameNameBug:
    """Test that global_dedup handles files with same name correctly."""

    def test_global_dedup_same_name_identical_content_in_subdirs(self):
        """
        Two identical files with same name in different subdirs
        should be deduplicated when using global_dedup.

        Setup:
        - dest/
        - dest/subdir1/test.md  (content: "Hello World")
        - dest/subdir2/test.md  (content: "Hello World")  <- identical

        Expected after extraction with global_dedup:
        - dest/test.md exists (only one file)
        - content_duplicates = 1 (second file detected as content duplicate)
        - global_duplicates = 0 (global is for different names, same content)
        - name_duplicates = 0 (no renaming)

        Note: Content duplicate = same name + same content
              Global duplicate = different name + same content
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir)

            # Create subdirectories with identical files
            subdir1 = dest / "subdir1"
            subdir2 = dest / "subdir2"
            subdir1.mkdir()
            subdir2.mkdir()

            # Same name, same content - should be deduplicated
            content = "Hello World - identical content"
            file1 = subdir1 / "test.md"
            file2 = subdir2 / "test.md"
            file1.write_text(content)
            file2.write_text(content)

            # Create file operations and mover
            file_ops = FileOperations()
            file_mover = FileMover(file_ops)

            # Execute move with global_dedup=True, deduplicate=False
            # (simulating --global-dedup without --deduplicate)
            (
                moved,
                errors,
                name_duplicates,
                content_duplicates,
                global_duplicates,
                history,
            ) = file_mover.move_files(
                files=[file1, file2],
                destination=dest,
                dry_run=False,
                deduplicate=False,  # Note: deduplicate is False!
                global_dedup=True,
            )

            # Check results
            assert errors == 0, "No errors expected"

            # The second file should be detected as a content duplicate
            # (same name + same content = content duplicate, not global duplicate)
            # Note: global_duplicate is for files with DIFFERENT names but same content
            assert content_duplicates == 1, (
                f"Expected 1 content duplicate, got {content_duplicates}. "
                f"The second identical file (same name + same content) should be "
                f"detected as a content duplicate."
            )

            # Global duplicates are for files with different names but same content
            assert global_duplicates == 0, (
                f"Expected 0 global duplicates, got {global_duplicates}. "
                f"Same name + same content = content duplicate, not global."
            )

            # Only one file should be moved, the other should be deleted
            assert moved == 1, (
                f"Expected 1 file moved, got {moved}. "
                f"The duplicate should be deleted, not moved."
            )

            # No name duplicates (renaming) should occur
            assert name_duplicates == 0, (
                f"Expected 0 name duplicates, got {name_duplicates}. "
                f"Files should be deduplicated by content, not renamed."
            )

            # Verify file system state
            assert (dest / "test.md").exists(), "Original file should exist"
            assert not (dest / "test_1.md").exists(), (
                "Renamed file should NOT exist - "
                "the duplicate should be deleted, not renamed"
            )

    def test_global_dedup_same_name_different_content_in_subdirs(self):
        """
        Two files with same name but DIFFERENT content should both be kept
        (one renamed) when using global_dedup.

        This is the expected behavior - no bug here.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir)

            # Create subdirectories with different files
            subdir1 = dest / "subdir1"
            subdir2 = dest / "subdir2"
            subdir1.mkdir()
            subdir2.mkdir()

            # Same name, different content - should NOT be deduplicated
            file1 = subdir1 / "test.md"
            file2 = subdir2 / "test.md"
            file1.write_text("Content version A")
            file2.write_text("Content version B")

            # Create file operations and mover
            file_ops = FileOperations()
            file_mover = FileMover(file_ops)

            # Execute move with global_dedup
            (
                moved,
                errors,
                name_duplicates,
                content_duplicates,
                global_duplicates,
                history,
            ) = file_mover.move_files(
                files=[file1, file2],
                destination=dest,
                dry_run=False,
                deduplicate=False,
                global_dedup=True,
            )

            # Both files should be kept since content differs
            assert moved == 2, "Both files should be moved"
            assert name_duplicates == 1, "Second file should be renamed"
            assert global_duplicates == 0, "No global duplicates (different content)"

            # Verify both files exist
            assert (dest / "test.md").exists()
            assert (dest / "test_1.md").exists()

    def test_global_dedup_with_deduplicate_flag_works(self):
        """
        When BOTH global_dedup and deduplicate are True, the bug doesn't occur
        because the content duplicate check runs.

        This test verifies the workaround.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir)

            # Create subdirectories with identical files
            subdir1 = dest / "subdir1"
            subdir2 = dest / "subdir2"
            subdir1.mkdir()
            subdir2.mkdir()

            content = "Same content"
            file1 = subdir1 / "test.md"
            file2 = subdir2 / "test.md"
            file1.write_text(content)
            file2.write_text(content)

            file_ops = FileOperations()
            file_mover = FileMover(file_ops)

            # With deduplicate=True, it should work correctly
            (
                moved,
                errors,
                name_duplicates,
                content_duplicates,
                global_duplicates,
                history,
            ) = file_mover.move_files(
                files=[file1, file2],
                destination=dest,
                dry_run=False,
                deduplicate=True,  # This makes it work!
                global_dedup=True,
            )

            # This works because content_duplicate check runs
            assert moved == 1, "Only one file should be moved"
            # Note: it counts as content_duplicate, not global_duplicate
            # because they have the same name
            assert content_duplicates == 1, "Second file is content duplicate"
            assert not (dest / "test_1.md").exists()


class TestGlobalDedupKeepsOriginalNotCopy:
    """Test that global_dedup keeps the original file, not the copy."""

    def test_keeps_shorter_filename_when_same_mtime(self):
        """
        When two identical files have the same mtime, the one with the
        shorter/simpler filename should be kept (assumed to be the original).

        Example:
        - test.md (7 chars) - should be kept
        - test kopie.md (13 chars) - should be deleted

        This handles cases where files are copied with preserved timestamps
        or extracted from archives with identical mtimes.
        """
        import os

        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir)

            subdir = dest / "subdir"
            subdir.mkdir()

            content = "Identical content"

            # Create both files
            original = subdir / "test.md"
            copy = subdir / "test kopie.md"
            original.write_text(content)
            copy.write_text(content)

            # Set SAME mtime for both (simulating archive extraction)
            same_time = 1700000000.0
            os.utime(original, (same_time, same_time))
            os.utime(copy, (same_time, same_time))

            file_ops = FileOperations()
            file_mover = FileMover(file_ops)

            # Pass files in "wrong" order - copy first
            # This tests that sorting handles equal mtimes correctly
            (
                moved,
                errors,
                name_duplicates,
                content_duplicates,
                global_duplicates,
                history,
            ) = file_mover.move_files(
                files=[copy, original],  # Copy listed first!
                destination=dest,
                dry_run=False,
                deduplicate=False,
                global_dedup=True,
            )

            assert errors == 0
            assert moved == 1
            assert global_duplicates == 1

            # The shorter filename (test.md) should be kept
            remaining = list(dest.glob("*.md"))
            assert len(remaining) == 1, f"Expected 1 file, got {remaining}"
            assert remaining[0].name == "test.md", (
                f"Expected 'test.md' to be kept (shorter name = original), "
                f"but got '{remaining[0].name}'"
            )

    def test_keeps_alphabetically_first_when_same_length_and_mtime(self):
        """
        When filenames have same length and same mtime, keep alphabetically first.

        Example:
        - file_a.md - should be kept
        - file_b.md - should be deleted
        """
        import os

        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir)

            subdir = dest / "subdir"
            subdir.mkdir()

            content = "Identical content"

            file_a = subdir / "file_a.md"
            file_b = subdir / "file_b.md"
            file_a.write_text(content)
            file_b.write_text(content)

            # Same mtime
            same_time = 1700000000.0
            os.utime(file_a, (same_time, same_time))
            os.utime(file_b, (same_time, same_time))

            file_ops = FileOperations()
            file_mover = FileMover(file_ops)

            # Pass in "wrong" order
            (
                moved,
                errors,
                name_duplicates,
                content_duplicates,
                global_duplicates,
                history,
            ) = file_mover.move_files(
                files=[file_b, file_a],  # B first, A second
                destination=dest,
                dry_run=False,
                deduplicate=False,
                global_dedup=True,
            )

            assert errors == 0
            assert moved == 1
            assert global_duplicates == 1

            remaining = list(dest.glob("*.md"))
            assert len(remaining) == 1
            assert remaining[0].name == "file_a.md", (
                f"Expected 'file_a.md' (alphabetically first), "
                f"but got '{remaining[0].name}'"
            )

    def test_older_file_still_wins_over_shorter_name(self):
        """
        Modification time is primary criterion. An older file should be kept
        even if it has a longer filename.
        """
        import os

        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir)

            subdir = dest / "subdir"
            subdir.mkdir()

            content = "Identical content"

            # Create with different mtimes - longer name is OLDER
            old_file = subdir / "document_original_version.md"  # Long name but older
            new_file = subdir / "doc.md"  # Short name but newer

            old_file.write_text(content)
            new_file.write_text(content)

            # Set old_file to be older
            old_time = 1600000000.0
            new_time = 1700000000.0
            os.utime(old_file, (old_time, old_time))
            os.utime(new_file, (new_time, new_time))

            file_ops = FileOperations()
            file_mover = FileMover(file_ops)

            (
                moved,
                errors,
                name_duplicates,
                content_duplicates,
                global_duplicates,
                history,
            ) = file_mover.move_files(
                files=[new_file, old_file],
                destination=dest,
                dry_run=False,
                deduplicate=False,
                global_dedup=True,
            )

            assert errors == 0
            assert moved == 1
            assert global_duplicates == 1

            remaining = list(dest.glob("*.md"))
            assert len(remaining) == 1
            # Older file wins, even though it has a longer name
            assert remaining[0].name == "document_original_version.md", (
                f"Expected older file 'document_original_version.md', "
                f"but got '{remaining[0].name}'"
            )


class TestGlobalDedupSameNameBugSorted:
    """Test the bug also exists in move_files_sorted (sort-by-type mode)."""

    def test_global_dedup_sorted_same_name_identical_content(self):
        """
        Same bug in move_files_sorted: identical files with same name
        in different subdirs should be deduplicated.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir)

            # Create subdirectories with identical files
            subdir1 = dest / "subdir1"
            subdir2 = dest / "subdir2"
            subdir1.mkdir()
            subdir2.mkdir()

            content = "Identical markdown content"
            file1 = subdir1 / "readme.md"
            file2 = subdir2 / "readme.md"
            file1.write_text(content)
            file2.write_text(content)

            file_ops = FileOperations()
            file_mover = FileMover(file_ops)

            # Execute sorted move with global_dedup
            (
                moved,
                errors,
                name_duplicates,
                content_duplicates,
                global_duplicates,
                history,
                created_folders,
            ) = file_mover.move_files_sorted(
                files=[file1, file2],
                destination=dest,
                dry_run=False,
                deduplicate=False,
                global_dedup=True,
            )

            assert errors == 0

            # The second file should be detected as a content duplicate
            # (same name + same content = content duplicate, not global duplicate)
            assert content_duplicates == 1, (
                f"Expected 1 content duplicate, got {content_duplicates}"
            )
            assert global_duplicates == 0, (
                f"Expected 0 global duplicates, got {global_duplicates}. "
                f"Same name + same content = content duplicate."
            )
            assert moved == 1, f"Expected 1 moved, got {moved}"
            assert name_duplicates == 0, (
                f"Expected 0 name duplicates, got {name_duplicates}"
            )

            # Check file system - should have MD folder with one file
            md_folder = dest / "MD"
            if md_folder.exists():
                md_files = list(md_folder.glob("*.md"))
                assert len(md_files) == 1, (
                    f"Expected 1 file in MD folder, got {len(md_files)}: {md_files}"
                )
