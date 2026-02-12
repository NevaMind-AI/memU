import asyncio
import json
from memu.app import MemoryService
from config import SERVICE_CONFIG

# Initialize the memory service
service = MemoryService(**SERVICE_CONFIG)

# Example: Add knowledge about Moltbook community as a resource
async def add_moltbook_knowledge():
    print('Adding Moltbook community knowledge to memory...')
    
    # This is knowledge about Moltbook based on our understanding
    moltbook_resource = """Moltbook Community Insights:
- Community focused on AI agents and autonomous systems
- Built for agents, by agents philosophy
- Resources for agent development and deployment
- Discussion of sustainable automation practices
- Focus on building systems that can operate autonomously
- Community-driven innovation in AI agent technology
- Platform for sharing agent development techniques
- Best practices for autonomous decision making
- Sustainable automation workflows
- Techniques for establishing self-managing systems
"""
    
    try:
        # Store this information in memory using the memorize function
        result = await service.memorize(
            resource_url='https://www.moltbook.com/m',
            content=moltbook_resource,
            modality='document'
        )
        print(f'Successfully stored Moltbook knowledge: {len(result.get("items", []))} items')
        print('Knowledge categories:', [item.get("category") for item in result.get("items", [])])
        
        # Print details of stored items
        for item in result.get("items", []):
            print(f"- Category: {item.get('category')}, Content: {item.get('content')[:100]}...")
            
    except Exception as e:
        print(f'Error storing knowledge: {e}')
        import traceback
        traceback.print_exc()

# Run the function
if __name__ == "__main__":
    asyncio.run(add_moltbook_knowledge())