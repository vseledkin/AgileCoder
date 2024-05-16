import html
import logging
import re
import time

import markdown
import inspect
from agilecoder.camel.messages.system_messages import SystemMessage
from agilecoder.online_log.app import send_msg, send_online_log


import ast
import os
import glob
class ClassCollector(ast.NodeVisitor):
    def __init__(self):
        self.classes = []

    def visit_ClassDef(self, node):
        self.classes.append(node.name)
        self.generic_visit(node)

def get_classes_in_file(file_path):
    with open(file_path, 'r') as file:
        try:
            tree = ast.parse(file.read(), filename=file_path)
        except SyntaxError as e:
            print(f"Syntax error in file {file_path}: {e}")
            return None

    class_collector = ClassCollector()
    class_collector.visit(tree)

    return class_collector.classes
def get_classes_in_folder(folder_path):
    paths = glob.glob(f'{folder_path}/*.py')
    outputs = {}
    for path in paths:
        outputs[os.path.basename(path)] = get_classes_in_file(path)
    return outputs

def now():
    return time.strftime("%Y%m%d%H%M%S", time.localtime())


def log_and_print_online(role, content=None):
    if not content:
        logging.info(role + "\n")
        send_online_log(logging.root.handlers[-1].buffer[-1])
        send_msg("System", role)
        # print(role + "\n")
    else:
        # print(str(role) + ": " + str(content) + "\n")
        logging.info(str(role) + ": " + str(content) + "\n")
        send_online_log(logging.root.handlers[-1].buffer[-1])
        if isinstance(content, SystemMessage):
            records_kv = []
            content.meta_dict["content"] = content.content
            for key in content.meta_dict:
                value = content.meta_dict[key]
                value = str(value) 
                value = html.unescape(value)
                value = markdown.markdown(value)
                value = re.sub(r'<[^>]*>', '', value)
                value = value.replace("\n", " ")
                records_kv.append([key, value])
            content = "**[SystemMessage**]\n\n" + convert_to_markdown_table(records_kv)
        else:
            role = str(role)
            content = str(content)
        send_msg(role, content)


def convert_to_markdown_table(records_kv):
    # Create the Markdown table header
    header = "| Parameter | Value |\n| --- | --- |"

    # Create the Markdown table rows
    rows = [f"| **{key}** | {value} |" for (key, value) in records_kv]

    # Combine the header and rows to form the final Markdown table
    markdown_table = header + "\n" + '\n'.join(rows)

    return markdown_table


def log_arguments(func):
    def wrapper(*args, **kwargs):
        sig = inspect.signature(func)
        params = sig.parameters

        all_args = {}
        all_args.update({name: value for name, value in zip(params.keys(), args)})
        all_args.update(kwargs)

        records_kv = []
        for name, value in all_args.items():
            if name in ["self", "chat_env", "task_type"]:
                continue
            value = str(value)
            value = html.unescape(value)
            value = markdown.markdown(value)
            value = re.sub(r'<[^>]*>', '', value)
            value = value.replace("\n", " ")
            records_kv.append([name, value])
        records = f"**[{func.__name__}]**\n\n" + convert_to_markdown_table(records_kv)
        # log_and_print_online("System", records)

        return func(*args, **kwargs)

    return wrapper

def extract_product_requirements(input, is_product = True):
    lines = input.splitlines()
    if is_product:
        keyword1 = 'product backlog'
        keyword2 = 'acceptance criteria'
    else:
        keyword1 = 'sprint backlog'
        keyword2 = 'sprint acceptance criteria'
    backlog, acceptance_criteria = [], []
    backlog_flag, criteria_flag = False, False
    for line in lines:
        _line = line.replace("_", ' ').lower()
        if keyword1 in _line:
            backlog_flag = True
            criteria_flag = False
            continue
        if keyword2 in _line:
            backlog_flag = False
            criteria_flag = True
            continue
        if backlog_flag:
            backlog.append(line)
        if criteria_flag:
            acceptance_criteria.append(line)
        if len(backlog) and len(acceptance_criteria) and len(_line.strip()) == 0: break
    return backlog, acceptance_criteria

def get_non_leaf_and_intermediate_files(adj_list):
    all_deps = []
    for node, deps in adj_list.items():
        if node.startswith('test_') or node.endswith('_test'): continue
        all_deps.extend(deps)
    return [node for node in adj_list if node not in all_deps and not (node.startswith('test_') or node.endswith('_test'))]