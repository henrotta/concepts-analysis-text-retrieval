import json


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
    results = set()

    def traverse(obj):
        if key in obj:
            for item in obj[key]:
                for concept in item['name'].split():
                    if concept_name:
                        if concept == concept_name:
                            results.add(obj.get(location_key))
                    else:
                        results.add(concept)

        for child_key in ['directories', 'files', 'codeFragments']:
            for sub_obj in obj.get(child_key, []):
                traverse(sub_obj)

    for item in data:
        traverse(item)

    return list(results)


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
    locations = set()
    for file_data in data[0]:
        for token in file_data["tokens"]:
            if token["concept"] == concept_name:
                locations.add(file_data["file"])
    return list(locations)


def process_project_data(project, source_path, output_path, find_all, find_locations):
    """
    Processes data for a given project, extracts concepts, and saves results.

    :param project: The name of the project.
    :param source_path: Path to the source JSON file.
    :param output_path: Path to save the extracted concepts.
    :param find_all: Function to find all concepts in the data.
    :param find_locations: Function to find locations of a given concept.
    """
    with open(source_path.format(project), 'r') as file:
        data = json.load(file)

    results = {concept: find_locations(data, concept) for concept in find_all(data)}

    # Display results
    for concept, locations in results.items():
        print(f"Locations found for concept '{concept}':")
        print(json.dumps(locations, indent=2))

    with open(output_path.format(project), 'w') as output_file:
        json.dump(results, output_file, indent=2)


if __name__ == "__main__":
    projects = ["robot-shop-master", "cinema-microservice-master", "overleaf-main"]

    for project in projects:
        # Process Heuristics
        process_project_data(
            project,
            './raw_response_from_heuristics/results_{}.json',
            './concepts_from_heuristics/{}.json',
            find_all_concepts_heuristics,
            find_locations_heuristics
        )

        # Process Text Retrieval
        process_project_data(
            project,
            './raw_response_from_text-retrieval/results_{}.json',
            './concepts_from_text_retrieval/{}.json',
            find_all_concepts_text_retrieval,
            find_locations_text_retrieval
        )
