

import json
import re
import csv
import pandas as pd
import matplotlib.pyplot as plt
from fcapy.context import FormalContext
from fcapy.lattice import ConceptLattice
from fcapy.visualizer import LineVizNx
from copy import deepcopy


# Define the project to analyze (uncomment the desired project)
# PROJECT_TO_ANALYZE = "robot-shop-master"
PROJECT_TO_ANALYZE = "cinema-microservice-master"
# PROJECT_TO_ANALYZE = "overleaf-main"



def normalize_path(path: str) -> str:
    """
    Normalizes a file path by:
    1. Replacing backslashes with slashes.
    2. Removing anything after '#' (inclusive).
    3. Keeping only the portion after the project root.
    """
    path = path.replace('\\', '/').split('#')[0]
    match = re.search(re.escape(PROJECT_TO_ANALYZE) + r'/(.*)', path)
    return match.group(1) if match else path


def load_json_files() -> tuple:
    """Loads heuristic and text retrieval JSON files for the selected project."""
    with open(f'./concepts_from_heuristics/{PROJECT_TO_ANALYZE}.json', 'r') as file1, \
         open(f'./concepts_from_text_retrieval/{PROJECT_TO_ANALYZE}.json', 'r') as file2:
        return json.load(file1), json.load(file2)


def generate_comparison_results(json1, json2):
    """Compares the two JSON files to find common and unique concepts."""
    keys_file1, keys_file2 = set(json1.keys()), set(json2.keys())
    common_keys = keys_file1 & keys_file2
    unique_to_file1, unique_to_file2 = keys_file1 - keys_file2, keys_file2 - keys_file1

    differences = {
        key: {
            'only_in_file1': list(set(map(normalize_path, json1[key])) - set(map(normalize_path, json2[key]))),
            'only_in_file2': list(set(map(normalize_path, json2[key])) - set(map(normalize_path, json1[key])))
        }
        for key in common_keys if set(map(normalize_path, json1[key])) != set(map(normalize_path, json2[key]))
    }

    return common_keys, unique_to_file1, unique_to_file2, differences


def print_comparison_results(common_keys, unique_to_file1, unique_to_file2, differences):
    """Prints a summary of the comparison results."""
    print(f"=== Common concepts ===\n{common_keys}")
    print(f"\n=== Unique to heuristic ===\n{unique_to_file1}")
    print(f"\n=== Unique to text retrieval ===\n{unique_to_file2}")

    if differences:
        print("\n=== Differences in common concepts ===")
        for key, diff in differences.items():
            print(f"Concept: {key}")
            if diff['only_in_file1']:
                print(f"  Only in HEURISTIC: {diff['only_in_file1']}")
            if diff['only_in_file2']:
                print(f"  Only in TEXT_RETRIEVAL: {diff['only_in_file2']}")
    else:
        print("\nNo differences found in common concepts.")


def generate_csv_report(common_keys, unique_to_file1, unique_to_file2, differences):
    """Generates a CSV file summarizing the comparison results."""
    filename = f"./results_csv/{PROJECT_TO_ANALYZE}.csv"
    rows = []

    for concept in common_keys | unique_to_file1 | unique_to_file2:
        in_heuristic, in_text_retrieval = concept in common_keys or concept in unique_to_file1, concept in common_keys or concept in unique_to_file2
        file1_files = ";".join(differences.get(concept, {}).get("only_in_file1", [])) or "None"
        file2_files = ";".join(differences.get(concept, {}).get("only_in_file2", [])) or "None"
        rows.append([concept, in_heuristic, in_text_retrieval, file1_files, file2_files])

    rows.sort(key=lambda x: (not x[1], not x[2], x[0]))

    with open(filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["Concept", "Present in HEURISTIC", "Present in TEXT_RETRIEVAL", "Files only in HEURISTIC", "Files only in TEXT_RETRIEVAL"])
        writer.writerows(rows)


def generate_matrix(json1, json2, focus_on_json1=False):
    """
    Generates a CSV matrix mapping files to concepts based on two JSON sources.
    If focus_on_json1 == True, only concepts from json1 are considered.
    """
    # Retrieve all unique concepts and files
    keys_file1, keys_file2 = set(json1.keys()), set(json2.keys())
    all_files = {file for key in keys_file1 for file in json1[key]} | \
                {file for key in keys_file2 for file in json2[key]}

    # Build the file → concept mapping
    concept_mapping = {}
    for file in all_files:
        normalized_file = normalize_path(file)
        concept_mapping.setdefault(normalized_file, set()).update(
            {key for key in keys_file1 if file in json1[key]},
            {key for key in keys_file2 if file in json2[key]}
        )

    # Determine the concepts to include in the matrix
    all_concepts = sorted(keys_file1 if focus_on_json1 else keys_file1 | keys_file2)

    # Normalize files from json1 to identify database-related files
    files_of_json1 = {normalize_path(file) for key in keys_file1 for file in json1[key]}
    filename = f"./results_matrix/{PROJECT_TO_ANALYZE}.csv"

    # Generate the CSV file
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["File", "is_db_file", "is_not_db_file"] + all_concepts)

        for file_name, concepts in concept_mapping.items():
            is_db_file = file_name in files_of_json1
            row = [("db|" if is_db_file else "") + file_name, is_db_file, not is_db_file]

            row.extend(concept in concepts for concept in all_concepts)
            writer.writerow(row)


def generate_FCA():
    """Generates a Formal Concept Analysis (FCA) lattice from the concept matrix."""
    context = FormalContext.from_pandas(pd.read_csv(f"./results_matrix/{PROJECT_TO_ANALYZE}.csv", index_col=0))
    lattice = ConceptLattice.from_context(context)

    color_categories = ('is_db_file', 'is_not_db_file')
    lattice_no_trivial = deepcopy(lattice)
    top_concepts = [c for c in lattice_no_trivial if not c.intent]

    for concept in lattice:
        if concept in top_concepts:
            continue
        if set(concept.intent) - set(color_categories) == set(top_concepts[0].intent):
            lattice_no_trivial.remove(concept)


    def node_label(c_i, L, color_categories=color_categories):
        lbl = LineVizNx.concept_lattice_label_func(c_i, L, flg_new_extent_count_prefix=False, flg_new_intent_count_prefix=False)
        for category in color_categories:
            lbl = lbl.replace(category, '')
        return lbl.replace(',', '')

    viz = LineVizNx(node_label_font_size=14)
    color_map = {
        frozenset(color_categories): viz.node_color,
        frozenset({color_categories[0]}): 'navy',
        frozenset({color_categories[1]}): 'orange'
    }

    node_colors = [color_map.get(frozenset(c.intent) & frozenset(color_categories), viz.node_color) for c in lattice_no_trivial]
    node_color_legend = {
        color_map[frozenset({color_categories[1]})]: 'Related to NON DB file only',
        color_map[frozenset({color_categories[0]})]: 'Related to DB file only',
        color_map[frozenset(color_categories)]: 'Related to both'
    }

    fig, ax = plt.subplots(figsize=(15, 7))
    viz.draw_concept_lattice(lattice_no_trivial, ax=ax, flg_drop_bottom_concept=True, node_color=node_colors, node_color_legend=node_color_legend, node_label_func=node_label)
    plt.legend(title='Color coding', fontsize=10, loc='upper right')
    plt.title('"Concept location lattice"', size=24)
    plt.tight_layout()
    plt.show()



if __name__ == "__main__":
    json1, json2 = load_json_files()
    common_keys, unique_to_file1, unique_to_file2, differences = generate_comparison_results(json1, json2)
    print_comparison_results(common_keys, unique_to_file1, unique_to_file2, differences)
    generate_csv_report(common_keys, unique_to_file1, unique_to_file2, differences)
    generate_matrix(json1, json2, focus_on_json1=True)
    generate_FCA()