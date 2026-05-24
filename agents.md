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
- **VideoSource**：视频文件读取
- **CameraSource**：摄像头实时捕获

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

## 相关资源

- [OpenCV文档](https://docs.opencv.org/)
- [PyQt5文档](https://www.riverbankcomputing.com/static/Docs/PyQt5/)
- [霍夫变换](https://en.wikipedia.org/wiki/Hough_transform)
