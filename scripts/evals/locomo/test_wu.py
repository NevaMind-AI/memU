
import json

def check_data():
    with open("data/locomo10.json", "r") as f:
        raw = json.load(f)

    res = {}
    for idx, item in enumerate(raw):
        conversation = item["conversation"] 
        speaker_a = conversation["speaker_a"]
        speaker_b = conversation["speaker_b"]
        # print(idx, speaker_a, speaker_b)
        times = []
        for key in conversation:
            if key.startswith("session") and key.endswith("date_time"):
                if key.replace("_date_time", "") in conversation:
                    # print(key, conversation[key])
                    times.append(conversation[key])
        # print()

        res[speaker_a] = times
        res[speaker_b] = times
    return res

def check_event_memory(res):
    for name, dates in res.items():
        try :
            with open(f"memory_debug/{name}_events.txt", "r") as f:
                events = f.read()
                print(name)
                for date in dates:
                    if date in events:
                        print(date.rjust(30), "YES")
                    else:
                        print(date.rjust(30), "NO")
                print()
        except Exception as e:
            print(name, "not found")

from mem_agent import MemAgent

def main():
    res = check_data()
    check_event_memory(res)

if __name__ == "__main__":
    main()