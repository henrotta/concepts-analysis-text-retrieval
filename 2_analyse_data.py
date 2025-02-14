

import json
import re
import csv
import pandas as pd
import matplotlib.pyplot as plt
from fcapy.context import FormalContext
from fcapy.lattice import ConceptLattice
from fcapy.visualizer import LineVizNx
from copy import deepcopy



# project_to_analyse = "cinema-microservice-master"
project_to_analyse = "robot-shop-master"
# project_to_analyse = "overleaf-main"





# concepts_to_focus = {"overleaf-main": ['project', 'doc deleted', 'doc', 'range', 'deleted', 'raw', 'peek', 'archive', 'unarchive', 'destroy', 'health check', 'status', 'doc ops', 'clear state', 'flush', 'history', 'resync', 'change', 'accept', 'comment', 'total', 'redis', 'redis cluster', 'doc snapshot', 'master', 'applied ops', 'room', 'message', 'thread', 'edit', 'resolve', 'reopen', 'env', 'compile', 'stop', 'sync', 'code', 'pdf', 'wordcount', 'user', 'build', 'content', 'output', 'oops', 'oops internal', 'smoke test force', 'state', 'up', 'down', 'maint', 'contact', 'file', 'template', 'public', 'size', 'bucket', 'key', 'notification', 'client', 'drain', 'disconnect', 'debug', 'event', 'editor events', 'cluster continual traffic', 'check', 'learn', 'unlearn', 'spelling preference', 'tag', 'rename', 'diff', 'update', 'export', 'version', 'restore', 'push', 'pull', 'all', 'dangling', 'pack', 'check lock', 'doc history', 'project history meta data', 'doc history index']
#      ,
#      "robot-shop-master": ["product", "cart", "shipping", "category", "metric", "health", "rename", "add", "update", "search", "user", "order", "history", "register", "login", "check", "uniqueid"]
#      , "cinema-microservice-master": ["booking", "verify", "payment", "make", "purchase", "notification", "send", "email", "ticket", "cinema", "movie", "premiere"]
# }


def normalize_path(path):
    """
    Normalise le chemin en :
    1. Remplaçant les backslashes par des slashes.
    2. Supprimant la partie après '#' (inclus).
    3. Conservant uniquement la partie après 'robot-shop-master'.
    """
    path = path.replace('\\', '/')
    
    # Retirer tout ce qui suit le caractère '#'
    path = path.split('#')[0]
    
    # Extraire uniquement la partie après le projet dans le chemin
    match = re.search(re.escape(project_to_analyse)+r'/(.*)', path)
    return match.group(1) if match else path









def main():
    # Charger les fichiers JSON
    with open(f'./concepts_from_heuristics/{project_to_analyse}.json', 'r') as file1:
        json1 = json.load(file1)

    with open(f'./concepts_from_text_retrieval/{project_to_analyse}.json', 'r') as file2:
        json2 = json.load(file2)

    main_generate_csv(json1, json2)
    main_generate_matrix(json1, json2)
    main_generate_FCA()


def main_generate_csv(json1, json2):
    # Trouver les concepts communs et uniques
    keys_file1 = set(json1.keys())
    keys_file2 = set(json2.keys())

    common_keys = keys_file1 & keys_file2
    unique_to_file1 = keys_file1 - keys_file2
    unique_to_file2 = keys_file2 - keys_file1

    # Comparer les listes des concepts communs en normalisant les chemins
    differences = {}

    for key in common_keys:
        list1_normalized = set([normalize_path(path) for path in json1[key]])
        list2_normalized = set([normalize_path(path) for path in json2[key]])

        if list1_normalized != list2_normalized:
            differences[key] = {
                'only_in_file1': list(list1_normalized - list2_normalized),
                'only_in_file2': list(list2_normalized - list1_normalized)
            }
        else:
            print(f"Pas de différence pour le concept : {key}")

    # Affichage des résultats
    print("=== Concepts communs ===")
    print(common_keys)

    print("\n=== Concepts uniques à fichier1 (heuristiques) ===")
    print(unique_to_file1)

    print("\n=== Concepts uniques à fichier2 (text retrieval) ===")
    print(unique_to_file2)

    if differences:
        print("\n=== Différences dans les concepts communs ===")
        for key, diff in differences.items():
            print(f"Concept : {key}")
            if diff['only_in_file1']:
                print(f"  Fichiers présents uniquement dans HEURISTIQUE : {diff['only_in_file1']}")
            if diff['only_in_file2']:
                print(f"  Fichiers présents uniquement dans TEXT_RETRIEVAL : {diff['only_in_file2']}")
    else:
        print("\nAucune différence trouvée dans les concepts communs.")

    # Génération du fichier csv
    generate_csv(keys_file1, keys_file2, unique_to_file1, unique_to_file2, differences)

# Fonction pour générer le CSV
def generate_csv(keys_file1, keys_file2, unique_to_file1, unique_to_file2, differences, filename=f"./results_csv/{project_to_analyse}.csv"):
    rows = []

    # Préparer les lignes pour le CSV
    for concept in keys_file1.union(keys_file2):
        concept_is_common = concept in keys_file1 & keys_file2
        if concept_is_common and concept in differences:
            separator = ";"
            file1_files = separator.join(differences[concept]["only_in_file1"]) or "None"
            file2_files = separator.join(differences[concept]["only_in_file2"]) or "None"
            rows.append([concept, concept not in unique_to_file2, concept not in unique_to_file1, file1_files, file2_files])
        else:
            rows.append([concept, concept not in unique_to_file2, concept not in unique_to_file1, "None", "None"])

    # Trier les lignes par "Présent dans fichier 1" puis "Présent dans fichier 2"
    rows.sort(key=lambda x: (not x[1], not x[2], x[0]))

    # Écriture des résultats triés dans le fichier CSV
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["Concept", "Présent dans HEURISTIQUE", "Présent dans TEXT_RETRIEVAL", "Fichiers uniquement dans HEURISTIQUE", "Fichiers uniquement dans TEXT_RETRIEVAL"])
        writer.writerows(rows)


def main_generate_matrix(json1, json2):
    # Trouver les concepts de chaque fichier JSON
    keys_file1 = set(json1.keys())
    keys_file2 = set(json2.keys())

    # Récupérer tous les fichiers uniques à partir des deux JSON
    all_files = set(file for key in keys_file1 for file in json1[key]) | set(file for key in keys_file2 for file in json2[key])
    
    print(all_files)

    # Associer chaque fichier normalisé à ses concepts
    concepts_by_file = {}

    for file in all_files:
        normalized_file = normalize_path(file)
        concepts_by_file.setdefault(normalized_file, [])

        # Ajouter les concepts provenant de json1
        concepts_by_file[normalized_file].extend(
            [key for key in keys_file1 if file in json1[key] and key not in concepts_by_file[normalized_file]]
        )

        # Ajouter les concepts provenant de json2
        concepts_by_file[normalized_file].extend(
            [key for key in keys_file2 if file in json2[key] and key not in concepts_by_file[normalized_file]]
        )

    print("------------")
    print(concepts_by_file)
    print("------------")

    # Générer le fichier CSV avec tous les concepts
    all_concepts = keys_file1.union(keys_file2)
    generate_matrix(concepts_by_file, all_concepts, keys_file1, json1)


def generate_matrix(concepts_by_file, all_concepts, keys_file1=None, json1=None, filename=f"./results_matrix/{project_to_analyse}.csv"):
    FOCUS_ON_MAXIME = False
    sorted_concepts = sorted(keys_file1 if FOCUS_ON_MAXIME else all_concepts)

    # Normaliser les chemins des fichiers de json1
    files_of_json1 = {normalize_path(file) for key in keys_file1 for file in json1[key]}

    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["Fichier", "is_db_file", "is_not_db_file"] + sorted_concepts)

        for file_name, concepts in concepts_by_file.items():
            is_db_file = normalize_path(file_name) in files_of_json1
            row = [("db|" if is_db_file else "") + file_name, is_db_file, not is_db_file]

            row.extend((concept in concepts and (not FOCUS_ON_MAXIME or concept in keys_file1)) for concept in sorted_concepts)
            writer.writerow(row)


# def main_generate_FCA():
#     # Charger le fichier CSV
#     context = concepts.Context.fromfile(f"./results_matrix/{project_to_analyse}.csv", "csv", encoding="utf-8")

#     # Générer et afficher le treillis conceptuel
#     lattice = context.lattice
#     graph = lattice.graphviz()

#     # Augmenter l'espace entre les nœuds
#     graph.attr(dpi="300")  # Augmenter la résolution
#     graph.attr(size="10,10")  # Augmenter la taille globale du graphe
#     graph.attr(ranksep="1.5", nodesep="1.0")  # Espacement entre rangs et nœuds

#     # Générer et afficher
#     graph.view()
#     # graph.render("output_graph", format="png") 





def main_generate_FCA():
    K = FormalContext.from_pandas(pd.read_csv(f"./results_matrix/{project_to_analyse}.csv", index_col=0))
    L = ConceptLattice.from_context(K)

    # Coloring
    ms_color = ('is_db_file', 'is_not_db_file')

    L_nolives = deepcopy(L)


    top_concepts = [concept for concept in L_nolives if len(concept.intent) == 0]

    # Drop the concepts that describe only the colourin
    for c in L:


        if c in top_concepts:
            continue
        
        if set(c.intent)-set(ms_color)==set(top_concepts[0].intent):
            L_nolives.remove(c)

            

    def node_clr_label_func(c_i, L, ms_color=ms_color):
        lbl = LineVizNx.concept_lattice_label_func(c_i, L, flg_new_extent_count_prefix=False, flg_new_intent_count_prefix=False)
        for s in ms_color:
            lbl = lbl.replace(s, '')
        lbl = lbl.replace(',', '')
        return lbl

    viz = LineVizNx(node_label_font_size=14)

    clr_map = {frozenset(ms_color): viz.node_color, frozenset({ms_color[0]}): 'navy', frozenset({ms_color[1]}): 'orange'}
    node_color_legend = {
        clr_map[frozenset({ms_color[1]})]: 'Related to NON DB file only',
        clr_map[frozenset({ms_color[0]})]: 'Related to DB file only',
        clr_map[frozenset(ms_color)]: 'Related to both'
    }


    node_color = [clr_map.get(frozenset(c.intent)&frozenset(ms_color), viz.node_color) for c in L_nolives]

    print([frozenset(c.intent)&frozenset(ms_color) for c in L_nolives])

    
    fig, ax = plt.subplots(figsize=(15, 7))
    viz.draw_concept_lattice(
        L_nolives, ax=ax,
        flg_drop_bottom_concept=True,
        node_color=node_color,
        node_color_legend=node_color_legend,
        node_label_func=node_clr_label_func,
    )

    leg = plt.legend(title='Color coding', title_fontproperties={'size': '12',}, fontsize=10, loc='upper right')
    leg._legend_box.align = "left"

    plt.title('"Concept location lattice"', size=24)
    plt.tight_layout()
    plt.show()



main()