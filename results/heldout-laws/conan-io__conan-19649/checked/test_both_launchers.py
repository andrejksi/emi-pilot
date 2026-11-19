import os
import textwrap

from conan.test.utils.tools import TestClient

# The issue does not fix the spelling of the conf value that asks for both
# launchers (A3), so any of these plausible spellings is accepted.
CANDIDATES = [
    "powershell.exe;bat", "powershell.exe;cmd", "powershell.exe;cmd.exe",
    "pwsh;bat", "pwsh;cmd", "pwsh.exe;cmd.exe", "powershell.exe,bat",
    "powershell.exe,cmd", "['powershell.exe', 'bat']", "['powershell.exe', 'cmd']",
    "['pwsh', 'cmd']", "['powershell.exe', 'cmd.exe']", "both", "bat+ps1",
    "powershell.exe+bat", "powershell.exe;bat.exe",
]

CONANFILE = textwrap.dedent("""
    from conan import ConanFile
    class Pkg(ConanFile):
        settings = "os"
        generators = "VirtualBuildEnv"
        def generate(self):
            pass
    """)

PROFILE = textwrap.dedent("""
    [settings]
    os=Windows
    [buildenv]
    MYVAR=myvalue
    """)


def _install(conf_value):
    c = TestClient(light=True)
    c.save({"conanfile.py": CONANFILE, "profile": PROFILE})
    c.run(f'install . -pr:a=profile -c "tools.env.virtualenv:powershell={conf_value}"',
          assert_error=None)
    return c


def _both_generated():
    for value in CANDIDATES:
        try:
            c = _install(value)
        except Exception:
            continue
        bat = os.path.join(c.current_folder, "conanbuild.bat")
        ps1 = os.path.join(c.current_folder, "conanbuild.ps1")
        if os.path.isfile(bat) and os.path.isfile(ps1):
            return c
    return None


def test_powershell_conf_can_generate_both_bat_and_ps1():
    """New: some value of tools.env.virtualenv:powershell makes a Windows install generate both conanbuild.bat and conanbuild.ps1 (A1, A3)."""
    assert _both_generated() is not None


def test_both_generated_launchers_set_the_buildenv_variable():
    """New: when both launchers are generated, conanbuild.bat and conanbuild.ps1 each set the buildenv variable MYVAR to myvalue (A1, A2, A3)."""
    c = _both_generated()
    assert c is not None
    bat_env = c.load("conanbuildenv.bat")
    ps1_env = c.load("conanbuildenv.ps1")
    assert "MYVAR" in bat_env and "myvalue" in bat_env
    assert "MYVAR" in ps1_env and "myvalue" in ps1_env
