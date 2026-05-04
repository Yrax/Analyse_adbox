from google.cloud import vision

# Crée un client Vision
client = vision.ImageAnnotatorClient()

# Charge l'image à analyser
with open("adbox-images/2049701.jpg", "rb") as image_file:
    content = image_file.read()

image = vision.Image(content=content)

# Appelle l'API pour détecter du texte
response = client.document_text_detection(image=image)

# Récupère le texte détecté
texts = response.full_text_annotation

checkMention = False
mentionPositionY = [-1, -1, -1, -1]
if texts:
    print("Texte détecté :")
    cpt = 1
    
    for block in texts.pages[0].blocks:
        print(block)
        # for paragraph in block.paragraphs:
        #     for word in paragraph.words:
        #         if "L'ABUS" in word.description:
        #             checkMention = True
        #             checkDirection = True
        #             mentionPositionY[0] = texts[cpt].bounding_poly.vertices[0].y
        #             mentionPositionY[1] = texts[cpt].bounding_poly.vertices[1].y
        #             mentionPositionY[2] = texts[cpt].bounding_poly.vertices[2].y
        #             mentionPositionY[3] = texts[cpt].bounding_poly.vertices[3].y
        #         if (
        #             mentionPositionY[0] != texts[cpt].bounding_poly.vertices[0].y 
        #             or mentionPositionY[1] != texts[cpt].bounding_poly.vertices[1].y 
        #             or mentionPositionY[2] != texts[cpt].bounding_poly.vertices[2].y 
        #             or mentionPositionY[3] != texts[cpt].bounding_poly.vertices[3].y
        #         ):
        #             checkDirection = False
        #         if checkMention:
        #             print(mot.description)
        #             print(checkDirection)
        #             print(mot.bounding_poly)
        #             print("*****************************")
        #         if "MODÉRATION" in mot.description:
        #             checkMention = False
        #         cpt += 1
else:
    print("Aucun texte trouvé.")

# Vérifie s'il y a eu des erreurs
if response.error.message:
    raise Exception(response.error.message)



# from google.cloud import vision

def print_methods_and_attributes(obj, depth=0, max_depth=2):
    """
    Affiche récursivement les méthodes et attributs d'un objet, jusqu'à un certain niveau de profondeur.
    """
    indent = '  ' * depth
    if depth > max_depth:
        return

    for attr in dir(obj):
        if attr.startswith("_"):
            continue
        try:
            value = getattr(obj, attr)
            if callable(value):
                print(f"{indent}- Méthode: {attr}()")
            else:
                print(f"{indent}- Attribut: {attr} -> {type(value).__name__}")
                # Récurse sur les sous-objets complexes (ex: Page, Block...)
                if hasattr(value, '__dict__') or isinstance(value, list):
                    print_methods_and_attributes(value, depth + 1, max_depth)
        except Exception as e:
            print(f"{indent}- {attr}: erreur ({e})")


def analyze_image(image_path):
    client = vision.ImageAnnotatorClient()

    with open(image_path, "rb") as image_file:
        content = image_file.read()

    image = vision.Image(content=content)

    response = client.document_text_detection(image=image)
    annotation = response.full_text_annotation

    print("Contenu de full_text_annotation :")
    print(f"Texte complet détecté :\n{annotation.text}\n")

    print("Structure de full_text_annotation :")
    print_methods_and_attributes(annotation)

    if response.error.message:
        raise Exception(f"Erreur de l'API Vision: {response.error.message}")

# Appel de la fonction avec ton image
# analyze_image("adbox-images/2664842.jpg")
