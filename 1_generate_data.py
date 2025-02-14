import json

def search(data, concept_name=None):
    results = []

    def traverse(obj):
        # If 'concepts' is present, search for concepts
        if 'concepts' in obj:
            for concept in obj["concepts"]:
                # If searching for a specific concept
                conceptSplits = concept['name'].split(" ")
                for conceptSplit in conceptSplits:
                    if concept_name:
                        if conceptSplit == concept_name:
                            results.append(obj.get("location"))
                    # If searching for all concepts, add them if not already present
                    elif conceptSplit not in results:
                        results.append(conceptSplit)

        # Traverse directories, files, and code fragments
        for key in ['directories', 'files', 'codeFragments']:
            if key in obj:
                for sub_obj in obj[key]:
                    traverse(sub_obj)

    # Iterate over data elements
    for item in data:
        traverse(item)

    return results


# Function to retrieve all concepts from the data
def find_all_concepts(data):
    return search(data)


# Function to search for objects containing a specific concept
def find_locations(data, concept_name):
    return search(data, concept_name)


if __name__ == "__main__":

    # Projects to analyze
    projects = ["overleaf-main", "robot-shop-master", "cinema-microservice-master"]

    # Load JSON data from a file
    for project in projects:

        with open(f'./raw_response_from_heuristics/results_{project}.json', 'r') as file:
            data = json.load(file)

        results = {}
        for concept in find_all_concepts(data):
            found_locations = find_locations(data, concept)

            # Display results
            print("Locations found for concept '" + concept + "':")
            results[concept] = found_locations
            for obj in found_locations:
                print(json.dumps(obj, indent=2))

        with open(f'./concepts_from_heuristics/{project}.json', 'w') as output_file:
            json.dump(results, output_file, indent=2)
