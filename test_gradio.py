import gradio as gr

with gr.Blocks(css="""
    /* 按钮公共样式 - 提取重复属性 */
    .custom-button {
        border: none !important;
        padding: 8px 16px !important;
        border-radius: 4px !important;
        font-weight: 500 !important;
        transition: background-color 0.3s ease !important;
        cursor: pointer !important;
    }
    
    /* 添加按钮样式 */
    .add-button {
        background-color: #4CAF50 !important; /* 绿色 */
        color: white !important;
    }
    
    /* 删除按钮样式 */
    .delete-button {
        background-color: #f44336 !important; /* 红色 */
        color: white !important;
    }
    
    /* 悬停效果 */
    .add-button:hover {
        background-color: #45a049 !important; /* 深一点的绿色 */
    }
    
    .delete-button:hover {
        background-color: #d32f2f !important; /* 深一点的红色 */
    }
    
    /* 激活效果（点击时） */
    .add-button:active {
        background-color: #3d8b40 !important;
    }
    
    .delete-button:active {
        background-color: #b71c1c !important;
    }
    
    /* 文本框样式优化 */
    .gr-textbox {
        border-radius: 4px !important;
    }
    
    /* 下拉框样式优化 */
    .gr-dropdown {
        border-radius: 4px !important;
    }
""") as demo:
    gr.Markdown("### GitHub仓库订阅管理")
    
    with gr.Accordion("管理GitHub订阅仓库", open=False):
        gr.Markdown("在这里添加或删除你想要订阅的GitHub仓库")
        
        with gr.Row():
            with gr.Column(scale=1):
                repo_input = gr.Textbox(
                    label="输入要订阅的仓库", 
                    placeholder="格式：owner/repo",
                    elem_classes=["repo-input"]
                )
                add_btn = gr.Button("添加仓库", elem_classes=["custom-button", "add-button"])
            
            with gr.Column(scale=1):
                subscription_list = gr.Dropdown(
                    ['owner/repo', 'qingni/repo'], 
                    label="已订阅的GitHub项目",
                    interactive=True
                )
                delete_btn = gr.Button("删除仓库", elem_classes=["custom-button", "delete-button"])

demo.launch()
    