#!/usr/bin/env python3
"""生成 docsify 侧边栏 _sidebar.md（递归任意深度，正确缩进，路径自动 URL 编码）"""

import argparse, json, os, fnmatch
from urllib.parse import quote


def get_entry_mtime(root: str, name: str) -> float:
    """获取文件或目录的最新修改时间（目录取内部文件最大 mtime）"""
    full = os.path.join(root, name)
    if os.path.isfile(full):
        return os.path.getmtime(full)
    max_mtime = 0.0
    for dirpath, _, filenames in os.walk(full):
        for f in filenames:
            try:
                mtime = os.path.getmtime(os.path.join(dirpath, f))
                if mtime > max_mtime:
                    max_mtime = mtime
            except OSError:
                continue
    return max_mtime


def should_include(name: str, is_dir: bool, config: dict) -> bool:
    """根据配置判断是否包含某个文件或目录（不区分大小写）"""
    name_lower = name.lower()
    if is_dir and 'include_dirs' in config:
        if name_lower in [d.lower() for d in config['include_dirs']]:
            return True
    if not is_dir and 'include_files' in config:
        for p in config['include_files']:
            if fnmatch.fnmatch(name_lower, p.lower()):
                return True
    if is_dir and 'exclude_dirs' in config:
        if name_lower in [d.lower() for d in config['exclude_dirs']]:
            return False
    if not is_dir and 'exclude_files' in config:
        for p in config['exclude_files']:
            if fnmatch.fnmatch(name_lower, p.lower()):
                return False
    return not (name_lower.startswith('.') or name_lower == '_sidebar.md')


def generate_auto_sidebar(root: str, config: dict, title: str) -> str:
    """递归扫描目录，生成正确缩进的层级侧边栏，并对路径进行 URL 编码"""
    lines = []
    if title:
        lines.append(f"# {title}\n")

    def process_dir(current_root: str, depth: int):
        out = []
        try:
            entries = os.listdir(current_root)
        except (FileNotFoundError, PermissionError):
            return out

        sub_dirs = []
        md_files = []
        for name in entries:
            full = os.path.join(current_root, name)
            is_dir = os.path.isdir(full)
            if not should_include(name, is_dir, config):
                continue
            if is_dir:
                sub_dirs.append(name)
            elif name.endswith('.md'):
                md_files.append(name)

        has_readme = 'README.md' in md_files
        link_readme = config.get('link_dirs_to_readme', False)
        if has_readme and link_readme:
            md_files.remove('README.md')

        sub_dirs.sort(key=lambda d: get_entry_mtime(current_root, d), reverse=True)
        md_files.sort(key=lambda f: get_entry_mtime(current_root, f), reverse=True)

        skip_empty = config.get('skip_empty_dirs', True)
        if skip_empty and not sub_dirs and not md_files:
            return out

        dir_indent = "  " * (depth - 1) if depth > 0 else ""
        file_indent = "  " * depth

        if depth > 0:
            dir_name = os.path.basename(current_root)
            rel_dir = os.path.relpath(current_root, root).replace(os.sep, '/')
            # URL 编码路径
            rel_dir_encoded = quote(rel_dir, safe='/')
            if has_readme and link_readme:
                entry = f"{dir_indent}- [{dir_name}]({rel_dir_encoded}/README.md)"
            else:
                entry = f"{dir_indent}- **{dir_name}**"
            out.append(entry)

        for d in sub_dirs:
            out.extend(process_dir(os.path.join(current_root, d), depth + 1))

        for f in md_files:
            rel_path = os.path.relpath(os.path.join(current_root, f), root).replace(os.sep, '/')
            rel_path_encoded = quote(rel_path, safe='/')  # 编码空格等特殊字符
            display = f[:-3]
            out.append(f"{file_indent}- [{display}]({rel_path_encoded})")

        return out

    root_lines = process_dir(os.path.abspath(root), 0)
    lines.extend(root_lines)
    return '\n'.join(lines) + '\n'


def generate_custom_sidebar(custom_structure: list, title: str) -> str:
    """根据自定义 JSON 生成侧边栏，用户需自行处理路径编码"""
    lines = []
    if title:
        lines.append(f"# {title}\n")
    for item in custom_structure:
        if isinstance(item, str):
            lines.append(item)
        elif isinstance(item, dict):
            title_text = item.get('title', '')
            path = item.get('path', '')
            # 可选：对自定义路径也进行编码（如果用户需要）
            # path_encoded = quote(path, safe='/')
            lines.append(f"- [{title_text}]({path})")
        else:
            lines.append(str(item))
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description='生成 docsify 侧边栏')
    parser.add_argument('--root', default='.', help='扫描根目录')
    parser.add_argument('--output', default='_sidebar.md', help='输出文件')
    parser.add_argument('--title', default='', help='侧边栏标题')
    parser.add_argument('--config-json', default='{}', help='配置 JSON 字符串')
    args = parser.parse_args()

    try:
        config = json.loads(args.config_json)
    except json.JSONDecodeError as e:
        print(f"❌ 配置 JSON 解析失败: {e}")
        config = {}

    if 'custom_sidebar' in config:
        content = generate_custom_sidebar(config['custom_sidebar'], args.title)
    else:
        content = generate_auto_sidebar(args.root, config, args.title)

    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ 侧边栏已生成：{args.output}")


if __name__ == '__main__':
    main()
