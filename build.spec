# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


ep_a = Analysis(['event-planner.py'],
             pathex=['.'],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

mvp_a = Analysis(['match-video-processer.py'],
             pathex=['.'],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

gp_a = Analysis(['game-producer.py'],
             pathex=['.'],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

# not working
# MERGE( (ep_a, 'event-planner', 'event-planner'), (mvp_a, 'match-video-processer', 'match-video-processer') )

ep_pyz = PYZ(ep_a.pure, ep_a.zipped_data,
             cipher=block_cipher)
ep_exe = EXE(ep_pyz,
          ep_a.scripts,
          ep_a.binaries,
          ep_a.zipfiles,
          ep_a.datas,
          [],
          name='event-planner',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True )

mvp_pyz = PYZ(mvp_a.pure, mvp_a.zipped_data,
             cipher=block_cipher)
mvp_exe = EXE(mvp_pyz,
          mvp_a.scripts,
          mvp_a.binaries,
          mvp_a.zipfiles,
          mvp_a.datas,
          [],
          name='match-video-processer',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True )

gp_pyz = PYZ(gp_a.pure, gp_a.zipped_data,
             cipher=block_cipher)
gp_exe = EXE(gp_pyz,
          gp_a.scripts,
          gp_a.binaries,
          gp_a.zipfiles,
          gp_a.datas,
          [],
          name='game-producer',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True )

