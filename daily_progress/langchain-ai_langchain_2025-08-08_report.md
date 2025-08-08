# langchain-ai/langchain Daily Progress - 2025-08-08

## 新增功能
- 添加了对gpt-oss:20b的支持，并支持工具调用 #32428
- 实现了空内容块的智能缓冲以提高groq的流式处理效率 #32414
- 增加了`json_mode`的支持 #32396

## 主要改进
- 更新了回调集成和示例文档 #32458
- 添加了Spider作为网页加载器 #32453
- 优化了`create_agent`方法 #32440
- 为可追踪PDF文件的v1消息修复了问题 #32434
- 添加了超链接检索集成功能 #32433

## 修复问题
- 修复了`avec_structured_output()`未实现的问题 #32460
- 解决了在openai模块中`ainvoke`调用了`_get_response`而非`_aget_response`的问题 #32398
- 修复了提取图片时出现的ValueError问题 #32391