# nuitka-project: --mode=standalone
# nuitka-project: --enable-plugin=pyside2
# nuitka-project: --include-module=PySide2.QtSvg
# nuitka-project: --include-data-dir={MAIN_DIRECTORY}/resource=resource
# nuitka-project: --include-package-data=dayu_widgets
# nuitka-project: --output-dir={MAIN_DIRECTORY}/dist
# nuitka-project: --output-filename=PMTimeMachine.exe
# nuitka-project: --windows-icon-from-ico={MAIN_DIRECTORY}/app.ico

# nuitka-project-set: APP_VERSION = __import__("runpy").run_path({MAIN_DIRECTORY} + "/pmtm/constant.py")["VERSION"]
# nuitka-project: --company-name=lingyunfx
# nuitka-project: --product-name=PM TimeMachine
# nuitka-project: --product-version={APP_VERSION}
# nuitka-project: --file-version={APP_VERSION}
# nuitka-project: --windows-console-mode=disable
# nuitka-project: --windows-create-installer
# nuitka-project: --windows-installer-output=PMTimeMachine-{APP_VERSION}-Setup.exe
# nuitka-project: --windows-installer-mode=user
# nuitka-project: --windows-installer-shortcuts=start-menu,desktop

import pmtm

if __name__ == "__main__":
    pmtm.run()
