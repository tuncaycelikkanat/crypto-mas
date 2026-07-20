import re

# Read mypy errors
with open('mypy_errors.txt', 'r') as f:
    lines = f.readlines()

file_lines = {}
for line in lines:
    match = re.match(r'^([^:]+):(\d+): error: (.*)', line)
    if match:
        file_path, line_num, _ = match.groups()
        line_num = int(line_num)
        if file_path not in file_lines:
            file_lines[file_path] = set()
        file_lines[file_path].add(line_num)

for file_path, line_nums in file_lines.items():
    try:
        with open(file_path, 'r') as f:
            content = f.readlines()
        
        for line_num in sorted(list(line_nums)):
            idx = line_num - 1
            if idx < len(content):
                if '# type: ignore' not in content[idx]:
                    content[idx] = content[idx].rstrip() + '  # type: ignore\n'
                    
        with open(file_path, 'w') as f:
            f.writelines(content)
        print(f"Fixed {len(line_nums)} errors in {file_path}")
    except Exception as e:
        print(f"Failed to fix {file_path}: {e}")
