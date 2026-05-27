# 焊缝识别系统 - 上下文维护文件

## 项目概述

这是一个基于纯视觉方案的焊缝识别系统，用于检测未焊接的焊缝线。系统使用Python和OpenCV实现，支持多种输入源（摄像头、视频、图片），当前专注于直线焊缝检测，后续可扩展至曲线焊缝。

当前版本已完成完整的GUI功能：实时检测、参数模板管理、图像放大查看、自动保存录像/截图、多摄像头切换等。

## 技术架构

### 核心技术栈
- **Python 3.8+**：主要编程语言
- **OpenCV 4.x**：图像处理和计算机视觉、VideoWriter
- **NumPy**：数值计算
- **PyQt5**：GUI框架
- **PyYAML**：配置文件管理

### 系统架构
```
输入源 → 预处理 → 边缘检测 → 直线检测 → 结果可视化
                                           → 自动保存（AVI/PNG）
```

## 模块说明

### 1. 核心检测模块 (src/core/)

#### preprocessing.py - 图像预处理器
- 灰度转换
- 高斯模糊/双边滤波
- CLAHE对比度增强（clip_limit 可拖拽滑块调整）
- 形态学关闭操作（可选）

#### detector.py - 焊缝检测器
- Canny边缘检测
- 概率霍夫变换（HoughLinesP）
- 线段过滤（长度、角度）
- 线段合并（考虑角度容差）
- 性能统计（平均耗时/FPS）

### 2. 输入源模块 (src/input_sources/)

- **ImageSource**：静态图像读取，自动扫描 `data/images` 目录，支持拖放导入和上一张/下一张浏览，加载后自动持续检测
- **VideoSource**：视频文件读取（支持上下文管理器、seek跳转），检测完毕后可重新开始
- **CameraSource**：摄像头实时捕获（支持上下文管理器），`list_cameras()` 静态方法扫描所有可用设备，GUI 支持多摄像头下拉切换（与输入源选择器 75%/25% 横向排列）

### 3. GUI模块 (src/gui/)

- **MainWindow**：主窗口
  - 三图同屏：原图、边缘图（居中）、处理图（下方），支持独立开关显示
  - 摄像头预览（检测前显示原始画面）
  - 图片自动持续检测（选择/拖入后自动开始，离开图片源自动停止）
  - 拖放文件加载（图片/视频）
  - 放大查看窗口（点击任意图片弹出）
    - 滚轮缩放（0.8×–3.0×，步长 0.2）
    - 鼠标左键拖拽平移视角
    - 系统标题栏最大化按钮
    - 摄像头/视频源实时更新画面
  - 切换输入源或原图变化时自动清除残留检测结果
  - 状态栏显示检测数量和当前状态
  - 视频检测完毕后可重新开始（seek(0)）
- **ControlPanel**：控制面板（固定宽度 380px）
  - 输入源组：输入源选择 + 多摄像头切换（仅摄像头源可见）
  - 检测参数组（合并预处理+检测）：模板管理（置顶）→ 所有参数滑块 → 恢复默认（置底）
  - 显示选项组：独立开关三图显示
  - 检测按钮行：开始检测（拉伸占满）→ 自动保存复选框 → 打开保存文件夹按钮
  - 所有参数支持悬停提示（含作用、原理、调整建议）
  - 参数模板管理：创建/保存/删除/切换，combo 可编辑名称，日志记录每次操作
  - CLAHE 限制、Canny 阈值等浮点参数支持滑块拖拽 + 数值输入
  - Canny 低/高阈值互锁保护，高斯核自动保持奇数
- **ScalableImageLabel**：可缩放、拖拽的图像控件（用于放大窗口）
- **ClickableLabel**：可点击的图像标签（信号：clicked）

### 4. 配置管理 (src/config/)

- **ConfigManager**：YAML配置文件管理
- **参数模板**：创建/保存/删除/切换，本地持久化到 `config/profiles.yaml`，操作日志到 `config/profiles_log.yaml`
- **配置链路**：GUI → detector/preprocessor params，所有参数均可通过模板保存和恢复

### 5. 工具函数 (src/utils/)

- **visualization**：检测结果可视化

### 6. 自动保存功能

- 勾选「自动保存」后，每次检测帧自动保存：
  - **摄像头/视频源** → 3 个独立 AVI 视频文件（original.avi / result.avi / edges.avi），写入 `data/saved/YYYY-MM-DD/HH-MM-SS_microseconds/`
  - **图片源** → 3 张 PNG 截图（image_original / result / edges）
- 切换源或停止检测时自动释放 VideoWriter，确保文件完整
- 📂 按钮一键打开保存目录（`os.startfile`）

## 关键算法

### 焊缝检测流程
1. **图像预处理**
   - 灰度转换
   - 高斯模糊（降噪，核自动保持奇数）
   - CLAHE对比度增强

2. **边缘检测**
   - Canny边缘检测
   - 可选形态学闭操作

3. **直线检测**
   - 概率霍夫变换
   - 线段过滤（长度、角度）
   - 线段合并

4. **结果输出**
   - 在原图上绘制检测结果
   - 显示检测数量
   - 可选自动保存到磁盘

## 配置参数

### 预处理参数
- `blur_kernel_size`：高斯模糊核大小（默认5，范围1-31，步长2，自动保持奇数）
- `clahe_clip_limit`：CLAHE对比度限制（默认2.0，范围0.1-10.0，步长0.1，浮点滑块）
- `clahe_grid_size`：CLAHE网格大小（默认8）

### 检测参数
- `canny_low`：Canny低阈值（默认50，范围0-255，自动保持 < canny_high）
- `canny_high`：Canny高阈值（默认150，范围0-255，自动保持 > canny_low）
- `hough_threshold`：霍夫变换阈值（默认50，范围1-200）
- `min_line_length`：最小线段长度（默认50，范围10-500）
- `max_line_gap`：最大线段间隔（默认10，范围1-100）
- `angle_tolerance`：角度容差（默认15°，范围1-45°）

## 使用指南

### 启动应用
```bash
python main.py
```
Windows 用户也可双击 `启动程序.pyw`。

### 基本使用流程
1. 选择输入源（摄像头/视频/图像文件），摄像头可进一步选择设备
2. 可选：切换或调整参数模板
3. 摄像头/视频点击「开始检测」；图片源自动检测
4. 点击任意图片放大细看
5. 勾选「自动保存」录制检测过程
6. 点击 📂 打开保存目录

## 扩展计划

### 短期目标
- [x] 参数模板管理（创建/保存/删除/切换）
- [x] 图像放大查看（滚轮缩放 + 拖拽 + 全屏）
- [x] 自动保存检测结果（AVI/PNG）
- [ ] 完善单元测试
- [ ] 添加示例数据

### 中期目标
- [ ] 曲线焊缝检测
- [ ] 标注文件生成
- [ ] 批量处理功能

### 长期目标
- [ ] 深度学习模型集成
- [ ] 3D定位支持
- [ ] 多焊缝同时检测

## 开发规范

### 代码风格
- 遵循PEP 8规范
- 使用类型注解
- 编写文档字符串

### 提交规范
- 使用中文提交信息
- 格式：`类型: 简短描述`
- 类型：feat/fix/docs/test/refactor
- Body 使用 `- ` 无序列表描述变更内容

## 注意事项

1. **图像质量**：确保输入图像有足够对比度
2. **焊缝特征**：当前主要检测直线焊缝
3. **实时性**：摄像头/视频约 30fps，图片源持续检测约 5fps
4. **硬件要求**：普通USB摄像头即可
5. **编码兼容性**：自动保存视频使用 XVID 编码（.avi），Windows 下通用
6. **布局约束**：控制面板固定宽度 380px，参数组内 spacing 2px
7. **高斯核**：GUI层自动将偶数核 +1 为奇数，避免 OpenCV 自动修正导致显示不一致
8. **Canny阈值保护**：低阈值始终 < 高阈值，滑块拖动时自动互锁

## 上下文维护规则

每次改动后（新增功能、重构模块、修改核心算法、调整 GUI 布局等），应：
1. 更新 AGENTS.md 对应章节，使其反映项目**当前状态**，避免后续对话信息过时或浪费 token。
2. 在 README.md「更新日志」末尾追加一条变更记录，格式：- YYYY-MM-DD: 变更描述。
## 相关资源

- [OpenCV文档](https://docs.opencv.org/)
- [PyQt5文档](https://www.riverbankcomputing.com/static/Docs/PyQt5/)
- [霍夫变换](https://en.wikipedia.org/wiki/Hough_transform)

---

## 相关 Skills（模型自动调用指南）

以下是本项目相关的 skills，模型在处理相关任务时应自动调用：

### 1. computer-vision-opencv
- **位置**: `C:\Users\Takobox\.agents\skills\computer-vision-opencv\SKILL.md`
- **用途**: OpenCV 和计算机视觉开发的最佳实践
- **何时调用**: 
  - 编写或修改图像处理代码时
  - 实现 OpenCV 相关功能时
  - 优化图像处理性能时
- **关键内容**:
  - 图像验证和数据类型处理
  - 色彩空间转换最佳实践
  - 视频资源管理（上下文管理器）
  - 性能优化建议

### 2. python-performance-optimization
- **位置**: `C:\Users\Takobox\.agents\skills\python-performance-optimization\SKILL.md`
- **用途**: Python 代码性能分析和优化
- **何时调用**:
  - 优化检测算法性能时
  - 分析性能瓶颈时
  - 实现实时处理功能时
- **关键内容**:
  - 使用 `time.perf_counter()` 测量时间
  - 使用装饰器进行性能监控
  - 避免不必要的数据拷贝
  - 使用 NumPy 向量化操作

### 3. python-testing-patterns
- **位置**: `C:\Users\Takobox\.agents\skills\python-testing-patterns\SKILL.md`
- **用途**: Python 测试最佳实践
- **何时调用**:
  - 编写单元测试时
  - 设置测试套件时
  - 实现测试驱动开发时
- **关键内容**:
  - pytest 使用指南
  - 测试夹具（fixtures）
  - 参数化测试
  - Mock 和 MonkeyPatch

### 4. logging-best-practices
- **位置**: `C:\Users\Takobox\.agents\skills\logging-best-practices\SKILL.md`
- **用途**: 日志记录最佳实践
- **何时调用**:
  - 添加日志记录时
  - 调试和监控应用时
  - 设计日志策略时
- **关键内容**:
  - 使用结构化日志
  - 宽事件（Wide Events）模式
  - 请求 ID 追踪
  - 避免日志滥用

### 5. deep-learning-pytorch
- **位置**: `C:\Users\Takobox\.agents\skills\deep-learning-pytorch\SKILL.md`
- **用途**: 深度学习和 PyTorch 开发
- **何时调用**:
  - 扩展深度学习模型时
  - 实现 U-Net 或 YOLO 时
  - 训练自定义模型时
- **关键内容**:
  - PyTorch 模型架构
  - 训练循环实现
  - 数据加载和预处理
  - 模型优化和部署

### 6. brainstorming
- **位置**: `C:\Users\Takobox\.codex\skills\brainstorming\SKILL.md`
- **用途**: 创意工作前的需求探索
- **何时调用**:
  - 设计新功能时
  - 探索用户需求时
  - 规划系统架构时

### 7. writing-plans
- **位置**: `C:\Users\Takobox\.codex\skills\writing-plans\SKILL.md`
- **用途**: 编写详细实现计划
- **何时调用**:
  - 实现多步骤任务前
  - 编写技术方案时
  - 规划项目进度时

### 8. systematic-debugging
- **位置**: `C:\Users\Takobox\.codex\skills\systematic-debugging\SKILL.md`
- **用途**: 系统化调试方法
- **何时调用**:
  - 遇到 bug 或测试失败时
  - 排查问题时
  - 分析错误日志时

### 9. test-driven-development
- **位置**: `C:\Users\Takobox\.codex\skills\test-driven-development\SKILL.md`
- **用途**: 测试驱动开发
- **何时调用**:
  - 实现新功能前
  - 修复 bug 前
  - 重构代码时

### 10. requesting-code-review
- **位置**: `C:\Users\Takobox\.codex\skills\requesting-code-review\SKILL.md`
- **用途**: 代码审查请求
- **何时调用**:
  - 完成重要功能后
  - 合并代码前
  - 验证工作质量时

---

## Skills 使用规则

1. **自动调用**: 当任务匹配 skill 描述时，模型应自动调用相应 skill
2. **优先级**: 专业技能（如 computer-vision-opencv）优先于通用技能
3. **组合使用**: 复杂任务可能需要多个 skills 配合
4. **文档记录**: 使用 skill 后应在代码中注明来源

