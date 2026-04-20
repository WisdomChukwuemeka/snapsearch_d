import re

with open(".env", "r", encoding="utf-8") as f:
    lines = f.readlines()

fixed_lines = []
inside_key = False
key_lines = []

for line in lines:
    if line.startswith("SCP_PRIVATE_KEY="):
        inside_key = True
        key_lines = [line.rstrip("\n")]
        # Check if it closes on the same line
        stripped = line.strip()
        if stripped.count('"') >= 2 and stripped.endswith('"'):
            inside_key = False
            fixed_lines.append(line)
            key_lines = []
    elif inside_key:
        key_lines.append(line.rstrip("\n"))
        if line.strip().endswith('"'):
            inside_key = False
            # Join all lines into one, replacing real newlines with \n
            full = "\n".join(key_lines)
            # Extract just the value between first and last quote
            match = re.search(r'SCP_PRIVATE_KEY="([\s\S]+)"', full)
            if match:
                key_value = match.group(1).replace("\n", "\\n")
                fixed_lines.append(f'SCP_PRIVATE_KEY="{key_value}"\n')
            else:
                fixed_lines.append(full + "\n")
            key_lines = []
    else:
        fixed_lines.append(line)

with open(".env", "w", encoding="utf-8") as f:
    f.writelines(fixed_lines)

print("Done. SCP_PRIVATE_KEY is now on a single line.")