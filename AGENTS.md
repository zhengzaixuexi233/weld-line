# 焊缝识别系统 - 上下文维护文件

## 项目概述

这是一个基于纯视觉方案的焊缝识别系统，用于检测未焊接的焊缝线。系统使用Python和OpenCV实现，支持多种输入源（照片、视频、摄像头），当前专注于直线焊缝检测，后续可扩展至曲线焊缝。

## 技术架构

### 核心技术栈
- **Python 3.8+**：主要编程语言
- **OpenCV 4.x**：图像处理和计算机视觉
- **NumPy**：数值计算
- **PyQt5**：GUI框架
- **PyYAML**：配置文件管理

### 系统架构
```
输入源 → 预处理 → 边缘检测 → 直线检测 → 结果可视化
```

## 模块说明

### 1. 核心检测模块 (src/core/)

#### preprocessing.py - 图像预处理器
- 灰度转换
- 高斯模糊/双边滤波
- CLAHE对比度增强
- 形态学操作

#### detector.py - 焊缝检测器
- Canny边缘检测
- 概率霍夫变换（HoughLinesP）
- 线段过滤（长度、角度）
- 线段合并

### 2. 输入源模块 (src/input_sources/)

- **ImageSource**：静态图像读取
- **VideoSource**：视频文件读取（支持上下文管理器）
- **CameraSource**：摄像头实时捕获（支持上下文管理器）

### 3. GUI模块 (src/gui/)

- **MainWindow**：主窗口，显示图像和检测结果
- **ControlPanel**：控制面板，参数调整

### 4. 配置管理 (src/config/)

- **ConfigManager**：YAML配置文件管理

### 5. 工具函数 (src/utils/)

- **visualization**：检测结果可视化

## 关键算法

### 焊缝检测流程
1. **图像预处理**
   - 灰度转换
   - 高斯模糊（降噪）
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

## 配置参数

### 预处理参数
- `blur_kernel_size`：高斯模糊核大小（默认5）
- `clahe_clip_limit`：CLAHE对比度限制（默认2.0）
- `clahe_grid_size`：CLAHE网格大小（默认8）

### 检测参数
- `canny_low`：Canny低阈值（默认50）
- `canny_high`：Canny高阈值（默认150）
- `hough_threshold`：霍夫变换阈值（默认50）
- `min_line_length`：最小线段长度（默认50）
- `max_line_gap`：最大线段间隔（默认10）
- `angle_tolerance`：角度容差（默认15度）

## 使用指南

### 启动应用
```bash
python main.py
```

### 基本使用流程
1. 选择输入源（摄像头/视频/图像）
2. 调整检测参数（可选）
3. 点击"开始检测"
4. 查看实时检测结果

### 参数调整建议
- **光线较暗**：增大`clahe_clip_limit`
- **噪声较多**：增大`blur_kernel_size`
- **漏检较多**：降低`canny_low`和`hough_threshold`
- **误检较多**：提高`min_line_length`和`hough_threshold`

## 扩展计划

### 短期目标
- [ ] 完善单元测试
- [ ] 添加示例数据
- [ ] 性能优化

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

## 注意事项

1. **图像质量**：确保输入图像有足够对比度
2. **焊缝特征**：当前主要检测直线焊缝
3. **实时性**：目标帧率≥15fps
4. **硬件要求**：普通USB摄像头即可


## 上下文维护规则

较大改动后（新增功能、重构模块、修改核心算法、调整 GUI 布局等），应：
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


