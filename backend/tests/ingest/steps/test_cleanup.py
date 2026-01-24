import pytest
import shutil
from pathlib import Path
from unittest.mock import patch
from app.ingest.steps.cleanup import CleanupStep
from app.ingest.pipeline import PipelineContext


@pytest.fixture
def mock_context(tmp_path):
    """Create a mock pipeline context."""
    return PipelineContext(run_id="test_run", base_dir=tmp_path)


def test_cleanup_step_name():
    """Test that the step has the correct name."""
    step = CleanupStep("test_key")
    assert step.name == "Cleanup"


def test_cleanup_step_initialization():
    """Test CleanupStep initialization with target_key."""
    step = CleanupStep("my_target")
    assert step.target_key == "my_target"


def test_cleanup_step_delete_file(mock_context, tmp_path):
    """Test deletion of a file."""
    # Create a test file
    test_file = tmp_path / "test_file.txt"
    test_file.write_text("test content")
    
    mock_context.state["file_to_delete"] = test_file
    
    step = CleanupStep("file_to_delete")
    step.run(mock_context)
    
    # Verify file was deleted
    assert not test_file.exists()


def test_cleanup_step_delete_directory(mock_context, tmp_path):
    """Test deletion of a directory."""
    # Create a test directory with files
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    (test_dir / "file1.txt").write_text("content1")
    (test_dir / "file2.txt").write_text("content2")
    (test_dir / "subdir").mkdir()
    (test_dir / "subdir" / "file3.txt").write_text("content3")
    
    mock_context.state["dir_to_delete"] = test_dir
    
    step = CleanupStep("dir_to_delete")
    step.run(mock_context)
    
    # Verify directory and all contents were deleted
    assert not test_dir.exists()


def test_cleanup_step_key_not_in_state(mock_context):
    """Test when target key is not in context state."""
    step = CleanupStep("nonexistent_key")
    step.run(mock_context)
    
    # Should not raise an error, just do nothing


def test_cleanup_step_path_not_path_object(mock_context):
    """Test when state value is not a Path object."""
    mock_context.state["not_a_path"] = "just a string"
    
    step = CleanupStep("not_a_path")
    step.run(mock_context)
    
    # Should not raise an error, just do nothing


def test_cleanup_step_path_does_not_exist(mock_context, tmp_path):
    """Test when path doesn't exist."""
    non_existent_path = tmp_path / "does_not_exist.txt"
    mock_context.state["missing_path"] = non_existent_path
    
    step = CleanupStep("missing_path")
    step.run(mock_context)
    
    # Should not raise an error


def test_cleanup_step_none_value(mock_context):
    """Test when state value is None."""
    mock_context.state["none_value"] = None
    
    step = CleanupStep("none_value")
    step.run(mock_context)
    
    # Should not raise an error


def test_cleanup_step_empty_directory(mock_context, tmp_path):
    """Test deletion of an empty directory."""
    empty_dir = tmp_path / "empty_dir"
    empty_dir.mkdir()
    
    mock_context.state["empty_dir"] = empty_dir
    
    step = CleanupStep("empty_dir")
    step.run(mock_context)
    
    # Verify directory was deleted
    assert not empty_dir.exists()


def test_cleanup_step_nested_directories(mock_context, tmp_path):
    """Test deletion of deeply nested directories."""
    nested_dir = tmp_path / "level1" / "level2" / "level3"
    nested_dir.mkdir(parents=True)
    (nested_dir / "file.txt").write_text("content")
    
    root_dir = tmp_path / "level1"
    mock_context.state["nested"] = root_dir
    
    step = CleanupStep("nested")
    step.run(mock_context)
    
    # Verify entire tree was deleted
    assert not root_dir.exists()


def test_cleanup_step_symlink_file(mock_context, tmp_path):
    """Test deletion of a symlink to a file."""
    # Create a real file and a symlink to it
    real_file = tmp_path / "real_file.txt"
    real_file.write_text("content")
    
    symlink = tmp_path / "symlink.txt"
    symlink.symlink_to(real_file)
    
    mock_context.state["symlink"] = symlink
    
    step = CleanupStep("symlink")
    step.run(mock_context)
    
    # Verify symlink was deleted but real file remains
    assert not symlink.exists()
    assert real_file.exists()


def test_cleanup_step_multiple_files_same_step(mock_context, tmp_path):
    """Test that CleanupStep only deletes the specified target."""
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"
    file1.write_text("content1")
    file2.write_text("content2")
    
    mock_context.state["file1"] = file1
    mock_context.state["file2"] = file2
    
    step = CleanupStep("file1")
    step.run(mock_context)
    
    # Only file1 should be deleted
    assert not file1.exists()
    assert file2.exists()


def test_cleanup_step_file_with_special_characters(mock_context, tmp_path):
    """Test deletion of file with special characters in name."""
    special_file = tmp_path / "file with spaces & special!chars.txt"
    special_file.write_text("content")
    
    mock_context.state["special"] = special_file
    
    step = CleanupStep("special")
    step.run(mock_context)
    
    assert not special_file.exists()


def test_cleanup_step_readonly_file(mock_context, tmp_path):
    """Test deletion of a read-only file."""
    readonly_file = tmp_path / "readonly.txt"
    readonly_file.write_text("content")
    readonly_file.chmod(0o444)  # Make read-only
    
    mock_context.state["readonly"] = readonly_file
    
    step = CleanupStep("readonly")
    step.run(mock_context)
    
    # Should still be deleted (unlink doesn't care about permissions)
    assert not readonly_file.exists()


def test_cleanup_step_large_directory(mock_context, tmp_path):
    """Test deletion of directory with many files."""
    large_dir = tmp_path / "large_dir"
    large_dir.mkdir()
    
    # Create 100 files
    for i in range(100):
        (large_dir / f"file_{i}.txt").write_text(f"content {i}")
    
    mock_context.state["large"] = large_dir
    
    step = CleanupStep("large")
    step.run(mock_context)
    
    assert not large_dir.exists()


def test_cleanup_step_integer_value(mock_context):
    """Test when state value is an integer."""
    mock_context.state["int_value"] = 42
    
    step = CleanupStep("int_value")
    step.run(mock_context)
    
    # Should not raise an error


def test_cleanup_step_list_value(mock_context):
    """Test when state value is a list."""
    mock_context.state["list_value"] = [1, 2, 3]
    
    step = CleanupStep("list_value")
    step.run(mock_context)
    
    # Should not raise an error


def test_cleanup_step_dict_value(mock_context):
    """Test when state value is a dict."""
    mock_context.state["dict_value"] = {"key": "value"}
    
    step = CleanupStep("dict_value")
    step.run(mock_context)
    
    # Should not raise an error
