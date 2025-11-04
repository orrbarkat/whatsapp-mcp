import os
import subprocess
from unittest.mock import MagicMock, patch

import pytest
from audio import convert_to_opus_ogg, convert_to_opus_ogg_temp


@patch("subprocess.run")
@patch("os.path.isfile")
def test_convert_to_opus_ogg_success(mock_isfile, mock_subprocess_run):
    mock_isfile.return_value = True
    mock_subprocess_run.return_value = MagicMock(
        stdout="", stderr="", returncode=0, check_returncode=lambda: None
    )

    input_file = "test.mp3"
    output_file = "test.ogg"
    result = convert_to_opus_ogg(input_file, output_file)

    assert result == output_file
    mock_subprocess_run.assert_called_once()
    args, _ = mock_subprocess_run.call_args
    assert "ffmpeg" in args[0]
    assert input_file in args[0]
    assert output_file in args[0]


@patch("os.path.isfile")
def test_convert_to_opus_ogg_input_not_found(mock_isfile):
    mock_isfile.return_value = False
    with pytest.raises(FileNotFoundError):
        convert_to_opus_ogg("nonexistent.mp3", "output.ogg")


@patch("subprocess.run")
@patch("os.path.isfile")
def test_convert_to_opus_ogg_ffmpeg_fails(mock_isfile, mock_subprocess_run):
    mock_isfile.return_value = True
    mock_subprocess_run.side_effect = subprocess.CalledProcessError(
        1, "ffmpeg", stderr="ffmpeg error"
    )

    with pytest.raises(RuntimeError) as excinfo:
        convert_to_opus_ogg("test.mp3", "test.ogg")
    assert "Failed to convert audio" in str(excinfo.value)


@patch("tempfile.NamedTemporaryFile")
@patch("audio.convert_to_opus_ogg")
def test_convert_to_opus_ogg_temp_success(mock_convert, mock_tempfile):
    mock_temp_file = MagicMock()
    mock_temp_file.name = "temp.ogg"
    mock_tempfile.return_value = mock_temp_file

    input_file = "test.mp3"
    result = convert_to_opus_ogg_temp(input_file)

    assert result == "temp.ogg"
    mock_convert.assert_called_once_with(
        input_file, "temp.ogg", "32k", 24000
    )


@patch("os.path.exists")
@patch("tempfile.NamedTemporaryFile")
@patch("audio.convert_to_opus_ogg")
@patch("os.unlink")
def test_convert_to_opus_ogg_temp_cleanup_on_failure(
    mock_unlink, mock_convert, mock_tempfile, mock_exists
):
    mock_exists.return_value = True
    mock_temp_file = MagicMock()
    mock_temp_file.name = "temp.ogg"
    mock_tempfile.return_value = mock_temp_file
    mock_convert.side_effect = RuntimeError("Conversion failed")

    with pytest.raises(RuntimeError):
        convert_to_opus_ogg_temp("test.mp3")

    mock_unlink.assert_called_once_with("temp.ogg")
