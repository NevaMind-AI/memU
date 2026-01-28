memorize_config = {
    "memory_types": [
        "record",
    ],
    "memory_type_prompts": {
        "record": {
            "objective": {
                "ordinal": 10,
                "prompt": "# Task Objective\nYou will be given a conversation between a user and an coding agent. Your goal is to extract detailed records for what are planed to do, and what have been done.",
            },
            "workflow": {
                "ordinal": 20,
                "prompt": "# Workflow\nRead through the conversation and extract records. You should expecially focus on:\n- What the user ask the agent to do\n- What plan does the agent suggest\n- What the agent has done",
            },
            "rules": {
                "ordinal": -1,
                "prompt": None,
            },
            "examples": {
                "ordinal": 60,
                "prompt": "# Example\n## Output\n<item>\n    <memory>\n        <content>The user ask the agent to generate a code example for fastapi</content>\n        <categories>\n            <category>todo</category>\n        </categories>\n    </memory>\n    <memory>\n        <content>The agent suggest to use the code example from the document</content>\n        <categories>\n            <category>todo</category>\n        </categories>\n    </memory>\n    <memory>\n        <content>The agent ask the user to specify the response type</content>\n        <categories>\n            <category>todo</category>\n        </categories>\n    </memory>\n</item>",
            },
        }
    },
    "memory_categories": [
        {
            "name": "todo",
            "description": "This file traces the latest status of the task. All records should be included in this file.",
            "target_length": None,
            "custom_prompt": {
                "objective": {
                    "ordinal": 10,
                    "prompt": "# Task Objective\nYou are a specialist in task management. You should update the markdown file to reflect the latest status of the task.",
                },
                "workflow": {
                    "ordinal": 20,
                    "prompt": "# Workflow\nRead through the existing markdown file and the new records. Then update the markdown file to reflect:\n- What existing tasks are completed\n- What new tasks are added\n- What tasks are still in progress",
                },
                "rules": {
                    "ordinal": 30,
                    "prompt": "# Rules\nFor each action-like record, explictly mark it as [Done] or [Todo].",
                },
                "examples": {
                    "ordinal": 50,
                    "prompt": "# Example\n## Output\n```markdown\n# Task\n## Task Objective\nThe user ask the agent to generate a code example for fastapi\n## Breakdown\n- [Done] The agent suggest to use the code example from the document\n- [Todo] The agent ask the user to specify the response type\n```",
                },
            },
        }
    ],
}

retrieve_config = {
    "method": "rag",
    "route_intention": False,
    "sufficiency_check": False,
    "category": {
        "enabled": False,
    },
    "item": {
        "enabled": True,
        "top_k": 10,
    },
    "resource": {
        "enabled": False,
    },
}
