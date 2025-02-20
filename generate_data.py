import json
import re

# Load JSON config file
with open("config.json", "r", encoding="utf-8") as file:
    CONFIG = json.load(file)

# Current project being generated
current_project_generated = None


def normalize_path(path: str) -> str:
    """
    Normalizes a file path by:
    1. Replacing backslashes with slashes.
    2. Removing anything after '#' (inclusive).
    3. Keeping only the portion after the project root.
    """
    path = path.replace('\\', '/').split('#')[0]
    match = re.search(re.escape(current_project_generated) + r'/(.*)', path)
    return match.group(1) if match else path


def find_all_concepts_heuristics(data):
    """Retrieves all unique concepts from the given data."""
    return search_heuristics(data)


def find_locations_heuristics(data, concept_name):
    """Finds locations where a specific concept appears."""
    return search_heuristics(data, concept_name)


def search_heuristics(data, concept_name=None, key="concepts", location_key="location"):
    """
    Searches for concepts in the given data.

    :param data: The input data containing concepts.
    :param concept_name: A specific concept to search for (optional).
    :param key: The key in the data where concepts are stored (default: "concepts").
    :param location_key: The key indicating the location of a concept (default: "location").
    :return: A list of locations (if concept_name is provided) or a list of unique concepts.
    """
    results = []

    def traverse(obj):
        if key in obj:
            if not CONFIG["KEEP_DB_CONCEPTS_ONLY_FROM_HEURISTICS"] or (("technology" in obj) and ("express" not in obj["technology"]["id"])):
                for item in obj[key]:
                        for concept in item['name'].split():
                            if concept_name:
                                if concept == concept_name and obj.get(location_key) not in list(map(lambda x: x["sourceFile"], results)):
                                    results.append({
                                        "sourceFile": normalize_path(obj.get(location_key))
                                    })
                            else:
                                if concept not in results:
                                    results.append(concept)

        for child_key in ['directories', 'files', 'codeFragments']:
            for sub_obj in obj.get(child_key, []):
                traverse(sub_obj)

    for item in data:
        traverse(item)

    return results


def find_all_concepts_text_retrieval(data):
    """Retrieves all unique concepts from text retrieval data."""
    results = set()

    def traverse(obj):
        if 'tokens' in obj:
            for token in obj["tokens"]:
                for concept in token['concept'].split():
                    results.add(concept)

    for file_data in data:
        for obj in file_data:
            traverse(obj)

    return list(results)


def find_locations_text_retrieval(data, concept_name):
    """Finds file locations where a specific concept appears in text retrieval data."""
    locations = []
    for file_data in data[0]:
        for token in file_data["tokens"]:
            if token["concept"] == concept_name and file_data["file"] not in list(map(lambda x: x["sourceFile"], locations)):
                print(token)
                locations.append({
                    "sourceFile": normalize_path(file_data["file"]),
                    "nbOccurence": token["nbOccurence"]
                })
    return locations


def process_project_data(source_path, output_path, find_all, find_locations):
    """
    Processes data for a given project, extracts concepts, and saves results.

    :param project: The name of the project.
    :param source_path: Path to the source JSON file.
    :param output_path: Path to save the extracted concepts.
    :param find_all: Function to find all concepts in the data.
    :param find_locations: Function to find locations of a given concept.
    """
    with open(source_path.format(current_project_generated), 'r') as file:
        data = json.load(file)

    results = {concept: find_locations(data, concept) for concept in find_all(data)}

    # Display results
    for concept, locations in results.items():
        print(f"Locations found for concept '{concept}':")
        print(json.dumps(locations, indent=2))

    with open(output_path.format(current_project_generated), 'w') as output_file:
        json.dump(results, output_file, indent=2)


def main():
    for project in CONFIG["PROJECTS_TO_GENERATE"]:

        # Set current project generated
        global current_project_generated
        current_project_generated = project

        # Process Heuristics
        process_project_data(
            './raw_response_from_heuristics/results_{}.json',
            './concepts_from_heuristics/{}.json',
            find_all_concepts_heuristics,
            find_locations_heuristics
        )

        # Process Text Retrieval
        process_project_data(
            './raw_response_from_text-retrieval/results_{}.json',
            './concepts_from_text_retrieval/{}.json',
            find_all_concepts_text_retrieval,
            find_locations_text_retrieval
        )
        

if __name__ == "__main__":
    main()