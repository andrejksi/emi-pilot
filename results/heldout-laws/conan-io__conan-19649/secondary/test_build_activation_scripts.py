from pathlib import Path

from conan.test.utils.tools import TestClient


def test_windows_install_generates_both_build_activation_scripts():
    """New: one Windows install can generate both conanbuild.ps1 for PowerShell and conanbuild.bat for CMD (A1)."""
    client = TestClient(light=True)
    client.save({"conanfile.txt": ""})
    client.run("install . -s:b os=Windows -s:h os=Windows "
               "-c tools.env.virtualenv:powershell=powershell.exe")
    generated_files = {entry.name for entry in Path(client.current_folder).iterdir()
                       if entry.is_file()}
    assert {"conanbuild.ps1", "conanbuild.bat"} <= generated_files
