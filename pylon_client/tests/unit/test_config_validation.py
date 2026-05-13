import pytest

from pylon_client.artanis import Config


def test_mtls_cert_path_without_mtls_key_path_raises_error(tmp_path):
    """
    Test that providing mtls_cert_path without mtls_key_path raises an error.
    """
    cert_file = tmp_path / "cert.pem"
    cert_file.write_text("cert")
    with pytest.raises(ValueError, match="mtls_cert_path and mtls_key_path must be provided together"):
        Config(address="http://localhost:8000", mtls_cert_path=str(cert_file))


def test_mtls_key_path_without_mtls_cert_path_raises_error(tmp_path):
    """
    Test that providing mtls_key_path without mtls_cert_path raises an error.
    """
    key_file = tmp_path / "key.pem"
    key_file.write_text("key")
    with pytest.raises(ValueError, match="mtls_cert_path and mtls_key_path must be provided together"):
        Config(address="http://localhost:8000", mtls_key_path=str(key_file))


def test_mtls_cert_path_not_found_raises_error(tmp_path):
    """
    Test that providing a non-existent mtls_cert_path raises an error.
    """
    key_file = tmp_path / "key.pem"
    key_file.write_text("key")
    with pytest.raises(ValueError, match="mtls_cert_path not found"):
        Config(address="http://localhost:8000", mtls_cert_path="/nonexistent/cert.pem", mtls_key_path=str(key_file))


def test_mtls_key_path_not_found_raises_error(tmp_path):
    """
    Test that providing a non-existent mtls_key_path raises an error.
    """
    cert_file = tmp_path / "cert.pem"
    cert_file.write_text("cert")
    with pytest.raises(ValueError, match="mtls_key_path not found"):
        Config(address="http://localhost:8000", mtls_cert_path=str(cert_file), mtls_key_path="/nonexistent/key.pem")


def test_neurons_file_not_found_raises_error():
    """
    Test that providing a non-existent neurons_file raises an error.
    """
    with pytest.raises(ValueError, match="neurons_file not found"):
        Config(address="http://localhost:8000", neurons_file="/nonexistent/neurons.json")


def test_valid_mtls_cert_and_key_paths(tmp_path):
    """
    Test that valid mtls_cert_path and mtls_key_path are accepted without errors.
    """
    cert_file = tmp_path / "cert.pem"
    key_file = tmp_path / "key.pem"
    cert_file.write_text("cert")
    key_file.write_text("key")
    config = Config(address="http://localhost:8000", mtls_cert_path=str(cert_file), mtls_key_path=str(key_file))
    assert config.mtls_cert_path == str(cert_file)
    assert config.mtls_key_path == str(key_file)


def test_valid_neurons_file(tmp_path):
    """
    Test that a valid neurons_file path is accepted without errors.
    """
    neurons_file = tmp_path / "neurons.json"
    neurons_file.write_text("[]")
    config = Config(address="http://localhost:8000", neurons_file=str(neurons_file))
    assert config.neurons_file == str(neurons_file)
