# duplicatemaster.spec

block_cipher = None

a = Analysis(
    ['src/gui/gui_app.py'],
    pathex=['.', 'src', 'src/duplicatemaster', 'src/gui'],
    binaries=[],
    datas=[('assets/fdf-icon.ico', 'assets')],
    hiddenimports=[
        'duplicatemaster.hasher',
        'duplicatemaster.deduper',
        'duplicatemaster.analyzer',
        'duplicatemaster.deletion',
        'duplicatemaster.exporter',
        'duplicatemaster.logger',
        'duplicatemaster.scanner',
        'gui.gui_app',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='DuplicateMaster',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='assets/fdf-icon.ico',
    version='version_info.txt'
)

