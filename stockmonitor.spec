# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

import PySide6


project_root = Path(SPECPATH)
src_root = project_root / "src"
pyside_dir = Path(PySide6.__file__).resolve().parent

hiddenimports = [
    "pywintypes",
    "pythoncom",
    "win32api",
    "win32con",
    "win32gui",
    "win32process",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
]

datas = [
    (str(pyside_dir / "plugins" / "platforms"), "PySide6/plugins/platforms"),
]

a = Analysis(
    [str(src_root / "stockmonitor" / "main.py")],
    pathex=[str(project_root), str(src_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "unittest",
        "test",
        "tests",
        "PySide6.Qt3DAnimation",
        "PySide6.Qt3DCore",
        "PySide6.Qt3DExtras",
        "PySide6.Qt3DInput",
        "PySide6.Qt3DLogic",
        "PySide6.Qt3DRender",
        "PySide6.QtBluetooth",
        "PySide6.QtCharts",
        "PySide6.QtDataVisualization",
        "PySide6.QtDesigner",
        "PySide6.QtGraphs",
        "PySide6.QtGraphsWidgets",
        "PySide6.QtHelp",
        "PySide6.QtHttpServer",
        "PySide6.QtLocation",
        "PySide6.QtMultimedia",
        "PySide6.QtMultimediaWidgets",
        "PySide6.QtNetworkAuth",
        "PySide6.QtNfc",
        "PySide6.QtOpenGL",
        "PySide6.QtOpenGLWidgets",
        "PySide6.QtPdf",
        "PySide6.QtPdfWidgets",
        "PySide6.QtPositioning",
        "PySide6.QtPrintSupport",
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.QtQuick3D",
        "PySide6.QtQuickControls2",
        "PySide6.QtQuickWidgets",
        "PySide6.QtRemoteObjects",
        "PySide6.QtScxml",
        "PySide6.QtSensors",
        "PySide6.QtSerialBus",
        "PySide6.QtSerialPort",
        "PySide6.QtSpatialAudio",
        "PySide6.QtSql",
        "PySide6.QtStateMachine",
        "PySide6.QtSvg",
        "PySide6.QtSvgWidgets",
        "PySide6.QtTest",
        "PySide6.QtTextToSpeech",
        "PySide6.QtUiTools",
        "PySide6.QtWebChannel",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineQuick",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebSockets",
        "PySide6.QtWebView",
        "PySide6.QtXml",
    ],
    noarchive=False,
    optimize=0,
)


def _keep_data(entry):
    src = str(entry[0]).replace('\\', '/').lower()
    blocked = [
        '/pyside6/translations/',
        '/pyside6/examples/',
        '/pyside6/qml/',
        '/pyside6/typesystems/',
        '/pyside6/support/',
        '/pyside6/scripts/',
        '/pyside6/include/',
    ]
    return not any(token in src for token in blocked)


def _keep_binary(entry):
    src = str(entry[0]).replace('\\', '/').lower()
    blocked = [
        'qt6webengine',
        'qt6qml',
        'qt6quick',
        'qt6pdf',
        'qt6multimedia',
        'qt63d',
        'qt6charts',
        'qt6datavisualization',
        'qt6designer',
        'qt6graphs',
        'qt6help',
        'qt6httpserver',
        'qt6location',
        'qt6networkauth',
        'qt6nfc',
        'qt6opengl',
        'qt6positioning',
        'qt6printsupport',
        'qt6remoteobjects',
        'qt6scxml',
        'qt6sensors',
        'qt6serial',
        'qt6spatialaudio',
        'qt6sql',
        'qt6statemachine',
        'qt6svg',
        'qt6test',
        'qt6texttospeech',
        'qt6uitools',
        'qt6webchannel',
        'qt6websockets',
        'qt6webview',
        'qt6xml',
    ]
    return not any(token in src for token in blocked)


a.datas = [entry for entry in a.datas if _keep_data(entry)]
a.binaries = [entry for entry in a.binaries if _keep_binary(entry)]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="StockMonitor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="StockMonitor",
)
