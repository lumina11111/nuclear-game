"""后续重构说明。

本版先解决可玩性与可理解性问题，同时为继续拆分 engine.py 留出边界：

- SaveManager：可迁移 safe_write_json、read_records、snapshot、restore_checkpoint。
- EventManager：可迁移 trigger_warning、trigger_dose_task、trigger_dispatch_task、update_dispatch_task。
- ThermalModel：可迁移 update_parameters 中的简化热工计算。
- PanelRenderer：可迁移 draw_left / draw_right / draw_bottom 等面板绘制。

这样可以先保持游戏可运行，再逐步拆分，避免一次性大改引入新 Bug。
"""
