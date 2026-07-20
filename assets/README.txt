素材资源目录说明

images/background  背景图
images/icons       图标
images/equipment   设备图片
images/ui          UI 装饰图
sounds             click.wav、success.wav、warning.wav、alarm.wav、place.wav 等音效
fonts              可放置 NotoSansCJK-Regular.ttc、msyh.ttc、simhei.ttf 等字体

游戏代码通过 nuclear_game/asset_manager.py 统一查找这些资源。资源不存在时会自动使用内置示意图和合成音效，不影响运行。
