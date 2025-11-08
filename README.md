# 优质数据集筛选系统

一个基于Vue 3 + FastAPI的现代化数据集筛选和标注系统，专为JSONL格式数据设计。

## 🌟 功能特性

- **现代化界面**: 基于Vue 3 + Element Plus的响应式设计
- **高性能后端**: FastAPI异步处理，支持大规模数据集
- **智能筛选**: 多条件筛选功能（搜索、质量分、选择状态）
- **批量操作**: 支持全选、取消全选等批量操作
- **实时统计**: 数据统计信息实时更新
- **质量标注**: 0-5分质量评分系统
- **导出功能**: 灵活的数据导出选项
- **拖拽上传**: 支持拖拽文件上传

## 📋 系统要求

- **Python**: 3.8+
- **Node.js**: 14.0+
- **npm**: 6.0+

## 🚀 快速开始

### 方法一：一键启动（推荐）

```bash
# 克隆项目
git clone <repository-url>
cd dataset_filter_system

# 一键启动
python start.py
```

启动脚本会自动：
- 检查环境依赖
- 安装Python和Node.js依赖
- 创建示例数据文件
- 启动后端和前端服务

### 方法二：手动启动

#### 启动后端服务

```bash
cd backend
pip install -r requirements.txt
python main.py
```

#### 启动前端服务

```bash
cd frontend
npm install
npm run dev
```

## 📁 项目结构

```
dataset_filter_system/
├── backend/                 # FastAPI后端
│   ├── main.py             # 主应用文件
│   └── requirements.txt    # Python依赖
├── frontend/               # Vue前端
│   ├── src/
│   │   ├── App.vue        # 主组件
│   │   └── main.js        # 入口文件
│   ├── index.html         # HTML模板
│   ├── package.json       # 前端依赖
│   └── vite.config.js     # Vite配置
├── start.py               # 一键启动脚本
├── sample_data.jsonl      # 示例数据
└── README.md             # 项目文档
```

## 📊 数据格式

系统支持JSONL格式的数据文件，每行一个JSON对象：

```json
{"system": "你是一位地理学家", "query": "中国的首都是哪里？", "response": "中国的首都是北京"}
{"system": "你是一位历史学家", "query": "秦始皇统一六国是哪一年？", "response": "秦始皇统一六国是在公元前221年"}
```

## 🔧 API文档

启动后端服务后，访问 http://localhost:8000/docs 查看完整的API文档。

### 主要API端点

- `POST /api/upload` - 上传JSONL文件
- `GET /api/data` - 获取筛选后的数据（支持分页）
- `POST /api/update` - 更新数据项（选择状态、质量分）
- `GET /api/stats/{filename}` - 获取数据统计信息
- `POST /api/export` - 导出筛选后的数据
- `GET /api/download/{filename}` - 下载导出的文件

## 💡 使用说明

1. **上传数据**: 将JSONL文件拖拽到上传区域或点击选择文件
2. **筛选数据**: 使用搜索框、质量分筛选器、选择状态筛选器
3. **标注数据**: 为每条数据设置质量分（0-5分）和选择状态
4. **批量操作**: 使用全选/取消全选按钮进行批量操作
5. **导出数据**: 选择导出选项并下载筛选后的数据

## 🎨 界面预览

- **现代化设计**: 渐变背景、卡片布局、动画效果
- **响应式布局**: 适配不同屏幕尺寸
- **直观操作**: 拖拽上传、实时预览、一键导出

## 🔧 开发环境

### 后端开发

```bash
cd backend
pip install -r requirements.txt
python main.py
```

### 前端开发

```bash
cd frontend
npm install
npm run dev
```

### 构建生产版本

```bash
cd frontend
npm run build
```

## 📝 示例数据

系统启动时会自动创建示例数据文件 `sample_data.jsonl`，包含10条不同领域的问答数据，可用于测试系统功能。

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🐛 问题反馈

如果您遇到任何问题或有改进建议，请在 GitHub 上提交 issue。

## 🔗 相关链接

- [Vue 3 官方文档](https://vuejs.org/)
- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [Element Plus 组件库](https://element-plus.org/)
- [Vite 构建工具](https://vitejs.dev/)

---

**注意**: 确保在启动前已安装Python 3.8+和Node.js 14.0+环境。
