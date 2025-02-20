

import json
import re
import csv
import pandas as pd
import matplotlib.pyplot as plt
from fcapy.context import FormalContext
from fcapy.lattice import ConceptLattice
from fcapy.visualizer import LineVizNx
from copy import deepcopy

# Load JSON config file
with open("config.json", "r", encoding="utf-8") as file:
    CONFIG = json.load(file)


def load_json_files() -> tuple:
    """Loads heuristic and text retrieval JSON files for the selected project."""
    with open(f'./concepts_from_heuristics/{CONFIG["PROJECT_TO_ANALYZE"]}.json', 'r') as file1, \
         open(f'./concepts_from_text_retrieval/{CONFIG["PROJECT_TO_ANALYZE"]}.json', 'r') as file2:
        return json.load(file1), json.load(file2)

def getArrayOfSourceFile(json, concept):
    return list(map(lambda x: x["sourceFile"], json[concept]))

def generate_comparison_results(json1, json2):
    """Compares the two JSON files to find common and unique concepts."""
    keys_file1, keys_file2 = set(json1.keys()), set(json2.keys())
    common_keys = keys_file1 & keys_file2
    unique_to_file1, unique_to_file2 = keys_file1 - keys_file2, keys_file2 - keys_file1

    differences = {
        key: {
            'only_in_file1': list(set(getArrayOfSourceFile(json1, key)) - set(getArrayOfSourceFile(json2, key))),
            'only_in_file2': list(set(getArrayOfSourceFile(json2, key)) - set(getArrayOfSourceFile(json1, key)))
        }
        for key in common_keys if set(getArrayOfSourceFile(json1, key)) != set(getArrayOfSourceFile(json2, key))
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
    filename = f"./results_csv/{CONFIG["PROJECT_TO_ANALYZE"]}.csv"
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


def generate_presence_matrix(json1, json2):
    """
    Generates a CSV matrix mapping files to concepts based on two JSON sources.
    If focus_on_json1 == True, only concepts from json1 are considered.
    """
    # Retrieve all unique concepts and files
    keys_file1, keys_file2 = set(json1.keys()), set(json2.keys())
    all_files = {file for key in keys_file1 for file in getArrayOfSourceFile(json1, key)} | \
                {file for key in keys_file2 for file in getArrayOfSourceFile(json2, key)}

    # Build the file → concept mapping
    concept_mapping = {}
    for file in all_files:
        concept_mapping.setdefault(file, set()).update(
            {key for key in keys_file1 if file in getArrayOfSourceFile(json1, key)},
            {key for key in keys_file2 if file in getArrayOfSourceFile(json2, key)}
        )

    # Determine the concepts to include in the matrix
    if CONFIG["FOCUS_ON_HEURISTIC_CONCEPTS"]:
        all_concepts = sorted([key for key in json2.keys() if key in keys_file1])
    else:
        all_concepts = keys_file1 | keys_file2


    files_of_json1 = {file for key in keys_file1 for file in getArrayOfSourceFile(json1, key)}
    filename = f"./results_matrix/{CONFIG["PROJECT_TO_ANALYZE"]}_presence.csv"

    # Generate the CSV file
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["File", "is_db_file", "is_not_db_file"] + all_concepts)

        for file_name, concepts in concept_mapping.items():
            is_db_file = file_name in files_of_json1
            row = [("db|" if is_db_file else "") + file_name, is_db_file, not is_db_file]
            rowMapping = [concept in concepts for concept in all_concepts]
            if any(rowMapping):
                row.extend(concept in concepts for concept in all_concepts)
                writer.writerow(row)


def generate_occurrence_matrix(json1, json2):
    """
    Generates a CSV matrix that includes:
    1. Aggregated occurrences by file category (DB vs Non-DB).
    2. Individual occurrences per file.
    """

    # Make sure json1 contains only DB concepts
    if not CONFIG["KEEP_DB_CONCEPTS_ONLY_FROM_HEURISTICS"]:
        raise Exception("The parameter 'KEEP_DB_CONCEPTS_ONLY_FROM_HEURISTICS' must be set to True to ensure that json1 contains only DB concepts before generating the occurrence matrix.")

    # Identify DB files
    keys_file1 = set(json1.keys())
    files_of_json1 = {file for key in keys_file1 for file in getArrayOfSourceFile(json1, key)}

    # Retrieve all unique files and concepts
    all_files = {entry["sourceFile"] for concept in json2.values() for entry in concept}
    all_concepts = sorted([key for key in json2.keys() if key in keys_file1])

    # Initialize structures for the matrix
    categories = {"DB Files": {concept: 0 for concept in all_concepts},
                  "Non-DB Files": {concept: 0 for concept in all_concepts}}
    file_concept_matrix = {file: {concept: 0 for concept in all_concepts} for file in all_files}

    # Fill the matrix
    for concept, entries in json2.items():
        if concept in keys_file1:
            for entry in entries:
                file = entry["sourceFile"]
                category = "DB Files" if file in files_of_json1 else "Non-DB Files"

                # Add to categories
                categories[category][concept] += entry["nbOccurence"]

                # Add to individual file data
                file_concept_matrix[file][concept] = entry["nbOccurence"]

    # Generate the CSV file
    output_filename = f"./results_matrix/{CONFIG['PROJECT_TO_ANALYZE']}_occurrence.csv"
    with open(output_filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        
        # Write the header
        writer.writerow(["Category/File"] + all_concepts)

        # Write category data
        for category, concept_counts in categories.items():
            values = [concept_counts[concept] for concept in all_concepts]
            if any(value > 0 for value in values):
                writer.writerow([category] + values)

        # Visual separation between categories and individual files
        writer.writerow([])

        # Write individual file data
        sorted_files = sorted(file_concept_matrix.items(), key=lambda x: x[0] not in files_of_json1)
        for file_name, concept_counts in sorted_files:
            values = [concept_counts[concept] for concept in all_concepts]
            if any(value > 0 for value in values):
                writer.writerow([("db|" if file_name in files_of_json1 else "") + file_name] + values)


def generate_FCA():
    """Generates a Formal Concept Analysis (FCA) lattice from the concept matrix."""
    context = FormalContext.from_pandas(pd.read_csv(f"./results_matrix/{CONFIG["PROJECT_TO_ANALYZE"]}_presence.csv", index_col=0))
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
        lbl = LineVizNx.concept_lattice_label_func(c_i, L, flg_new_extent_count_prefix=False, flg_new_intent_count_prefix=False, max_new_intent_count=10, max_new_extent_count=10)
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
        color_map[frozenset({color_categories[1]})]: 'Related to TEXT RETRIEVAL file only',
        color_map[frozenset({color_categories[0]})]: 'Related to DB file only' if CONFIG["KEEP_DB_CONCEPTS_ONLY_FROM_HEURISTICS"] else 'Related to HEURISTIC file only',
        color_map[frozenset(color_categories)]: 'Related to both'
    }

    fig, ax = plt.subplots(figsize=(15, 7))
    viz.draw_concept_lattice(lattice_no_trivial, ax=ax, flg_drop_bottom_concept=True, node_color=node_colors, node_color_legend=node_color_legend, node_label_func=node_label)
    plt.legend(title='Color coding', fontsize=10, loc='upper right')
    plt.title(f'"Concept location lattice ({CONFIG["PROJECT_TO_ANALYZE"]})\"', size=24)
    plt.tight_layout()
    plt.show()


def main():
    json1, json2 = load_json_files()
    common_keys, unique_to_file1, unique_to_file2, differences = generate_comparison_results(json1, json2)
    
    print_comparison_results(common_keys, unique_to_file1, unique_to_file2, differences)
    generate_csv_report(common_keys, unique_to_file1, unique_to_file2, differences)
    
    generate_presence_matrix(json1, json2)
    generate_FCA()
    
    generate_occurrence_matrix(json1, json2)


if __name__ == "__main__":
    main()