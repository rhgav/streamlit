from openai import OpenAI
import os

# 初始化OpenAI客户端
client = OpenAI(
    # 如果没有配置环境变量，请用百炼API Key替换：api_key="sk-xxx"
    api_key="sk-105b5332bd4f442bbcaf298eefda8cb7",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

def main():
    reasoning_content = ""  # 定义完整思考过程
    answer_content = ""     # 定义完整回复
    is_answering = False   # 判断是否结束思考过程并开始回复

    # 创建聊天完成请求
    stream = client.chat.completions.create(
        model="deepseek-r1",  # 此处以 deepseek-v3 为例，可按需更换模型名称
        messages=[
            {"role": "user", "content": "请根据毕设题目的研究内容、基本要求和额外要求编写一开题报告的技术路线部分，该部分不少于5000字 要求：以文字方案形式表达，编写论文开题报告，要具体、明确，是研究内容的进一步细化，每个研究内容要有多种方案可以选择，采用 4技术路线 实现内容的技术和方法 4.1.1知识提取（方法） 4.1.2知识清洗 4.1.3时空关联 毕设题目： 本科毕业设计题目：基于知识提取的历史人文数据地理信息可视化 研究内容 本课题旨在结合自然语言处理（NLP）技术与地理信息系统（GIS）平台，开发一套面向考古领域的知识提取与可视化系统。通过分析历史文献与考古报告中的语义信息，构建历史人文数据的知识图谱，并在Unity中实现可交互的二维GIS可视化，支持用户在时空维度上探索文物和历史事件的关联性。研究内容包括： 1.文本知识提取： o设计基于NLP的大模型（如BERT或GPT）对历史文献和考古报告进行信息抽取，提取地理位置、时间节点、考古对象及其关系（如“文物出土于某地”）。 o将文本分析结果以知识三元组形式存储，构建基础考古知识库。 2.知识图谱构建： o利用Neo4j或RDF等工具，将抽取的知识体系化，建立面向考古研究的知识图谱。 o支持文物、地理位置、历史事件的语义查询和知识推理。 3.GIS平台的构建与整合： o以Unity为基础，设计二维GIS可视化界面，将历史人文数据知识图谱与地理位置信息结合，动态呈现历史人文数据。 o实现交互功能，如事件的时序动态展示、特定区域文物分布查询等。 4.系统功能验证： o使用公开的考古数据集（如历史文献中的出土记录）对系统进行测试，验证提取方法的准确性和GIS展示效果的可用性。 5.对比分析： o比较传统知识提取方法与基于NLP的知识提取方法的优缺点，总结本系统在考古研究领域的优势。 6.总结与展望： o提炼研究成果，提出未来发展方向。 基本要求 1.理论掌握： o理解自然语言处理和知识图谱构建的基础理论，熟悉GIS系统及其相关技术。 2.实践能力： o能够根据考古研究需求，设计文本知识提取与二维GIS展示的技术方案。 3.工具与平台应用： o使用Python完成NLP模型的微调与文本信息抽取； o掌握Neo4j构建知识图谱； o使用Unity实现GIS数据的动态展示与交互功能。 4.系统开发与测试： o完成历史人文数据知识提取与可视化系统的开发，进行功能验证与效果优化。 5.结果分析与总结： o提出完整的实验数据和分析报告，确保结果具有可信度和学术价值。 额外要求： 1. 通过大模型、或从文献中抽取知识的方式构建包含价值属性的历史文物知识，价值属性包括每个历史文物或遗迹的关联文献、关联历史人物、关联文献词频等，通过这些价值属性对知识图谱进行切片；2. 通过单一价值属性或者组合价值属性构建价值评估模型，基于该模型生成的结果在GIS上绘制热力图，图的形式可以是散点、线型、区域型；3. 对绘制的热力图与手机信令生成的热力图进行对比，看看我们方法的精度。"}
        ],
        stream=True
        # 解除以下注释会在最后一个chunk返回Token使用量
        # stream_options={
        #     "include_usage": True
        # }
    )

    print("\n" + "=" * 20 + "思考过程" + "=" * 20 + "\n")

    for chunk in stream:
        # 处理usage信息
        if not getattr(chunk, 'choices', None):
            print("\n" + "=" * 20 + "Token 使用情况" + "=" * 20 + "\n")
            print(chunk.usage)
            continue

        delta = chunk.choices[0].delta

        # 检查是否有reasoning_content属性
        if not hasattr(delta, 'reasoning_content'):
            continue

        # 处理空内容情况
        if not getattr(delta, 'reasoning_content', None) and not getattr(delta, 'content', None):
            continue

        # 处理开始回答的情况
        if not getattr(delta, 'reasoning_content', None) and not is_answering:
            print("\n" + "=" * 20 + "完整回复" + "=" * 20 + "\n")
            is_answering = True

        # 处理思考过程
        if getattr(delta, 'reasoning_content', None):
            print(delta.reasoning_content, end='', flush=True)
            reasoning_content += delta.reasoning_content
        # 处理回复内容
        elif getattr(delta, 'content', None):
            print(delta.content, end='', flush=True)
            answer_content += delta.content

    # 如果需要打印完整内容，解除以下的注释
    """
    print("=" * 20 + "完整思考过程" + "=" * 20 + "\n")
    print(reasoning_content)
    print("=" * 20 + "完整回复" + "=" * 20 + "\n")
    print(answer_content)
    """

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"发生错误：{e}")