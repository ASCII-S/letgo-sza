# 信号类型结果分布热力图生成工具

## 功能概述

本工具用于为给定的CSV文件（如`merged_result_sig1_distribution.csv`）生成热力图，直观展示不同程序在不同信号类型下的结果分布情况。主要功能包括：

1. 为每个程序生成单独的热力图，横坐标为信号类型，纵坐标为结果类型
2. 为每个信号类型生成单独的热力图，横坐标为结果类型，纵坐标为程序
3. 为每个结果类型生成单独的热力图，横坐标为程序，纵坐标为信号类型
4. 支持丰富的自定义配置选项，包括颜色方案、布局类型、排序规则等
5. 支持对数刻度，更好地展示数值差异较大的数据
6. 全面的图表文本和字体样式定制，包括标题、标签、字体、颜色等

## 文件结构

```
analyze_Sig1_result_dist/
├── sig1_heatmap.py               # 主脚本文件
├── sig1_heatmap_config.py        # 配置文件
├── README_heatmap.md             # 本说明文件
└── analysis_results/
    ├── merged_result_sig1_distribution.csv  # 输入数据文件
    └── heatmaps/                 # 输出热力图目录
        ├── 2mm_heatmap.png       # 程序热力图
        ├── signal_SIGBUS_heatmap.png  # 信号热力图
        ├── result_C_Masked_heatmap.png # 结果热力图
        └── ...
```

## 依赖项

- Python 3.6+
- pandas
- matplotlib
- seaborn
- numpy

可以使用以下命令安装必要的依赖：

```bash
pip install pandas matplotlib seaborn numpy
```

## 使用方法

### 基本使用

直接运行主脚本：

```bash
python sig1_heatmap.py
```

脚本会读取配置文件中指定的CSV文件，根据配置的布局类型生成热力图，并保存到指定的输出目录。

### 配置选项

所有配置选项都在`sig1_heatmap_config.py`文件中，可以根据需要进行修改：

#### 基本配置

- `CSV_FILE`：输入CSV文件路径
- `OUTPUT_DIR`：输出目录路径
- `SIGNAL_COLUMNS`：要显示的信号列，如果为`None`则显示所有信号列
- `RESULT_TYPES`：要显示的结果类型，如果为`None`则显示所有结果类型
- `PROGRAM_LIST`：要显示的程序列表，如果为`None`则显示所有程序

#### 布局配置

- `HEATMAP_LAYOUT`：热力图布局类型，可选值：
  - `1`: 程序为单独的热力图，行=结果类型，列=信号类型
  - `2`: 信号类型为单独的热力图，行=程序，列=结果类型
  - `3`: 结果类型为单独的热力图，行=信号类型，列=程序

#### 标题和标签配置

- 布局类型1（程序为中心）：
  - `PROGRAM_CHART_TITLE_TEMPLATE`：标题模板，`{program}`将被替换为具体程序名
  - `PROGRAM_CHART_XLABEL`：X轴标签
  - `PROGRAM_CHART_YLABEL`：Y轴标签
- 布局类型2（信号为中心）：
  - `SIGNAL_CHART_TITLE_TEMPLATE`：标题模板，`{signal}`将被替换为具体信号名
  - `SIGNAL_CHART_XLABEL`：X轴标签
  - `SIGNAL_CHART_YLABEL`：Y轴标签
- 布局类型3（结果为中心）：
  - `RESULT_CHART_TITLE_TEMPLATE`：标题模板，`{result}`将被替换为具体结果类型
  - `RESULT_CHART_XLABEL`：X轴标签
  - `RESULT_CHART_YLABEL`：Y轴标签

#### 排序配置

- `SORT_BY_PROGRAM`：是否按程序名称排序
- `SORT_BY_RESULT`：是否按结果类型排序
- `SORT_BY_SIGNAL`：是否按信号类型排序
- `SIGNAL_ORDER`：信号类型显示顺序，如果为`None`则按字母顺序排序
- `RESULT_ORDER`：结果类型显示顺序，如果为`None`则按字母顺序排序

#### 图表样式

- `FIGURE_SIZE`：图表尺寸，格式为`(宽度, 高度)`，单位为英寸
- `CMAP`：热力图颜色方案，可选值包括`YlGnBu`、`viridis`、`Blues`等
- `USE_LOG_SCALE`：是否使用对数刻度
- `SHOW_ANNOTATIONS`：是否在每个单元格中显示数值
- `LINEWIDTHS`：热力图单元格边框宽度
- `FIGURE_FACECOLOR`：图表背景色
- `AXES_FACECOLOR`：坐标轴区域背景色
- `SHOW_GRID`：是否显示网格线
- `GRID_COLOR`：网格线颜色
- `GRID_LINESTYLE`：网格线样式
- `GRID_LINEWIDTH`：网格线宽度

#### 字体设置

- `FONT_FAMILY`：字体族，可选值包括`serif`、`sans-serif`、`cursive`、`fantasy`、`monospace`
- `FONT_WEIGHT`：字体粗细，可选值包括`normal`、`bold`、`light`、`ultralight`、`heavy`
- `FONT_STYLE`：字体样式，可选值包括`normal`、`italic`、`oblique`
- `TITLE_FONTSIZE`：标题字体大小
- `XLABEL_FONTSIZE`：x轴标签字体大小
- `YLABEL_FONTSIZE`：y轴标签字体大小
- `TICK_FONTSIZE`：刻度标签字体大小
- `ANNOT_FONTSIZE`：单元格中注释文本的字体大小
- `TITLE_COLOR`：标题字体颜色
- `XLABEL_COLOR`：x轴标签字体颜色
- `YLABEL_COLOR`：y轴标签字体颜色
- `TICK_COLOR`：刻度标签字体颜色
- `ANNOT_COLOR`：单元格中注释文本的字体颜色

#### 坐标轴设置

- `ROTATE_XTICKS`：X轴标签旋转角度（当程序数量多时）
- `XTICKS_HA`：X轴标签水平对齐方式，可选值包括`left`、`right`、`center`

#### 输出设置

- `DPI`：图像输出DPI（每英寸点数）
- `ANNOTATION_FORMAT`：热力图单元格标注格式，`'d'`表示整数，`'.1f'`表示保留一位小数
- `IMAGE_FORMAT`：输出图像格式，可选`'png'`、`'jpg'`、`'svg'`、`'pdf'`

#### 其他选项

- `AUTO_ADJUST_FIGSIZE`：是否根据数据大小自动调整图形大小
- `MAX_ROW_HEIGHT_RATIO`：最大行高比例（相对于图形高度）
- `MIN_ROW_HEIGHT`：最小行高（英寸）

## 示例输出

根据不同的布局类型，会生成不同类型的热力图：

### 布局类型1：程序为中心

每个程序生成一张热力图，横坐标是信号类型，纵坐标是结果类型。

例如：`2mm_heatmap.png` 显示了程序2mm在不同信号类型和结果类型下的分布情况。

### 布局类型2：信号为中心

每个信号类型生成一张热力图，横坐标是结果类型，纵坐标是程序。

例如：`signal_SIGBUS_heatmap.png` 显示了SIGBUS信号在不同程序和结果类型下的分布情况。

### 布局类型3：结果为中心

每个结果类型生成一张热力图，横坐标是程序，纵坐标是信号类型。

例如：`result_C_Masked_heatmap.png` 显示了C-Masked结果类型在不同程序和信号类型下的分布情况。

## 注意事项

1. 输入CSV文件必须包含`program`和`result`列，以及至少一个信号类型列
2. 如果数据中存在大量的零值或数值差异很大，建议开启对数刻度（`USE_LOG_SCALE = True`）
3. 如果程序数量很多或结果类型很多，可能需要调整图表尺寸或开启自动调整尺寸（`AUTO_ADJUST_FIGSIZE = True`）
4. 对于布局类型3（结果为中心），如果程序数量较多，脚本会自动调整x轴标签的角度以避免重叠
5. 值为0的单元格会显示为最淡的颜色，而不是空白，使得热力图的视觉效果更加完整

## 扩展与定制

本工具设计为模块化结构，可以根据需要进行扩展：

1. 修改配置文件中的参数，调整热力图样式和布局
2. 在主脚本中添加新的分析功能
3. 开发新的可视化方式，如饼图、条形图等 