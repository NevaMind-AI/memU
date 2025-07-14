#!/bin/bash

# Enhanced Memory Test Runner for Locomo Evaluation
# This script runs the enhanced memory agent test that:
# 1. Processes each session sequentially
# 2. Updates memory files (profile.md, event.md) after each session
# 3. Uses merged memory context for QA testing

echo "🚀 启动增强记忆代理 Locomo 测试..."

# 设置环境变量
export PYTHONPATH="${PYTHONPATH}:$(pwd)/../../.."

# 检查数据文件
if [ ! -f "data/locomo10.json" ]; then
    echo "❌ 错误: 找不到数据文件 data/locomo10.json"
    echo "请确保数据文件存在于正确的位置"
    exit 1
fi

# 显示配置信息
echo "📋 测试配置:"
echo "  Chat部署: ${AZURE_OPENAI_CHAT_DEPLOYMENT:-gpt-4o-mini}"
echo "  API版本: ${AZURE_OPENAI_API_VERSION:-2024-02-01}"
echo "  使用Entra ID: ${USE_ENTRA_ID:-false}"
echo "  记忆目录: memory"

# 创建必要的目录
mkdir -p logs
mkdir -p memory

# 运行测试
echo ""
echo "🔄 开始运行增强记忆测试..."
echo "💾 记忆文件将保存在 memory/ 目录中"
echo "📊 每个session结束后会更新 profile.md, event.md (每一行都包含Theory of Mind注释)"
echo "🧠 QA测试时会合并所有记忆文件作为上下文"
echo ""

python -u enhanced_memory_test.py 2>&1 | tee logs/enhanced_memory_test_$(date +%Y%m%d_%H%M%S).log

# 检查运行结果
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 测试完成！"
    
    # 查找最新的结果文件
    LATEST_RESULT=$(ls -t enhanced_memory_test_results_*.json 2>/dev/null | head -1)
    if [ -n "$LATEST_RESULT" ]; then
        echo "📊 结果文件: $LATEST_RESULT"
        echo "📝 日志文件: logs/enhanced_memory_test_$(date +%Y%m%d_%H%M%S).log"
        
        # 显示简要结果
        echo ""
        echo "🎯 测试结果摘要:"
        python -c "
import json
import sys
try:
    with open('$LATEST_RESULT', 'r') as f:
        data = json.load(f)
    stats = data['overall_statistics']
    info = data['test_info']
    print(f'   总样本数: {info[\"total_samples\"]}')
    print(f'   总QA数: {stats[\"total_qa\"]}')
    print(f'   一致性率: {stats[\"consistency_rate\"]:.1%}')
    print(f'   平均准确性: {stats[\"avg_accuracy\"]:.2f}/5')
    print(f'   平均处理时间: {stats[\"avg_processing_time\"]:.2f}s/样本')
    print(f'   总时间: {info[\"total_time\"]:.2f}s')
except Exception as e:
    print(f'   无法读取结果文件: {e}')
"
    fi
    
    # 显示记忆文件信息
    echo ""
    echo "📁 生成的记忆文件:"
    if [ -d "memory" ]; then
        find memory -name "*.md" -type f | sort | while read file; do
            echo "   $file ($(wc -l < "$file") 行)"
        done
    fi
    
    # 显示记忆文件示例
    echo ""
    echo "📖 记忆文件示例 (profile.md):"
    SAMPLE_PROFILE=$(find memory -name "*_profile.md" -type f | head -1)
    if [ -n "$SAMPLE_PROFILE" ]; then
        echo "   文件: $SAMPLE_PROFILE"
        echo "   内容预览:"
        head -20 "$SAMPLE_PROFILE" | sed 's/^/     /'
        echo "     ..."
    fi
    
else
    echo ""
    echo "❌ 测试失败！"
    echo "请检查日志文件获取更多信息"
    exit 1
fi

echo ""
echo "🎉 增强记忆测试完成！"
echo "💡 算法特点:"
echo "   - 每个session后更新记忆文件"
echo "   - 维护角色画像、事件记录、心理状态"
echo "   - QA时合并所有记忆信息"
echo "   - 结构化记忆管理" 