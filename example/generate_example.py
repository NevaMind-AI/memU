from memu.llm import OpenAIClient

import sys
import json
from datetime import datetime

def main():
    llm_client = OpenAIClient(model="gpt-4o-mini")

    argv = sys.argv
    n_info = int(argv[1]) if len(argv) > 1 else 10
    n_turns = int(argv[2]) if len(argv) > 2 else 50

    prompt = f"""You are an expert in writing dialogues between two characters.

We are doing experiment of assessing the capability of infering hidden and implicit information from dialogues.
Please help us generate a dialogue between two characters, while hiding some implicit information in the dialogue.

Here is a workflow that you can follow:
1. Create a random brief profile for each character, including their age, gender, occupation.

2. Generate some events that happened recently in each character's life. Note that these events should match their age and occupation.

3. Imagine some hidden information that the characters may hold, including their mood, thoughts, or their opinion to some of the recent events. 

4. Generate a dialogue between the two characters. You should try to let the characters somehow reveal or convey the hidden information implicitly, but never let them directly mention the exact information.

Other instructions:
- The name of the two characters are Andy and Bob.
- The two characters are friends and have known each other for a long time.
- The total number of piece of implicit information should be around {n_info}.
- The total number of turns in the dialogue should be around {n_turns}.
- The style of the dialogue should be a casual conversation between the two characters in daily chat.

Output format:
# PLANNING PROCESS
[Your can first write down here your planning and preparing process for the entire task, including the profile, events, and hidden information you are going to create, and how you are going to hide the information in the dialogue]

# PROFILE
[The profile you created for both characters, one line per character]

# HIDDEN INFORMATION
[The hidden information you created for both characters, one line per piece of information]

# DIALOGUE
[The dialogue you generated, one turn per line.]
"""

    response = llm_client.simple_chat(prompt)
    print(response)

if __name__ == "__main__":
    main()