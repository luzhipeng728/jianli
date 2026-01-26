# 快速开始指南

## 1. 首次启动

### 安装依赖（已完成）
```bash
npm install
```

### 配置环境变量
```bash
# 复制环境变量模板（已创建 .env 文件）
cp .env.example .env

# 编辑 .env 文件，配置后端 API 地址
# VITE_API_BASE_URL=http://localhost:8000/api
```

## 2. 开发模式

```bash
npm run dev
```

访问：http://localhost:5174

## 3. 生产构建

```bash
npm run build
```

构建产物在 `dist/` 目录

## 4. 预览生产版本

```bash
npm run preview
```

## 5. 测试访问

使用有效的面试 token 访问：
```
http://localhost:5174/interview/{token}
```

## 注意事项

1. 确保后端服务运行在 `http://localhost:8000`
2. 确保后端 CORS 配置允许前端域名
3. Token 必须是后端生成的有效面试邀请链接

## 目录说明

- `src/api/` - API 请求封装
- `src/views/` - 页面组件
- `src/components/` - 可复用组件（待添加）
- `src/types/` - TypeScript 类型定义
- `src/composables/` - 组合式函数（待添加）
