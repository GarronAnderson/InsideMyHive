import json


def handle_crash(data, filename="reload.json"):
    with open(filename, "w") as f:
        json.dump(data, f)


def crash_recovery(filename="reload.json"):
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


# Example usage
# Save the data
handle_crash({"data": ["Test: 1", "Test: 2"], "last_tx": "12:30 PM"})

# Reload the data
reloaded_data = crash_recovery()
print(reloaded_data)
